import sys
import unittest
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from news_reporter.models import NewsItem
from news_reporter.intelligence import analyze, inspect_item
from news_reporter.summarizer import Summarizer
from news_reporter.report import ReportComposer


def item(title, body='', region='Brasil', url='https://example.org/a', score=80):
    return NewsItem(source_id='test', source_name='Fonte de teste', title=title,
                    subtitle=None, url=url, published_at=datetime(2026, 10, 19, tzinfo=timezone.utc),
                    collected_at=datetime(2026, 10, 20, tzinfo=timezone.utc), raw_language='pt',
                    description=body, content=body, image_url=None, region=region, score=score,
                    normalized_text=title + '. ' + body, translated_title_pt=title)


class IntelligenceTests(unittest.TestCase):
    def test_empty_has_no_invented_thesis(self):
        result = analyze([], ['Brasil'])
        self.assertEqual(result['signals'], [])
        self.assertFalse(result['connector']['supported'])
        self.assertIn('insuficiente', result['executive_summary'].lower())

    def test_procurement_is_signal_not_confirmed_sale(self):
        signal = inspect_item(item('Publicado edital de licitação de manutenção predial',
                                   'O município abriu licitação para contratar serviços de manutenção.'))
        self.assertEqual(signal['stage'], 'Contratação aberta')
        self.assertIn('Verificar', signal['action'])
        self.assertIn('hipótese', signal['implication'].lower())
        self.assertEqual(signal['evidence'][0]['url'], 'https://example.org/a')

    def test_conditional_cannot_be_open_procurement(self):
        signal = inspect_item(item('Prefeitura poderá abrir licitação de manutenção'))
        self.assertNotEqual(signal['stage'], 'Contratação aberta')
        self.assertIn('condicional', ' '.join(signal['gaps']).lower())

    def test_negation_cannot_be_open_procurement(self):
        signal = inspect_item(item('Prefeitura não abriu licitação de manutenção'))
        self.assertNotEqual(signal['stage'], 'Contratação aberta')

    def test_cancelled_overrides_procurement(self):
        signal = inspect_item(item('Licitação de manutenção foi cancelada'))
        self.assertEqual(signal['stage'], 'Suspenso/cancelado')
        self.assertIn('cancel', signal['risk'].lower())

    def test_risk_does_not_depend_on_relevance_score(self):
        self.assertEqual(inspect_item(item('Inauguração de hospital', score=10))['risk'],
                         inspect_item(item('Inauguração de hospital', score=99))['risk'])

    def test_sparse_input_warns_and_avoids_strong_evidence(self):
        signal = inspect_item(item('Novo investimento'))
        self.assertEqual(signal['evidence_quality'], 'Limitada')
        self.assertTrue(signal['gaps'])

    def test_long_headline_repeated_in_feed_is_still_limited(self):
        title = ('Portugal atingiu em 2025 a meta de investimento de 2% do PIB na defesa. '
                 'O investimento só por si significa pouco; quem não evolui perde no campo de batalha.')
        signal = inspect_item(item(title, title + ' Fonte agregadora de notícias'))
        self.assertEqual(signal['evidence_quality'], 'Limitada')

    def test_duplicate_urls_do_not_create_connection(self):
        a = item('Publicado edital de licitação de manutenção predial')
        result = analyze([a, a], ['Brasil'])
        self.assertEqual(len(result['signals']), 1)
        self.assertFalse(result['connector']['supported'])

    def test_shared_qualified_signal_connects_with_sources(self):
        a = item('Publicado edital de licitação de manutenção predial', url='https://example.org/a')
        b = item('Aberta licitação de manutenção hospitalar', region='Portugal', url='https://example.org/b')
        result = analyze([a, b], ['Brasil', 'Portugal'])
        self.assertTrue(result['connector']['supported'])
        self.assertEqual(len(result['connector']['evidence']), 2)
        self.assertIn('hipótese', result['connector']['center'].lower())

    def test_unrelated_events_do_not_force_connection(self):
        result = analyze([item('Festival cultural na cidade'),
                          item('Campeonato de xadrez', url='https://example.org/b')])
        self.assertFalse(result['connector']['supported'])

    def test_comparative_matrix_contains_evidence_and_action(self):
        result = analyze([item('Empresa anuncia construção de hospital')], ['Brasil', 'Angola'])
        row = result['comparative_rows'][0]
        self.assertTrue(row['evidence'])
        self.assertTrue(row['action'])
        self.assertEqual(result['uncovered_regions'], ['Angola'])

    def test_no_claim_of_acceleration_without_history(self):
        result = analyze([item('Empresa anuncia construção de hospital')])
        self.assertNotIn('aceleração', result['executive_summary'].lower())
        self.assertIn('histórico', ' '.join(result['attention']).lower())

    def test_weekly_summary_is_dynamic_and_legacy_is_available(self):
        summarizer = Summarizer.__new__(Summarizer)
        news = [item('Publicado edital de licitação de manutenção predial')]
        enhanced = summarizer.weekly_synthesis(news, ['Brasil'])
        legacy = summarizer.weekly_synthesis(news, ['Brasil'], analysis_mode='legacy')
        self.assertIn('Contratação aberta', enhanced['executive_summary'])
        self.assertIn('analysis', enhanced)
        self.assertNotIn('analysis', legacy)

    def test_render_has_evidence_matrix_connector_and_safe_markup(self):
        news = [item('Publicado edital de licitação de manutenção predial <script>alert(1)</script>')]
        summary = Summarizer.__new__(Summarizer).weekly_synthesis(news, ['Brasil'])
        templates = Path(__file__).resolve().parents[1] / 'src/news_reporter/templates'
        with tempfile.TemporaryDirectory() as folder:
            composer = ReportComposer(str(templates), include_images=False)
            markup, text, path = composer.compose(news, summary, 'Teste', datetime.now(timezone.utc), folder)
            self.assertIn('Evidência e estágio', markup)
            self.assertIn('Próximo passo', markup)
            self.assertIn('https://example.org/a', markup)
            self.assertNotIn('<script>alert(1)</script>', markup)
            self.assertIn('Matriz comparativa', text)
            self.assertIn('Eixo conector', text)
            self.assertTrue(Path(path).exists())

    def test_legacy_template_keeps_original_matrix(self):
        news = [item('Evento econômico')]
        summary = Summarizer.__new__(Summarizer).weekly_synthesis(news, ['Brasil'], analysis_mode='legacy')
        templates = Path(__file__).resolve().parents[1] / 'src/news_reporter/templates'
        with tempfile.TemporaryDirectory() as folder:
            markup, _, _ = ReportComposer(str(templates), analysis_mode='legacy').compose(
                news, summary, 'Legado', datetime.now(timezone.utc), folder)
            self.assertIn('Vetor de Oportunidade', markup)
            self.assertNotIn('Evidência e estágio', markup)

    def test_unsafe_source_url_is_not_rendered_as_analysis_link(self):
        signal = inspect_item(item('Novo investimento', url='javascript:alert(1)'))
        self.assertEqual(signal['evidence'][0]['url'], '')

    def test_negative_expansion_does_not_create_a_signal_or_axis(self):
        news = [item('Hospital segue sem expansão'), item('Fábrica não terá construção', url='https://example.org/b')]
        result = analyze(news)
        self.assertFalse(result['connector']['supported'])
        self.assertTrue(all(not s['signal_types'] for s in result['signals']))

    def test_future_procurement_is_not_already_open(self):
        signal = inspect_item(item('Edital de manutenção será publicado em novembro'))
        self.assertNotEqual(signal['stage'], 'Contratação aberta')
        self.assertNotIn('services_procurement', signal['signal_types'])

    def test_reflexive_se_does_not_negate_open_procurement(self):
        signal = inspect_item(item('Abriu-se licitação de manutenção do hospital'))
        self.assertEqual(signal['stage'], 'Contratação aberta')

    def test_repeated_headline_does_not_create_false_connection(self):
        a = item('Publicado edital de licitação de manutenção predial')
        b = item(a.title, url='https://example.net/republicado')
        self.assertFalse(analyze([a, b])['connector']['supported'])

    def test_preventive_language_is_not_an_actual_delay(self):
        signal = inspect_item(item('Para evitar atrasos, o hospital iniciou a expansão.'))
        self.assertNotIn('Sinal explícito', signal['risk'])

    def test_all_themes_and_empty_reports_keep_core_sections(self):
        templates = Path(__file__).resolve().parents[1] / 'src/news_reporter/templates'
        for theme in ('light', 'dark_exec', 'boardroom_print'):
            for news in ([], [item('Publicado edital de licitação de manutenção predial')]):
                with self.subTest(theme=theme, empty=not news), tempfile.TemporaryDirectory() as folder:
                    markup, text, _ = ReportComposer(str(templates), include_images=False).compose(
                        news, {}, 'Teste', datetime.now(timezone.utc), folder, theme, ['Brasil'])
                    self.assertIn('Notícias Curadas', markup)
                    self.assertIn('Eixo conector', text)
                    self.assertNotIn('<img', markup)

    def test_normal_report_keeps_feed_image_and_fallback(self):
        templates = Path(__file__).resolve().parents[1] / 'src/news_reporter/templates'
        for image in ('https://example.org/feed-image.jpg', None):
            news = item('Publicado edital de licitação de manutenção predial')
            news.image_url = image
            with self.subTest(image=image), tempfile.TemporaryDirectory() as folder:
                markup, _, _ = ReportComposer(str(templates), include_images=True).compose(
                    [news], {}, 'Teste', datetime.now(timezone.utc), folder)
                self.assertIn('<img', markup)
                self.assertIn(image or 'https://picsum.photos/seed/', markup)

    def test_http_response_identifies_installed_analysis_version(self):
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.request import urlopen
        from embedded_webapp import make_handler
        with patch('embedded_webapp.render_page', return_value='<html>ok</html>'):
            with ThreadingHTTPServer(('127.0.0.1', 0), make_handler(object())) as server:
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    with urlopen(f'http://127.0.0.1:{server.server_port}/', timeout=5) as response:
                        self.assertEqual(response.headers.get('X-Nexus-Analysis-Version'), 'rules-v2')
                        self.assertEqual(response.read(), b'<html>ok</html>')
                finally:
                    server.shutdown()
                    thread.join(timeout=5)

    def test_pipeline_facade_end_to_end_without_external_writes(self):
        from news_reporter.config import AppConfig
        from news_reporter.pipeline import WeeklyReporterPipeline
        from nexus_like.pipeline import NexusCompatiblePipeline
        with tempfile.TemporaryDirectory() as folder:
            cfg = AppConfig({'project': {'include_images': False},
                'monitoring': {'regions': ['Brasil']},
                'filters': {'time_window_days': 3660, 'min_text_length': 10},
                'runtime': {'output_dir': folder, 'keep_execution_history': False}})
            news = [item('Publicado edital de licitação de manutenção predial no Brasil',
                         'O município abriu licitação de manutenção predial no Brasil.')]
            progress = []
            with patch.object(WeeklyReporterPipeline, '_collect_all', return_value=(news, [])), \
                 patch('news_reporter.summarizer.ReportTranslator'), \
                 patch('news_reporter.pipeline.save_report_snapshot') as save, \
                 patch('news_reporter.pipeline.fetch_market_snapshot', return_value=[]):
                result = NexusCompatiblePipeline(cfg, {}, lambda message, percent: progress.append(percent)).run()
            self.assertEqual(result.counters.approved, 1)
            self.assertEqual(progress, [5, 100])
            self.assertIn('Contratação aberta', result.report_html)
            self.assertIn('Matriz comparativa', result.report_text)
            self.assertTrue(Path(result.report_path_html).exists())
            save.assert_called_once()


if __name__ == '__main__':
    unittest.main()

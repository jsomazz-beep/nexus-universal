import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from test_intelligence import item
from news_reporter.models import NewsItem
from news_reporter.summarizer import Summarizer
from news_reporter.intelligence import analyze, inspect_item


class TranslationAndContextTests(unittest.TestCase):
    def test_sentence_split_preserves_decimal_amounts(self):
        self.assertEqual(Summarizer._split_sentences('Investment is US$2.5bn. Work begins soon.'),
                         ['Investment is US$2.5bn', 'Work begins soon'])
    def test_english_content_is_translated_and_preserved_separately(self):
        news = item('Dubai completes public facilities', 'Dubai completes public facilities')
        news.normalized_language = 'en'
        translator = Summarizer.__new__(Summarizer)
        translator._translator = Mock()
        translator._translator.translate.return_value = 'Dubai conclui instalações públicas'
        translator.summarize([news])
        self.assertEqual(news.translation_status, 'translated')
        self.assertEqual(news.translated_content_pt, 'Dubai conclui instalações públicas')
        self.assertEqual(news.content, 'Dubai completes public facilities')
        self.assertEqual(translator._translator.translate.call_count, 1)

    def test_portuguese_does_not_consume_translation_requests(self):
        news = item('Hospital entrega obras de manutenção')
        news.normalized_language = 'pt'
        translator = Summarizer.__new__(Summarizer)
        translator._translator = Mock()
        translator.summarize([news])
        translator._translator.translate.assert_not_called()
        self.assertEqual(news.translation_status, 'original_pt')

    def test_translation_failure_is_exposed_to_analysis(self):
        news = item('Dubai completes public facilities')
        news.normalized_language = 'en'
        translator = Summarizer.__new__(Summarizer)
        translator._translator = Mock()
        translator._translator.translate.side_effect = RuntimeError('test outage')
        translator.summarize([news])
        self.assertEqual(news.translation_status, 'failed')
        self.assertTrue(any('tradução' in v.lower() for v in analyze([news])['attention']))

    def test_matrix_uses_portuguese_evidence_and_preserves_original(self):
        news = item('Dubai completes public facilities')
        news.translated_title_pt = 'Dubai conclui instalações públicas'
        news.translated_content_pt = 'Dubai conclui instalações públicas'
        news.translation_status = 'translated'
        signal = inspect_item(news)
        self.assertIn('conclui', signal['evidence'][0]['excerpt'])
        self.assertIn('completes', signal['evidence'][0]['original_excerpt'])

    def test_real_topics_have_different_specific_questions(self):
        fleet = inspect_item(item('Investimento de 50 milhões de euros numa frota de veículos elétricos e numa rede de carregamento em Portugal'))
        ports = inspect_item(item('Portos portugueses com investimento de quatro mil milhões na próxima década'))
        sanitation = inspect_item(item('Setor de saneamento cobra dados mais confiáveis para cumprir metas de universalização'))
        self.assertEqual(fleet['topic'], 'Frota e recarga')
        self.assertIn('50 milhões de euros', fleet['quantities'])
        self.assertNotEqual(fleet['implication'], ports['implication'])
        self.assertNotEqual(ports['action'], sanitation['action'])
        self.assertIn('recarga', fleet['action'].lower())
        self.assertIn('port', ports['action'].lower())
        self.assertIn('saneamento', sanitation['action'].lower())

    def test_completed_english_projects_are_not_generic_unknown(self):
        row = inspect_item(item('Dubai completes more than 107 projects worth $436m across beaches, parks and public facilities'))
        self.assertEqual(row['stage'], 'Entrega/conclusão citada')
        self.assertIn('asset_operation', row['signal_types'])

    def test_unknown_item_is_not_repeated_as_a_generic_matrix_row(self):
        result = analyze([item('Festival de xadrez na cidade')])
        self.assertEqual(result['comparative_rows'], [])
        self.assertEqual(len(result['matrix_excluded']), 1)

    def test_negative_fleet_investment_is_not_a_positive_signal(self):
        row = inspect_item(item('Empresa não fará investimento de 50 milhões em frota elétrica'))
        self.assertFalse(row['signal_types'])

    def test_numeric_reference_uses_original_not_translated_currency(self):
        news = item('Jordan launches US$2.5bn mining railway project')
        news.translated_title_pt = 'Jordânia lança projeto ferroviário de mineração de US$2,5 bilhões'
        news.translated_content_pt = news.translated_title_pt
        news.translation_status = 'translated'
        self.assertIn('US$2.5bn', inspect_item(news)['quantities'])

    def test_currency_magnitude_is_never_truncated(self):
        for value in ('R$ 1 bilhão', 'R$ 1 milhão', 'US$ 1 trillion', 'R$ 1 trilhão'):
            with self.subTest(value=value):
                self.assertIn(value, inspect_item(item(f'Investimento de {value} em portos'))['quantities'])
        self.assertEqual(inspect_item(item('Investimento de R$ 1 quadrilhão em portos'))['quantities'], [])

    def test_completed_study_or_course_is_not_an_operational_asset(self):
        news = [item('Ministério conclui estudo sobre energia solar'),
                item('Universidade conclui curso de energia', url='https://example.org/b')]
        result = analyze(news)
        self.assertFalse(result['connector']['supported'])
        self.assertTrue(all('asset_operation' not in s['signal_types'] for s in result['signals']))

    def test_neutral_title_does_not_override_negated_investment_body(self):
        row = inspect_item(item('Empresa revisa estratégia de frota', 'Não haverá investimento em recarga'))
        self.assertNotEqual(row['stage'], 'Investimento citado; fase a confirmar')
        self.assertNotIn('investimento/anúncio pode afetar', row['implication'])

    def test_rss_preserves_feed_id_but_uses_reported_publisher(self):
        import feedparser
        from news_reporter.collectors.rss_collector import RSSCollector
        parsed = feedparser.parse(b'<rss version="2.0"><channel><title>Search - Google News</title><item><title>News</title><link>https://example.org/a</link><source url="https://publisher.example">Publisher</source></item></channel></rss>')
        with patch('news_reporter.collectors.rss_collector.feedparser.parse', return_value=parsed):
            news = RSSCollector({'id':'configured_feed','url':'https://example.org/rss'}, {}, {}).collect()[0]
        self.assertEqual(news.source_id, 'configured_feed')
        self.assertEqual(news.source_name, 'Publisher')
        self.assertEqual(news.metadata['feed_name'], 'Search - Google News')

    def test_json_translator_has_timeout_and_can_fall_back(self):
        from news_reporter.translation import ReportTranslator
        fallback = Mock()
        fallback.translate.return_value = 'Tradução de contingência'
        response = Mock(status_code=429)
        with patch('news_reporter.translation.requests.get', return_value=response) as get:
            self.assertEqual(ReportTranslator(fallback=fallback).translate('Public facilities are completed'),
                             'Tradução de contingência')
        self.assertIn('timeout', get.call_args.kwargs)


if __name__ == '__main__':
    unittest.main()

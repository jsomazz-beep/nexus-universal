import sys
sys.path.insert(0, 'src')

from nexus.config import load_config
from nexus.models import NewsItem
from nexus.pipeline import NexusPipeline
from nexus.collectors import build_collector
from nexus.normalizer import Normalizer
from nexus.filters import FilterEngine
from nexus.deduplicator import Deduplicator
from nexus.classifier import TopicClassifier, OpportunityDetector
from nexus.scoring import Scorer
from nexus.summarizer import Summarizer
from nexus.report import ReportComposer

print("ALL IMPORTS OK")

cfg = load_config("config/config.yaml")
regions = cfg.monitoring.get("regions", [])
print(f"Sources : {len(cfg.sources)}")
print(f"Topics  : {len(cfg.topics)}")
print(f"Regions : {regions}")

# Quick pipeline smoke test with 0 sources
from nexus.config import AppConfig
import copy
raw = copy.deepcopy(cfg.raw)
raw["sources"] = []  # no network calls
raw["project"]["max_news"] = 5
test_cfg = AppConfig(raw=raw)

pipeline = NexusPipeline(test_cfg, {})
result = pipeline.run()
print(f"Pipeline OK — approved={result.counters.approved}, report={result.report_path_html}")
print("SMOKE TEST PASSED")

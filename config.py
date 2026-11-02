import yaml
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')

def load_config(config_path=None):
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

config_data = load_config()
KEYWORDS = config_data.get('keywords', {})
PUBLIC_GOV_SOURCES = config_data.get('public_gov_sources', [])
DYNAMIC_CONFIG_SEED = config_data.get('dynamic_config_registry', [])

# 언어별 Dict 유지 (collector 용)
INDUSTRY_KEYWORDS_DICT = KEYWORDS.get('industry', {})
SIGNAL_KEYWORDS_DICT = KEYWORDS.get('deal_signal', {})
FINANCIAL_KEYWORDS_DICT = KEYWORDS.get('profitability_revenue', {})

# 모든 언어 통합 Set 생성 (analyzer 용)
def flatten_keywords(kw_dict):
    result = set()
    if isinstance(kw_dict, dict):
        for lang, words in kw_dict.items():
            result.update(words)
    elif isinstance(kw_dict, list):
        result.update(kw_dict)
    return result

INDUSTRY_KEYWORDS = flatten_keywords(INDUSTRY_KEYWORDS_DICT)
SIGNAL_KEYWORDS = flatten_keywords(SIGNAL_KEYWORDS_DICT)
FINANCIAL_KEYWORDS = flatten_keywords(FINANCIAL_KEYWORDS_DICT)

def get_dynamic_registry_seed():
    """동적 설정 레지스트리(법령·세무·벤처제도 파라미터) 최신 YAML 시드 반환"""
    fresh = load_config()
    return fresh.get('dynamic_config_registry', [])

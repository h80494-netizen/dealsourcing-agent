import yaml
import os

def load_config(config_path='config.yaml'):
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config_data = load_config()
KEYWORDS = config_data.get('keywords', {})

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


import os
import csv
import re
from typing import Dict, List, Any, Optional

class IndustryManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(IndustryManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, csv_path: Optional[str] = None):
        if self._initialized:
            return
        
        self.csv_path = self._resolve_csv_path(csv_path)
        self.rows: List[Dict[str, Any]] = []
        self.hierarchy: Dict[str, Dict[str, Any]] = {}
        self.code_map: Dict[str, Dict[str, Any]] = {}
        self.minor_map: Dict[str, Dict[str, Any]] = {}
        
        self._load_data()
        self._initialized = True

    def _resolve_csv_path(self, custom_path: Optional[str]) -> str:
        candidates = []
        if custom_path:
            candidates.append(custom_path)
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.extend([
            os.path.join(base_dir, 'data', 'vc_industry.csv'),
            os.path.join(base_dir, '..', 'data', 'vc_industry.csv'),
            os.path.join(base_dir, '..', 'db', 'vc_industry.csv'),
            os.path.join(base_dir, 'db', 'vc_industry.csv'),
            r"c:\Users\llll\Documents\두인경매\벤처캐피탈\data\vc_industry.csv"
        ])
        
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]

    def _clean_keywords(self, raw_str: str) -> List[str]:
        if not raw_str or not isinstance(raw_str, str):
            return []
        # 1. 쉼표, 세미콜론 등으로 1차 분리
        tokens = re.split(r'[,;\n·]', raw_str)
        cleaned = []
        for t in tokens:
            t = t.strip().strip('"').strip("'")
            if not t:
                continue
            cleaned.append(t)
            
            # 괄호 안팎 분리 (예: "자율주행(센서/라이다/SW)" -> "자율주행", "센서", "라이다", "SW")
            sub_matches = re.findall(r'\((.*?)\)', t)
            main_val = re.sub(r'\(.*?\)', '', t).strip()
            if main_val and main_val != t:
                cleaned.append(main_val)
                # 메인 텍스트 내 슬래시가 있으면 슬래시도 분리
                for mv in main_val.split('/'):
                    if mv.strip(): cleaned.append(mv.strip())

            for sub in sub_matches:
                for sub_token in re.split(r'[/,·]', sub):
                    st = sub_token.strip()
                    if st:
                        cleaned.append(st)
                        
            # 슬래시 분리 (예: "STT/TTS" -> "STT", "TTS")
            if '/' in t and not sub_matches:
                for slash_token in t.split('/'):
                    st = slash_token.strip()
                    if st:
                        cleaned.append(st)

        return list(dict.fromkeys([c for c in cleaned if len(c) >= 2]))

    def _load_data(self):
        if not os.path.exists(self.csv_path):
            print(f"[IndustryManager] Warning: CSV not found at {self.csv_path}")
            return

        with open(self.csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for r in reader:
                code = r.get('분류코드(Code)', '').strip()
                major = r.get('대분류(Major)', '').strip()
                ind_type = r.get('산업구분(Type)', '').strip()
                middle = r.get('중분류(Middle)', '').strip()
                minor = r.get('소분류_한국어표준(Minor_KR)', '').strip()
                
                kw_kr = self._clean_keywords(r.get('세부키워드_한국어(Keywords_KR)', ''))
                kw_en = self._clean_keywords(r.get('영어_키워드(Keywords_EN)', ''))
                kw_zh = self._clean_keywords(r.get('중국어_키워드(Keywords_ZH)', ''))
                kw_ja = self._clean_keywords(r.get('일본어_키워드(Keywords_JA)', ''))
                kw_de = self._clean_keywords(r.get('독일어_키워드(Keywords_DE)', ''))
                kw_fr = self._clean_keywords(r.get('프랑스어_키워드(Keywords_FR)', ''))
                
                # 모든 키워드 통합 목록
                all_kws = list(dict.fromkeys(kw_kr + kw_en + kw_zh + kw_ja + kw_de + kw_fr))
                # 소분류명과 중분류명 자체도 매칭 키워드로 추가
                all_kws.append(minor)
                clean_minor = re.sub(r'\(.*?\)', '', minor).strip()
                if clean_minor and clean_minor != minor:
                    all_kws.append(clean_minor)

                item = {
                    'code': code,
                    'major': major,
                    'type': ind_type,
                    'middle': middle,
                    'minor': minor,
                    'formatted': f"{major} > {middle} > {minor}",
                    'keywords_kr': kw_kr,
                    'keywords_en': kw_en,
                    'keywords_zh': kw_zh,
                    'keywords_ja': kw_ja,
                    'keywords_de': kw_de,
                    'keywords_fr': kw_fr,
                    'all_keywords': all_kws
                }
                
                self.rows.append(item)
                self.code_map[code] = item
                self.minor_map[minor] = item
                
                # Build hierarchy
                if major not in self.hierarchy:
                    self.hierarchy[major] = {}
                if middle not in self.hierarchy[major]:
                    self.hierarchy[major][middle] = []
                self.hierarchy[major][middle].append({
                    'code': code,
                    'type': ind_type,
                    'minor': minor,
                    'formatted': item['formatted'],
                    'keywords_count': len(all_kws)
                })

    def get_hierarchy(self) -> Dict[str, Any]:
        """대분류 > 중분류 > 소분류 트리 구조 반환"""
        return self.hierarchy

    def get_all_rows(self) -> List[Dict[str, Any]]:
        """42개 소분류 전체 항목 반환"""
        return self.rows

    def get_all_keywords(self) -> List[str]:
        """모든 6개 국어 키워드 고유 리스트 반환"""
        kws = set()
        for r in self.rows:
            kws.update(r['all_keywords'])
        return sorted(list(kws))

    def classify_keyword(self, keyword: str) -> Dict[str, Any]:
        """
        단일 키워드(예: '양자컴퓨팅', 'LLM', '자율주행')에 대해 가장 알맞은 대분류/중분류/소분류 판별
        분류가 애매하거나 일치도가 낮으면 '기타 > 기타/미정 > 기타'로 분류
        """
        kw_clean = keyword.strip().lower()
        if not kw_clean or len(kw_clean) < 2:
            return {
                'major': '기타',
                'middle': '기타/미정',
                'minor': '기타',
                'formatted': '기타 > 기타/미정 > 기타',
                'score': 0
            }

        best_match = None
        best_score = 0

        # 불용어성 조사/접미사 제거 헬퍼
        stem = re.sub(r'(기술|컴퓨팅|시스템|솔루션|플랫폼|서비스|산업|분야)$', '', kw_clean).strip()
        if len(stem) < 2:
            stem = kw_clean

        for r in self.rows:
            score = 0
            minor_lower = r['minor'].lower()
            middle_lower = r['middle'].lower()
            major_lower = r['major'].lower()

            # 1. 완전 일치
            if kw_clean == minor_lower:
                score += 30
            elif kw_clean in minor_lower or minor_lower in kw_clean:
                score += 20
            elif stem and (stem in minor_lower):
                score += 15

            # 2. 키워드 목록 매칭
            for k in r['all_keywords']:
                k_lower = k.lower()
                if kw_clean == k_lower:
                    score += 25
                    break
                
                # 라틴/알파벳 단어는 부분 매칭 방지 (예: SMR에 MR이 부분 매칭되는 것 방지)
                is_latin = re.match(r'^[a-zA-Z0-9\-_ ]+$', kw_clean) and re.match(r'^[a-zA-Z0-9\-_ ]+$', k_lower)
                if is_latin:
                    if re.search(r'\b' + re.escape(kw_clean) + r'\b', k_lower) or re.search(r'\b' + re.escape(k_lower) + r'\b', kw_clean):
                        score += 15
                        break
                else:
                    if len(kw_clean) >= 2 and (kw_clean in k_lower or k_lower in kw_clean):
                        score += 12
                        break
                    elif len(stem) >= 2 and (stem in k_lower):
                        score += 10
                        break

            # 3. 중분류/대분류 매칭 보너스
            if kw_clean in middle_lower:
                score += 8
            if kw_clean == major_lower:
                score += 6

            if score > best_score:
                best_score = score
                best_match = r

        # 확실한 매칭 기준 (점수 10점 이상)
        if best_match and best_score >= 10:
            return {
                'major': best_match['major'],
                'middle': best_match['middle'],
                'minor': best_match['minor'],
                'code': best_match['code'],
                'formatted': best_match['formatted'],
                'score': best_score
            }

        # 모호하거나 매칭 점수가 낮은 경우 "기타" 항목으로 따로 명확히 분류
        return {
            'major': '기타',
            'middle': '기타/미정',
            'minor': '기타',
            'formatted': '기타 > 기타/미정 > 기타',
            'score': 0
        }

    def classify_text(self, text: str) -> Dict[str, Any]:
        """
        뉴스 기사 텍스트(제목 + 본문)를 바탕으로 42개 소분류 중 가장 관련도가 높은 분류 판별.
        분류가 애매하거나 불명확한 경우 '기타 > 기타/미정 > 기타' 항목으로 따로 분류.
        """
        default_other = {
            'major': '기타',
            'middle': '기타/미정',
            'minor': '기타',
            'code': 'OT-ETC',
            'type': '기타',
            'formatted': '기타 > 기타/미정 > 기타',
            'matched_keywords': []
        }

        if not text:
            return default_other

        text_lower = text.lower()
        candidates = []

        for r in self.rows:
            matched_kws = []
            score = 0
            
            # 소분류 명칭 매칭 (가장 높은 가중치)
            minor_clean = re.sub(r'\(.*?\)', '', r['minor']).lower().strip()
            if minor_clean and (minor_clean in text_lower):
                score += 20
                matched_kws.append(r['minor'])

            # 6개 국어 키워드 매칭
            for kw in r['all_keywords']:
                kw_str = kw.strip()
                if not kw_str or len(kw_str) < 2:
                    continue
                
                kw_l = kw_str.lower()
                # 알파벳만으로 구성된 단어는 단어 경계(\b) 매칭
                if re.match(r'^[a-zA-Z0-9\-_ ]+$', kw_l):
                    pattern = r'\b' + re.escape(kw_l) + r'\b'
                    if re.search(pattern, text_lower):
                        score += 10
                        matched_kws.append(kw_str)
                else:
                    # 한국어, 중국어, 일본어 등은 포함 여부 매칭
                    if kw_l in text_lower:
                        score += 10
                        matched_kws.append(kw_str)

            if score > 0:
                candidates.append({
                    'row': r,
                    'score': score,
                    'matched_keywords': list(dict.fromkeys(matched_kws))
                })

        if not candidates:
            return default_other

        # 점수 기준 정렬
        candidates.sort(key=lambda x: x['score'], reverse=True)
        top = candidates[0]
        
        # 매칭 점수가 10점 미만(너무 애매하거나 단순 스쳐 지나가는 단어 1개)인 경우 '기타'로 분류
        if top['score'] < 10:
            return default_other

        r = top['row']
        return {
            'major': r['major'],
            'middle': r['middle'],
            'minor': r['minor'],
            'code': r['code'],
            'type': r['type'],
            'formatted': r['formatted'],
            'matched_keywords': top['matched_keywords']
        }

# 싱글톤 인스턴스
industry_manager = IndustryManager()

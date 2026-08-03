import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import init_db, get_session
from database.models import ResearchDomain

def seed_domains():
    engine = init_db()
    session = get_session(engine)
    
    domains = [
    {
      "country": "미국",
      "category": "뉴스/미디어",
      "name": "TechCrunch",
      "url": "https://techcrunch.com",
      "rss_url": "https://techcrunch.com/feed/",
      "purpose": "글로벌 스타트업 투자 유치 및 펀드 조성 소식"
    },
    {
      "country": "미국",
      "category": "뉴스/미디어",
      "name": "The Information",
      "url": "https://theinformation.com",
      "rss_url": None,
      "purpose": "빅테크·AI·VC 미공개 딜 심층 취재"
    },
    {
      "country": "미국",
      "category": "뉴스/미디어",
      "name": "VentureBeat",
      "url": "https://venturebeat.com",
      "rss_url": "https://venturebeat.com/feed/",
      "purpose": "AI, 피지컬 AI, 엔터프라이즈 테크 전문 분석"
    },
    {
      "country": "미국",
      "category": "기업 DB",
      "name": "Crunchbase",
      "url": "https://crunchbase.com",
      "rss_url": None,
      "purpose": "글로벌 스타트업 펀딩, 지분, 딜 내역 DB"
    },
    {
      "country": "미국",
      "category": "기업 DB",
      "name": "PitchBook",
      "url": "https://pitchbook.com",
      "rss_url": "https://pitchbook.com/news/rss",
      "purpose": "VC/PE 펀드, Valuation, Cap Table 전문 DB"
    },
    {
      "country": "미국",
      "category": "기업 DB",
      "name": "CB Insights",
      "url": "https://cbinsights.com",
      "rss_url": "https://www.cbinsights.com/research/feed/",
      "purpose": "유니콘 기업 및 기술 마켓맵 리포트"
    },
    {
      "country": "미국",
      "category": "정부/정책",
      "name": "SEC EDGAR",
      "url": "https://sec.gov/edgar",
      "rss_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=D&company=&datea=&dateb=&owner=include&count=100&output=atom",
      "purpose": "상장신고서(S-1) 및 사모펀드 모집(Form D) 공시"
    },
    {
      "country": "미국",
      "category": "정부/정책",
      "name": "USPTO",
      "url": "https://uspto.gov",
      "rss_url": None,
      "purpose": "미국 특허청 특허 출원/등록 검색"
    },
    {
      "country": "미국",
      "category": "정부/정책",
      "name": "NSF",
      "url": "https://nsf.gov",
      "rss_url": "https://www.nsf.gov/rss/rss_www_news.xml",
      "purpose": "미국 국립과학재단 첨단기술 R&D 지원 현황"
    },
    {
      "country": "한국",
      "category": "뉴스/미디어",
      "name": "플래텀 (Platum)",
      "url": "https://platum.kr",
      "rss_url": "https://platum.kr/feed",
      "purpose": "국내 스타트업 투자 유치 및 데모데이 뉴스"
    },
    {
      "country": "한국",
      "category": "뉴스/미디어",
      "name": "벤처스퀘어",
      "url": "https://venturesquare.net",
      "rss_url": "https://www.venturesquare.net/feed",
      "purpose": "스타트업 및 창업 생태계 전문 매체"
    },
    {
      "country": "한국",
      "category": "뉴스/미디어",
      "name": "아웃스탠딩",
      "url": "https://outstanding.kr",
      "rss_url": "https://outstanding.kr/feed",
      "purpose": "IT/스타트업 트렌드 심층 분석"
    },
    {
      "country": "한국",
      "category": "기업 DB",
      "name": "더브이씨 (THE VC)",
      "url": "https://thevc.kr",
      "rss_url": None,
      "purpose": "국내 스타트업 투자 유치 및 펀드 DB"
    },
    {
      "country": "한국",
      "category": "기업 DB",
      "name": "혁신의숲",
      "url": "https://innoforest.co.kr",
      "rss_url": None,
      "purpose": "트래픽(MAU), 고용, 매출 등 스타트업 성장 데이터"
    },
    {
      "country": "한국",
      "category": "기업 DB",
      "name": "DART",
      "url": "https://dart.fss.or.kr",
      "rss_url": "https://dart.fss.or.kr/api/todayRSS.xml",
      "purpose": "금융감독원 전자공시 (감사보고서, M&A 공시)"
    },
    {
      "country": "한국",
      "category": "정부/정책",
      "name": "K-Startup",
      "url": "https://k-startup.go.kr",
      "rss_url": None,
      "purpose": "중소벤처기업부 공식 창업지원 포털"
    },
    {
      "country": "한국",
      "category": "정부/정책",
      "name": "TIPS 포털",
      "url": "https://jointips.or.kr",
      "rss_url": None,
      "purpose": "민간투자주도형 기술창업지원(TIPS) 선정 기업"
    },
    {
      "country": "한국",
      "category": "정부/정책",
      "name": "한국벤처투자 (KVIC)",
      "url": "https://kvic.or.kr",
      "rss_url": None,
      "purpose": "모태펀드 출자 사업 및 결성 현황"
    },
    {
      "country": "한국",
      "category": "정부/정책",
      "name": "KIPRIS",
      "url": "https://kipris.or.kr",
      "rss_url": None,
      "purpose": "특허청 지식재산권 통합 검색 서비스"
    },
    {
      "country": "한국",
      "category": "정보마당",
      "name": "한국벤처캐피탈협회 (KVCA)",
      "url": "https://www.kvca.or.kr/Program/board/list.html?a_gb=board&a_cd=12&a_item=0&sm=4_3",
      "rss_url": None,
      "purpose": "협회 공지사항 및 벤처 동향"
    },
    {
      "country": "한국",
      "category": "정보마당",
      "name": "벤처기업협회 (KOVA)",
      "url": "https://www.venture.or.kr/home/kor/M899149446/notify/announce/group/index.do",
      "rss_url": None,
      "purpose": "벤처기업협회 사업공고"
    },
    {
      "country": "일본",
      "category": "뉴스/미디어",
      "name": "BRIDGE",
      "url": "https://thebridge.jp",
      "rss_url": "https://thebridge.jp/feed",
      "purpose": "일본 대표 스타트업 & 테크 전문 미디어"
    },
    {
      "country": "일본",
      "category": "뉴스/미디어",
      "name": "PR TIMES",
      "url": "https://prtimes.jp",
      "rss_url": "https://prtimes.jp/index.rdf",
      "purpose": "일본 스타트업 보도자료 및 신제품/투자 공식 발표"
    },
    {
      "country": "일본",
      "category": "기업 DB",
      "name": "INITIAL",
      "url": "https://initial.inc",
      "rss_url": None,
      "purpose": "일본 스타트업 기업가치 및 자금 조달 DB"
    },
    {
      "country": "일본",
      "category": "정부/정책",
      "name": "METI (경제산업성)",
      "url": "https://meti.go.jp",
      "rss_url": "https://www.meti.go.jp/ml_rss/meti_news.xml",
      "purpose": "일본 첨단산업(반도체, AI, 에너지) 지원 정책"
    },
    {
      "country": "일본",
      "category": "정부/정책",
      "name": "NEDO",
      "url": "https://nedo.go.jp",
      "rss_url": "https://www.nedo.go.jp/rss/index.xml",
      "purpose": "딥테크, 피지컬 AI, 수소/배터리 R&D 정부과제"
    },
    {
      "country": "일본",
      "category": "정부/정책",
      "name": "JETRO",
      "url": "https://jetro.go.jp",
      "rss_url": "https://www.jetro.go.jp/rss/biznews.xml",
      "purpose": "일본 무역진흥기구 스타트업 해외진출 정보"
    },
    {
      "country": "중국",
      "category": "뉴스/미디어",
      "name": "36Kr (36氪)",
      "url": "https://36kr.com",
      "rss_url": "https://36kr.com/feed",
      "purpose": "중국 최대 스타트업/VC/테크 미디어"
    },
    {
      "country": "중국",
      "category": "뉴스/미디어",
      "name": "TMTPost (钛媒体)",
      "url": "https://tmtpost.com",
      "rss_url": "https://www.tmtpost.com/rss.xml",
      "purpose": "IT, 반도체, AI, 전기차 등 신산업 전문 분석"
    },
    {
      "country": "중국",
      "category": "기업 DB",
      "name": "ITJuzi (IT桔子)",
      "url": "https://itjuzi.com",
      "rss_url": None,
      "purpose": "중국 스타트업 투자 유치 및 벤처 DB"
    },
    {
      "country": "중국",
      "category": "정부/정책",
      "name": "MIIT (공업정보화부)",
      "url": "https://miit.gov.cn",
      "rss_url": None,
      "purpose": "IT, 반도체, AI, 로봇, 전기차 산업 정책/규제"
    },
    {
      "country": "중국",
      "category": "정부/정책",
      "name": "CAC (인터넷정보판공실)",
      "url": "https://cac.gov.cn",
      "rss_url": None,
      "purpose": "AI 모델 등록 및 데이터 보안 규제 발표"
    },
    {
      "country": "유럽",
      "category": "뉴스/미디어",
      "name": "Sifted",
      "url": "https://sifted.eu",
      "rss_url": "https://sifted.eu/feed",
      "purpose": "FT(Financial Times) 후원 유럽 VC/스타트업 미디어"
    },
    {
      "country": "유럽",
      "category": "뉴스/미디어",
      "name": "Tech.eu",
      "url": "https://tech.eu",
      "rss_url": "https://tech.eu/feed/",
      "purpose": "유럽 스타트업 딜, M&A, 투자 뉴스 전문"
    },
    {
      "country": "유럽",
      "category": "뉴스/미디어",
      "name": "EU-Startups",
      "url": "https://eu-startups.com",
      "rss_url": "https://www.eu-startups.com/feed/",
      "purpose": "유럽 국가별 초기 스타트업 소식 모니터링"
    },
    {
      "country": "유럽",
      "category": "기업 DB",
      "name": "Dealroom",
      "url": "https://dealroom.co",
      "rss_url": "https://dealroom.co/blog/feed",
      "purpose": "유럽 스타트업/유니콘/정부 출자 데이터 플랫폼"
    },
    {
      "country": "유럽",
      "category": "정부/정책",
      "name": "EIC",
      "url": "https://eic.ec.europa.eu",
      "rss_url": None,
      "purpose": "유럽혁신위원회 딥테크/기후테크 투융자 공시"
    }
    ]
    
    count = 0
    updated_count = 0
    for d in domains:
        # 기존 URL 기반으로 체크 (과거 데이터가 스키마 없이 있을 수 있으므로)
        # URL 형태가 조금 다를 수 있으므로 완전 일치 혹은 like 검색 필요할수 있음.
        # 안전하게 새로 추가.
        exists = session.query(ResearchDomain).filter(ResearchDomain.url.like(f"%{d['url'].replace('https://', '')}%")).first()
        if not exists:
            new_d = ResearchDomain(
                name=d.get('name'),
                url=d['url'],
                rss_url=d.get('rss_url'),
                purpose=d.get('purpose'),
                country=d['country'],
                category=d['category']
            )
            session.add(new_d)
            count += 1
        else:
            exists.name = d.get('name')
            exists.url = d['url'] # update with full url
            exists.rss_url = d.get('rss_url')
            exists.purpose = d.get('purpose')
            exists.country = d.get('country')
            exists.category = d.get('category')
            updated_count += 1
            
    session.commit()
    session.close()
    print(f"Successfully added {count} new domains, updated {updated_count} existing domains.")

if __name__ == '__main__':
    seed_domains()

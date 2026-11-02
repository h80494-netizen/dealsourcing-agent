import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models import Base, DynamicConfigRegistry

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_FILE = os.path.join(ROOT_DIR, 'dealsourcing.db')

_schema_migrated = False

def _resolve_db_path(db_path='dealsourcing.db'):
    if db_path == 'dealsourcing.db':
        return DEFAULT_DB_FILE
    return db_path

def get_engine(db_path='dealsourcing.db'):
    resolved = _resolve_db_path(db_path)
    return create_engine(f'sqlite:///{resolved}', echo=False)

def _ensure_migrations_and_registry(engine):
    global _schema_migrated
    if _schema_migrated:
        return
    with engine.connect() as conn:
        # 기존 deal_articles 테이블 컬럼 무중단 확장 (기존 데이터 100% 보존)
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(deal_articles)")).fetchall()]
        if 'source_type' not in cols:
            conn.execute(text("ALTER TABLE deal_articles ADD COLUMN source_type VARCHAR(30) DEFAULT 'private_media'"))
        if 'ministry_name' not in cols:
            conn.execute(text("ALTER TABLE deal_articles ADD COLUMN ministry_name VARCHAR(100)"))
        conn.commit()

    # 동적 설정 레지스트리(법령·세무·벤처제도 파라미터) 초기 시드 동기화
    try:
        from config import get_dynamic_registry_seed
        Session = sessionmaker(bind=engine)
        session = Session()
        seed_items = get_dynamic_registry_seed()
        for item in seed_items:
            exists = session.query(DynamicConfigRegistry).filter_by(config_key=item['config_key']).first()
            if not exists:
                session.add(DynamicConfigRegistry(
                    config_group=item.get('config_group', 'general'),
                    config_key=item['config_key'],
                    config_label=item.get('config_label', item['config_key']),
                    config_value=str(item.get('config_value', '')),
                    unit=item.get('unit', ''),
                    legal_basis=item.get('legal_basis', ''),
                    effective_date=item.get('effective_date', ''),
                    description=item.get('description', '')
                ))
        session.commit()
        session.close()
    except Exception as e:
        print(f"DynamicConfigRegistry sync warning: {e}")

    _schema_migrated = True

def init_db(db_path='dealsourcing.db'):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    _ensure_migrations_and_registry(engine)
    return engine

def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()

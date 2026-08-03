import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database.db_manager import init_db, get_session
from database.models import ResearchDomain

def import_targets():
    with open('targets.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    engine = init_db()
    session = get_session(engine)
    
    added = 0
    for t in data.get('targets', []):
        exists = session.query(ResearchDomain).filter_by(url=t['url']).first()
        if not exists:
            new_domain = ResearchDomain(
                country=t.get('country', ''),
                category=t.get('category', ''),
                name=t.get('name', ''),
                url=t.get('url', ''),
                rss_url=t.get('rss_url'),
                purpose=t.get('purpose', '')
            )
            session.add(new_domain)
            added += 1
            
    session.commit()
    session.close()
    print(f"Successfully imported {added} new domains.")

if __name__ == "__main__":
    import_targets()

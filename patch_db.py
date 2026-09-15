import sqlite3
import os
import sys
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from processor.analyzer import translate_to_korean

DB_PATH = 'dealsourcing.db'

def patch_db():
    if not os.path.exists(DB_PATH):
        print("DB not found.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT id, impact_score, news_grade, title FROM deal_articles")
    rows = c.fetchall()
    
    updated_count = 0
    for row_id, impact_score, current_grade, title in rows:
        score = float(impact_score) if impact_score else 0.0
        if score >= 95:
            new_grade = "S"
        elif score >= 90:
            new_grade = "AAA"
        elif score >= 85:
            new_grade = "AA"
        elif score >= 80:
            new_grade = "A"
        elif score >= 70:
            new_grade = "BBB"
        elif score >= 60:
            new_grade = "BB"
        elif score >= 50:
            new_grade = "B"
        else:
            new_grade = "기타"
            
        new_title = title
        if not re.search(r'[가-힣]', title):
            new_title = translate_to_korean(title)
            
        if current_grade != new_grade or title != new_title:
            c.execute("UPDATE deal_articles SET news_grade = ?, title = ? WHERE id = ?", (new_grade, new_title, row_id))
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully updated {updated_count} rows to the new subdivided grades.")

if __name__ == "__main__":
    patch_db()

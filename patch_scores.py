import sqlite3
import os
import random

DB_PATH = 'dealsourcing.db'

def patch_scores():
    if not os.path.exists(DB_PATH):
        print("DB not found.")
        return
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT id, news_grade, impact_score FROM deal_articles")
    rows = c.fetchall()
    
    updated_count = 0
    for row_id, grade, current_score in rows:
        if current_score is not None:
            new_score = current_score
            if grade == 'S':
                new_score = random.uniform(95.0, 99.9)
            elif grade == 'AAA':
                new_score = random.uniform(90.0, 94.9)
            elif grade == 'AA':
                new_score = random.uniform(85.0, 89.9)
            elif grade == 'A':
                new_score = random.uniform(80.0, 84.9)
            elif grade == 'BBB':
                new_score = random.uniform(70.0, 79.9)
            elif grade == 'BB':
                new_score = random.uniform(60.0, 69.9)
            elif grade == 'B':
                new_score = random.uniform(50.0, 59.9)
            else:
                new_score = random.uniform(10.0, 49.9)
                
            new_score = round(new_score, 1)
            c.execute("UPDATE deal_articles SET impact_score = ? WHERE id = ?", (new_score, row_id))
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully fine-tuned scores for {updated_count} old articles.")

if __name__ == "__main__":
    patch_scores()

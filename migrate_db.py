import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'dealsourcing.db')

def migrate_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns in deal_articles
    cursor.execute("PRAGMA table_info(deal_articles)")
    columns = [row[1] for row in cursor.fetchall()]
    
    cursor.execute("PRAGMA table_info(research_domains)")
    rd_columns = [row[1] for row in cursor.fetchall()]
    
    try:
        if 'compressed_summary' not in columns:
            cursor.execute("ALTER TABLE deal_articles ADD COLUMN compressed_summary TEXT")
            
        if rd_columns and 'name' not in rd_columns:
            cursor.execute("ALTER TABLE research_domains ADD COLUMN name VARCHAR(100)")
            cursor.execute("ALTER TABLE research_domains ADD COLUMN rss_url VARCHAR(500)")
            cursor.execute("ALTER TABLE research_domains ADD COLUMN purpose VARCHAR(200)")
            
        # Create research_domains
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_domains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url VARCHAR(500) UNIQUE,
            country VARCHAR(20),
            category VARCHAR(100),
            is_active BOOLEAN DEFAULT 1
        )
        """)
        
        # Create search_keywords
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword VARCHAR(100) UNIQUE,
            type VARCHAR(20),
            category VARCHAR(50),
            is_active BOOLEAN DEFAULT 1
        )
        """)
        
        conn.commit()
        print("Database migration successful.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_db()

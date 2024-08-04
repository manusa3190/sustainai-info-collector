import sqlite3
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from typing import Optional, List, Type
import json

@dataclass
class Article:
    id: str = ""
    fetch_date: datetime = datetime.now()
    release_date: Optional[datetime] = None
    source: str = ""
    title: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    ai_guess_interest_level: int = 1
    user_scored_interest_level: Optional[int] = None

    def ai_summarize(self):
        self.summary = self.content[:300]

def get_sqlite_type(field_type: Type) -> str:
    type_map = {
        datetime: 'TEXT',
        str: 'TEXT',
        int: 'INTEGER',
        list: 'TEXT',
        type(None): 'TEXT'
    }
    return type_map.get(field_type, 'TEXT')

def setup_database(db_path: str = 'articles.db'):
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()

        article_fields = fields(Article)
        column_definitions = [f"{field.name} {get_sqlite_type(field.type)}" for field in article_fields]

        c.execute(f'''
            CREATE TABLE IF NOT EXISTS articles (
                {", ".join(column_definitions)}
            )
        ''')

def save_to_sqlite(article_list: List[Article], db_path: str = 'articles.db'):
    columns = [field.name for field in fields(Article)]
    placeholders = ", ".join(["?" for _ in columns])
    values_list = []

    for article in article_list:
        values = []
        for col in columns:
            value = getattr(article, col)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, list):
                value = json.dumps(value)  # リストをJSON文字列に変換
            values.append(value)
        values_list.append(values)

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.executemany(f"INSERT INTO articles ({', '.join(columns)}) VALUES ({placeholders})", values_list)

def fetch_recent_articles(db_path: str = 'articles.db', days: int = 7) -> List[Article]:
    now = datetime.now()
    one_week_ago = now - timedelta(days=days)

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT * FROM articles
            WHERE release_date >= ?
        ''', (one_week_ago.isoformat(),))

        rows = c.fetchall()

    articles = []
    for row in rows:
        articles.append(Article(row))

    return articles

# 使用例
if __name__ == "__main__":
    setup_database()
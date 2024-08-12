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

def setup_database(table_name:str):
    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()

        table_fields = fields(Article)
        column_definitions = [f"{field.name} {get_sqlite_type(field.type)}" for field in table_fields]

        c.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {", ".join(column_definitions)}
            )
        ''')

def save_to_sqlite(article_list: List[Article]):
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

    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()
        c.executemany(f"INSERT INTO articles ({', '.join(columns)}) VALUES ({placeholders})", values_list)

def fetch_recent_articles(table_name:str,days: int = 7) -> List[Article]:
    now = datetime.now()
    one_week_ago = now - timedelta(days=days)

    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()
        c.execute(f'''
            SELECT * FROM {table_name}
            WHERE release_date >= ?
        ''', (one_week_ago.isoformat(),))

        rows = c.fetchall()

    articles = []
    for row in rows:
        articles.append(Article(row))

    return articles

def getItems(table_name:str, ids:List[str]):
    placeholder = ', '.join(['?'] * len(ids))
    select_query = f'''
        SELECT * FROM {table_name} WHERE id IN ({placeholder})
    '''

    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()

        c.execute(select_query, ids)
        records = c.fetchall()

        articles = []
        for record in records:
            # レコードをArticleフィールドにマッピング
            article = Article(
                id=record[0],
                fetch_date=datetime.fromisoformat(record[1]),
                release_date=datetime.fromisoformat(record[2]) if record[2] else None,
                source=record[3],
                title=record[4],
                content=record[5],
                keywords=json.loads(record[6]),  # keywordsはリスト型として保存されていると仮定
                summary=record[7],
                ai_guess_interest_level=record[8],
                user_scored_interest_level=record[9]
            )
            articles.append(article)

        return articles

        return articles

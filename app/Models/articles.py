import sqlite3
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from typing import Optional, List, Type, Dict, Any
import json

@dataclass
class Article:
    article_id: str = ""
    acquition_date: datetime = datetime.now()
    publish_date: Optional[datetime] = None
    source: str = ""
    title: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()

def get_sqlite_type(field_type: Type) -> str:
    type_map = {
        datetime: 'TEXT',
        str: 'TEXT',
        int: 'INTEGER',
        list: 'TEXT',
        type(None): 'TEXT'
    }
    return type_map.get(field_type, 'TEXT')


def convert_value(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()  # datetimeをISOフォーマットの文字列に変換
    elif isinstance(value, list):
        return json.dumps(value,ensure_ascii=False)  # リストをJSON形式の文字列に変換
    return value  # その他の型はそのまま返す

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

def getItem(table_name:str,id:str):
    select_query = f'''
        SELECT * FROM {table_name} WHERE id 
    '''

    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()

        c.execute(select_query, ids)
        records = c.fetchall()

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
    

def updateItem(table_name:str, data:Dict[str,str]):
    # 更新するフィールドと対応するプレースホルダーを動的に生成
    fieldNames = ', '.join([f"{key} = ?" for key in data.keys() if key != 'id'])
    
    # クエリの生成 例: UPDATE articles SET keywords = ? WHERE id = ?
    query = f"UPDATE {table_name} SET {fieldNames} WHERE id = ?"
    
    # プレースホルダーに入る値を準備（idは最後に渡す）例: ['["東京湾", "環境一斉調査"]', 'moe01']
    values = [convert_value(value) for key, value in data.items() if key != 'id']
    values.append(data['id'])
    print(values)
    
    # データベースの接続を確立してクエリを実行
    with sqlite3.connect('articles.db') as conn:
        c = conn.cursor()
        c.execute(query, values)
        conn.commit()


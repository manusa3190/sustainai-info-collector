from datetime import datetime
from typing import Optional, List, Type, Dict, Any, Tuple
import sqlite3
from sqlite3 import Cursor

from dataclasses import fields
import json

from .articles import Article
from .preferences import Preference
from .users import User

DB_PATH = 'sustainai.db'
TABLES = {
    'articles'   :Article,
    'preferences':Preference,
    'users'      :User,
}

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

def parse_value(value: str):
    if value == "":
        return None
    
    try:
        return datetime.fromisoformat(value) # ISO 8601形式の日付時間であればdatetimeに変換
    except ValueError:
        pass
    
    try:
        return json.loads(value) # JSON形式であればリストや辞書に変換
    except (ValueError, json.JSONDecodeError):
        pass

    # その他のケースでは文字列のまま返す
    return value

def setup_database():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        for table_name, the_class in TABLES.items():
            field_names = fields(the_class)
            column_definitions = [f"{field.name} {get_sqlite_type(field.type)}" for field in field_names]

            c.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    {", ".join(column_definitions)}
                )
            ''')

def set_doc(table_name:str,data:Dict[str,str]):
    target_class = TABLES[table_name]
    key_name:str = fields(target_class)[0].name

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        results = c.execute(f'''SELECT * FROM {table_name} WHERE {key_name} = ?''', (data[key_name],))
        record = results.fetchone()

        if record:
            # 更新するフィールドと対応するプレースホルダーを動的に生成
            fieldNames = ', '.join([f"{key} = ?" for (i,key) in enumerate(data.keys()) if i != 0])

            # プレースホルダーに入る値を準備（idは最後に渡す）例: ['["東京湾", "環境一斉調査"]', 'moe01']
            values = [convert_value(value) for key, value in data.items() if key != key_name]
            values.append(data[key_name])

            # クエリの生成 例: UPDATE articles SET keywords = ? WHERE id = ?
            query = f"UPDATE {table_name} SET {fieldNames} WHERE {key_name} = ?"
            c.execute(query, values)
                                    
        else:
            fieldNames = ', '.join([f"{key}" for key in data.keys()])
            placeholders = ', '.join([f"?" for key in data.keys() ])
            values = [convert_value(value) for value in data.values()]
            c.execute(f"INSERT INTO {table_name} ({fieldNames}) VALUES ({placeholders})", values)

# 【作成中】
def get_doc(table_name:str,id:str):
    target_class = TABLES[table_name]
    key_name:str = fields(target_class)[0].name

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        results = c.execute(f'''SELECT * FROM {table_name} WHERE {key_name} = ?''', (id,))
        record = results.fetchone()

        return record # 修正必要

def get_docs(table_name:str,query:Optional[Tuple[str,str,str]]):
    target_class = TABLES[table_name]
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        results:Cursor

        if(query is None):
            results = c.execute(f'''SELECT * FROM {table_name}''')

        elif(query[1]=='=='):
            results = c.execute(f'''SELECT * FROM {table_name} WHERE {query[0]} = ?''', (query[2],))

        items = []

        for values in results.fetchall():
            d:Dict = {f.name: convert_value(value) for f, value in zip(fields(Article), values)}
            items.append(target_class(**d))

        return items

def update_doc(table_name:str,data:Dict[str,Any]):
    pass
        # with sqlite3.connect(DB_PATH) as conn:
        #      c = conn.cursor()
        #     # 更新するフィールドと対応するプレースホルダーを動的に生成
        #     fieldNames = ', '.join([f"{key} = ?" for (i,key) in enumerate(data.keys()) if i != 0])
            
        #     # クエリの生成 例: UPDATE articles SET keywords = ? WHERE id = ?
        #     query = f"UPDATE {table_name} SET {fieldNames} WHERE {key_name} = ?"
            
        #     # プレースホルダーに入る値を準備（idは最後に渡す）例: ['["東京湾", "環境一斉調査"]', 'moe01']
        #     values = [convert_value(value) for key, value in data.items() if key != key_name]
        #     values.append(data[key_name])
        


# 【編集中】Dict型のdataを渡します。
# def set_docs(table_name:str,datas:List[Dict[str,Any]]):
#     with sqlite3.connect(DB_PATH) as conn:
#         c = conn.cursor()

#         key_name:str = str(fields(Article)[0])

#         # 更新するフィールドと対応するプレースホルダーを動的に生成
#         fieldNames = ', '.join([f"{key} = ?" for (i,key) in enumerate(data.keys()) if i != 0])
        
#         # クエリの生成 例: UPDATE articles SET keywords = ? WHERE id = ?
#         query = f"UPDATE {table_name} SET {fieldNames} WHERE {key_name} = ?"
        
#         # プレースホルダーに入る値を準備（idは最後に渡す）例: ['["東京湾", "環境一斉調査"]', 'moe01']
#         values = [convert_value(value) for key, value in data.items() if key != key_name]
#         values.append(data[key_name])
#         print(values)
        
#         # データベースの接続を確立してクエリを実行
#         with sqlite3.connect(DB_PATH) as conn:
#             c = conn.cursor()
#             c.execute(query, values)
#             conn.commit()


# def save_to_sqlite(article_list: List[Article], db_path: str = 'articles.db'):
#     columns = [field.name for field in fields(Article)]
#     placeholders = ", ".join(["?" for _ in columns])
#     values_list = []

#     for article in article_list:
#         values = []
#         for col in columns:
#             value = getattr(article, col)
#             if isinstance(value, datetime):
#                 value = value.isoformat()
#             elif isinstance(value, list):
#                 value = json.dumps(value)  # リストをJSON文字列に変換
#             values.append(value)
#         values_list.append(values)

#     with sqlite3.connect(db_path) as conn:
#         c = conn.cursor()
#         c.executemany(f"INSERT INTO articles ({', '.join(columns)}) VALUES ({placeholders})", values_list)

# def fetch_recent_articles(db_path: str = 'articles.db', days: int = 7) -> List[Article]:
#     now = datetime.now()
#     one_week_ago = now - timedelta(days=days)

#     with sqlite3.connect(db_path) as conn:
#         c = conn.cursor()
#         c.execute('''
#             SELECT * FROM articles
#             WHERE release_date >= ?
#         ''', (one_week_ago.isoformat(),))

#         rows = c.fetchall()

#     articles = []
#     for row in rows:
#         articles.append(Article(row))

#     return articles

# # 使用例
# if __name__ == "__main__":
#     setup_database()
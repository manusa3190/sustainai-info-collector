import sqlite3
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from typing import Optional, List, Type
import json

@dataclass
class Preference:
    keyword: str = ""
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
    score:int = 0


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
    with sqlite3.connect('preferences.db') as conn:
        c = conn.cursor()

        table_fields = fields(Preference)
        column_definitions = [f"{field.name} {get_sqlite_type(field.type)}" for field in table_fields]

        c.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                {", ".join(column_definitions)}
            )
        ''')

def adjust_score(table_name:str,keyword:str,range:int):
    with sqlite3.connect('preferences.db') as conn:
        c = conn.cursor()

        # 特定のレコードのscoreを取得
        select_query = f'''
          SELECT score FROM {table_name} WHERE keyword = ?
        '''
        c.execute(select_query, (keyword,))
        result = c.fetchone()

        if result is not None:
            current_score = result[0]
            new_score = current_score + range

            # scoreを更新
            update_query = f'''
                UPDATE {table_name}
                SET score = ?
                WHERE id = ?
            '''
            c.execute(update_query, (new_score, keyword))

            # 変更を保存
            conn.commit()

            print(f"Record with id {keyword} updated successfully. New score: {new_score}")
        else:
            print(f"Record with id {keyword} not found.")




# 使用例
if __name__ == "__main__":
    setup_database()
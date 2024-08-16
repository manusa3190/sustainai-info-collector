from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, List, Type

@dataclass
class Preference:
    preference_id:str = ""
    user_id:str = ""
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
    article_id:str = ""
    ai_score:int = 0
    user_score:int = 0

def get_sqlite_type(field_type: Type) -> str:
    type_map = {
        datetime: 'TEXT',
        str: 'TEXT',
        int: 'INTEGER',
        list: 'TEXT',
        type(None): 'TEXT'
    }
    return type_map.get(field_type, 'TEXT')
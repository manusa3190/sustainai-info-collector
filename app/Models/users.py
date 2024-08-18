from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, List, Type

@dataclass
class User:
    user_id:int = 0
    name:str = ""
    preference:str = ""
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
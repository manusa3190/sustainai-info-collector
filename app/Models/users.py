import sqlite3
from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from typing import Optional, List, Type
import json

@dataclass
class User:
    user_id:str = ""
    name:str = ""
    preference = ""
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
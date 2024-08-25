from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, List, Type, Union

@dataclass
class Preference:
    preference_id:Union[int, None] = None
    user_id:int = 0
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()
    article_id:int = 0
    ai_score:int = 0
    user_score:int = 0
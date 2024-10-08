from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, List,Union


@dataclass
class Article:
    row_num:Union[None,int] = None
    article_id: int = 0
    acquition_date: datetime = datetime.now()
    publish_date: Optional[datetime] = None
    source: str = ""
    title: str = ""
    content: str = ""
    keywords: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    created_at:datetime = datetime.now()
    updated_at:datetime = datetime.now()

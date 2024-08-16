from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Optional, List


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

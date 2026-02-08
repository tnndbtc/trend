from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict


class Topic(BaseModel):
    title: str
    description: str
    source: str
    url: str
    timestamp: datetime
    metrics: Dict = {}


class Trend(BaseModel):
    rank: int
    title: str
    summary: str
    key_points: List[str]
    sources: List[str]
    score: float

# app/models.py
from pydantic import BaseModel
from typing import List


class OrganizeRequest(BaseModel):
    items: List[str]
    store_id: int


class OrganizedGroup(BaseModel):
    zone: str
    items: List[str]


class OrganizeResponse(BaseModel):
    content: List[OrganizedGroup]

class StoreDetailRequest(BaseModel):
    store_name: str
    postal_code: str = None

class StoreDetailsResponse(BaseModel):
    store_id: int
    name: str
    chain: str
    postal_code: str
    location_id: int
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SearchCriteria(BaseModel):
    """Модель для критериев поиска."""
    industries: List[str] = []
    regions: List[str] = []
    positions: List[str] = []
    company_size: List[str] = Field(default=[], alias="companySize")
    keywords: List[str] = []
    comments: Optional[str] = None


class Order(BaseModel):
    """Модель для заказа."""
    user_id: str = Field(..., alias="userId")
    created_at: datetime = Field(..., alias="createdAt")
    status: str
    required_contacts: int = Field(..., alias="requiredContacts")
    search_criteria: SearchCriteria = Field(..., alias="searchCriteria")

    class Config:
        # Позволяет Pydantic работать с моделями, у которых есть псевдонимы (alias)
        populate_by_name = True
        # Позволяет использовать вложенные модели
        from_attributes = True
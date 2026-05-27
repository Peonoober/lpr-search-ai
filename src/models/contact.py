from pydantic import BaseModel
from typing import Optional

class FoundContact(BaseModel):
    """Модель для контакта, найденного AI-агентом."""
    full_name: str
    position: str
    company_name: str
    email: str
    linkedin_url: Optional[str] = None
    source_url: str
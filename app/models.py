# models.py
import uuid
from sqlmodel import SQLModel, Field
from datetime import date
from typing import Optional

class Employee(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True
    )
    emp_id: int = Field(unique=True, index=True)
    emp_name: str
    city: str
    country: str
    emp_dob: date

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)

# app/schemas.py
import uuid
from sqlmodel import SQLModel, Field
from pydantic import ConfigDict, field_validator
from datetime import date
from typing import Optional



# --- Pydantic V2 validator function ---
# We define it once and reuse it
@field_validator('emp_dob', mode='before')  # 'before' validates the raw data
def validate_dob_not_in_future(cls, v: date) -> date:
    """Validates the date of birth is not in the future."""
    if v is None:  # Allow None for optional fields (like in EmployeeUpdate)
        return None

    # Handle if the input is a string (like from JSON)
    if isinstance(v, str):
        try:
            v = date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format: {v}")

    if v > date.today():
        raise ValueError("Date of birth cannot be in the future")
    return v


# Shared properties
class EmployeeBase(SQLModel):
    # --- FIX: Removed json_schema_extra from all Fields ---
    emp_id: int = Field(..., ge=1)
    emp_name: str = Field(...)
    city: str = Field(...)
    country: str = Field(...)
    emp_dob: date = Field(...)

    # Apply validator
    _validate_dob = validate_dob_not_in_future

    # --- FIX: Examples are added to the model's config ---
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "emp_id": 101,
                "emp_name": "Jane Doe",
                "city": "London",
                "country": "UK",
                "emp_dob": "1990-01-15"
            }
        }
    )


# Schema for creating an employee
class EmployeeCreate(EmployeeBase):
    # This schema will inherit the example from EmployeeBase.
    # We can override it by adding a new model_config if needed.
    pass


# Schema for reading an employee
class EmployeeRead(EmployeeBase):
    id: uuid.UUID

    # Override config to add the 'id' to the example
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6",
                "emp_id": 101,
                "emp_name": "Jane Doe",
                "city": "London",
                "country": "UK",
                "emp_dob": "1990-01-15"
            }
        }
    )


# Schema for updating an employee
class EmployeeUpdate(SQLModel):
    emp_id: Optional[int] = Field(default=None, ge=1)
    emp_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    emp_dob: Optional[date] = None

    # Apply validator
    _validate_dob = validate_dob_not_in_future

    # Add a specific example for the update schema
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "emp_name": "Jane A. Doe",
                "city": "Manchester"
            }
        }
    )


# --- Schemas for Auth ---

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    username: Optional[str] = None


class UserCreate(SQLModel):
    username: str
    password: str


class UserRead(SQLModel):
    id: int
    username: str
    is_admin: bool

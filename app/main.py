# main.py
from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from contextlib import asynccontextmanager
from enum import Enum

from . import crud, schemas, models
from .database import get_async_session, create_db_and_tables, AsyncSessionFactory
from .security import get_current_user, get_current_admin_user
from . import auth


# --- Enums for Sorting ---
class SortableFields(str, Enum):
    emp_id = "emp_id"
    emp_name = "emp_name"
    emp_dob = "emp_dob"
    city = "city"
    country = "country"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating database and tables...")
    await create_db_and_tables()
    print("Database and tables created.")

    print("Checking for admin user...")
    async with AsyncSessionFactory() as session:
        admin_user = await crud.get_user_by_username(session, "admin")
        if not admin_user:
            print("Admin user not found, creating one...")
            admin_user_data = schemas.UserCreate(
                username="admin",
                password="adminpassword"
            )
            await crud.create_admin_user(session, admin_user_data)
            print("Admin user 'admin' created.")
        else:
            print("Admin user already exists.")

    yield


app = FastAPI(
    title="Employee Management API (Production Ready)",
    description="A secure, high-performance API using SQLModel, PostgreSQL, OAuth2, and Auth scopes.",
    lifespan=lifespan,
)

app.include_router(auth.router)


# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the Employee Management API."}


@app.post(
    "/employees/",
    response_model=schemas.EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Employees"]
)
async def create_employee_endpoint(
        employee_input: schemas.EmployeeCreate,
        db: AsyncSession = Depends(get_async_session),
        current_admin: models.User = Depends(get_current_admin_user)
):
    """Create a new employee record. (Admin Only)"""
    return await crud.create_employee(db=db, employee=employee_input)


@app.get("/employees/", response_model=List[schemas.EmployeeRead], tags=["Employees"])
async def get_all_employees_endpoint(
        db: AsyncSession = Depends(get_async_session),
        current_user: models.User = Depends(get_current_user),
        offset: int = 0,
        limit: int = 100,
        city: Optional[str] = None,
        country: Optional[str] = None,
        sort_by: SortableFields = SortableFields.emp_id,
        order: SortOrder = SortOrder.asc
):
    """
    Retrieve all employees. (Authenticated Users Only)
    Supports pagination, filtering by city/country, and sorting.
    """
    return await crud.get_all_employees(
        db=db,
        offset=offset,
        limit=limit,
        city=city,
        country=country,
        sort_by=sort_by.value,
        order=order.value
    )


@app.get("/employees/{emp_id}", response_model=schemas.EmployeeRead, tags=["Employees"])
async def get_employee_by_emp_id_endpoint(
        emp_id: int,
        db: AsyncSession = Depends(get_async_session),
        current_user: models.User = Depends(get_current_user)
):
    """Retrieve an employee by their emp_id. (Authenticated Users Only)"""
    employee = await crud.get_employee_by_emp_id(db, emp_id)
    if not employee:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with emp_id '{emp_id}' not found"
        )
    return employee


@app.patch("/employees/{emp_id}", response_model=schemas.EmployeeRead, tags=["Employees"])
async def update_employee_by_emp_id_endpoint(
        emp_id: int,
        updated_details: schemas.EmployeeUpdate,
        db: AsyncSession = Depends(get_async_session),
        current_admin: models.User = Depends(get_current_admin_user)
):
    """
    Updates the record for a specific employee. (Admin Only)
    This uses PATCH logic (only updates provided fields).
    """
    updated_employee = await crud.update_employee(
        db=db,
        emp_id=emp_id,
        employee_update=updated_details
    )
    if not updated_employee:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with emp_id '{emp_id}' not found"
        )
    return updated_employee


@app.delete(
    "/employees/{emp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Employees"]
)
async def delete_employee_by_emp_id_endpoint(
        emp_id: int,
        db: AsyncSession = Depends(get_async_session),
        current_admin: models.User = Depends(get_current_admin_user)
):
    """Delete an employee using their emp_id. (Admin Only)"""
    success = await crud.delete_employee(db=db, emp_id=emp_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Employee with emp_id '{emp_id}' not found"
        )
    return None

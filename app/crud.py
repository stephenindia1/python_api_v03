# crud.py
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from .models import Employee, User
from .schemas import EmployeeCreate, EmployeeUpdate, UserCreate
from typing import List, Optional
from .security import get_password_hash


# --- Employee CRUD ---

async def create_employee(db: AsyncSession, employee: EmployeeCreate) -> Employee:
    existing = await get_employee_by_emp_id(db, employee.emp_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee business ID '{employee.emp_id}' already exists"
        )

    db_employee = Employee.model_validate(employee)

    try:
        db.add(db_employee)
        await db.commit()
        await db.refresh(db_employee)
        return db_employee
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: A race condition occurred or emp_id was just created."
        )


async def get_employee_by_emp_id(db: AsyncSession, emp_id: int) -> Optional[Employee]:
    statement = select(Employee).where(Employee.emp_id == emp_id)
    result = await db.execute(statement)
    return result.scalars().first()


async def get_all_employees(
        db: AsyncSession,
        offset: int,
        limit: int,
        city: Optional[str] = None,
        country: Optional[str] = None,
        sort_by: str = "emp_id",
        order: str = "asc"
) -> List[Employee]:
    statement = select(Employee)

    if city:
        statement = statement.where(Employee.city.ilike(f"%{city}%"))
    if country:
        statement = statement.where(Employee.country.ilike(f"%{country}%"))

    sort_column = getattr(Employee, sort_by, Employee.emp_id)
    if order.lower() == "desc":
        statement = statement.order_by(sort_column.desc())
    else:
        statement = statement.order_by(sort_column.asc())

    statement = statement.offset(offset).limit(limit)

    result = await db.execute(statement)
    return result.scalars().all()


async def update_employee(
        db: AsyncSession,
        emp_id: int,
        employee_update: EmployeeUpdate
) -> Optional[Employee]:
    db_employee = await get_employee_by_emp_id(db, emp_id)
    if not db_employee:
        return None

    update_data = employee_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_employee, key, value)

    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee


async def delete_employee(db: AsyncSession, emp_id: int) -> bool:
    db_employee = await get_employee_by_emp_id(db, emp_id)
    if not db_employee:
        return False

    await db.delete(db_employee)
    await db.commit()
    return True


# --- User CRUD ---

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    result = await db.execute(statement)
    return result.scalars().first()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    existing = await get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        hashed_password=hashed_password,
        is_admin=False  # Regular users are not admin
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def create_admin_user(db: AsyncSession, user: UserCreate) -> User:
    """A special function to create an admin user."""
    if await get_user_by_username(db, user.username):
        raise HTTPException(status_code=409, detail="Username exists")

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        hashed_password=hashed_password,
        is_admin=True
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

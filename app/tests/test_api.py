# tests/test_api.py
import pytest
from httpx import AsyncClient

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_read_root(client: AsyncClient):
    """Test the root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Employee Management API."}


# --- Auth Endpoint Tests ---

async def test_register_user(client: AsyncClient):
    response = await client.post(
        "/auth/register",
        json={"username": "newuser", "password": "newpassword"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["is_admin"] is False
    assert "id" in data


async def test_login_for_token(normal_user_client: AsyncClient):
    # The fixture 'normal_user_client' already logs in.
    # We can just check that the client has auth headers.
    assert "Authorization" in normal_user_client.headers
    assert normal_user_client.headers["Authorization"].startswith("Bearer ")


# --- Employee Endpoint Tests ---

async def test_create_employee_as_admin(admin_user_client: AsyncClient):
    response = await admin_user_client.post(
        "/employees/",
        json={
            "emp_id": 101,
            "emp_name": "Test Employee",
            "city": "Test City",
            "country": "Test Country",
            "emp_dob": "2000-01-01"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["emp_id"] == 101
    assert data["emp_name"] == "Test Employee"


async def test_create_employee_as_normal_user(normal_user_client: AsyncClient):
    response = await normal_user_client.post(
        "/employees/",
        json={
            "emp_id": 102,
            "emp_name": "Another Employee",
            "city": "Another City",
            "country": "Another Country",
            "emp_dob": "2001-01-01"
        }
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "The user does not have administrative privileges"}


async def test_create_employee_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/employees/",
        json={"emp_id": 103, "emp_name": "Ghost", "city": "N/A", "country": "N/A", "emp_dob": "2001-01-01"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_create_employee_invalid_data(admin_user_client: AsyncClient):
    # Test emp_dob in future
    response_future = await admin_user_client.post(
        "/employees/",
        json={"emp_id": 104, "emp_name": "Future", "city": "N/A", "country": "N/A", "emp_dob": "2099-01-01"}
    )
    assert response_future.status_code == 422
    assert "Date of birth cannot be in the future" in response_future.text

    # Test emp_id less than 1
    response_zero_id = await admin_user_client.post(
        "/employees/",
        json={"emp_id": 0, "emp_name": "Zero", "city": "N/A", "country": "N/A", "emp_dob": "2000-01-01"}
    )
    assert response_zero_id.status_code == 422
    assert "Input should be greater than or equal to 1" in response_zero_id.text


async def test_get_employees_filtering_sorting_paging(
        admin_user_client: AsyncClient,
        normal_user_client: AsyncClient
):
    # Admin creates employees
    await admin_user_client.post("/employees/", json={
        "emp_id": 1, "emp_name": "Alice", "city": "London", "country": "UK", "emp_dob": "1990-01-01"
    })
    await admin_user_client.post("/employees/", json={
        "emp_id": 2, "emp_name": "Bob", "city": "New York", "country": "USA", "emp_dob": "1995-01-01"
    })
    await admin_user_client.post("/employees/", json={
        "emp_id": 3, "emp_name": "Charlie", "city": "London", "country": "UK", "emp_dob": "1985-01-01"
    })

    # Test filtering
    response_filter = await normal_user_client.get("/employees/?city=London")
    assert response_filter.status_code == 200
    data = response_filter.json()
    assert len(data) == 2
    assert {e["emp_name"] for e in data} == {"Alice", "Charlie"}

    # Test sorting
    response_sort = await normal_user_client.get("/employees/?sort_by=emp_dob&order=asc")
    assert response_sort.status_code == 200
    data = response_sort.json()
    assert len(data) == 3
    assert data[0]["emp_name"] == "Charlie"
    assert data[1]["emp_name"] == "Alice"
    assert data[2]["emp_name"] == "Bob"

    # Test pagination
    response_page = await normal_user_client.get("/employees/?limit=1&offset=1&sort_by=emp_id")
    assert response_page.status_code == 200
    data = response_page.json()
    assert len(data) == 1
    assert data[0]["emp_name"] == "Bob"  # emp_id 2 is at offset 1


async def test_patch_employee_as_admin(admin_user_client: AsyncClient):
    await admin_user_client.post("/employees/", json={
        "emp_id": 201, "emp_name": "To Be Patched", "city": "Old City", "country": "N/A", "emp_dob": "2000-01-01"
    })

    patch_resp = await admin_user_client.patch(
        "/employees/201",
        json={"city": "New City"}
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["city"] == "New City"
    assert data["emp_name"] == "To Be Patched"  # Name is unchanged


async def test_patch_employee_as_normal_user(
        normal_user_client: AsyncClient,
        admin_user_client: AsyncClient  # <-- Correct: just add it to the arguments
):
    """
    FAIL: Normal user cannot patch an employee.
    """
    # 1. Use the ADMIN client to create an employee
    create_resp = await admin_user_client.post(
        "/employees/",
        json={
            "emp_id": 202,
            "emp_name": "No Patch",
            "city": "N/A",
            "country": "N/A",
            "emp_dob": "2000-01-01"
        }
    )
    assert create_resp.status_code == 201

    # 2. Use the NORMAL user client to try and patch it
    patch_resp = await normal_user_client.patch(
        "/employees/202",
        json={"city": "New City"}
    )

    # 3. Assert that the normal user was Forbidden
    assert patch_resp.status_code == 403


async def test_delete_employee_as_admin(admin_user_client: AsyncClient):
    await admin_user_client.post("/employees/", json={
        "emp_id": 301, "emp_name": "To Be Deleted", "city": "Temp", "country": "N/A", "emp_dob": "2000-01-01"
    })

    delete_resp = await admin_user_client.delete("/employees/301")
    assert delete_resp.status_code == 204

    get_resp = await admin_user_client.get("/employees/301")
    assert get_resp.status_code == 404

import sys
import os
import pytest

# Add project root to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import crud
from app.schemas import UserCreate

def test_get_user_count(client, db):
    """
    Tests the user count endpoint.
    """
    # 1. Setup: Ensure the database is clean and then create a known number of users.
    # The test DB is clean at the start of each test thanks to our fixtures.
    db.query(crud.models.User).delete()
    db.commit()

    users_to_create = [
        UserCreate(username="count_user_1", email="cu1@example.com", password="p1"),
        UserCreate(username="count_user_2", email="cu2@example.com", password="p2"),
        UserCreate(username="count_user_3", email="cu3@example.com", password="p3"),
    ]

    for user in users_to_create:
        crud.create_user(db, user=user)

    # 2. Action: Call the new endpoint
    response = client.get("/users/count")

    # 3. Assertions
    assert response.status_code == 200
    assert response.json() == {"total_users": 3} 
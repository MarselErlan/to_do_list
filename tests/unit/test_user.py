import pytest
from sqlalchemy.orm import Session
from app import crud, schemas
from app.models import User

def test_create_user(db: Session):
    """
    Test that a new user can be created in the database.
    """
    user_data = schemas.UserCreate(
        username="testuser",
        email="test@example.com",
        password="a-secure-password"
    )
    
    # Create the user
    db_user = crud.create_user(db=db, user=user_data)
    
    # Assert that the user was created correctly
    assert db_user is not None
    assert db_user.username == "testuser"
    assert db_user.email == "test@example.com"
    assert db_user.is_active is True # Default to active for now
    
    # Verify the password was hashed and is not stored in plaintext
    assert hasattr(db_user, 'hashed_password')
    assert db_user.hashed_password != "a-secure-password"
    
    # Retrieve the user from the DB to confirm persistence
    stored_user = db.query(User).filter(User.id == db_user.id).first()
    assert stored_user is not None
    assert stored_user.username == "testuser" 
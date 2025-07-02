import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine
from app import crud, schemas, models

def run_db_test():
    db: Session = SessionLocal()
    test_user = None
    test_todo = None
    
    print("--- Running Database User Feature Test ---")
    
    try:
        # 1. Create a User
        print("Step 1: Creating a test user...")
        user_schema = schemas.UserCreate(
            username="db_test_user",
            email="db_test@example.com",
            password="password123"
        )
        test_user = crud.create_user(db, user=user_schema)
        assert test_user is not None
        assert test_user.username == "db_test_user"
        print(f"✅ User '{test_user.username}' created successfully with ID: {test_user.id}")
        
        # 2. Create a Todo for that User
        print("\nStep 2: Creating a to-do for the test user...")
        todo_schema = schemas.TodoCreate(
            title="DB Test Todo",
            description="A test task for the database."
        )
        test_todo = crud.create_todo(db, todo=todo_schema, owner_id=test_user.id)
        assert test_todo is not None
        assert test_todo.title == "DB Test Todo"
        print(f"✅ Todo '{test_todo.title}' created successfully with ID: {test_todo.id}")
        
        # 3. Verify Todo Ownership
        print("\nStep 3: Verifying to-do ownership...")
        retrieved_todo = crud.get_todo(db, todo_id=test_todo.id)
        assert retrieved_todo is not None
        assert retrieved_todo.owner_id == test_user.id
        print(f"✅ Ownership verified: Todo owner_id ({retrieved_todo.owner_id}) matches user_id ({test_user.id}).")
        
        # 4. Verify getting todos by user
        print("\nStep 4: Verifying get_todos_by_user...")
        user_todos = crud.get_todos_by_user(db, user_id=test_user.id)
        assert len(user_todos) == 1
        assert user_todos[0].id == test_todo.id
        print(f"✅ Successfully retrieved {len(user_todos)} to-do(s) for the user.")

        print("\n--- ✅ DATABASE TEST SUCCEEDED! ---")
        
    except Exception as e:
        print(f"\n--- ❌ DATABASE TEST FAILED ---")
        print(f"Error: {e}")
        
    finally:
        # Cleanup
        print("\n--- Cleaning up test data ---")
        if test_todo:
            print(f"Deleting test todo (ID: {test_todo.id})...")
            crud.delete_todo(db, todo_id=test_todo.id)
        if test_user:
            print(f"Deleting test user (ID: {test_user.id})...")
            # We need a direct way to delete a user for testing
            db.delete(test_user)
            db.commit()
        
        db.close()
        print("--- Test finished ---")

if __name__ == "__main__":
    run_db_test() 
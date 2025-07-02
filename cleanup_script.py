import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.database import SessionLocal
from app import crud

def run_cleanup():
    """
    Connects to the database and runs the cleanup process for expired
    email verification codes.
    """
    print("--- Running cleanup for expired verification codes ---")
    
    db = SessionLocal()
    
    try:
        deleted_count = crud.cleanup_expired_codes(db)
        if deleted_count > 0:
            print(f"✅ Successfully cleaned up {deleted_count} expired code(s).")
        else:
            print("✅ No expired codes to clean up.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        db.close()
        print("--- Cleanup finished ---")

if __name__ == "__main__":
    run_cleanup() 
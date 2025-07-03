from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from typing import Optional
from . import models, schemas
from .security import get_password_hash, verify_password
from passlib.context import CryptContext
import random
import string

MAX_VERIFICATION_ATTEMPTS = 4

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User CRUD Functions

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Authenticates a user by checking the username and password.
    Returns the user object if authentication is successful, otherwise None.
    """
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_hashed_password(password: str) -> str:
    return pwd_context.hash(password)

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_hashed_password(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create a private session for the new user
    private_session = models.Session(created_by_id=db_user.id)
    db.add(private_session)
    db.commit()
    db.refresh(private_session)

    # Add the user as the owner of their private session
    session_member = models.SessionMember(
        session_id=private_session.id,
        user_id=db_user.id,
        role="owner"
    )
    db.add(session_member)
    db.commit()

    return db_user

def create_team_session(db: Session, session: schemas.SessionCreate, owner_id: int) -> models.Session:
    """Creates a new team session and assigns the creator as the owner."""
    # Create the new session
    db_session = models.Session(
        name=session.name,
        created_by_id=owner_id
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Add the creator as the owner in session_members
    member = models.SessionMember(
        session_id=db_session.id,
        user_id=owner_id,
        role="owner"
    )
    db.add(member)
    db.commit()

    return db_session

def invite_user_to_session(db: Session, session_id: int, invitee_email: str) -> models.SessionMember | None:
    """Adds a user to a session as a collaborator."""
    # Find the user to invite
    user_to_invite = get_user_by_email(db, email=invitee_email)
    if not user_to_invite:
        return None # User not found

    # Check if the user is already in the session
    existing_member = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session_id,
        models.SessionMember.user_id == user_to_invite.id
    ).first()
    if existing_member:
        return None # Already a member

    # Add the user to the session
    new_member = models.SessionMember(
        session_id=session_id,
        user_id=user_to_invite.id,
        role="collaborator"
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member

def update_user_password(db: Session, user: models.User, new_password: str):
    """Updates a user's password."""
    user.hashed_password = get_hashed_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def count_users(db: Session) -> int:
    """Returns the total number of users in the database."""
    return db.query(models.User).count()

# Todo CRUD Functions

def get_todo(db: Session, todo_id: int):
    return db.query(models.Todo).filter(models.Todo.id == todo_id).first()

def get_todos_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Todo).filter(models.Todo.owner_id == user_id).offset(skip).limit(limit).all()

def create_todo(db: Session, todo: schemas.TodoCreate, owner_id: int):
    session_id_to_use = todo.session_id
    is_private = True

    if session_id_to_use:
        # If a session_id is provided, verify the user is a member.
        member_check = db.query(models.SessionMember).filter(
            models.SessionMember.session_id == session_id_to_use,
            models.SessionMember.user_id == owner_id
        ).first()
        if not member_check:
            raise Exception("User is not a member of the target session.")
        is_private = False # Todos in team sessions are not private
    else:
        # If no session_id, find the user's private session.
        private_session = db.query(models.Session).filter(
            models.Session.created_by_id == owner_id,
            models.Session.name == None
        ).first()
        if not private_session:
            raise Exception("User has no private session.")
        session_id_to_use = private_session.id
        is_private = True
    
    db_todo = models.Todo(
        **todo.model_dump(exclude={"session_id"}),
        owner_id=owner_id,
        session_id=session_id_to_use,
        is_private=is_private
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, todo: schemas.TodoUpdate, owner_id: int):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if db_todo:
        # Ensure the todo belongs to the current user
        if db_todo.owner_id != owner_id:
            raise ValueError("Not authorized to update this todo")

        update_data = todo.model_dump(exclude_unset=True)

        # Handle session_id and is_private logic
        if "session_id" in update_data:
            new_session_id = update_data["session_id"]
            if new_session_id is not None:
                # Verify user is a member of the target session
                member_check = db.query(models.SessionMember).filter(
                    models.SessionMember.session_id == new_session_id,
                    models.SessionMember.user_id == owner_id
                ).first()
                if not member_check:
                    raise ValueError("User is not a member of the target session.")

                # Determine if the new session is a private session (unnamed)
                target_session = db.query(models.Session).filter(
                    models.Session.id == new_session_id
                ).first()
                if target_session and target_session.name is None and target_session.created_by_id == owner_id:
                    # It's the user's own private session
                    db_todo.is_private = True
                else:
                    # It's a team session
                    db_todo.is_private = False
                db_todo.session_id = new_session_id
            else:
                # If session_id is explicitly set to None, move to private session
                private_session = db.query(models.Session).filter(
                    models.Session.created_by_id == owner_id,
                    models.Session.name == None
                ).first()
                if not private_session:
                    raise ValueError("User has no private session to move todo to.")
                db_todo.session_id = private_session.id
                db_todo.is_private = True

        for key, value in update_data.items():
            if key != "session_id": # session_id handled separately to manage is_private
                setattr(db_todo, key, value)
        
        db.add(db_todo) # Re-add to session to ensure changes are tracked
        db.commit()
        db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if db_todo:
        db.delete(db_todo)
        db.commit()
    return db_todo

# Time Management Functions

def get_todos_today(db: Session, user_id: int):
    """Get todos for a specific user due today"""
    today = date.today()
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date == today
    ).all()

def get_todos_for_week(db: Session, user_id: int):
    """Get todos for a specific user due this week"""
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date >= week_start,
        models.Todo.due_date <= week_end
    ).all()

def get_todos_for_month(db: Session, user_id: int):
    """Get todos for a specific user due this month"""
    today = date.today()
    month_start = today.replace(day=1)
    
    if today.month == 12:
        next_month_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_start = today.replace(month=today.month + 1, day=1)
    
    month_end = next_month_start - timedelta(days=1)
    
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date >= month_start,
        models.Todo.due_date <= month_end
    ).all()

def get_todos_for_year(db: Session, user_id: int):
    """Get todos for a specific user due this year"""
    today = date.today()
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date >= year_start,
        models.Todo.due_date <= year_end
    ).all()

def get_overdue_todos(db: Session, user_id: int):
    """Get overdue todos for a specific user"""
    today = date.today()
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date < today,
        models.Todo.done == False
    ).all()

def get_todos_by_time_range(db: Session, start_time: datetime, end_time: datetime):
    """Get todos within a specific time range"""
    return db.query(models.Todo).filter(
        models.Todo.start_time >= start_time,
        models.Todo.start_time <= end_time
    ).all()

def get_todos_by_date(db: Session, target_date: date):
    return db.query(models.Todo).filter(models.Todo.due_date == target_date).all()

def get_todos_by_date_range(db: Session, user_id: int, start_date: date, end_date: date):
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date.between(start_date, end_date)
    ).all()

# --- Email Verification CRUD ---

def create_verification_code(db: Session, email: str) -> tuple[str | None, int]:
    """
    Generates, stores, and returns a 6-digit verification code for an email.
    Handles rate-limiting by tracking attempts within the 5-hour window.
    Returns a tuple: (plain_code, attempts_left).
    plain_code is None if the attempt limit has been reached.
    """
    existing_verification = db.query(models.EmailVerification).filter(
        models.EmailVerification.email == email,
        models.EmailVerification.verified == False
    ).first()

    plain_code = None
    attempts_left = MAX_VERIFICATION_ATTEMPTS

    now = datetime.utcnow()

    if existing_verification and existing_verification.expires_at > now:
        # Existing unexpired code found, increment attempts
        existing_verification.attempts += 1
        if existing_verification.attempts <= MAX_VERIFICATION_ATTEMPTS:
            # Still within limits, generate new code, reset expiry
            plain_code = "".join(random.choices(string.digits, k=6))
            existing_verification.code = pwd_context.hash(plain_code)
            existing_verification.expires_at = now + timedelta(hours=5)
            attempts_left = MAX_VERIFICATION_ATTEMPTS - existing_verification.attempts
        else:
            # Exceeded attempts, do not generate new code
            plain_code = None
            attempts_left = 0 # No attempts left
        db.add(existing_verification)
        db.commit()
        db.refresh(existing_verification)
    else:
        # No existing unexpired code, or it's expired. Create a new one.
        plain_code = "".join(random.choices(string.digits, k=6))
        db_verification = models.EmailVerification(
            email=email,
            code=pwd_context.hash(plain_code),
            attempts=1, # First attempt for this new/expired window
            expires_at=now + timedelta(hours=5) # Set expiry for 5 hours from now
        )
        db.add(db_verification)
        db.commit()
        db.refresh(db_verification)
        attempts_left = MAX_VERIFICATION_ATTEMPTS - 1

    return plain_code, attempts_left

def verify_code(db: Session, email: str, code: str) -> bool:
    """
    Verifies the provided code for the given email.
    """
    verification_entry = get_verification_code(db, email=email)
    
    if not verification_entry:
        return False
        
    # Check if expired
    if verification_entry.expires_at < datetime.utcnow():
        return False
        
    # Check if code matches
    if not pwd_context.verify(code, verification_entry.code):
        return False
        
    # Mark as verified and clean up
    verification_entry.verified = True
    db.delete(verification_entry) # Delete the entry upon successful verification
    db.commit()
    
    return True

def get_verification_code(db: Session, email: str) -> models.EmailVerification:
    """
    Retrieves the latest verification code entry for an email.
    """
    return db.query(models.EmailVerification).filter(models.EmailVerification.email == email).first()

def cleanup_expired_codes(db: Session) -> int:
    """
    Deletes all unverified and expired email verification codes from the database.
    Returns the number of deleted records.
    """
    now = datetime.utcnow()
    
    # Query for records that are unverified AND past their expiration time
    expired_codes_query = db.query(models.EmailVerification).filter(
        models.EmailVerification.verified == False,
        models.EmailVerification.expires_at < now
    )
    
    deleted_count = expired_codes_query.delete(synchronize_session=False)
    db.commit()
    
    return deleted_count

def get_todos_by_session(db: Session, session_id: int, user_id_filter: int | None = None) -> list[models.Todo]:
    """
    Gets all todos for a given session.
    If user_id_filter is provided, it returns only todos created by that user.
    """
    query = db.query(models.Todo).filter(
        models.Todo.session_id == session_id,
        models.Todo.is_private == False
    )

    if user_id_filter:
        query = query.filter(models.Todo.owner_id == user_id_filter)

    return query.all()

def get_sessions_for_user(db: Session, user_id: int):
    """
    Gets all sessions a user is a member of, along with their role in each.
    """
    return db.query(
        models.Session.id,
        models.Session.name,
        models.SessionMember.role
    ).join(models.SessionMember).filter(models.SessionMember.user_id == user_id).all()

def get_session_members(db: Session, session_id: int):
    """
    Gets all members for a given session, including their username and role.
    """
    return db.query(
        models.SessionMember.user_id,
        models.User.username,
        models.SessionMember.role
    ).join(models.User).filter(models.SessionMember.session_id == session_id).all()

def get_private_session_for_user(db: Session, user_id: int) -> models.Session | None:
    """
    Retrieves the private session for a given user.
    """
    return db.query(models.Session).filter(
        models.Session.created_by_id == user_id,
        models.Session.name == None
    ).first()

def get_session_member_by_user_and_session(db: Session, session_id: int, user_id: int) -> models.SessionMember | None:
    """
    Retrieves a specific SessionMember entry.
    """
    return db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session_id,
        models.SessionMember.user_id == user_id
    ).first()

def remove_user_from_session(db: Session, session_id: int, user_id: int) -> bool:
    """
    Removes a user from a session and reassigns their public todos in that session to their private session.
    If the user is the owner and is leaving, the entire session is deleted.
    Returns True if the session was deleted, False otherwise.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise ValueError("Session not found.")

    member_entry = get_session_member_by_user_and_session(db, session_id, user_id)
    if not member_entry:
        raise ValueError("User is not a member of this session.")

    # Check if the user is the owner of the session
    if session.created_by_id == user_id:
        # If the owner is leaving, delete the entire session (Option 3)
        delete_session(db, session_id, user_id)
        return True  # Session was deleted
    else:
        # If a non-owner is leaving, reassign their public todos and remove membership
        todos_to_reassign = db.query(models.Todo).filter(
            models.Todo.session_id == session_id,
            models.Todo.owner_id == user_id,
            models.Todo.is_private == False # Only public todos created by this user in this session
        ).all()

        private_session = get_private_session_for_user(db, user_id)
        if not private_session:
            raise ValueError("User has no private session to reassign todos to.")

        for todo in todos_to_reassign:
            todo.session_id = private_session.id
            todo.is_private = True
            db.add(todo)

        db.delete(member_entry)
        db.commit()
    
    return False # Session was not deleted

def remove_session_member(db: Session, session_id: int, member_user_id: int, performing_user_id: int):
    """
    Allows a session owner to remove a specific member from a team session.
    The removed member's public todos in that session are reassigned to their private session.
    """
    # 1. Verify the performing_user_id is the owner of the session
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise ValueError("Session not found.")

    if session.created_by_id != performing_user_id:
        raise ValueError("Only the session owner can remove members.")

    # 2. Prevent owner from removing themselves if they are the only owner (complex business logic, for now allow)
    # We might add more sophisticated checks here, like ensuring at least one owner remains.

    # 3. Use the existing remove_user_from_session logic
    # Make sure the member_user_id is not the owner trying to remove themselves as this logic is handled by leave_session
    if session.created_by_id == member_user_id:
        raise ValueError("Owner cannot remove themselves via this endpoint. Use leave_session endpoint to leave a session.")

    return remove_user_from_session(db, session_id, member_user_id)

def delete_session(db: Session, session_id: int, owner_id: int):
    """
    Deletes a team session and reassigns all public todos linked to it back to their original owners' private sessions.
    Only the owner of the session can delete it.
    """
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise ValueError("Session not found.")

    if db_session.created_by_id != owner_id:
        raise ValueError("Only the session owner can delete the session.")

    # Reassign public todos from this session to their owners' private sessions
    todos_to_reassign = db.query(models.Todo).filter(
        models.Todo.session_id == session_id,
        models.Todo.is_private == False # Only public todos
    ).all()

    for todo in todos_to_reassign:
        # Find the owner's private session
        owner_private_session = db.query(models.Session).filter(
            models.Session.created_by_id == todo.owner_id,
            models.Session.name == None
        ).first()
        
        if not owner_private_session:
            # This case should ideally not happen if create_user always creates a private session
            # For robustness, we could delete the todo or raise an error.
            # For now, we'll reassign to the owner's private session, assuming it exists.
            print(f"Warning: Private session not found for user {todo.owner_id}. Todo {todo.id} not reassigned.")
            continue

        todo.session_id = owner_private_session.id
        todo.is_private = True
        db.add(todo)

    # Delete all session members
    db.query(models.SessionMember).filter(models.SessionMember.session_id == session_id).delete(synchronize_session=False)

    # Delete the session itself
    db.delete(db_session)
    db.commit()

    return True

def update_session(db: Session, session_id: int, session_update: schemas.SessionUpdate, owner_id: int):
    """
    Updates a team session's metadata.
    Only the owner of the session can update it.
    """
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise ValueError("Session not found.")

    if db_session.created_by_id != owner_id:
        raise ValueError("Only the session owner can update the session.")

    update_data = session_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_session, key, value)

    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

 
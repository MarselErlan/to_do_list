from sqlalchemy.orm import Session
from app import crud, schemas, models

def test_create_user_creates_private_session(db: Session):
    """
    Unit test to verify that calling crud.create_user also creates
    a private session and sets the user as the owner.
    """
    user_in = schemas.UserCreate(username="unit_test_user", email="unit@test.com", password="password")
    user = crud.create_user(db, user=user_in)

    # Verify session was created
    session = db.query(models.Session).filter(models.Session.created_by_id == user.id).first()
    assert session is not None
    assert session.name is None

    # Verify user is the owner
    member = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session.id,
        models.SessionMember.user_id == user.id
    ).first()
    assert member is not None
    assert member.role == "owner"

def test_create_team_session(db: Session):
    """Unit test for crud.create_team_session."""
    user = crud.create_user(db, schemas.UserCreate(username="owner", email="owner@test.com", password="p"))
    session_in = schemas.SessionCreate(name="Test Team")
    session = crud.create_team_session(db, session=session_in, owner_id=user.id)

    assert session.name == "Test Team"
    assert session.created_by_id == user.id
    
    member = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session.id,
        models.SessionMember.user_id == user.id
    ).first()
    assert member is not None
    assert member.role == "owner"

def test_invite_user_to_session(db: Session):
    """Unit test for crud.invite_user_to_session."""
    owner = crud.create_user(db, schemas.UserCreate(username="owner_invite", email="owner_invite@test.com", password="p"))
    invitee = crud.create_user(db, schemas.UserCreate(username="invitee", email="invitee@test.com", password="p"))
    session = crud.create_team_session(db, schemas.SessionCreate(name="Invite Test"), owner_id=owner.id)

    member = crud.invite_user_to_session(db, session_id=session.id, invitee_email=invitee.email)
    assert member is not None
    assert member.user_id == invitee.id
    assert member.role == "collaborator"
    
    # Test inviting an already existing member
    duplicate_invite = crud.invite_user_to_session(db, session_id=session.id, invitee_email=invitee.email)
    assert duplicate_invite is None

def test_get_sessions_for_user(db: Session):
    """Unit test for crud.get_sessions_for_user."""
    user1 = crud.create_user(db, schemas.UserCreate(username="user1_get", email="user1@get.com", password="p"))
    user2 = crud.create_user(db, schemas.UserCreate(username="user2_get", email="user2@get.com", password="p"))
    session1 = crud.create_team_session(db, schemas.SessionCreate(name="Team 1"), owner_id=user1.id)
    session2 = crud.create_team_session(db, schemas.SessionCreate(name="Team 2"), owner_id=user2.id)
    crud.invite_user_to_session(db, session_id=session2.id, invitee_email=user1.email)

    user1_sessions = crud.get_sessions_for_user(db, user_id=user1.id)
    # 2 teams + 1 private session
    assert len(user1_sessions) == 3

def test_get_session_members(db: Session):
    """Unit test for crud.get_session_members."""
    owner = crud.create_user(db, schemas.UserCreate(username="owner_get_m", email="owner_get_m@test.com", password="p"))
    c1 = crud.create_user(db, schemas.UserCreate(username="c1_get_m", email="c1_get_m@test.com", password="p"))
    session = crud.create_team_session(db, schemas.SessionCreate(name="Members Test"), owner_id=owner.id)
    crud.invite_user_to_session(db, session_id=session.id, invitee_email=c1.email)

    members = crud.get_session_members(db, session_id=session.id)
    assert len(members) == 2
    member_map = {m.username: m for m in members}
    assert member_map["owner_get_m"].role == "owner"
    assert member_map["c1_get_m"].role == "collaborator"

def test_get_todos_by_session(db: Session):
    """Unit test for crud.get_todos_by_session."""
    user = crud.create_user(db, schemas.UserCreate(username="todo_user", email="todo@test.com", password="p"))
    team_session = crud.create_team_session(db, schemas.SessionCreate(name="Todo Team"), owner_id=user.id)
    
    # Create one public and one private todo for the user
    private_todo_in = schemas.TodoCreate(title="Private")
    crud.create_todo(db, todo=private_todo_in, owner_id=user.id)
    team_todo_in = schemas.TodoCreate(title="Team", session_id=team_session.id)
    crud.create_todo(db, todo=team_todo_in, owner_id=user.id)
    
    team_todos = crud.get_todos_by_session(db, session_id=team_session.id)
    assert len(team_todos) == 1
    assert team_todos[0].title == "Team"
    
    # Test filtering
    user2 = crud.create_user(db, schemas.UserCreate(username="user2_todo", email="user2@todo.com", password="p"))
    crud.invite_user_to_session(db, session_id=team_session.id, invitee_email=user2.email)
    team_todo_2_in = schemas.TodoCreate(title="Team 2", session_id=team_session.id)
    crud.create_todo(db, todo=team_todo_2_in, owner_id=user2.id)

    user2_todos = crud.get_todos_by_session(db, session_id=team_session.id, user_id_filter=user2.id)
    assert len(user2_todos) == 1
    assert user2_todos[0].title == "Team 2" 
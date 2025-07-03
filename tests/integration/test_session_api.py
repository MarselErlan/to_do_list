from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import models

def test_private_session_is_created_for_new_user(client: TestClient, db: Session):
    """
    When a new user is created, a private session should be automatically
    created for them, and they should be the owner of that session.
    """
    # 1. Create a new user
    user_data = {
        "username": "testsessionuser",
        "email": "session@example.com",
        "password": "testpassword"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    new_user = response.json()
    user_id = new_user["id"]

    # 2. Verify the private session was created
    private_session = db.query(models.Session).filter(
        models.Session.created_by_id == user_id
    ).first()
    assert private_session is not None
    assert private_session.name is None  # Private sessions are unnamed

    # 3. Verify the user is the owner of the session
    session_member = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == private_session.id,
        models.SessionMember.user_id == user_id
    ).first()
    assert session_member is not None
    assert session_member.role == "owner"

def test_create_todo_is_added_to_private_session(authenticated_client: TestClient, db: Session):
    """
    When an authenticated user creates a new todo, it should be automatically
    added to their private session and marked as private.
    """
    # The authenticated_client fixture provides a user and their auth headers
    # We need to get that user's ID to find their private session
    user = db.query(models.User).filter(models.User.username == "testuser").first()
    assert user is not None

    private_session = db.query(models.Session).filter(
        models.Session.created_by_id == user.id
    ).first()
    assert private_session is not None

    # 1. Create a new todo
    todo_data = {"title": "My Private Todo"}
    response = authenticated_client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    new_todo = response.json()

    # 2. Verify it's linked to the private session and marked as private
    db_todo = db.query(models.Todo).filter(models.Todo.id == new_todo["id"]).first()
    assert db_todo is not None
    assert db_todo.session_id == private_session.id
    assert db_todo.is_private is True

def test_create_team_session(authenticated_client: TestClient, db: Session):
    """
    An authenticated user should be able to create a new team session.
    They should become the owner of this new session.
    """
    # Get the authenticated user
    user = db.query(models.User).filter(models.User.username == "testuser").first()
    assert user is not None

    # 1. Create a new team session
    session_data = {"name": "My New Team"}
    response = authenticated_client.post("/sessions/", json=session_data)
    assert response.status_code == 200
    new_session = response.json()

    # 2. Verify the session was created in the database
    db_session = db.query(models.Session).filter(models.Session.id == new_session["id"]).first()
    assert db_session is not None
    assert db_session.name == "My New Team"
    assert db_session.created_by_id == user.id

    # 3. Verify the user is the owner
    member = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == db_session.id,
        models.SessionMember.user_id == user.id
    ).first()
    assert member is not None
    assert member.role == "owner"

def test_invite_user_to_team_session(client: TestClient, db: Session):
    """
    The owner of a session should be able to invite another user to the session.
    The invited user should be added as a collaborator.
    """
    # 1. Create session owner and another user to invite
    owner_data = {"username": "owner", "email": "owner@test.com", "password": "password"}
    client.post("/users/", json=owner_data)
    invitee_data = {"username": "invitee", "email": "invitee@test.com", "password": "password"}
    client.post("/users/", json=invitee_data)
    
    # Log in as owner to get token
    login_response = client.post("/token", data={"username": "owner", "password": "password"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Owner creates a team session
    session_response = client.post("/sessions/", json={"name": "Team Invite Test"}, headers=headers)
    session_id = session_response.json()["id"]

    # 3. Owner invites the other user
    invite_data = {"email": "invitee@test.com"}
    invite_response = client.post(f"/sessions/{session_id}/invite", json=invite_data, headers=headers)
    assert invite_response.status_code == 200
    assert invite_response.json()["message"] == "User invited successfully"

    # 4. Verify the user was added as a collaborator
    invitee_user = db.query(models.User).filter(models.User.email == "invitee@test.com").first()
    member = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session_id,
        models.SessionMember.user_id == invitee_user.id
    ).first()
    assert member is not None
    assert member.role == "collaborator"

def test_view_team_session_todos(client: TestClient, db: Session):
    """
    Test viewing todos in a team session, including role permissions and filtering.
    - Owner can see all todos.
    - Collaborator can see all todos.
    - Anyone in the session can filter to see todos by a specific user.
    """
    # 1. Create owner, collaborator1, and collaborator2
    client.post("/users/", json={"username": "owner2", "email": "owner2@test.com", "password": "p"})
    client.post("/users/", json={"username": "c1", "email": "c1@test.com", "password": "p"})
    client.post("/users/", json={"username": "c2", "email": "c2@test.com", "password": "p"})

    # 2. Owner logs in, creates a session, and invites collaborators
    owner_token = client.post("/token", data={"username": "owner2", "password": "p"}).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    session_id = client.post("/sessions/", json={"name": "Viewing Test"}, headers=owner_headers).json()["id"]
    client.post(f"/sessions/{session_id}/invite", json={"email": "c1@test.com"}, headers=owner_headers)
    client.post(f"/sessions/{session_id}/invite", json={"email": "c2@test.com"}, headers=owner_headers)
    
    # 3. Each user creates a todo in their own private session (these should NOT be visible)
    c1_token = client.post("/token", data={"username": "c1", "password": "p"}).json()["access_token"]
    c1_headers = {"Authorization": f"Bearer {c1_token}"}
    client.post("/todos/", json={"title": "C1 Private"}, headers=c1_headers)

    # 4. Owner and Collaborator create todos in the TEAM session
    client.post("/todos/", json={"title": "Owner Team Todo 1", "session_id": session_id}, headers=owner_headers)
    client.post("/todos/", json={"title": "Owner Team Todo 2", "session_id": session_id}, headers=owner_headers)
    client.post("/todos/", json={"title": "C1 Team Todo", "session_id": session_id}, headers=c1_headers)

    # 5. Test Viewing Logic
    # Owner should see all 3 team todos
    response = client.get(f"/sessions/{session_id}/todos", headers=owner_headers)
    assert response.status_code == 200
    assert len(response.json()) == 3

    # Collaborator1 should also see all 3 team todos
    response = client.get(f"/sessions/{session_id}/todos", headers=c1_headers)
    assert response.status_code == 200
    assert len(response.json()) == 3

    # 6. Test Filtering
    owner_user = db.query(models.User).filter_by(username="owner2").first()
    c1_user = db.query(models.User).filter_by(username="c1").first()

    # Collaborator1 filters for owner's todos (should see 2)
    response = client.get(f"/sessions/{session_id}/todos?user_id={owner_user.id}", headers=c1_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["title"] in ["Owner Team Todo 1", "Owner Team Todo 2"]

    # Owner filters for C1's todos (should see 1)
    response = client.get(f"/sessions/{session_id}/todos?user_id={c1_user.id}", headers=owner_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "C1 Team Todo"

def test_get_all_user_sessions(client: TestClient, db: Session):
    """
    A user should be able to retrieve a list of all sessions they are a member of,
    including their private session and team sessions.
    """
    # 1. Create two users
    user1_data = {"username": "user1_sessions", "email": "user1@sessions.com", "password": "p"}
    user2_data = {"username": "user2_sessions", "email": "user2@sessions.com", "password": "p"}
    client.post("/users/", json=user1_data)
    client.post("/users/", json=user2_data)

    # 2. Log in as both users and create sessions
    user1_token = client.post("/token", data={"username": "user1_sessions", "password": "p"}).json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    user2_token = client.post("/token", data={"username": "user2_sessions", "password": "p"}).json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}

    # User1 creates a team session
    client.post("/sessions/", json={"name": "U1 Team"}, headers=user1_headers)
    # User2 creates a team session and invites User1
    session2_id = client.post("/sessions/", json={"name": "U2 Team"}, headers=user2_headers).json()["id"]
    client.post(f"/sessions/{session2_id}/invite", json={"email": "user1@sessions.com"}, headers=user2_headers)

    # 3. Get all sessions for User1
    response = client.get("/sessions/", headers=user1_headers)
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 3 # Private session, U1 Team, U2 Team

    # 4. Verify the contents
    session_names = {s["name"] for s in sessions}
    assert None in session_names # Private session has no name
    assert "U1 Team" in session_names
    assert "U2 Team" in session_names

def test_get_session_members(client: TestClient, db: Session):
    """
    A member of a session should be able to retrieve a list of all members
    of that session.
    """
    # 1. Create owner and collaborator
    owner_data = {"username": "owner_members", "email": "owner@members.com", "password": "p"}
    c1_data = {"username": "c1_members", "email": "c1@members.com", "password": "p"}
    client.post("/users/", json=owner_data)
    client.post("/users/", json=c1_data)

    # 2. Owner logs in, creates a session, and invites collaborator
    owner_token = client.post("/token", data={"username": "owner_members", "password": "p"}).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    session_id = client.post("/sessions/", json={"name": "Membership Test"}, headers=owner_headers).json()["id"]
    client.post(f"/sessions/{session_id}/invite", json={"email": "c1@members.com"}, headers=owner_headers)

    # 3. Get the list of members
    response = client.get(f"/sessions/{session_id}/members", headers=owner_headers)
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2

    # 4. Verify the contents
    member_info = {m["username"]: m["role"] for m in members}
    assert member_info.get("owner_members") == "owner"
    assert member_info.get("c1_members") == "collaborator"

def test_non_owner_cannot_invite_to_session(client: TestClient, db: Session):
    """
    Verify that only the owner of a session can invite new members.
    A collaborator's attempt to invite should be rejected.
    """
    # 1. Create owner, collaborator, and a third user
    owner_data = {"username": "owner_neg", "email": "owner@neg.com", "password": "p"}
    c1_data = {"username": "c1_neg", "email": "c1@neg.com", "password": "p"}
    c2_data = {"username": "c2_neg", "email": "c2@neg.com", "password": "p"}
    client.post("/users/", json=owner_data)
    client.post("/users/", json=c1_data)
    client.post("/users/", json=c2_data)

    # 2. Owner creates session and invites collaborator
    owner_token = client.post("/token", data={"username": "owner_neg", "password": "p"}).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    session_id = client.post("/sessions/", json={"name": "Invite Rights Test"}, headers=owner_headers).json()["id"]
    client.post(f"/sessions/{session_id}/invite", json={"email": "c1@neg.com"}, headers=owner_headers)

    # 3. Collaborator logs in and attempts to invite the third user
    c1_token = client.post("/token", data={"username": "c1_neg", "password": "p"}).json()["access_token"]
    c1_headers = {"Authorization": f"Bearer {c1_token}"}
    invite_response = client.post(f"/sessions/{session_id}/invite", json={"email": "c2@neg.com"}, headers=c1_headers)

    # 4. Assert the attempt was forbidden
    assert invite_response.status_code == 403
    assert invite_response.json()["detail"] == "Only the session owner can invite users"

def test_non_member_cannot_create_todo_in_session(client: TestClient, db: Session):
    """
    Verify that a user cannot create a to-do in a session they are not a member of.
    """
    # 1. Create two users
    user1_data = {"username": "member_user", "email": "member@test.com", "password": "p"}
    user2_data = {"username": "non_member_user", "email": "nonmember@test.com", "password": "p"}
    client.post("/users/", json=user1_data)
    client.post("/users/", json=user2_data)

    # 2. User 1 creates a session
    user1_token = client.post("/token", data={"username": "member_user", "password": "p"}).json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    session_id = client.post("/sessions/", json={"name": "Membership Required"}, headers=user1_headers).json()["id"]

    # 3. User 2 (a non-member) logs in and attempts to create a todo in the session
    user2_token = client.post("/token", data={"username": "non_member_user", "password": "p"}).json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    todo_data = {"title": "Trespasser Todo", "session_id": session_id}
    response = client.post("/todos/", json=todo_data, headers=user2_headers)

    # 4. Assert the attempt was forbidden
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"]

def test_non_member_cannot_view_session_data(client: TestClient, db: Session):
    """
    Verify that a user who is not a member of a session cannot get that
    session's todos or member list.
    """
    # 1. Create two users
    user1_data = {"username": "member_viewer", "email": "member_viewer@test.com", "password": "p"}
    user2_data = {"username": "non_member_viewer", "email": "nonmember_viewer@test.com", "password": "p"}
    client.post("/users/", json=user1_data)
    client.post("/users/", json=user2_data)

    # 2. User 1 creates a session
    user1_token = client.post("/token", data={"username": "member_viewer", "password": "p"}).json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    session_id = client.post("/sessions/", json={"name": "Viewing Rights Test"}, headers=user1_headers).json()["id"]

    # 3. User 2 (a non-member) logs in and attempts to view session data
    user2_token = client.post("/token", data={"username": "non_member_viewer", "password": "p"}).json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    
    # Attempt to get todos
    todos_response = client.get(f"/sessions/{session_id}/todos", headers=user2_headers)
    assert todos_response.status_code == 403
    assert "not a member" in todos_response.json()["detail"]

    # Attempt to get members
    members_response = client.get(f"/sessions/{session_id}/members", headers=user2_headers)
    assert members_response.status_code == 403
    assert "not a member" in members_response.json()["detail"] 
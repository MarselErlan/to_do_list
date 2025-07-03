from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import models
from app import crud

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

def test_public_and_private_todo_visibility(client: TestClient, db: Session):
    """
    Tests that a user can create both private and public todos, and that
    fetching all todos returns both with correct visibility flags.
    """
    # 1. Create a new user
    user_data = {
        "username": "visibility_user",
        "email": "visibility@example.com",
        "password": "testpassword"
    }
    client.post("/users/", json=user_data)

    # 2. Log in as the new user to get an access token
    login_response = client.post("/token", data={"username": "visibility_user", "password": "testpassword"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create a team session (for public todos)
    team_session_name = "Public Todos Team"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 4. Create a private todo (should automatically link to private session)
    private_todo_title = "My Secret Todo"
    private_todo_data = {"title": private_todo_title, "description": "Only for me"}
    private_todo_response = client.post("/todos/", json=private_todo_data, headers=headers)
    assert private_todo_response.status_code == 200
    assert private_todo_response.json()["is_private"] is True

    # 5. Create a public todo (linked to the team session)
    public_todo_title = "Team Shared Todo"
    public_todo_data = {"title": public_todo_title, "description": "For the team", "session_id": team_session_id}
    public_todo_response = client.post("/todos/", json=public_todo_data, headers=headers)
    assert public_todo_response.status_code == 200
    assert public_todo_response.json()["is_private"] is False
    assert public_todo_response.json()["session_id"] == team_session_id

    # 6. Fetch all todos for the user
    all_todos_response = client.get("/todos/", headers=headers)
    assert all_todos_response.status_code == 200
    all_todos = all_todos_response.json()

    # 7. Assert both todos are present with correct visibility
    assert len(all_todos) == 2

    private_found = False
    public_found = False

    for todo in all_todos:
        if todo["title"] == private_todo_title:
            assert todo["is_private"] is True
            private_found = True
        elif todo["title"] == public_todo_title:
            assert todo["is_private"] is False
            public_found = True

    assert private_found is True
    assert public_found is True

def test_change_public_todo_to_private(client: TestClient, db: Session):
    """
    Tests that a user can change a public todo (in a team session) back to a private todo.
    """
    # 1. Create user and log in
    user_data = {"username": "public_to_private_user", "email": "public_to_private@example.com", "password": "password"}
    client.post("/users/", json=user_data)

    login_response = client.post("/token", data={"username": "public_to_private_user", "password": "password"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_obj = crud.get_user_by_username(db, username="public_to_private_user")
    assert user_obj

    # 2. Create a team session
    team_session_name = "Private Conversion Team"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 3. Create a public todo in the team session
    public_todo_title = "Initially Public Todo"
    public_todo_data = {"title": public_todo_title, "session_id": team_session_id}
    create_response = client.post("/todos/", json=public_todo_data, headers=headers)
    assert create_response.status_code == 200
    created_todo = create_response.json()
    created_todo_id = created_todo["id"]
    assert created_todo["is_private"] is False
    assert created_todo["session_id"] == team_session_id

    # Verify it's visible via the team session endpoint before conversion
    team_todos_response_before = client.get(f"/sessions/{team_session_id}/todos", headers=headers)
    assert team_todos_response_before.status_code == 200
    assert len(team_todos_response_before.json()) == 1

    # 4. Update the todo to make it private (by setting session_id to null)
    update_data = {"session_id": None}
    update_response = client.put(f"/todos/{created_todo_id}", json=update_data, headers=headers)
    
    # This assertion will initially fail (Red step)
    assert update_response.status_code == 200
    updated_todo = update_response.json()
    assert updated_todo["is_private"] is True
    
    # Fetch the user's private session ID for comparison
    user_private_session = crud.get_private_session_for_user(db, user_obj.id)
    assert user_private_session is not None
    assert updated_todo["session_id"] == user_private_session.id

    # Verify it's no longer visible via the team session endpoint
    team_todos_response_after = client.get(f"/sessions/{team_session_id}/todos", headers=headers)
    assert team_todos_response_after.status_code == 200
    assert len(team_todos_response_after.json()) == 0

    # Verify it is visible via the user's private todos endpoint
    private_todos_response = client.get("/todos/", headers=headers)
    assert private_todos_response.status_code == 200
    private_todos = private_todos_response.json()
    assert len(private_todos) == 1
    assert private_todos[0]["title"] == public_todo_title
    assert private_todos[0]["is_private"] is True

def test_move_todo_between_team_sessions(client: TestClient, db: Session):
    """
    Tests that a user can move a public todo from one team session to another.
    """
    # 1. Create user and log in
    user_data = {"username": "move_todo_user", "email": "move_todo@example.com", "password": "password"}
    client.post("/users/", json=user_data)

    login_response = client.post("/token", data={"username": "move_todo_user", "password": "password"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_obj = crud.get_user_by_username(db, username="move_todo_user")
    assert user_obj

    # 2. Create two team sessions (TeamA and TeamB)
    team_a_response = client.post("/sessions/", json={"name": "Team A"}, headers=headers)
    assert team_a_response.status_code == 200
    team_a_id = team_a_response.json()["id"]

    team_b_response = client.post("/sessions/", json={"name": "Team B"}, headers=headers)
    assert team_b_response.status_code == 200
    team_b_id = team_b_response.json()["id"]

    # 3. Create a public todo in TeamA
    todo_title = "Todo to Move"
    create_response = client.post("/todos/", json={
        "title": todo_title,
        "session_id": team_a_id
    }, headers=headers)
    assert create_response.status_code == 200
    created_todo = create_response.json()
    created_todo_id = created_todo["id"]
    assert created_todo["is_private"] is False
    assert created_todo["session_id"] == team_a_id

    # Verify it's visible in TeamA and not in TeamB initially
    team_a_todos = client.get(f"/sessions/{team_a_id}/todos", headers=headers).json()
    assert len(team_a_todos) == 1
    assert team_a_todos[0]["title"] == todo_title

    team_b_todos = client.get(f"/sessions/{team_b_id}/todos", headers=headers).json()
    assert len(team_b_todos) == 0

    # 4. Move the todo to TeamB
    update_response = client.put(f"/todos/{created_todo_id}", json={
        "session_id": team_b_id
    }, headers=headers)

    # This assertion will initially fail (Red step if logic is missing)
    assert update_response.status_code == 200
    updated_todo = update_response.json()
    assert updated_todo["session_id"] == team_b_id
    assert updated_todo["is_private"] is False

    # Verify it's no longer visible in TeamA and now visible in TeamB
    team_a_todos_after = client.get(f"/sessions/{team_a_id}/todos", headers=headers).json()
    assert len(team_a_todos_after) == 0

    team_b_todos_after = client.get(f"/sessions/{team_b_id}/todos", headers=headers).json()
    assert len(team_b_todos_after) == 1
    assert team_b_todos_after[0]["title"] == todo_title
    assert team_b_todos_after[0]["session_id"] == team_b_id

def test_non_member_cannot_view_session_members(client: TestClient, db: Session):
    """
    Tests that a user who is not a member of a session cannot view its members list.
    """
    # 1. Create User1 (session owner) and log in
    user1_data = {"username": "owner_user_members", "email": "owner_members@example.com", "password": "password"}
    client.post("/users/", json=user1_data)
    login_response_user1 = client.post("/token", data={"username": "owner_user_members", "password": "password"})
    assert login_response_user1.status_code == 200
    token_user1 = login_response_user1.json()["access_token"]
    headers_user1 = {"Authorization": f"Bearer {token_user1}"}

    # 2. Create User2 (non-member) and log in
    user2_data = {"username": "non_member_user_members", "email": "non_member_members@example.com", "password": "password"}
    client.post("/users/", json=user2_data)
    login_response_user2 = client.post("/token", data={"username": "non_member_user_members", "password": "password"})
    assert login_response_user2.status_code == 200
    token_user2 = login_response_user2.json()["access_token"]
    headers_user2 = {"Authorization": f"Bearer {token_user2}"}

    # 3. User1 creates a team session
    team_session_name = "Restricted Members Team"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=headers_user1)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 4. User2 (non-member) attempts to view the session members
    response = client.get(f"/sessions/{team_session_id}/members", headers=headers_user2)

    # This assertion will initially fail if the endpoint is not properly secured
    assert response.status_code == 403
    assert response.json()["detail"] == "User is not a member of this session"

def test_collaborator_cannot_invite_user_to_session(client: TestClient, db: Session):
    """
    Tests that a collaborator (non-owner) cannot invite a new user to a session.
    """
    # 1. Create owner user and log in
    owner_data = {"username": "owner_invite_test", "email": "owner.invite@example.com", "password": "password"}
    client.post("/users/", json=owner_data)
    owner_login_response = client.post("/token", data={"username": "owner_invite_test", "password": "password"})
    assert owner_login_response.status_code == 200
    owner_token = owner_login_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Create collaborator user and log in
    collaborator_data = {"username": "collaborator_invite_test", "email": "collaborator.invite@example.com", "password": "password"}
    client.post("/users/", json=collaborator_data)
    collaborator_login_response = client.post("/token", data={"username": "collaborator_invite_test", "password": "password"})
    assert collaborator_login_response.status_code == 200
    collaborator_token = collaborator_login_response.json()["access_token"]
    collaborator_headers = {"Authorization": f"Bearer {collaborator_token}"}

    # 3. Create a new user to be invited later (by owner and then by collaborator)
    new_user_data = {"username": "new_invited_user", "email": "new.invited@example.com", "password": "password"}
    client.post("/users/", json=new_user_data)

    # 4. Owner creates a team session
    team_session_name = "Owner Invite Team"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=owner_headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 5. Owner invites the collaborator to the session
    invite_collaborator_data = {"email": collaborator_data["email"]}
    invite_response_owner = client.post(f"/sessions/{team_session_id}/invite", json=invite_collaborator_data, headers=owner_headers)
    assert invite_response_owner.status_code == 200

    # 6. Collaborator (non-owner) attempts to invite the new user to the session
    invite_new_user_data = {"email": new_user_data["email"]}
    invite_response_collaborator = client.post(f"/sessions/{team_session_id}/invite", json=invite_new_user_data, headers=collaborator_headers)

    # This assertion will initially fail if collaborator can invite
    assert invite_response_collaborator.status_code == 403
    assert invite_response_collaborator.json()["detail"] == "Only the session owner can invite users"

def test_direct_private_todo_access_by_non_owner_fails(client: TestClient, db: Session):
    """
    Tests that a user cannot directly access a private todo belonging to another user.
    """
    # 1. Create User1 and log in (owner of the private todo)
    user1_data = {"username": "owner_private_todo", "email": "owner.private@example.com", "password": "password"}
    client.post("/users/", json=user1_data)
    login_response_user1 = client.post("/token", data={"username": "owner_private_todo", "password": "password"})
    assert login_response_user1.status_code == 200
    token_user1 = login_response_user1.json()["access_token"]
    headers_user1 = {"Authorization": f"Bearer {token_user1}"}
    user1_obj = crud.get_user_by_username(db, username="owner_private_todo")
    assert user1_obj

    # 2. Create User2 and log in (non-owner attempting access)
    user2_data = {"username": "non_owner_private_todo", "email": "non.owner.private@example.com", "password": "password"}
    client.post("/users/", json=user2_data)
    login_response_user2 = client.post("/token", data={"username": "non_owner_private_todo", "password": "password"})
    assert login_response_user2.status_code == 200
    token_user2 = login_response_user2.json()["access_token"]
    headers_user2 = {"Authorization": f"Bearer {token_user2}"}

    # 3. User1 creates a private todo
    private_todo_title = "User1's Secret Todo"
    create_response = client.post("/todos/", json={
        "title": private_todo_title
    }, headers=headers_user1)
    assert create_response.status_code == 200
    created_todo = create_response.json()
    private_todo_id = created_todo["id"]
    assert created_todo["is_private"] is True
    assert created_todo["owner_id"] == user1_obj.id

    # 4. User2 attempts to retrieve User1's private todo by its ID
    response_user2 = client.get(f"/todos/{private_todo_id}", headers=headers_user2)

    # This assertion will initially fail if not properly secured
    assert response_user2.status_code == 403
    assert response_user2.json()["detail"] == "Not enough permissions"

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

def test_full_team_collaboration_workflow(client: TestClient, db: Session):
    """
    Comprehensive test for team collaboration: multiple users create public todos,
    a team is formed, users are invited, and a user can view and filter team todos.
    """
    # 1. Create and log in users
    user1_data = {"username": "user1_team", "email": "user1_team@example.com", "password": "password"}
    user2_data = {"username": "user2_team", "email": "user2_team@example.com", "password": "password"}
    user3_data = {"username": "user3_team", "email": "user3_team@example.com", "password": "password"}

    client.post("/users/", json=user1_data)
    client.post("/users/", json=user2_data)
    client.post("/users/", json=user3_data)

    user1_token = client.post("/token", data={"username": "user1_team", "password": "password"}).json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    user2_token = client.post("/token", data={"username": "user2_team", "password": "password"}).json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    # user3_token is not needed for direct actions, but for user_id filtering later

    # Get user IDs for filtering
    user1_obj = crud.get_user_by_username(db, username="user1_team")
    user2_obj = crud.get_user_by_username(db, username="user2_team")
    user3_obj = crud.get_user_by_username(db, username="user3_team")
    assert user1_obj and user2_obj and user3_obj

    # 2. User1 creates Team1
    team_name = "Team Alpha"
    team_session_response = client.post("/sessions/", json={"name": team_name}, headers=user1_headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 3. User1 invites User2 and User3 to Team1
    client.post(f"/sessions/{team_session_id}/invite", json={"email": user2_data["email"]}, headers=user1_headers)
    client.post(f"/sessions/{team_session_id}/invite", json={"email": user3_data["email"]}, headers=user1_headers)

    # 4. User1 creates a public todo in Team1
    user1_public_todo_title = "User1's Public Team Todo"
    user1_public_todo_data = {"title": user1_public_todo_title, "session_id": team_session_id}
    user1_public_todo_response = client.post("/todos/", json=user1_public_todo_data, headers=user1_headers)
    assert user1_public_todo_response.status_code == 200
    assert user1_public_todo_response.json()["is_private"] is False

    # 5. User2 creates a public todo in Team1
    user2_public_todo_title = "User2's Public Team Todo"
    user2_public_todo_data = {"title": user2_public_todo_title, "session_id": team_session_id}
    user2_public_todo_response = client.post("/todos/", json=user2_public_todo_data, headers=user2_headers)
    assert user2_public_todo_response.status_code == 200
    assert user2_public_todo_response.json()["is_private"] is False

    # 6. Verify User1 can see all users in Team1
    members_response = client.get(f"/sessions/{team_session_id}/members", headers=user1_headers)
    assert members_response.status_code == 200
    members = members_response.json()
    member_usernames = {m["username"] for m in members}
    assert len(members) == 3
    assert "user1_team" in member_usernames
    assert "user2_team" in member_usernames
    assert "user3_team" in member_usernames

    # 7. Verify User1 can filter to see only User2's public todo in Team1
    user1_filtered_todos_response = client.get(f"/sessions/{team_session_id}/todos?user_id={user2_obj.id}", headers=user1_headers)
    assert user1_filtered_todos_response.status_code == 200
    filtered_todos = user1_filtered_todos_response.json()
    assert len(filtered_todos) == 1
    assert filtered_todos[0]["title"] == user2_public_todo_title
    assert filtered_todos[0]["is_private"] is False
    assert filtered_todos[0]["owner_id"] == user2_obj.id

def test_change_private_todo_to_public(client: TestClient, db: Session):
    """
    Tests that a user can change a private todo to a public todo by assigning it to a team session.
    """
    # 1. Create user and log in
    user_data = {"username": "private_to_public_user", "email": "private_to_public@example.com", "password": "password"}
    client.post("/users/", json=user_data)

    login_response = client.post("/token", data={"username": "private_to_public_user", "password": "password"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_obj = crud.get_user_by_username(db, username="private_to_public_user")
    assert user_obj

    # 2. Create a team session
    team_session_name = "Public Conversion Team"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 3. Create an initial private todo (automatically assigned to private session)
    private_todo_title = "Initially Private Todo"
    private_todo_data = {"title": private_todo_title}
    create_response = client.post("/todos/", json=private_todo_data, headers=headers)
    assert create_response.status_code == 200
    created_todo = create_response.json()
    created_todo_id = created_todo["id"]
    assert created_todo["is_private"] is True
    assert created_todo["session_id"] is not None # Should be linked to user's private session

    # 4. Update the todo to make it public by assigning it to the team session
    update_data = {"session_id": team_session_id}
    update_response = client.put(f"/todos/{created_todo_id}", json=update_data, headers=headers)
    
    # This assertion will initially fail (Red step)
    assert update_response.status_code == 200
    updated_todo = update_response.json()
    assert updated_todo["is_private"] is False
    assert updated_todo["session_id"] == team_session_id

    # Verify it's now visible via the team session endpoint
    team_todos_response = client.get(f"/sessions/{team_session_id}/todos", headers=headers)
    assert team_todos_response.status_code == 200
    team_todos = team_todos_response.json()
    assert len(team_todos) == 1
    assert team_todos[0]["title"] == private_todo_title
    assert team_todos[0]["is_private"] is False

    assert updated_todo["owner_id"] == user_obj.id

def test_user_leaves_team_session_and_session_is_deleted(client: TestClient, db: Session):
    """
    Tests that when a session owner leaves a team session, the entire session is deleted,
    and all public todos within that session are reassigned to their respective owners' private sessions.
    """
    # 1. Create owner user and log in
    owner_data = {"username": "owner_leaving_session", "email": "owner.leaving@example.com", "password": "password"}
    client.post("/users/", json=owner_data)
    owner_login_response = client.post("/token", data={"username": "owner_leaving_session", "password": "password"})
    assert owner_login_response.status_code == 200
    owner_token = owner_login_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_obj = crud.get_user_by_username(db, username="owner_leaving_session")
    assert owner_obj

    # 2. Create collaborator user and log in
    collaborator_data = {"username": "collaborator_in_leaving_session", "email": "collab.leaving@example.com", "password": "password"}
    client.post("/users/", json=collaborator_data)
    collaborator_login_response = client.post("/token", data={"username": "collaborator_in_leaving_session", "password": "password"})
    assert collaborator_login_response.status_code == 200
    collaborator_token = collaborator_login_response.json()["access_token"]
    collaborator_headers = {"Authorization": f"Bearer {collaborator_token}"}
    collaborator_obj = crud.get_user_by_username(db, username="collaborator_in_leaving_session")
    assert collaborator_obj

    # 3. Owner creates a team session
    team_session_name = "Session to be Deleted by Owner Leave"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=owner_headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 4. Owner invites collaborator to the session
    invite_data = {"email": collaborator_data["email"]}
    invite_response = client.post(f"/sessions/{team_session_id}/invite", json=invite_data, headers=owner_headers)
    assert invite_response.status_code == 200

    # 5. Owner creates a public todo in the team session
    owner_todo_title = "Owner's Public Todo in Deleting Session"
    owner_todo_data = {"title": owner_todo_title, "session_id": team_session_id}
    owner_todo_response = client.post("/todos/", json=owner_todo_data, headers=owner_headers)
    assert owner_todo_response.status_code == 200
    owner_created_todo_id = owner_todo_response.json()["id"]

    # 6. Collaborator creates a public todo in the team session
    collaborator_todo_title = "Collaborator's Public Todo in Deleting Session"
    collaborator_todo_data = {"title": collaborator_todo_title, "session_id": team_session_id}
    collaborator_todo_response = client.post("/todos/", json=collaborator_todo_data, headers=collaborator_headers)
    assert collaborator_todo_response.status_code == 200
    collaborator_created_todo_id = collaborator_todo_response.json()["id"]

    # Verify both todos are visible in the team session initially (for owner)
    team_todos_before_leave = client.get(f"/sessions/{team_session_id}/todos", headers=owner_headers).json()
    assert len(team_todos_before_leave) == 2

    # 7. Owner leaves the team session (which should trigger deletion)
    leave_session_response = client.delete(f"/sessions/{team_session_id}/members/me", headers=owner_headers)
    assert leave_session_response.status_code == 200
    assert leave_session_response.json()["message"] == f"Session {team_session_id} deleted successfully."

    # 8. Verify the session is deleted (attempting to access should fail with 404)
    check_session_todos_response = client.get(f"/sessions/{team_session_id}/todos", headers=owner_headers)
    assert check_session_todos_response.status_code == 404

    check_session_members_response = client.get(f"/sessions/{team_session_id}/members", headers=owner_headers)
    assert check_session_members_response.status_code == 404

    # 9. Verify owner's todo is deleted (attempting to access should fail with 404)
    owner_todo_after_leave_response = client.get(f"/todos/{owner_created_todo_id}", headers=owner_headers)
    assert owner_todo_after_leave_response.status_code == 404

    # 10. Verify collaborator's todo is deleted (attempting to access should fail with 404)
    collaborator_todo_after_leave_response = client.get(f"/todos/{collaborator_created_todo_id}", headers=collaborator_headers)
    assert collaborator_todo_after_leave_response.status_code == 404

    # 11. Verify collaborator is no longer a member of the session
    check_collab_sessions_response = client.get("/sessions/", headers=collaborator_headers)
    assert check_collab_sessions_response.status_code == 200
    collab_sessions = check_collab_sessions_response.json()
    assert not any(s["id"] == team_session_id for s in collab_sessions)

def test_owner_removes_collaborator_from_session(client: TestClient, db: Session):
    """
    Tests that a session owner can remove a collaborator, and the collaborator's public todos
    in that session are reassigned to their private session.
    """
    # 1. Create owner and collaborator users and log in
    owner_data = {"username": "owner_remove_member", "email": "owner.remove@example.com", "password": "password"}
    client.post("/users/", json=owner_data)
    owner_login_response = client.post("/token", data={"username": "owner_remove_member", "password": "password"})
    assert owner_login_response.status_code == 200
    owner_token = owner_login_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_obj = crud.get_user_by_username(db, username="owner_remove_member")
    assert owner_obj

    collaborator_data = {"username": "collaborator_to_be_removed", "email": "removed.collaborator@example.com", "password": "password"}
    client.post("/users/", json=collaborator_data)
    collaborator_login_response = client.post("/token", data={"username": "collaborator_to_be_removed", "password": "password"})
    assert collaborator_login_response.status_code == 200
    collaborator_token = collaborator_login_response.json()["access_token"]
    collaborator_headers = {"Authorization": f"Bearer {collaborator_token}"}
    collaborator_obj = crud.get_user_by_username(db, username="collaborator_to_be_removed")
    assert collaborator_obj

    # 2. Owner creates a team session
    team_session_name = "Team for Member Removal Test"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=owner_headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 3. Owner invites collaborator to the session
    invite_data = {"email": collaborator_data["email"]}
    invite_response = client.post(f"/sessions/{team_session_id}/invite", json=invite_data, headers=owner_headers)
    assert invite_response.status_code == 200

    # 4. Collaborator creates a public todo in the team session
    collaborator_todo_title = "Collaborator's Todo in Team"
    collaborator_todo_data = {"title": collaborator_todo_title, "session_id": team_session_id}
    collaborator_todo_response = client.post("/todos/", json=collaborator_todo_data, headers=collaborator_headers)
    assert collaborator_todo_response.status_code == 200
    collaborator_created_todo_id = collaborator_todo_response.json()["id"]
    
    # Verify todo is visible in team session initially
    team_todos_before_remove = client.get(f"/sessions/{team_session_id}/todos", headers=owner_headers).json()
    assert any(t["id"] == collaborator_created_todo_id for t in team_todos_before_remove)

    # 5. Owner removes the collaborator from the session
    remove_member_response = client.delete(f"/sessions/{team_session_id}/members/{collaborator_obj.id}", headers=owner_headers)
    assert remove_member_response.status_code == 200
    assert remove_member_response.json()["message"] == "Successfully left session"

    # 6. Verify collaborator is no longer a member (attempt to get session members should fail for collaborator)
    check_members_response_collab = client.get(f"/sessions/{team_session_id}/members", headers=collaborator_headers)
    assert check_members_response_collab.status_code == 403
    assert check_members_response_collab.json()["detail"] == "User is not a member of this session"

    # 7. Verify collaborator's todo is now private and in their private session
    collaborator_todo_after_remove = client.get(f"/todos/{collaborator_created_todo_id}", headers=collaborator_headers).json()
    assert collaborator_todo_after_remove["is_private"] is True
    collab_private_session = crud.get_private_session_for_user(db, collaborator_obj.id)
    assert collaborator_todo_after_remove["session_id"] == collab_private_session.id

    # 8. Verify the todo is no longer visible via the team session endpoint (for owner)
    team_todos_after_remove = client.get(f"/sessions/{team_session_id}/todos", headers=owner_headers).json()
    assert not any(t["id"] == collaborator_created_todo_id for t in team_todos_after_remove)

def test_collaborator_cannot_remove_member_from_session(client: TestClient, db: Session):
    """
    Tests that a collaborator (non-owner) cannot remove another user from a session.
    """
    # 1. Create owner, collaborator, and a third user
    owner_data = {"username": "owner_no_remove", "email": "owner.no.remove@example.com", "password": "password"}
    client.post("/users/", json=owner_data)
    collab_data = {"username": "collab_no_remove", "email": "collab.no.remove@example.com", "password": "password"}
    client.post("/users/", json=collab_data)
    user_to_remove_data = {"username": "user_to_remove", "email": "user.to.remove@example.com", "password": "password"}
    client.post("/users/", json=user_to_remove_data)
    user_to_remove_obj = crud.get_user_by_username(db, username="user_to_remove")
    assert user_to_remove_obj

    # 2. Owner logs in and creates a session
    owner_login_response = client.post("/token", data={"username": "owner_no_remove", "password": "password"})
    assert owner_login_response.status_code == 200
    owner_token = owner_login_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    
    team_session_name = "Team for Restricted Removal"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=owner_headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 3. Owner invites collaborator and the user_to_remove to the session
    client.post(f"/sessions/{team_session_id}/invite", json={"email": collab_data["email"]}, headers=owner_headers)
    client.post(f"/sessions/{team_session_id}/invite", json={"email": user_to_remove_data["email"]}, headers=owner_headers)

    # 4. Collaborator logs in
    collab_login_response = client.post("/token", data={"username": "collab_no_remove", "password": "password"})
    assert collab_login_response.status_code == 200
    collab_token = collab_login_response.json()["access_token"]
    collab_headers = {"Authorization": f"Bearer {collab_token}"}

    # 5. Collaborator attempts to remove user_to_remove from the session
    remove_attempt_response = client.delete(f"/sessions/{team_session_id}/members/{user_to_remove_obj.id}", headers=collab_headers)

    # This assertion will initially fail if collaborator can remove members
    assert remove_attempt_response.status_code == 403
    assert remove_attempt_response.json()["detail"] == "Only the session owner can remove members."

    # Verify user_to_remove is still a member (owner should still see them)
    session_members_after_attempt = client.get(f"/sessions/{team_session_id}/members", headers=owner_headers).json()
    member_ids = [m["user_id"] for m in session_members_after_attempt]
    assert user_to_remove_obj.id in member_ids

def test_owner_can_update_session_name(client: TestClient, db: Session):
    """
    Tests that a session owner can successfully update the session's name.
    """
    # 1. Create owner user and log in
    owner_data = {"username": "owner_update_session", "email": "owner.update@example.com", "password": "password"}
    client.post("/users/", json=owner_data)
    owner_login_response = client.post("/token", data={"username": "owner_update_session", "password": "password"})
    assert owner_login_response.status_code == 200
    owner_token = owner_login_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Owner creates a team session
    old_session_name = "Original Session Name"
    create_session_response = client.post("/sessions/", json={"name": old_session_name}, headers=owner_headers)
    assert create_session_response.status_code == 200
    session_id = create_session_response.json()["id"]

    # 3. Owner updates the session name
    new_session_name = "Updated Session Name"
    update_data = {"name": new_session_name}
    update_response = client.put(f"/sessions/{session_id}", json=update_data, headers=owner_headers)
    assert update_response.status_code == 200
    updated_session = update_response.json()
    assert updated_session["name"] == new_session_name
    assert updated_session["id"] == session_id

    # 4. Verify the name change by fetching the session details
    fetch_session_response = client.get(f"/sessions/", headers=owner_headers)
    assert fetch_session_response.status_code == 200
    sessions = fetch_session_response.json()
    found_session = next((s for s in sessions if s["id"] == session_id), None)
    assert found_session
    assert found_session["name"] == new_session_name

def test_collaborator_cannot_update_session_name(client: TestClient, db: Session):
    """
    Tests that a collaborator (non-owner) cannot update a session's name.
    """
    # 1. Create owner and collaborator users and log in
    owner_data = {"username": "owner_no_update", "email": "owner.no.update@example.com", "password": "password"}
    client.post("/users/", json=owner_data)
    owner_login_response = client.post("/token", data={"username": "owner_no_update", "password": "password"})
    assert owner_login_response.status_code == 200
    owner_token = owner_login_response.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    collab_data = {"username": "collab_no_update", "email": "collab.no.update@example.com", "password": "password"}
    client.post("/users/", json=collab_data)
    collab_login_response = client.post("/token", data={"username": "collab_no_update", "password": "password"})
    assert collab_login_response.status_code == 200
    collab_token = collab_login_response.json()["access_token"]
    collab_headers = {"Authorization": f"Bearer {collab_token}"}

    # 2. Owner creates a team session
    original_session_name = "Session to Attempt Update"
    create_session_response = client.post("/sessions/", json={"name": original_session_name}, headers=owner_headers)
    assert create_session_response.status_code == 200
    session_id = create_session_response.json()["id"]

    # 3. Owner invites collaborator to the session
    invite_data = {"email": collab_data["email"]}
    invite_response = client.post(f"/sessions/{session_id}/invite", json=invite_data, headers=owner_headers)
    assert invite_response.status_code == 200

    # 4. Collaborator attempts to update the session name
    new_session_name_attempt = "Forbidden Updated Name"
    update_data = {"name": new_session_name_attempt}
    update_attempt_response = client.put(f"/sessions/{session_id}", json=update_data, headers=collab_headers)

    # This assertion will initially fail if collaborator can update
    assert update_attempt_response.status_code == 403
    assert update_attempt_response.json()["detail"] == "Only the session owner can update the session."

    # 5. Verify the session name was NOT changed by fetching with owner
    fetch_session_response = client.get(f"/sessions/", headers=owner_headers)
    assert fetch_session_response.status_code == 200
    sessions = fetch_session_response.json()
    found_session = next((s for s in sessions if s["id"] == session_id), None)
    assert found_session
    assert found_session["name"] == original_session_name 
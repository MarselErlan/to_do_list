from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_collaboration_smoke_workflow(client: TestClient, db: Session):
    """
    A high-level smoke test for the entire collaboration workflow:
    1. An owner creates a team session.
    2. The owner invites a collaborator.
    3. The collaborator creates a to-do in the team session.
    4. The owner can view the new to-do from the collaborator.
    """
    # 1. Create owner and collaborator users
    owner_data = {"username": "smoke_owner", "email": "smoke_owner@test.com", "password": "p"}
    collaborator_data = {"username": "smoke_collaborator", "email": "smoke_c1@test.com", "password": "p"}
    client.post("/users/", json=owner_data)
    client.post("/users/", json=collaborator_data)

    # 2. Owner logs in, creates a session, and invites the collaborator
    owner_token = client.post("/token", data={"username": "smoke_owner", "password": "p"}).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    session_id = client.post("/sessions/", json={"name": "Smoke Test Team"}, headers=owner_headers).json()["id"]
    client.post(f"/sessions/{session_id}/invite", json={"email": "smoke_c1@test.com"}, headers=owner_headers)

    # 3. Collaborator logs in and creates a to-do in the team session
    collaborator_token = client.post("/token", data={"username": "smoke_collaborator", "password": "p"}).json()["access_token"]
    collaborator_headers = {"Authorization": f"Bearer {collaborator_token}"}
    todo_data = {"title": "Collaborator Smoke Todo", "session_id": session_id}
    response = client.post("/todos/", json=todo_data, headers=collaborator_headers)
    assert response.status_code == 200

    # 4. Owner views the session todos and sees the new todo
    response = client.get(f"/sessions/{session_id}/todos", headers=owner_headers)
    assert response.status_code == 200
    todos = response.json()
    assert len(todos) == 1
    assert todos[0]["title"] == "Collaborator Smoke Todo" 
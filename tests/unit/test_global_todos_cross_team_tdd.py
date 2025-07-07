"""
TDD Tests for global todos - cross-team visibility
Testing that global todos are visible to ALL users across different teams/sessions
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, time
import json

from app import crud, schemas, models
from app.security import create_access_token

class TestGlobalTodosCrossTeamTDD:
    """TDD tests for global todos visibility across different teams and users"""

    def test_global_todos_visible_across_different_teams(self, client: TestClient, db: Session):
        """Test that global todos are visible to users in different teams"""
        # Create three users
        user1_data = schemas.UserCreate(username="teamuser1", password="pass1", email="team1@test.com")
        user2_data = schemas.UserCreate(username="teamuser2", password="pass2", email="team2@test.com")
        user3_data = schemas.UserCreate(username="teamuser3", password="pass3", email="team3@test.com")
        
        user1 = crud.create_user(db, user1_data)
        user2 = crud.create_user(db, user2_data)
        user3 = crud.create_user(db, user3_data)
        
        # Create two different team sessions
        team1_session = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Team 1", description="First team"),
            owner_id=user1.id
        )
        
        team2_session = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Team 2", description="Second team"),
            owner_id=user2.id
        )
        
        # User1 creates a global todo (should be visible to ALL users regardless of team)
        global_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Global Todo Visible to All",
                description="This should be visible to users in any team",
                is_global_public=True,
                is_private=False
            ),
            owner_id=user1.id
        )
        
        # User1 creates a team-specific todo in Team 1
        team1_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Team 1 Todo",
                description="This should only be visible to Team 1 members",
                is_global_public=False,
                is_private=False,
                session_id=team1_session.id
            ),
            owner_id=user1.id
        )
        
        # User2 creates a team-specific todo in Team 2
        team2_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Team 2 Todo",
                description="This should only be visible to Team 2 members",
                is_global_public=False,
                is_private=False,
                session_id=team2_session.id
            ),
            owner_id=user2.id
        )
        
        # User1 creates a private todo
        private_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="User1 Private Todo",
                description="This should only be visible to User1",
                is_private=True,
                is_global_public=False
            ),
            owner_id=user1.id
        )
        
        # Test User1 visibility (should see: global + team1 + private)
        login_data = {"username": "teamuser1", "password": "pass1"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token1 = response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        response = client.get("/todos/", headers=headers1)
        assert response.status_code == 200
        user1_todos = response.json()
        user1_titles = [todo["title"] for todo in user1_todos]
        
        assert "Global Todo Visible to All" in user1_titles
        assert "Team 1 Todo" in user1_titles
        assert "User1 Private Todo" in user1_titles
        # Should NOT see Team 2 todo
        assert "Team 2 Todo" not in user1_titles
        
        # Test User2 visibility (should see: global + team2, but NOT user1's private or team1 todos)
        login_data = {"username": "teamuser2", "password": "pass2"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token2 = response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response = client.get("/todos/", headers=headers2)
        assert response.status_code == 200
        user2_todos = response.json()
        user2_titles = [todo["title"] for todo in user2_todos]
        
        assert "Global Todo Visible to All" in user2_titles  # Global should be visible
        assert "Team 2 Todo" in user2_titles  # Own team todo
        # Should NOT see other team's todos or private todos
        assert "Team 1 Todo" not in user2_titles
        assert "User1 Private Todo" not in user2_titles
        
        # Test User3 visibility (not in any team, should only see global todos)
        login_data = {"username": "teamuser3", "password": "pass3"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token3 = response.json()["access_token"]
        headers3 = {"Authorization": f"Bearer {token3}"}
        
        response = client.get("/todos/", headers=headers3)
        assert response.status_code == 200
        user3_todos = response.json()
        user3_titles = [todo["title"] for todo in user3_todos]
        
        assert "Global Todo Visible to All" in user3_titles  # Global should be visible
        # Should NOT see any team-specific or private todos
        assert "Team 1 Todo" not in user3_titles
        assert "Team 2 Todo" not in user3_titles
        assert "User1 Private Todo" not in user3_titles

    def test_multiple_global_todos_from_different_users(self, client: TestClient, db: Session):
        """Test that global todos from different users are all visible to everyone"""
        # Create multiple users
        users = []
        for i in range(3):
            user_data = schemas.UserCreate(
                username=f"globaluser{i+1}", 
                password=f"pass{i+1}", 
                email=f"global{i+1}@test.com"
            )
            users.append(crud.create_user(db, user_data))
        
        # Each user creates a global todo
        global_todos = []
        for i, user in enumerate(users):
            global_todo = crud.create_todo(
                db=db,
                todo=schemas.TodoCreate(
                    title=f"Global Todo by User {i+1}",
                    description=f"Global todo created by user {i+1}",
                    is_global_public=True,
                    is_private=False
                ),
                owner_id=user.id
            )
            global_todos.append(global_todo)
        
        # Test that each user can see ALL global todos
        for i, user in enumerate(users):
            login_data = {"username": f"globaluser{i+1}", "password": f"pass{i+1}"}
            response = client.post("/token", data=login_data)
            assert response.status_code == 200
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = client.get("/todos/", headers=headers)
            assert response.status_code == 200
            user_todos = response.json()
            user_titles = [todo["title"] for todo in user_todos]
            
            # Should see all global todos
            for j in range(3):
                assert f"Global Todo by User {j+1}" in user_titles

    def test_global_todos_vs_team_todos_distinction(self, authenticated_client: TestClient, db: Session):
        """Test the clear distinction between global todos and team todos"""
        # Get current user
        response = authenticated_client.get("/users/me")
        assert response.status_code == 200
        user_data = response.json()
        user_id = user_data["id"]
        
        # Create a team session
        team_session = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Test Team", description="Team for testing"),
            owner_id=user_id
        )
        
        # Create different types of todos
        todos_to_create = [
            {
                "title": "Global Todo",
                "description": "Visible to ALL users everywhere",
                "is_global_public": True,
                "is_private": False
            },
            {
                "title": "Team Todo",
                "description": "Only visible to team members",
                "is_global_public": False,
                "is_private": False,
                "session_id": team_session.id
            },
            {
                "title": "Private Todo",
                "description": "Only visible to me",
                "is_private": True,
                "is_global_public": False
            },
            {
                "title": "Default Todo",
                "description": "Default behavior todo"
                # No flags set - should default to private
            }
        ]
        
        created_todos = []
        for todo_data in todos_to_create:
            response = authenticated_client.post("/todos/", json=todo_data)
            assert response.status_code == 200
            created_todos.append(response.json())
        
        # Verify properties
        global_todo = next(t for t in created_todos if t["title"] == "Global Todo")
        assert global_todo["is_global_public"] is True
        assert global_todo["is_private"] is False
        # Global todo will be assigned to user's private session (that's the backend logic)
        assert global_todo["session_id"] is not None
        
        team_todo = next(t for t in created_todos if t["title"] == "Team Todo")
        assert team_todo["is_global_public"] is False
        assert team_todo["is_private"] is False
        assert team_todo["session_id"] == team_session.id
        
        private_todo = next(t for t in created_todos if t["title"] == "Private Todo")
        assert private_todo["is_global_public"] is False
        assert private_todo["is_private"] is True
        
        default_todo = next(t for t in created_todos if t["title"] == "Default Todo")
        assert default_todo["is_global_public"] is False
        assert default_todo["is_private"] is True  # Default behavior

    def test_global_todos_frontend_scenario_cross_team(self, client: TestClient, db: Session):
        """Test the frontend scenario where global todos should persist across team switches"""
        # Create two users in different teams
        user1_data = schemas.UserCreate(username="frontend1", password="pass1", email="frontend1@test.com")
        user2_data = schemas.UserCreate(username="frontend2", password="pass2", email="frontend2@test.com")
        
        user1 = crud.create_user(db, user1_data)
        user2 = crud.create_user(db, user2_data)
        
        # Create two team sessions
        team1 = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Frontend Team 1", description="First frontend team"),
            owner_id=user1.id
        )
        
        team2 = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Frontend Team 2", description="Second frontend team"),
            owner_id=user2.id
        )
        
        # User1 creates a global todo
        global_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Global Frontend Todo",
                description="Should be visible when switching between teams",
                is_global_public=True,
                is_private=False
            ),
            owner_id=user1.id
        )
        
        # Login as user1 and verify they see the global todo
        login_data = {"username": "frontend1", "password": "pass1"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token1 = response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        response = client.get("/todos/", headers=headers1)
        assert response.status_code == 200
        user1_todos = response.json()
        user1_titles = [todo["title"] for todo in user1_todos]
        assert "Global Frontend Todo" in user1_titles
        
        # Login as user2 (different team) and verify they ALSO see the global todo
        login_data = {"username": "frontend2", "password": "pass2"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token2 = response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response = client.get("/todos/", headers=headers2)
        assert response.status_code == 200
        user2_todos = response.json()
        user2_titles = [todo["title"] for todo in user2_todos]
        assert "Global Frontend Todo" in user2_titles
        
        # This simulates the frontend scenario where switching teams/workspaces
        # should still show global todos

    def test_global_todos_cross_team_comprehensive(self, client: TestClient, db: Session):
        """Comprehensive test of global todos behavior across multiple teams and scenarios"""
        # Create 4 users
        users = []
        for i in range(4):
            user_data = schemas.UserCreate(
                username=f"compuser{i+1}", 
                password=f"pass{i+1}", 
                email=f"comp{i+1}@test.com"
            )
            users.append(crud.create_user(db, user_data))
        
        # Create 2 teams
        team1 = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Comp Team 1", description="First comprehensive team"),
            owner_id=users[0].id
        )
        
        team2 = crud.create_team_session(
            db=db,
            session=schemas.SessionCreate(name="Comp Team 2", description="Second comprehensive team"),
            owner_id=users[1].id
        )
        
        # Add user2 to team1 (so user2 is in both teams)
        crud.invite_user_to_session(db, team1.id, users[1].email)
        
        # Create various todos:
        # User1: Global todo
        global_todo1 = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Global by User1",
                description="Global todo by user 1",
                is_global_public=True,
                is_private=False
            ),
            owner_id=users[0].id
        )
        
        # User2: Global todo
        global_todo2 = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Global by User2",
                description="Global todo by user 2",
                is_global_public=True,
                is_private=False
            ),
            owner_id=users[1].id
        )
        
        # User1: Team1 todo
        team1_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Team1 Todo",
                description="Team 1 specific todo",
                is_global_public=False,
                is_private=False,
                session_id=team1.id
            ),
            owner_id=users[0].id
        )
        
        # User2: Team2 todo  
        team2_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Team2 Todo",
                description="Team 2 specific todo",
                is_global_public=False,
                is_private=False,
                session_id=team2.id
            ),
            owner_id=users[1].id
        )
        
        # User3: Private todo
        private_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Private Todo",
                description="Private todo by user 3",
                is_private=True,
                is_global_public=False
            ),
            owner_id=users[2].id
        )
        
        # Test each user's visibility
        expected_visibility = {
            "compuser1": ["Global by User1", "Global by User2", "Team1 Todo"],  # Team1 owner
            "compuser2": ["Global by User1", "Global by User2", "Team1 Todo", "Team2 Todo"],  # In both teams
            "compuser3": ["Global by User1", "Global by User2", "Private Todo"],  # No team membership
            "compuser4": ["Global by User1", "Global by User2"]  # No team membership, no private todos
        }
        
        for i, user in enumerate(users):
            username = f"compuser{i+1}"
            login_data = {"username": username, "password": f"pass{i+1}"}
            response = client.post("/token", data=login_data)
            assert response.status_code == 200
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            response = client.get("/todos/", headers=headers)
            assert response.status_code == 200
            user_todos = response.json()
            user_titles = [todo["title"] for todo in user_todos]
            
            expected_titles = expected_visibility[username]
            
            # Check that user sees all expected todos
            for expected_title in expected_titles:
                assert expected_title in user_titles, f"User {username} should see '{expected_title}'"
            
            # Check that user doesn't see unexpected todos
            all_possible_titles = [
                "Global by User1", "Global by User2", "Team1 Todo", 
                "Team2 Todo", "Private Todo"
            ]
            for title in all_possible_titles:
                if title not in expected_titles:
                    assert title not in user_titles, f"User {username} should NOT see '{title}'"

    def test_global_todos_unauthenticated_access_should_fail(self, client: TestClient, db: Session):
        """Test that unauthenticated users cannot access global todos through /todos/ endpoint"""
        # Create a user and a global todo
        user_data = schemas.UserCreate(username="globalcreator", password="pass", email="global@test.com")
        user = crud.create_user(db, user_data)
        
        global_todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(
                title="Global Todo for Auth Test",
                description="Global todo that should require auth to access",
                is_global_public=True,
                is_private=False
            ),
            owner_id=user.id
        )
        
        # Try to access /todos/ without authentication
        response = client.get("/todos/")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
        
        # Note: This test confirms that even global todos require authentication
        # to access through the /todos/ endpoint. If we wanted unauthenticated
        # access to global todos, we'd need a separate endpoint like /public-todos/

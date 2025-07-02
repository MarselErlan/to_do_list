# Frontend Integration Guide

This document outlines the recent backend changes and provides a guide for the frontend team to integrate with the new features and updated API.

## 1. Major Changes Overview

The backend has undergone significant changes, including:

- **Multi-User Support & JWT Authentication**: All To-Do list operations are now user-specific. Access to these endpoints requires a valid JSON Web Token (JWT).
- **Email Verification for Registration**: New users must verify their email address with a code before they can register.
- **Password Reset Flow**: Users can securely reset their password via an email-based code verification system.
- **Database Schema Changes**: The `datetime` fields for tasks have been separated into `date` and `time` fields.

## 2. API Health Check

Before making any authenticated requests, you can check if the API is online and reachable.

- **Endpoint**: `GET /health`
- **Authentication**: None required.
- **Description**: A simple endpoint to confirm the backend server is running.
- **Success Response (200 OK)**:
  ```json
  {
    "status": "ok"
  }
  ```

## 3. Authentication

All endpoints related to managing To-Do items are now protected. The frontend must acquire a JWT and include it in the `Authorization` header for all subsequent requests to protected endpoints.

### 3.1. Getting an Access Token

- **Endpoint**: `POST /token`
- **Authentication**: None required.
- **Description**: Authenticates a user with their username (which is their email) and password, and returns an access token.
- **Request Body**: The request must be `application/x-www-form-urlencoded` with the following fields:
  - `username`: The user's email address.
  - `password`: The user's password.
- **Success Response (200 OK)** (`schemas.Token`):
  ```json
  {
    "access_token": "your_jwt_token_here",
    "token_type": "bearer"
  }
  ```

### 3.2. Making Authenticated Requests

Once you have the `access_token`, you must include it in the `Authorization` header for all protected API calls.

- **Header Format**: `Authorization: Bearer <access_token>`

## 4. User Registration Flow

User registration is now a two-step process to ensure email validity.

### Step 1: Request Verification Code

- **Endpoint**: `POST /auth/request-verification`
- **Authentication**: None required.
- **Description**: The user provides their email address. The backend generates a verification code, stores it, and sends it to the user's email.
- **Request Body** (`schemas.EmailVerificationRequest`):
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Verification code sent successfully"
  }
  ```
- **Error Response (400 Bad Request)**: If the email is already associated with an existing account.

### Step 2: Create User Account

- **Endpoint**: `POST /auth/register`
- **Authentication**: None required.
- **Description**: After the user receives the code via email, they submit it along with their desired username and password to create their account.
- **Request Body** (`schemas.UserCreateAndVerify`):
  ```json
  {
    "username": "newuser",
    "email": "user@example.com",
    "password": "a_strong_password",
    "code": "123456"
  }
  ```
- **Success Response (200 OK)**: Returns a JWT token, immediately logging the user in (`schemas.Token`).
  ```json
  {
    "access_token": "your_jwt_token_here",
    "token_type": "bearer"
  }
  ```
- **Error Response (400 Bad Request)**: If the code is invalid/expired or the username/email is already taken.

## 5. Password Reset Flow

If a user forgets their password, they can reset it using this two-step flow.

### Step 1: Request Password Reset Code

- **Endpoint**: `POST /auth/forgot-password`
- **Authentication**: None required.
- **Description**: The user enters their email address. The backend sends a password reset code to that email. This endpoint is rate-limited to prevent abuse (one request per 5 hours per email).
- **Request Body** (`schemas.EmailVerificationRequest`):
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Password reset code sent"
  }
  ```
- **Error Responses**:
  - `404 Not Found`: If no user exists with that email.
  - `429 Too Many Requests`: If a request for the same email was made within the last 5 hours.

### Step 2: Reset the Password

- **Endpoint**: `POST /auth/reset-password`
- **Authentication**: None required.
- **Description**: The user provides their email, the reset code, and their new password.
- **Request Body** (`schemas.PasswordReset`):
  ```json
  {
    "email": "user@example.com",
    "code": "654321",
    "new_password": "my_new_secure_password"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Password has been reset successfully"
  }
  ```
- **Error Response (400 Bad Request)**: If the code is invalid or expired.

## 6. To-Do Endpoints

**IMPORTANT**: All `/todos/` endpoints are now protected and require a valid JWT in the `Authorization` header. They now operate only on the data owned by the authenticated user.

- `POST /todos/`: Create a new to-do.
- `GET /todos/`: Get all to-dos for the user.
- `GET /todos/{todo_id}`: Get a specific to-do.
- `PUT /todos/{todo_id}`: Update a to-do.
- `DELETE /todos/{todo_id}`: Delete a to-do.

### Time-based Filtering Endpoints:

These endpoints also require authentication.

- `GET /todos/today`
- `GET /todos/week`
- `GET /todos/month`
- `GET /todos/year`
- `GET /todos/overdue`
- `GET /todos/range?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

## 7. Public Endpoints

- **Endpoint**: `GET /users/count`
- **Authentication**: None required.
- **Description**: Returns the total number of registered users in the application.
- **Success Response (200 OK)** (`schemas.UserCount`):
  ```json
  {
    "total_users": 42
  }
  ```

## 8. Data Schemas

The primary data models the frontend will interact with are defined in `app/schemas.py`.

### `TodoCreate` / `TodoUpdate`

Note the separation of `date` and `time` fields. All are optional except for `title` during creation.

```python
class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False
    start_date: Optional[date] = None # "YYYY-MM-DD"
    start_time: Optional[time] = None # "HH:MM:SS"
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    due_date: Optional[date] = None
```

### `Todo` (Response)

This is the structure of a to-do item returned by the API.

```python
class Todo(BaseModel):
    id: int
    title: str
    description: Optional[str]
    done: bool
    owner_id: int
    start_date: Optional[date]
    start_time: Optional[time]
    end_date: Optional[date]
    end_time: Optional[time]
    due_date: Optional[date]
```

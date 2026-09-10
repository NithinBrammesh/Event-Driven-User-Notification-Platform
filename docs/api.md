# API Documentation

## Base URL

Local client-facing API:

```text
http://localhost:8000
```

The API Gateway is the public API boundary.

---

## Authentication

Protected endpoints use JWT bearer authentication:

```http
Authorization: Bearer <JWT>
```

---

# User APIs

## 1. Register User

### Endpoint

```http
POST /api/users
```

### Request

```json
{
  "full_name": "Example User",
  "email": "example@example.com",
  "password": "TestPassword123"
}
```

### Example response

```json
{
  "id": 1,
  "email": "example@example.com",
  "full_name": "Example User",
  "is_active": true
}
```

### Behavior

After successful registration:

```text
User Service
    |
    v
NATS JetStream
    |
    v
user.created
    |
    v
Notification Service
```

Notification processing is asynchronous.

---

## 2. Login

### Endpoint

```http
POST /api/users/login
```

### Request

```json
{
  "email": "example@example.com",
  "password": "TestPassword123"
}
```

### Response

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer"
}
```

---

## 3. Get Current User

### Endpoint

```http
GET /api/users/me
```

### Authentication

Required:

```http
Authorization: Bearer <JWT>
```

### Example response

```json
{
  "user": {
    "id": 1,
    "email": "example@example.com",
    "full_name": "Example User",
    "is_active": true
  }
}
```

---

## 4. Get User by ID

### Endpoint

```http
GET /api/users/{user_id}
```

### Authentication

Required:

```http
Authorization: Bearer <JWT>
```

### Example

```bash
curl http://localhost:8000/api/users/1 \
  -H "Authorization: Bearer <JWT>"
```

### Example response

```json
{
  "id": 1,
  "email": "example@example.com",
  "full_name": "Example User",
  "is_active": true
}
```

---

# Health APIs

## Gateway

```http
GET /health
```

Example:

```json
{
  "status": "ok",
  "service": "api-gateway"
}
```

## User Service

Internal:

```http
GET /health
```

Example:

```json
{
  "status": "ok",
  "service": "user-service"
}
```

## Notification Service

Internal:

```http
GET /health
```

Example:

```json
{
  "status": "ok",
  "service": "notification-service"
}
```

---

# Notification Diagnostic API

## Last Event

Internal endpoint:

```http
GET /notifications/last-event
```

This endpoint is intended for local development and verification.

---

# Event Contract

## `user.created`

### NATS Subject

```text
user.created
```

### Payload

```json
{
  "event_id": "982ef354-3b67-4b3f-82ee-9a6e84d57125",
  "event_type": "user.created",
  "user_id": 19,
  "email": "user@example.com",
  "created_at": "2026-09-10T09:32:19.032703"
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `event_id` | UUID | Yes | Unique event identifier |
| `event_type` | string | Yes | Event type |
| `user_id` | integer | Yes | Created user ID |
| `email` | string | Yes | User email |
| `created_at` | datetime | Yes | Creation timestamp |

The Notification Service validates this payload before processing.

---

# Error Responses

## Missing Authentication

```http
401 Unauthorized
```

```json
{
  "detail": "Missing authentication token"
}
```

## Invalid Authentication

```http
401 Unauthorized
```

```json
{
  "detail": "Invalid authentication token"
}
```

## User Service Unavailable

```http
503 Service Unavailable
```

Returned when the Gateway cannot communicate with the internal User Service.

## Validation Errors

FastAPI/Pydantic validation is used to reject invalid request or event payloads.

---

# API Flow

```text
Client
  |
  | HTTP + JWT
  v
API Gateway
  |
  | Internal HTTP
  v
User Service
  |
  | NATS JetStream
  v
Notification Service
```

The User Service and Notification Service do not call each other's REST endpoints.

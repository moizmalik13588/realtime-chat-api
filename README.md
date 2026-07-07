# Realtime Chat API

A production-grade, real-time chat backend built with **FastAPI**, **WebSockets**, and **SQLAlchemy**. Supports multi-device messaging, JWT authentication with refresh token rotation, read receipts, typing indicators, and Redis-backed presence tracking.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Features

### Authentication & Security

- JWT-based authentication with **short-lived access tokens** (15 min) and **rotating refresh tokens** (7 days)
- Refresh tokens are **hashed (SHA-256) before storage** — raw tokens are never persisted
- Refresh token **rotation on every use**, with revocation support
- Role-based access control (`admin` / `user`) via dependency injection
- Password hashing with **bcrypt**
- HttpOnly, Secure, SameSite cookies to mitigate XSS/CSRF
- Rate limiting on authentication endpoints (`slowapi`)
- Strong password validation (length, digit, uppercase requirements)

### Real-Time Messaging

- WebSocket-based chat with **multi-device support** — a single user can be connected from multiple clients simultaneously, and messages sync across all of them
- Graceful handling of malformed payloads (invalid JSON, missing fields) without dropping the connection
- Self-messaging and invalid-recipient protection
- Configurable message length limits
- **Typing indicators** (transient, not persisted)
- **Read receipts** with real-time push notification to the sender
- **Unread message counts**, grouped by sender
- **Cursor-based pagination** for chat history (avoids duplicate/missing messages during infinite scroll when new messages arrive)
- Redis-backed **online/offline presence tracking**, aware of multiple simultaneous device connections
- Redis Pub/Sub hook for horizontal scaling across multiple server instances

### Data Layer

- SQLAlchemy ORM with PostgreSQL/SQLite support
- Alembic migrations for schema versioning
- Efficient queries using SQL joins (aliased) instead of N+1 lookups

---

## Tech Stack

| Layer              | Technology                              |
| ------------------ | --------------------------------------- |
| Framework          | FastAPI                                 |
| Real-time          | WebSockets (native FastAPI support)     |
| ORM                | SQLAlchemy                              |
| Migrations         | Alembic                                 |
| Auth               | JWT (`python-jose`), `passlib` (bcrypt) |
| Caching / Presence | Redis                                   |
| Rate Limiting      | SlowAPI                                 |
| Validation         | Pydantic v2                             |

---

## Architecture

```
chat-app/
├── auth/
│   ├── auth_security.py      # Password hashing, JWT creation/verification
│   └── auth_dependency.py    # Auth guards & role-based access control
├── routers/
│   ├── auth_router.py        # Signup, login, logout, profile
│   ├── refresh_router.py     # Token refresh with rotation
│   └── chat_router.py        # WebSocket chat + REST chat endpoints
├── schemas/
│   └── user_schema.py        # Pydantic request/response models
├── alembic/                  # Database migrations
├── connection_manager.py     # In-memory multi-device WebSocket registry
├── models.py                 # SQLAlchemy models
├── database.py                # DB session/engine setup
├── config.py                  # Environment-based settings
└── main.py                    # App entrypoint
```

### Multi-device connection handling

Unlike a naive single-connection-per-user design, the `ConnectionManager` maintains a **list of active WebSocket connections per user**. This means:

- A message sent to a user is delivered to **all** of their connected devices
- When a user sends a message from one device, it is **synced in real time** to their other connected devices
- Presence (`online: true/false`) only flips to `false` once **every** device has disconnected, tracked via a Redis connection counter

---

## Getting Started

### Prerequisites

- Python 3.11+
- Redis server
- PostgreSQL (or SQLite for local development)

### Installation

```bash
git clone https://github.com/moizmalik13588/realtime-chat-api.git
cd realtime-chat-api
python -m venv env
source env/bin/activate   # Windows: env\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
DATABASE_URL=postgresql://user:password@localhost:5432/chatdb
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Start the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

---

## API Reference

### Authentication

| Method | Endpoint         | Description                            |
| ------ | ---------------- | -------------------------------------- |
| POST   | `/sign-up`       | Register a new user                    |
| POST   | `/login`         | Authenticate and receive auth cookies  |
| POST   | `/refresh-token` | Rotate access & refresh tokens         |
| GET    | `/profile`       | Get current authenticated user         |
| POST   | `/logout`        | Revoke refresh token and clear cookies |

### Chat

| Method | Endpoint                        | Description                                   |
| ------ | ------------------------------- | --------------------------------------------- |
| WS     | `/ws/chat?token=<access_token>` | Real-time chat connection                     |
| GET    | `/chat/history/{other_user_id}` | Paginated conversation history (cursor-based) |
| PATCH  | `/chat/mark-read/{sender_id}`   | Mark messages from a sender as read           |
| GET    | `/chat/unread-counts`           | Unread message count grouped by sender        |
| GET    | `/chat/status/{user_id}`        | Check if a user is currently online           |

### WebSocket Message Formats

**Sending a chat message:**

```json
{ "receiver_id": 2, "content": "Hello!" }
```

**Sending a typing signal:**

```json
{ "type": "typing", "receiver_id": 2 }
```

**Incoming message format:**

```
"<sender_id>:<message_content>"
```

**Incoming typing indicator:**

```
"typing:<sender_id>"
```

**Incoming read receipt:**

```
"read_receipt:<reader_id>"
```

---

## Security Notes

- Refresh tokens are never stored in plaintext — only their SHA-256 hash is persisted, so a database leak does not expose usable tokens
- Access tokens are short-lived (15 minutes) to limit the blast radius of a leaked token
- All auth cookies are `HttpOnly` and `Secure` to prevent client-side script access and enforce HTTPS-only transmission
- Rate limiting is applied to the login endpoint to mitigate brute-force attempts

---

## Roadmap

- [ ] Message delivery guarantees via Redis Pub/Sub subscriber (multi-server horizontal scaling)
- [ ] File/media attachments in chat
- [ ] Group chat support
- [ ] Push notifications for offline users
- [ ] Dockerized deployment

---

## Author

**Muhammad Moiz**
Final-year Computer Science student | Full-stack & Backend Developer
[GitHub](https://github.com/moizmalik13588)

---

## License

This project is licensed under the MIT License.

```markdown
# 🤖 AI Agent with FastAPI, PostgreSQL, and OpenAI Agent SDK

A production-ready **AI Agent application** built with:
- [FastAPI](https://fastapi.tiangolo.com/) for high-performance APIs
- [PostgreSQL](https://www.postgresql.org/) for database storage
- [SQLAlchemy](https://docs.sqlalchemy.org/) ORM for data models
- [Pydantic v2](https://docs.pydantic.dev/) for request/response validation
- [JWT Authentication](https://jwt.io/) for secure user management
- [OpenAI Agent SDK](https://platform.openai.com/) for LLM-powered conversations

This project demonstrates:
- ✅ User registration & authentication with hashed passwords  
- ✅ JWT-based session management  
- ✅ Multi-threaded conversation storage (sessions → threads → messages)  
- ✅ AI-powered chat endpoint with conversation history persistence  


## ⚡ Features

- 👤 **User System**  
  - Registration with username, email, password  
  - Password hashing (argon2/bcrypt)  
  - JWT authentication  

- 💬 **Conversation Management**  
  - Sessions → Threads → Messages hierarchy  
  - Store messages from both **user** and **assistant**  
  - Retrieve conversation history per thread  

- 🤖 **LLM Integration**  
  - OpenAI Agent SDK integration  
  - Conversation history passed to the model for context  

- 🔐 **Security**  
  - JWT token authentication  
  - Password hashing using [Passlib](https://passlib.readthedocs.io/)  

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/tayyab0055/learning_mode_agent.git
cd ai-agent-fastapi
````

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 📦 Dependencies

Key packages:

```txt
fastapi
openai-agents
uvicorn
sqlalchemy
psycopg2-binary
alembic
pydantic
passlib[argon2]
python-jose[cryptography]
```

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/agentdb
SECRET_KEY=secretkey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
GEMINI_API_KEY=your_gemini_api_key
```

---

## 🗄️ Database Setup

Create the PostgreSQL database:

```sql
CREATE DATABASE agentdb;
```

Run migrations (if using Alembic) or create tables directly:

Creates tables on startup (dev) automatically.

---

## 🚀 Running the App

```bash
uvicorn app.main:app --reload
```

Visit API docs at:
👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🔑 API Overview

### **Auth Routes**

* `POST /auth/register` → Create new user (username, email, password)
* `POST /auth/login` → Login & get JWT token

### **Session & Thread Routes**

* `POST /sessions/` → Create new session for a user

* Input: `agent_type`→ Optional (query)

* `POST /threads/` → Create new thread in a session
* `GET /threads/{thread_id}` → Get all messages in a thread

### **Message Route (LLM Chat)**

* `POST /messages/{thread_id}`

  * Input: `thread_id`, `message`
  * Process: Sends history + new message to LLM
  * Output: Assistant reply + updated history

---

## 🧪 Example Request

```http
POST /auth/register
Content-Type: application/json

{
  "username": "tayyab",
  "email": "tayyab@example.com",
  "password": "securepassword"
}
```

```http
POST /auth/login
{
  "username": "tayyab",
  "password": "securepassword"
}

# Response:
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```

```http
POST /messages/send
Authorization: Bearer <jwt_token>
{
  "thread_id": 1,
  "message": "Hello Agent!"
}

# Response:
{
  "response": "Hello! How can I help you?",
  "history": [...]
}
```

---

## 🏗️ Future Improvements

* [ ] Email verification system
* [ ] Refresh tokens for long-lived sessions
* [ ] Role-based access control
* [ ] Deploy with Docker + Nginx + Gunicorn

---

## 📜 License

MIT License. Feel free to use and modify.

---

## 👨‍💻 Author

**Tayyab Hussain**

🚀 Building AI-powered apps with FastAPI & OpenAI SDK.


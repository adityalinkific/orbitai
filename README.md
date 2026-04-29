# Orbit Governance System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A role-based enterprise governance platform with AI-powered assistant for task, project, and document management.

## 🚀 Features

### Core Capabilities
- **Orbit Assistant**: AI Governance Engine powered by Llama 3.1 (via Groq API)
- **Natural Language Interface**: Chat with the system to manage users, projects, tasks, and departments
- **Role-Based Access Control (RBAC)**: Granular permissions across 6 roles (SUPERADMIN, ADMIN, HEAD, MANAGER, EMPLOYEE, INTERN)
- **Meeting Management**: Schedule meetings with attendee tracking and automated email invitations
- **Project & Task Management**: Full CRUD operations with workflow orchestration
- **Department Management**: Organizational structure with department heads
- **User Management**: Register, update, and delete users with role assignments

### Security Features
- **JWT Authentication**: Secure token-based authentication with configurable expiration
- **XSS Protection**: Input sanitization using bleach library
- **Security Headers**: CSP, X-Frame-Options, X-Content-Type-Options, XSS Protection
- **Rate Limiting**: Slowapi with configurable limits (200/minute default)
- **Input Validation**: Entity resolver with comprehensive validation
- **Audit Immutability**: Database triggers prevent audit log modification
- **Safety Middleware**: Observer-only security layer for RBAC decisions

### Enterprise Reliability
- **Retry Mechanism**: Tenacity with exponential backoff
- **Circuit Breaker**: Custom circuit breaker for external service failure isolation
- **Timeout Protection**: Async timeout context manager
- **Exception Normalization**: Centralized error handling
- **Concurrency Control**: Per-user semaphore limiting
- **Database Safety**: AsyncSession with transaction rollback

### Observability
- **Structured Logging**: JSON format with request_id, user_id, session_id context
- **Request Tracing**: End-to-end execution tracking
- **Metrics Collection**: Request count, error rate, duration tracking
- **Health Endpoints**: `/health/live` and `/health/ready` probes
- **Audit Logging**: Before/after state capture for all operations

### Deployment
- **Docker Support**: Multi-stage Dockerfile with health checks
- **Docker Compose**: Complete stack with PostgreSQL and Redis
- **Environment Configuration**: .env.example with all required variables
- **Production Config**: config.production.yaml for production deployment

## 🏗 System Architecture

```mermaid
graph TB
    subgraph "User Layer"
        User[User/Frontend]
    end
    
    subgraph "API Layer"
        API[FastAPI API Gateway]
        CORS[CORS Middleware]
        RateLimit[Rate Limiting]
    end
    
    subgraph "Security Layer"
        JWT[JWT Authentication]
        Safety[Safety Middleware]
        RBAC[RBAC Engine]
        Scope[Scope Guard]
        InputSan[Input Sanitization]
    end
    
    subgraph "NLU Layer"
        NLU[NLU Engine]
        Regex[Regex Matcher]
        RAG[RAG Intent Matcher]
        LLM[LLM Fallback]
    end
    
    subgraph "AI Security Layer"
        EntityVal[Entity Validator]
        EntityRes[Entity Resolver]
        Audit[Audit Logger]
    end
    
    subgraph "Execution Layer"
        Executor[Executor]
        Workflows[Workflow Orchestrator]
        ServiceBridge[Service Bridge]
    end
    
    subgraph "Service Layer"
        AuthService[Auth Service]
        UserService[User Service]
        ProjectService[Project Service]
        TaskService[Task Service]
        DeptService[Department Service]
        MeetingService[Meeting Service]
    end
    
    subgraph "Background Tasks"
        Celery[Celery Workers]
        Redis[Redis Broker]
    end
    
    subgraph "AI Engine Layer"
        Groq[Groq API]
        Llama[Llama 3.1]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL)]
        ChromaDB[(ChromaDB)]
    end
    
    User --> API
    API --> CORS
    CORS --> RateLimit
    RateLimit --> JWT
    JWT --> Safety
    Safety --> RBAC
    RBAC --> Scope
    Scope --> InputSan
    InputSan --> NLU
    
    NLU --> Regex
    Regex -->|No Match| RAG
    RAG -->|Low Confidence| LLM
    LLM --> EntityVal
    EntityVal --> EntityRes
    EntityRes --> Audit
    Audit --> Executor
    
    Executor --> Workflows
    Workflows --> ServiceBridge
    ServiceBridge --> AuthService
    ServiceBridge --> UserService
    ServiceBridge --> ProjectService
    ServiceBridge --> TaskService
    ServiceBridge --> DeptService
    ServiceBridge --> MeetingService
    
    AuthService --> PostgreSQL
    UserService --> PostgreSQL
    ProjectService --> PostgreSQL
    TaskService --> PostgreSQL
    DeptService --> PostgreSQL
    MeetingService --> PostgreSQL
    
    RAG --> ChromaDB
    LLM --> Groq
    Groq --> Llama
    
    Executor --> Celery
    Celery --> Redis
    
    style User fill:#e1f5ff
    style API fill:#fff4e1
    style Safety fill:#ffe1e1
    style NLU fill:#e1ffe1
    style Executor fill:#f0e1ff
    style Celery fill:#fff0e1
    style Groq fill:#e1f0ff
    style PostgreSQL fill:#e1e1ff
```

### Architecture Flow

1. **User Request** → User sends natural language query via frontend
2. **API Gateway** → FastAPI receives request with CORS and rate limiting
3. **Authentication** → JWT token validation and user context extraction
4. **Security Layer** → Multi-layer security checks:
   - Safety Middleware: Observer-only security intelligence
   - RBAC Engine: Permission validation
   - Scope Guard: Contextual scope validation
   - Input Sanitization: XSS protection
5. **NLU Processing** → Intent detection pipeline:
   - Regex Matcher: Fast pattern matching
   - RAG Matcher: Semantic similarity with vector embeddings
   - LLM Fallback: Context-aware AI processing
6. **AI Security** → Entity validation and resolution
7. **Execution** → Intent execution with workflow orchestration
8. **Service Layer** → Business logic processing
9. **Background Tasks** → Async processing via Celery/Redis
10. **AI Engine** → Llama 3.1 via Groq API for complex queries
11. **Data Layer** → PostgreSQL for persistent data, ChromaDB for vectors

## 🏗 System Design Patterns & Techniques

### Architecture Patterns
- **Layered Architecture**: Clear separation between controllers, services, repositories, and models
- **Repository Pattern**: Data access abstraction for clean database operations
- **Service Layer Pattern**: Business logic encapsulation independent of data access
- **Dependency Injection**: FastAPI's dependency system for loose coupling
- **Middleware Pattern**: Cross-cutting concerns (CORS, security, rate limiting) as middleware chain

### Security Design
- **Safety Middleware Pattern**: Observer-only security layer that emits security intelligence without making RBAC decisions
- **Scope Guard Pattern**: Contextual scope validation based on user role and intent
- **RBAC with Hierarchical Roles**: 6-tier role system (SUPERADMIN > ADMIN > HEAD > MANAGER > EMPLOYEE > INTERN)
- **Audit Immutability Pattern**: Database triggers prevent audit log modification
- **Input Sanitization Pattern**: XSS protection using bleach library

### Resilience Patterns
- **Circuit Breaker Pattern**: External service failure isolation with automatic recovery
- **Retry Pattern with Exponential Backoff**: Tenacity-based retry for transient failures
- **Timeout Protection Pattern**: Async timeout context manager for preventing hanging operations
- **Exception Normalization Pattern**: Centralized error handling with consistent error responses
- **Concurrency Control Pattern**: Per-user semaphore limiting to prevent resource exhaustion

### AI & NLP Design
- **Entity Resolver Pattern**: Name-to-ID resolution for natural language inputs (department_name → department_id)
- **Intent Normalization Pattern**: Standardizing intent names across different sources
- **Workflow Orchestrator Pattern**: Multi-step operations with state management
- **Confirmation Manager Pattern**: Two-phase confirmation for destructive operations
- **Response Builder Pattern**: Role-aware response formatting based on user permissions
- **RAG-based Intent Matching**: Vector embeddings for semantic intent recognition with ChromaDB
- **Multi-Stage NLU Pipeline**: Regex → RAG → LLM fallback for robust intent detection

### Observability Patterns
- **Structured Logging Pattern**: JSON format with request_id, user_id, session_id context
- **Audit Logging Pattern**: Before/after state capture for all operations
- **Health Check Pattern**: Liveness and readiness probes for container orchestration
- **Metrics Collection Pattern**: Request count, error rate, duration tracking

### Performance Patterns
- **Async/Await Pattern**: Non-blocking I/O with SQLAlchemy async for high concurrency
- **Connection Pooling**: Database connection reuse for optimal performance
- **Rate Limiting Pattern**: Token bucket algorithm for API throttling
- **Lazy Loading**: On-demand data fetching to reduce initial load time

### Data Management
- **ORM Pattern**: SQLAlchemy async for type-safe database operations
- **Migration Pattern**: Alembic for version-controlled database schema changes
- **Transaction Management**: AsyncSession with automatic rollback on errors
- **Soft Delete Pattern**: Logical deletion with audit trail preservation

### Background Task Processing
- **Celery Worker Pattern**: Distributed task queue for asynchronous job processing
- **Redis as Message Broker**: High-performance message broker for Celery
- **Task Routing Pattern**: Route specific tasks to dedicated queues (auth, user, assistant)
- **Rate Limiting Pattern**: Per-task rate limiting to prevent resource exhaustion
- **Task Retry Pattern**: Automatic retry with exponential backoff for failed tasks


TECH STACK:-

Backend        : Python (FastAPI)
Database       : PostgreSQL
Authentication : JWT
ORM            : SQLAlchemy (Async)
AI Engine      : Llama 3.1 (via Groq)
NLP            : Sentence Transformers, ChromaDB
Task Queue     : Celery with Redis
Message Broker : Redis
API Testing    : Swagger UI and Postman
Security       : Bleach, Slowapi, Tenacity
Observability  : Structured Logging, Metrics
Deployment     : Docker, Docker Compose


INSTALLATION:-

1. Clone Repository:-

git clone <repository-url>
cd orbitai
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Variables

Create a `.env` file in the root directory:

```env
# Application
APP_NAME=Orbit
APP_VERSION=1.0.0
APP_ENV=development
APP_DEBUG=true
FRONTEND_URL='["http://localhost:5173","http://localhost:3000"]'

# Database
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/orbit"

# JWT
JWT_SECRET_KEY=your_jwt_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Rate Limiting
LOGIN_RATE_LIMIT_MAX_REQUESTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_BLOCK_SECONDS=300

# AI Engine (Groq)
XAI_API_KEY=your_groq_api_key_here
GROK_BASE_URL=https://api.groq.com/openai/v1
GROK_MODEL=llama-3.1-8b-instant

# Redis Configuration for Celery
REDIS_URL=redis://localhost:6379/0
```

### 5. Database Migration

```bash
alembic upgrade head
```

## 🏃 Running the Application

### Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
docker-compose up -d
```

### Running Celery Workers

For background task processing, you need to run Celery workers alongside the main application:

```bash
# Development - Run Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Development - Run Celery beat for scheduled tasks
celery -A app.core.celery_app beat --loglevel=info

# Production - Run with Docker Compose (includes Celery)
docker-compose up -d
```

### Available Celery Tasks

The system includes the following background tasks:

**Auth Module Tasks:**
- `send_welcome_email` - Send welcome email to new users
- `send_password_reset_email` - Send password reset emails
- `cleanup_expired_tokens` - Cleanup expired JWT tokens

**User Module Tasks:**
- `send_user_update_notification` - Notify on user updates
- `generate_user_report` - Generate comprehensive user reports
- `cleanup_inactive_users` - Cleanup inactive user accounts

**Orbit Assistant Tasks:**
- `process_ai_request` - Process AI requests asynchronously
- `send_meeting_reminder` - Send meeting reminder emails
- `cleanup_old_sessions` - Cleanup old chat sessions
- `generate_analytics_report` - Generate analytics reports

## 🧠 RAG-based Intent Recognition

The Orbit Assistant uses a multi-stage NLU pipeline for robust intent detection:

### NLU Pipeline Stages

1. **Regex Pattern Matching** (Primary - Fastest)
   - Pre-defined regex patterns for common intents
   - Instant matching with entity extraction
   - Used for high-confidence, well-defined patterns

2. **RAG-based Semantic Matching** (Secondary - Smart)
   - Vector embeddings using Sentence Transformers (all-MiniLM-L6-v2)
   - ChromaDB for similarity search
   - Semantic understanding of natural language variations
   - 70% confidence threshold for matches

3. **LLM Fallback** (Tertiary - Most Flexible)
   - Groq's Llama 3.1 for complex/unknown queries
   - Context-aware intent detection
   - Used when regex and RAG don't match

### User-Friendly Intent Examples

The RAG system includes extensive user-friendly examples for each intent:

**User Management:**
- "show me all users", "who works here", "team members", "employees list"
- "add a new user", "register user", "hire someone", "create account for"
- "remove user", "delete user", "terminate user", "fire employee"

**Project Management:**
- "show all projects", "what projects do we have", "current projects"
- "create a project", "start a project", "new project", "set up project"
- "start project", "launch project", "kick off project"

**Task Management:**
- "show all tasks", "what tasks do we have", "current tasks"
- "create a task", "add task", "new task", "add to-do"
- "complete task", "finish task", "mark task done", "task completed"
- "assign task to", "give task to", "delegate task"

**Department Management:**
- "show all departments", "what departments do we have", "teams"
- "create a department", "add department", "create team"

### Adding Custom Intents

You can add custom intents dynamically:

```python
from app.modules.orbit_assistant.engine.intent_rag import intent_rag

intent_rag.add_custom_intent(
    intent="CUSTOM_INTENT",
    description="Description of your custom intent",
    examples=[
        "example phrase 1",
        "example phrase 2",
        "another way to say it"
    ]
)
```

### RAG Configuration

The RAG system uses:
- **Model**: all-MiniLM-L6-v2 (fast, efficient sentence transformer)
- **Vector Database**: ChromaDB with persistent storage
- **Similarity Metric**: Cosine similarity
- **Confidence Threshold**: 0.7 (70%)
- **Storage**: `./chroma_db` directory

### Health Checks

- **Liveness**: `http://localhost:8000/health/live`
- **Readiness**: `http://localhost:8000/health/ready`

## 📚 API Documentation

Swagger UI is available at:
- `http://localhost:8000/docs` (development)
- `https://your-domain.com/docs` (production)

## 🤖 Orbit Assistant Examples

The Orbit Assistant understands natural language commands. Here are some examples:

### User Management
```
"list all users"
"register user named John Doe"
"delete user thor"
"update user Jane email to jane@example.com"
```

### Project Management
```
"create a project called NebulaX"
"list all projects"
"delete NebulaX project"
"start NebulaX project"
```

### Task Management
```
"create a task named API Integration in NebulaX project"
"list all tasks"
"close Backend Integration task"
"assign Backend Integration task to Sudheer"
```

### Department Management
```
"create department named Engineering"
"list all departments"
"show details of Engineering department"
```

### Meeting Management
```
"create a meeting"
"list all meetings"
"show meeting details"
```

## 📁 Project Structure

```
orbitai/
├── app/
│   ├── core/                 # Core functionality (config, security, middleware)
│   │   ├── database/         # Database configuration
│   │   ├── middleware/       # CORS, rate limiting, security headers
│   │   ├── observability/    # Structured logging
│   │   ├── reliability/      # Circuit breaker, retry, timeout
│   │   ├── resolvers/        # Entity resolution
│   │   └── security/         # Input sanitization
│   ├── modules/              # Feature modules
│   │   ├── auth/            # Authentication & authorization
│   │   ├── department/      # Department management
│   │   ├── meeting/         # Meeting management
│   │   ├── orbit_assistant/ # AI assistant engine
│   │   ├── project/         # Project management
│   │   ├── role/            # Role management
│   │   ├── task/            # Task management
│   │   └── user/            # User management
│   └── main.py              # Application entry point
├── alembic/                 # Database migrations
├── .env                     # Environment variables (not committed)
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

## 🔒 Error Handling

Centralized error-handling middleware handles:
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Support

For support, email support@orbitai.com or open an issue in the repository.

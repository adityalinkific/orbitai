PROJECT NAME: ORBIT GOVERNANCE SYSTEM API

The Orbit Governance System is a role-based task, project, and document management platform designed for
enterprise governance


PROJECT STRUCTURE: -

Orbit/
│
├── .env
├── .git/
├── .gitignore
├── README.md
├── alembic/
│   ├── README
│   ├── __pycache__/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 207841ef4bf3_add_chat_session_tables.py
│       └── __pycache__/
├── alembic.ini
├── app/
│   ├── __pycache__/
│   ├── core/
│   │   ├── __pycache__/
│   │   ├── config.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   └── database.py
│   │   ├── dependency.py
│   │   ├── error_handler.py
│   │   ├── governance_policy.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── cors_middleware.py
│   │   │   └── error_handlers.py
│   │   ├── resolvers/
│   │   │   ├── __pycache__/
│   │   │   └── entity_resolver.py
│   │   ├── schema.py
│   │   └── security.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── __pycache__/
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── __pycache__/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── auth_controller.py
│   │   │   ├── auth_model.py
│   │   │   ├── auth_repository.py
│   │   │   ├── auth_routers.py
│   │   │   ├── auth_schema.py
│   │   │   └── auth_services.py
│   │   ├── department/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── department_controller.py
│   │   │   ├── department_model.py
│   │   │   ├── department_repository.py
│   │   │   ├── department_routers.py
│   │   │   ├── department_schema.py
│   │   │   └── department_services.py
│   │   ├── health/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── health_controller.py
│   │   │   ├── health_repository.py
│   │   │   ├── health_routers.py
│   │   │   └── health_services.py
│   │   ├── meeting/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── meeting_controller.py
│   │   │   ├── meeting_model.py
│   │   │   ├── meeting_repository.py
│   │   │   ├── meeting_routers.py
│   │   │   ├── meeting_schema.py
│   │   │   └── meeting_services.py
│   │   ├── orbit_assistant/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── assistant_error_handler.py
│   │   │   ├── assistant_router.py
│   │   │   ├── assistant_service.py
│   │   │   ├── config.yaml
│   │   │   ├── engine/
│   │   │   │   ├── __pycache__/
│   │   │   │   ├── api_client.py
│   │   │   │   ├── assistant_logger.py
│   │   │   │   ├── audit_logger.py
│   │   │   │   ├── capability_validator.py
│   │   │   │   ├── close_task_workflow.py
│   │   │   │   ├── confirmation_manager.py
│   │   │   │   ├── context_manager.py
│   │   │   │   ├── email_composer.py
│   │   │   │   ├── email_service.py
│   │   │   │   ├── entity_resolver.py
│   │   │   │   ├── error_handler.py
│   │   │   │   ├── executor.py
│   │   │   │   ├── hire_candidate_workflow.py
│   │   │   │   ├── intent_normalizer.py
│   │   │   │   ├── intent_validator.py
│   │   │   │   ├── logger.py
│   │   │   │   ├── nlu_engine.py
│   │   │   │   ├── rbac_validator.py
│   │   │   │   ├── response_builder.py
│   │   │   │   ├── start_project_workflow.py
│   │   │   │   └── workflow_orchestrator.py
│   │   │   ├── orbit_assistant_model.py
│   │   │   ├── router.py
│   │   │   ├── routes/
│   │   │   │   ├── __pycache__/
│   │   │   │   ├── capabilities.py
│   │   │   │   └── history.py
│   │   │   ├── schemas.py
│   │   │   └── system_intents.py
│   │   ├── project/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── project_controller.py
│   │   │   ├── project_model.py
│   │   │   ├── project_repository.py
│   │   │   ├── project_routers.py
│   │   │   ├── project_schema.py
│   │   │   └── project_services.py
│   │   ├── role/
│   │   │   ├── __pycache__/
│   │   │   ├── role_controller.py
│   │   │   ├── role_repository.py
│   │   │   ├── role_routers.py
│   │   │   ├── role_schema.py
│   │   │   └── role_services.py
│   │   ├── task/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   ├── task_controller.py
│   │   │   ├── task_model.py
│   │   │   ├── task_repository.py
│   │   │   ├── task_routers.py
│   │   │   ├── task_schema.py
│   │   │   └── task_services.py
│   │   └── user/
│   │       ├── __pycache__/
│   │       ├── user_controller.py
│   │       ├── user_repository.py
│   │       ├── user_routers.py
│   │       ├── user_schema.py
│   │       └── user_services.py
│   └── routers/
│       ├── __init__.py
│       └── __pycache__/
├── requirements.txt
└── venv/


FEATURES: -

- Modular folder structure
- JWT-based authentication
- **Orbit Assistant**: AI Governance Engine powered by Llama 3.1 (via Groq)
- **Meeting Module**: Schedule and manage meetings with attendee tracking and dates.
- **Email Invitations**: Automated email notifications for attendees.


TECH STACK:-

Backend        : Python (FastAPI)
Database       : PostgreSQL
Authentication : JWT
ORM            : SQLAlchemy (Async)
AI Engine      : Llama 3.1 (via Groq)
API Testing    : Swagger UI and Postman


INSTALLATION:-

1. Clone Repository:-

git clone <repository-url>
cd orbit


2. Install Dependencies:-

python -m venv venv
source venv/bin/activate   (Linux/Mac)
venv\Scripts\activate      (Windows)
pip install -r requirements.txt

3. ENVIRONMENT VARIABLES:-

Create a `.env` file in the root directory.

APP_NAME=Orbit
APP_VERSION=1.0.0
APP_ENV=development
APP_DEBUG=true
FRONTEND_URL='["http://localhost:5173","http://localhost:3000"]'

DATABASE_URL=""

JWT_SECRET_KEY=your_jwt_secret=
ALGORITHM=
ACCESS_TOKEN_EXPIRE_MINUTES=10080

LOGIN_RATE_LIMIT_MAX_REQUESTS=
LOGIN_RATE_LIMIT_WINDOW_SECONDS=
LOGIN_RATE_LIMIT_BLOCK_SECONDS=

XAI_API_KEY=your_groq_api_key_here
GROK_BASE_URL=https://api.groq.com/openai/v1
GROK_MODEL=llama-3.1-8b-instant



4. RUN APPLICATION:-
uvicorn app.main:app


For Alembic Migration:-

alembic init alembic



ERROR HANDLING:-

Centralized error-handling middleware handles:
401 - Unauthorized
403 - Forbidden
404 - Not Found
422 - Validation Error
500 - Internal Server Error


API DOCUMENTATION:-

Swagger UI available at:
http://localhost:8000/docs
or
domain-url/docs

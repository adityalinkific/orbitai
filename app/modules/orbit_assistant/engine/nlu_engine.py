"""
NLU Engine — Intent & Entity Extraction via xAI Grok.
Prompts the LLM with a strict JSON schema to extract structured data.
"""

import json
from typing import Any, Dict

from openai import AsyncOpenAI

from app.modules.orbit_assistant.engine.logger import get_logger
from app.modules.orbit_assistant.engine.error_handler import OrbitError, ErrorType
from app.modules.orbit_assistant.engine.intent_normalizer import normalize_intent
from app.core.config import settings

log = get_logger("nlu_engine")
log.info("NLU Engine loaded")


# ==========================================================
# FEW SHOT + SYSTEM PROMPT (UNCHANGED)
# ==========================================================

FEW_SHOT_EXAMPLES = """
# Greetings
User: hello orbit
Response: {"intent": "GREETING", "entities": {}, "confidence": 0.99}

User: hi there
Response: {"intent": "GREETING", "entities": {}, "confidence": 0.99}

# Capabilities & Meta
User: what can you do
Response: {"intent": "LIST_MANAGEABLE_TASKS", "entities": {}, "confidence": 0.99}

User: what tasks can you manage
Response: {"intent": "LIST_MANAGEABLE_TASKS", "entities": {}, "confidence": 0.99}

User: who am I
Response: {"intent": "LIST_MY_INFO", "entities": {}, "confidence": 0.99}

# Projects
User: create a new project called NebulaX
Response: {"intent": "CREATE_PROJECT", "entities": {"name": "NebulaX"}, "confidence": 0.98}

User: show details of NebulaX project
Response: {"intent": "GET_PROJECT", "entities": {"name": "NebulaX"}, "confidence": 0.97}

User: update NebulaX project description to AI governance
Response: {"intent": "UPDATE_PROJECT", "entities": {"name": "NebulaX", "field": "description", "value": "AI governance"}, "confidence": 0.96}

User: list all projects
Response: {"intent": "LIST_PROJECTS", "entities": {}, "confidence": 0.99}

User: delete NebulaX project
Response: {"intent": "DELETE_PROJECT", "entities": {"name": "NebulaX"}, "confidence": 0.97}

User: start NebulaX project
Response: {"intent": "START_PROJECT", "entities": {"name": "NebulaX"}, "confidence": 0.98}

# Tasks
User: create a task named API Integration in NebulaX project
Response: {"intent": "CREATE_TASK", "entities": {"name": "API Integration", "project": "NebulaX"}, "confidence": 0.97}

User: show details of API Integration task
Response: {"intent": "GET_TASK", "entities": {"name": "API Integration"}, "confidence": 0.97}

User: list all tasks
Response: {"intent": "LIST_TASKS", "entities": {}, "confidence": 0.99}

User: update API Integration task description to backend integration phase
Response: {"intent": "UPDATE_TASK", "entities": {"name": "API Integration", "field": "description", "value": "backend integration phase"}, "confidence": 0.96}

User: rename API Integration task to Backend Integration
Response: {"intent": "UPDATE_TASK", "entities": {"name": "API Integration", "new_name": "Backend Integration"}, "confidence": 0.97}

User: assign Backend Integration task to Sudheer
Response: {"intent": "ASSIGN_TASK", "entities": {"task": "Backend Integration", "user": "Sudheer"}, "confidence": 0.97}

User: close Backend Integration task
Response: {"intent": "CLOSE_TASK", "entities": {"name": "Backend Integration"}, "confidence": 0.97}

User: delete API Integration task
Response: {"intent": "DELETE_TASK", "entities": {"name": "API Integration"}, "confidence": 0.97}

User: close it
Response: {"intent": "CLOSE_TASK", "entities": {"name": "it"}, "confidence": 0.95}

User: assign it to Sudheer
Response: {"intent": "ASSIGN_TASK", "entities": {"task": "it", "user": "Sudheer"}, "confidence": 0.95}

# Users
User: list all users
Response: {"intent": "LIST_USERS", "entities": {}, "confidence": 0.99}

User: register a user named Aarav
Response: {"intent": "REGISTER_USER", "entities": {"name": "Aarav"}, "confidence": 0.97}

User: update user sreeja email to newmail@orbit.com
Response: {"intent": "UPDATE_USER", "entities": {"name": "sreeja", "field": "email", "value": "newmail@orbit.com"}, "confidence": 0.95}

User: update user details for sreeja
Response: {"intent": "UPDATE_USER", "entities": {"name": "sreeja"}, "confidence": 0.95}

User: change user email for sreeja to test@example.com
Response: {"intent": "UPDATE_USER", "entities": {"name": "sreeja", "email": "test@example.com"}, "confidence": 0.95}

# Departments
User: list all departments
Response: {"intent": "LIST_DEPARTMENTS", "entities": {}, "confidence": 0.99}

User: show details of Engineering department
Response: {"intent": "GET_DEPARTMENT", "entities": {"name": "Engineering"}, "confidence": 0.97}

# Roles
User: list all roles
Response: {"intent": "LIST_ROLES", "entities": {}, "confidence": 0.99}

User: update admin role permissions
Response: {"intent": "UPDATE_ROLE", "entities": {"role": "admin"}, "confidence": 0.96}

User: update admin role permissions to full system access
Response: {"intent": "UPDATE_PERMISSIONS", "entities": {"role": "admin", "description": "full system access"}, "confidence": 0.95}

# Email
User: send email to sudheer@gmail.com saying orbit certification successful
Response: {"intent": "SEND_EMAIL", "entities": {"email": "sudheer@gmail.com", "body": "orbit certification successful"}, "confidence": 0.97}

# Workflows
User: hire candidate named Aarav into Engineering department
Response: {"intent": "HIRE_CANDIDATE", "entities": {"name": "Aarav", "department": "Engineering"}, "confidence": 0.97}

User: start a project called DevOps
Response: {"intent": "START_PROJECT", "entities": {"name": "DevOps"}, "confidence": 0.98}

User: show my tasks
Response: {"intent": "LIST_MY_TASKS", "entities": {}, "confidence": 0.99}

User: what are my tasks
Response: {"intent": "LIST_MY_TASKS", "entities": {}, "confidence": 0.99}
"""

SYSTEM_PROMPT = """
You are the Orbit Governance Assistant. Your job is to extract the user's INTENT and ENTITIES from their message.
You MUST respond with valid JSON ONLY.

KNOWN INTENTS:
{intents}

Rules:
1. If you don't know the intent, use "UNKNOWN".
2. If it's a greeting, use "GREETING".
3. Extract names, IDs, and payloads for the requested action.
4. Output strict JSON format.

Response Schema:
{
  "intent": "STRING",
  "entities": "OBJECT",
  "confidence": "FLOAT"
}
"""


# ==========================================================
# ALIAS MAPPING (Phase 3)
# ==========================================================
ALIAS_MAP = {
    "start it": "START_PROJECT",
    "start project": "START_PROJECT",
    "close it": "CLOSE_TASK",
    "close task": "CLOSE_TASK",
    "assign it": "ASSIGN_TASK",
    "delete it": "DELETE_PROJECT",
    "project info": "SHOW_PROJECT_DETAILS",
    "show info": "SHOW_PROJECT_DETAILS",
    "show details": "SHOW_PROJECT_DETAILS",
    "list departments": "LIST_DEPARTMENTS",
    "list projects": "LIST_PROJECTS",
    "list users": "LIST_USERS"
}


# ==========================================================
# CORE PARSER FUNCTION
# ==========================================================

import re

INTENT_PATTERNS = {
    "GREETING": [r"^(?:hello|hi|hey|howdy)\b", r"hello orbit"],
    "CREATE_PROJECT": [r"create (?:a (?:new )?)?project (?:named )?(?P<name>[\w\s-]+)"],
    "CREATE_TASK": [
        r"create (?:a (?:new )?)?task (?:named )?(?P<name>[\w\s-]+) in (?P<project>[\w\s-]+) project",
        r"create (?:a (?:new )?)?task (?:named )?(?P<name>[\w\s-]+)"
    ],
    "LIST_TASKS": [r"list all tasks", r"show all tasks", r"get all tasks"],
    "ASSIGN_TASK": [r"assign (?P<task>[\w\s-]+) task to (?P<user>[\w\s-]+)"],
    "DELETE_PROJECT": [r"delete (?P<name>[\w\s-]+) project"],
    "LIST_MANAGEABLE_TASKS": [r"what (?:tasks |things )?can you (?:do|manage|help with)", r"list your capabilities"],
    "LIST_MY_INFO": [r"who am i", r"my profile", r"show my info", r"my account"],
    "SHOW_PROJECT_DETAILS": [r"show (?:details of )?(?P<name>[\w\s-]+) project"],
    "UPDATE_PROJECT": [
        r"update (?P<name>[\w\s-]+) project (?P<field>\w+) (?:into|to) (?P<value>.+)",
        r"rename (?P<name>[\w\s-]+) project to (?P<new_name>[\w\s-]+)"
    ],
    "START_PROJECT": [r"start (?:the )?(?P<name>[\w\s-]+) project", r"launch (?P<name>[\w\s-]+) project", r"start project (?P<name>[\w\s-]+)"],
    "UPDATE_TASK": [
        r"update (?P<name>[\w\s]+) task (?P<field>\w+) (?:into|to) (?P<value>.+)",
        r"rename (?P<name>[\w\s]+) task to (?P<new_name>[\w\s]+)"
    ],
    "DELETE_TASK": [r"delete (?P<name>[\w\s]+) task", r"remove (?P<name>[\w\s]+) task", r"delete task (?:named )?(?P<name>[\w\s]+)", r"remove task (?:named )?(?P<name>[\w\s]+)"],
    "CLOSE_TASK": [r"close (?P<name>[\w\s]+) task", r"mark (?P<name>[\w\s]+) (?:as )?done", r"close task (?P<name>[\w\s]+)"],
    "LIST_USERS": [r"list all users", r"show all users", r"list users", r"show users", r"test LIST_USERS", r"LIST_USERS"],
    "UPDATE_USER": [
        r"update email of (?P<name>[\w\s]+) to (?P<email>[\w.@+]+)",
        r"update user (?P<name>[\w\s]+) (?P<field>\w+) to (?P<value>.+)",
        r"update user (?P<name>[\w\s]+)",
        r"test UPDATE_USER", r"UPDATE_USER"
    ],
    "DELETE_USER": [
        r"delete user (?P<name>[\w\s]+)",
        r"delete (?P<name>[\w\s]+) user",
        r"remove user (?P<name>[\w\s]+)",
        r"test DELETE_USER", r"DELETE_USER"
    ],
    "LIST_DEPARTMENTS": [r"list all departments", r"show all departments", r"list departments", r"show departments", r"test LIST_DEPARTMENTS", r"LIST_DEPARTMENTS"],
    "LIST_PROJECTS": [r"list all projects", r"show projects", r"all projects", r"list projects", r"my projects", r"test LIST_PROJECTS", r"LIST_PROJECTS"],
    "LIST_TASKS": [r"list all tasks", r"show all tasks", r"get all tasks", r"test LIST_TASKS", r"LIST_TASKS"],
    "GET_DEPARTMENT": [r"show (?:details of )?(?P<name>[\w\s]+) department", r"test GET_DEPARTMENT", r"GET_DEPARTMENT", r"view department", r"department info"],
    "LIST_ROLES": [r"list all roles", r"show all roles", r"list roles", r"show roles"],
    "UPDATE_ROLE": [r"update (?P<role>[\w\s]+) role", r"update role (?P<role>[\w\s]+)", r"test UPDATE_ROLE", r"UPDATE_ROLE"],
    "UPDATE_PERMISSIONS": [r"update (?P<role>[\w\s]+) role permissions", r"update permissions for (?P<role>[\w\s]+)", r"test UPDATE_PERMISSIONS", r"UPDATE_PERMISSIONS"],
    "REGISTER_USER": [r"register (?:a )?user named (?P<name>[\w\s]+)", r"register user (?P<name>[\w\s]+)", r"create user (?P<name>[\w\s]+)", r"test REGISTER_USER", r"REGISTER_USER"],
    "CREATE_DEPARTMENT": [r"create (?:a )?department named (?P<name>[\w\s]+)", r"create department (?P<name>[\w\s]+)", r"add department (?P<name>[\w\s]+)", r"test CREATE_DEPARTMENT", r"CREATE_DEPARTMENT"],
    "UPDATE_DEPARTMENT": [r"update (?P<name>[\w\s]+) department", r"rename department (?P<name>[\w\s]+) to (?P<new_name>[\w\s]+)", r"test UPDATE_DEPARTMENT", r"UPDATE_DEPARTMENT"],
    "DELETE_DEPARTMENT": [r"delete (?P<name>[\w\s]+) department", r"delete department (?P<name>[\w\s]+)", r"remove department (?P<name>[\w\s]+)", r"test DELETE_DEPARTMENT", r"DELETE_DEPARTMENT"],
    "SYSTEM_STATUS": [r"show system status", r"system status", r"check system status", r"test SYSTEM_STATUS", r"SYSTEM_STATUS"],
    "SEND_EMAIL": [r"send (?:an )?email to (?P<email>[\w.@+]+) saying (?P<body>.+)", r"send mail", r"email user", r"send email", r"mail notification", r"test SEND_EMAIL", r"SEND_EMAIL"],
    "HIRE_CANDIDATE": [
        r"hire (?:candidate )?(?:named )?(?P<name>[\w\s]+) into (?P<department>[\w\s]+) department",
        r"hire (?:candidate )?(?P<name>[\w\s]+) into (?P<department>[\w\s]+)",
    ],
    "LIST_MY_TASKS": [r"(?:show |list |get )?my tasks", r"tasks assigned to me", r"what are my tasks"],
    
    # Admin/Enterprise capabilities
    "ENTERPRISE_REASONING": [r"i want to restructure", r"restructure the organization", r"expand the company", r"ai expansion", r"organizational restructuring", r"test ENTERPRISE_REASONING", r"ENTERPRISE_REASONING"],
    "AI_ORG_INSIGHTS": [r"ai (?:organization|org) insights", r"show ai insights", r"analyze organization", r"test AI_ORG_INSIGHTS", r"AI_ORG_INSIGHTS", r"organization insights", r"org analytics", r"company insights", r"organization intelligence"],
    "DEPARTMENT_STATUS_REPORT": [r"department status report", r"show department status", r"department report", r"test DEPARTMENT_STATUS_REPORT", r"DEPARTMENT_STATUS_REPORT", r"department performance", r"dept performance", r"department progress"],
    "GET_MEETING": [r"show meeting", r"get meeting", r"meeting details", r"test GET_MEETING", r"GET_MEETING"],
    "LIST_MEETINGS": [r"list all meetings", r"show meetings", r"upcoming meetings"],
    "ORG_PERFORMANCE_SUMMARY": [r"organization performance", r"org performance summary", "show performance"],
    "SHOW_ORG_DASHBOARD": [r"show (?:organization|org) dashboard", r"org dashboard"],
    "TEAM_PROGRESS_REPORT": [r"team progress report", r"show team progress", "team progress"],
    "SEND_NOTIFICATION": [r"send notification", r"notify"],
    "GET_PROJECT": [r"show project", r"get project", r"project details", r"test GET_PROJECT", r"GET_PROJECT"],
    "CREATE_MEETING": [r"create (?:a )?meeting", r"schedule meeting", r"new meeting", r"test CREATE_MEETING", r"CREATE_MEETING"],
    "INVITE_USER": [r"invite user (?P<user>[\w\s]+) to (?P<meeting>[\w\s]+)", r"test INVITE_USER", r"INVITE_USER", r"invite to meeting"],
    "SHOW_DEPARTMENT_DASHBOARD": [r"show (?:department|dept) dashboard", r"test SHOW_DEPARTMENT_DASHBOARD", r"SHOW_DEPARTMENT_DASHBOARD", r"department dashboard", r"dept dashboard"],
    "UPDATE_MEETING": [r"update (?:the )?meeting", r"reschedule meeting", r"change meeting", r"test UPDATE_MEETING", r"UPDATE_MEETING"],
    "DELETE_MEETING": [r"delete meeting", r"cancel meeting", r"remove meeting", r"test DELETE_MEETING", r"DELETE_MEETING"],
    "REPORT_BLOCKER": [r"report blocker (?:for )?(?:task )?(?P<task_id>[\d]+)?", r"i (?:am |'m )stuck", r"task (?:is )?blocked", r"i have a blocker (?:on )?(?:task )?(?P<task_id>[\d]+)?", r"test REPORT_BLOCKER", r"REPORT_BLOCKER"],
    "SHOW_TEAM_DASHBOARD": [r"show team dashboard", r"team dashboard", r"test SHOW_TEAM_DASHBOARD", r"SHOW_TEAM_DASHBOARD"],
    "UPDATE_TASK_PROGRESS": [r"update task progress (?:to )?(?P<progress>[\d%]+)", r"mark task progress (?P<progress>[\d%]+)", r"set progress to (?P<progress>[\d%]+)", r"test UPDATE_TASK_PROGRESS", r"UPDATE_TASK_PROGRESS"],
    "REQUEST_HELP": [r"request help", r"i need help", r"need assistance", r"ask for help", r"test REQUEST_HELP", r"REQUEST_HELP"],
    "JOIN_MEETING": [r"join meeting (?P<meeting_id>[\d]+)", r"join (?:the )?meeting (?P<meeting_id>[\d]+)", r"attend meeting (?P<meeting_id>[\d]+)", r"test JOIN_MEETING", r"JOIN_MEETING"],
    "SHOW_PERSONAL_DASHBOARD": [r"show (?:my )?dashboard", r"personal dashboard", r"my dashboard", r"test SHOW_PERSONAL_DASHBOARD", r"SHOW_PERSONAL_DASHBOARD"],
    "SHOW_EXECUTION_GUIDANCE": [r"what should i do next", r"show execution guidance", r"execution guidance", r"test SHOW_EXECUTION_GUIDANCE", r"SHOW_EXECUTION_GUIDANCE"],
    "SHOW_EXPECTED_OUTPUT": [r"show expected output", r"expected output", r"test SHOW_EXPECTED_OUTPUT", r"SHOW_EXPECTED_OUTPUT"],
    "SHOW_NEXT_STEP": [r"show next step", r"next step", r"what's next", r"show my next step", r"test SHOW_NEXT_STEP", r"SHOW_NEXT_STEP"],
}


def _disambiguate_update_intent(message: str, entities: dict) -> tuple:
    """
    Disambiguate between UPDATE_USER and UPDATE_ROLE intents.
    
    Rules:
    - UPDATE_USER: modifies a person's details (name, email, department)
    - UPDATE_ROLE: modifies role permissions only
    - UPDATE_PERMISSIONS: explicitly about permissions
    
    Returns: (intent, entities)
    """
    msg_lower = message.lower()
    
    # Explicit permission-related keywords → UPDATE_PERMISSIONS or UPDATE_ROLE
    permission_keywords = ['permission', 'access', 'privilege', 'capability', 'right']
    if any(keyword in msg_lower for keyword in permission_keywords):
        if 'role' in msg_lower:
            return ('UPDATE_PERMISSIONS', entities)
        return ('UPDATE_ROLE', entities)
    
    # Explicit role keywords without permission context → UPDATE_ROLE
    role_keywords = ['role permissions', 'role access', 'role capability']
    if any(keyword in msg_lower for keyword in role_keywords):
        return ('UPDATE_PERMISSIONS', entities)
    
    # User-specific keywords → UPDATE_USER
    user_keywords = ['user', 'employee', 'member', 'staff', 'person']
    if any(keyword in msg_lower for keyword in user_keywords):
        return ('UPDATE_USER', entities)
    
    # Check entities for clues
    if entities.get('role') and not entities.get('name') and not entities.get('email'):
        # Only role entity provided, no user details → UPDATE_ROLE
        return ('UPDATE_ROLE', entities)
    
    if entities.get('name') or entities.get('email') or entities.get('username'):
        # User details provided → UPDATE_USER
        return ('UPDATE_USER', entities)
    
    # Default fallback based on pattern matching
    return ('UPDATE_USER', entities)


def _normalize_input(user_message: str) -> str:
    """
    Normalize user input by removing polite words and helper verbs.
    
    This helps match intents when users use natural language variations.
    """
    # Convert to lowercase
    normalized = user_message.lower().strip()
    
    # Remove polite words and helper phrases
    polite_phrases = [
        r"\bplease\b",
        r"\bcan you\b",
        r"\bcould you\b",
        r"\bkindly\b",
        r"\bi want to\b",
        r"\bshow me\b",
        r"\bgive me\b",
        r"\btell me\b",
        r"\bi would like to\b",
        r"\bmay i\b",
        r"\bcan i\b",
        r"\bhelp me\b",
        r"\bjust\b",
        r"\bneed to\b"
    ]
    
    for phrase in polite_phrases:
        normalized = re.sub(phrase, "", normalized, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    return normalized

async def parse_command(
    client: AsyncOpenAI,
    user_message: str,
    config: dict,
    model: str = None,
    user_context: dict = None,
) -> Dict[str, Any]:

    resolved_model = model or settings.GROK_MODEL
    log.info(f"Detected Intent: Processing '{user_message[:80]}...'")

    # 0. PREPROCESSING - Normalize input by removing polite words and helper verbs
    clean_msg = _normalize_input(user_message)
    
    # 1. REGEX PATTERN MATCHING (PRIMARY METHOD - FAST & RELIABLE)
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, clean_msg, re.IGNORECASE)
            if match:
                entities = match.groupdict()
                
                # Apply intent disambiguation for UPDATE intents
                if intent in ["UPDATE_USER", "UPDATE_ROLE"]:
                    disambiguated_intent, entities = _disambiguate_update_intent(user_message, entities)
                    intent = disambiguated_intent
                
                # Validate entities using entity_validator
                try:
                    from .entity_validator import entity_validator
                    is_valid, validated_entities, error = entity_validator.validate_and_extract_entities(
                        entities, normalize_intent(intent)
                    )
                    if not is_valid:
                        log.warning(f"Entity validation failed for {intent}: {error}")
                        # Still return the intent but with validation error in entities
                        entities["_validation_error"] = error
                    else:
                        entities = validated_entities
                except ImportError:
                    # Fallback if validator not available
                    log.warning("Entity validator not available, skipping validation")
                
                log.info(f"Detected Intent: {intent} (regex match)")
                return {
                    "intent": normalize_intent(intent),
                    "entities": entities,
                    "confidence": 1.0
                }

    # 2. FALLBACK TO LLM (ONLY IF REGEX FAILS)
    log.info(f"Detected Intent: No regex match, trying LLM")
    
    known_intents = set(config.get("intents", {}).keys())
    known_workflows = set(config.get("workflows", {}).keys())

    all_known = known_intents | known_workflows | {"HELLO", "GREETING", "LIST_MY_INFO"}
    all_known |= {
        "SHOW_PROJECT_DETAILS", "UPDATE_PROJECT", "DELETE_PROJECT",
        "UPDATE_TASK", "DELETE_TASK", "ASSIGN_TASK",
        "LIST_USERS", "REGISTER_USER", "UPDATE_USER_EMAIL", "LIST_MY_INFO",
        "LIST_ROLES", "UPDATE_ROLE_PERMISSIONS", "SEND_EMAIL",
        "HIRE_CANDIDATE", "START_PROJECT", "CLOSE_TASK",
        "LIST_MY_TASKS", "CREATE_MEETING", "INVITE_USER",
        "SHOW_DEPARTMENT_DASHBOARD", "UPDATE_MEETING", "DELETE_MEETING",
        "REPORT_BLOCKER", "SHOW_TEAM_DASHBOARD"
    }

    intents_str = ", ".join(list(all_known))

    system = SYSTEM_PROMPT.replace("{intents}", intents_str)

    if user_context:
        context_str = (
            f"You are assisting User: "
            f"{user_context.get('name','N/A')} "
            f"(Role: {user_context.get('role','N/A')}).\n"
        )
        system = context_str + system

    system = system.replace(
        "KNOWN INTENTS:",
        FEW_SHOT_EXAMPLES + "\nKNOWN INTENTS:",
    )

    raw = None

    try:
        response = await client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content
        cleaned = raw.strip()

        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")

        if start_idx != -1 and end_idx != -1:
            cleaned = cleaned[start_idx : end_idx + 1]

        parsed = json.loads(cleaned)
        
        raw_intent = parsed.get("intent", "UNKNOWN")
        parsed["intent"] = normalize_intent(raw_intent)

        if not parsed.get("intent") or parsed.get("intent") == "None":
            log.warning(f"Detected Intent: Fallback to UNKNOWN for message: {user_message[:50]}")
            parsed["intent"] = "UNKNOWN"

        if "data" in parsed and "entities" not in parsed:
            parsed["entities"] = parsed.pop("data")

        parsed.setdefault("entities", {})

        intent = parsed.get('intent')
        confidence = parsed.get('confidence')
        log.info(f"Detected Intent: {intent} (LLM, confidence: {confidence})")

        return parsed

    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON from LLM: {raw}")
        log.warning(f"Detected Intent: Fallback to UNKNOWN due to JSON parse error")
        return {
            "intent": "UNKNOWN",
            "entities": {},
            "confidence": 0.0
        }

    except Exception as e:
        log.error(f"LLM call failed: {e}")
        log.warning(f"Detected Intent: Fallback to UNKNOWN due to LLM error")
        return {
            "intent": "UNKNOWN",
            "entities": {},
            "confidence": 0.0
        }


# ==========================================================
# NLUEngine CLASS  ⭐⭐⭐ (THIS WAS MISSING)
# ==========================================================

class NLUEngine:
    """
    Orbit NLU Engine Wrapper
    Provides clean interface used by assistant_service
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.XAI_API_KEY,
            base_url=settings.GROK_BASE_URL,
        )

    async def parse(
        self,
        message: str,
        config: dict,
        user_context: dict | None = None,
    ) -> Dict[str, Any]:
        """
        Main entrypoint used by assistant service
        """
        return await parse_command(
            client=self.client,
            user_message=message,
            config=config,
            user_context=user_context,
        )


# ==========================================================
# EXPORT SINGLETON INSTANCE  ⭐⭐⭐
# ==========================================================

nlu_engine = NLUEngine()
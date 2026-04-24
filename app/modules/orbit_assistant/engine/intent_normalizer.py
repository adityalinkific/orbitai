"""
Orbit Intent Normalizer
Canonicalizes fragmented NLU intents into a single standard Governance Map.

DESIGN: We normalize DOWN to the canonical form that the Executor handles.
The executor uses the CANONICAL form as its routing key.
"""

CANONICAL_INTENTS = {
    # Project Canonicalization
    "SHOW_PROJECT": "GET_PROJECT",
    "SHOW_PROJECT_DETAILS": "GET_PROJECT",
    "LIST_PROJECT_INFO": "GET_PROJECT",
    "GET_PROJECT_DETAILS": "GET_PROJECT",
    "DESCRIBE_PROJECT": "GET_PROJECT",
    "PROJECT_DETAILS": "GET_PROJECT",

    # Task Canonicalization
    "SHOW_TASK": "GET_TASK",
    "SHOW_TASK_DETAILS": "GET_TASK",
    "GET_TASK_DETAILS": "GET_TASK",
    "LIST_TASK_INFO": "GET_TASK",
    "RENAME_TASK": "UPDATE_TASK",
    "MODIFY_TASK": "UPDATE_TASK",

    # Department Canonicalization
    "LIST_DEPARTMENT_DETAILS": "GET_DEPARTMENT",
    "SHOW_DEPARTMENT": "GET_DEPARTMENT",
    "GET_DEPARTMENT_DETAILS": "GET_DEPARTMENT",

    # User Canonicalization
    "GET_USER": "LIST_USERS",
    "SHOW_USERS": "LIST_USERS",

    # Role Canonicalization
    "UPDATE_ROLE_PERMISSIONS": "UPDATE_PERMISSIONS",

    # Greetings
    "HELLO": "GREETING",
    "HI": "GREETING",
    "HEY": "GREETING",
}

def normalize_intent(intent: str) -> str:
    """Returns the canonical intent for a given raw NLU intent."""
    if not intent: return "UNKNOWN"
    return CANONICAL_INTENTS.get(intent.upper(), intent.upper())

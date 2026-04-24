"""
System Intents Firewall
Intents that are only available via system API, not conversational assistant.
"""

# Intents that should never be accessible via chat
SYSTEM_ONLY_INTENTS = [
    "GET_USER_HISTORY",
    "GET_SESSION_HISTORY",
    "LIST_CAPABILITIES",
    "ADD_MEMBER",
    "UPDATE_EMAIL",
]

def is_system_only_intent(intent: str) -> bool:
    """Check if an intent is system-only (not accessible via chat)."""
    return intent.upper() in [i.upper() for i in SYSTEM_ONLY_INTENTS]

"""
Orbit Governance Policy
Centralized control for restricted intents and capabilities.
"""

# Intents that are restricted from chatbot exposure
# These remain available as internal APIs for admin/system use
RESTRICTED_INTENTS = {
    "LIST_ACTIVITY_LOG",
    "GET_SESSION_HISTORY",
    "SHOW_CAPABILITIES",
}

# Intents that require admin role
ADMIN_ONLY_INTENTS = {
    "DELETE_PROJECT",
    "DELETE_TASK",
    "DELETE_USER",
    "UPDATE_ROLE",
    "UPDATE_PERMISSIONS",
}

# Intents that require confirmation before execution
CONFIRMATION_REQUIRED_INTENTS = {
    "DELETE_PROJECT",
    "DELETE_TASK",
}

def is_restricted_intent(intent: str) -> bool:
    """Check if an intent is restricted from chatbot exposure."""
    return intent in RESTRICTED_INTENTS

def is_admin_only_intent(intent: str) -> bool:
    """Check if an intent requires admin role."""
    return intent in ADMIN_ONLY_INTENTS

def is_confirmation_required(intent: str) -> bool:
    """Check if an intent requires confirmation before execution."""
    return intent in CONFIRMATION_REQUIRED_INTENTS

"""
ORBIT Assistant Capabilities API
Returns role-filtered capabilities based on authenticated user's JWT token.
"""
from fastapi import APIRouter, Depends
from app.modules.orbit_assistant.engine.capability_resolver import capability_resolver
from app.core.dependency import get_current_user

router = APIRouter(prefix="/assistant", tags=["Assistant"])

@router.get("/capabilities")
def get_capabilities(current_user = Depends(get_current_user)):
    """
    Returns ONLY capabilities allowed for the logged-in user.
    Derives role from JWT and dynamically filters capabilities.
    Never returns full system capabilities.
    """
    try:
        # Debug logging
        print(f"[DEBUG CAPABILITIES] current_user attributes: {dir(current_user)}")
        print(f"[DEBUG CAPABILITIES] hasattr role_from_token: {hasattr(current_user, 'role_from_token')}")
        print(f"[DEBUG CAPABILITIES] hasattr role: {hasattr(current_user, 'role')}")
        
        # Extract role from JWT token (priority) or database relationship (fallback)
        user_role = None
        
        # First try to get role from JWT token (most reliable)
        if hasattr(current_user, 'role_from_token'):
            user_role = current_user.role_from_token
            print(f"[DEBUG CAPABILITIES] Got role from JWT token: {user_role}")
        # Fallback to database relationship
        elif hasattr(current_user, 'role') and current_user.role:
            user_role = current_user.role.role
            print(f"[DEBUG CAPABILITIES] Got role from database: {user_role}")
        else:
            print(f"[DEBUG CAPABILITIES] No role found anywhere")
        
        if not user_role:
            return {
                "role": "UNKNOWN",
                "capabilities": [],
                "total": 0,
                "error": "Unable to determine user role from JWT or database"
            }

        # Get role-filtered capabilities
        capabilities = capability_resolver.get_user_capabilities(user_role)

        return {
            "role": user_role.upper(),
            "capabilities": capabilities,
            "total": len(capabilities)
        }
    except Exception as e:
        print(f"[DEBUG CAPABILITIES] Exception: {str(e)}")
        return {
            "role": "UNKNOWN",
            "capabilities": [],
            "total": 0,
            "error": str(e)
        }

"""
Global Safety Middleware — AI Safety Lockdown
Enforces zero-tolerance safety rules for all AI executions.

Blocks execution when:
- capability unknown
- entity missing
- role unauthorized
- cross-scope detected
- ambiguous entity detected

AI MUST ASK USER FOR CLARIFICATION instead of guessing.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.orbit_assistant.engine.capability_resolver import capability_resolver
from app.modules.orbit_assistant.engine.rbac_validator import rbac_validator
from app.modules.orbit_assistant.engine.scope_guard import scope_guard


class SafetyMiddleware:
    """
    Global safety middleware that enforces zero-tolerance safety rules.
    All executions must pass through this layer before proceeding.
    """

    # Ambiguity detection patterns
    AMBIGUOUS_PATTERNS = [
        "test", "example", "sample", "default", "placeholder",
        "updated", "new", "the", "a", "an"
    ]

    @staticmethod
    async def validate_execution(
        intent: str,
        entities: Dict[str, Any],
        db: AsyncSession,
        user,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive safety validation before execution.
        
        Args:
            intent: The intent being executed
            entities: Extracted entities from NLU
            db: Database session
            user: Current user
            session_id: Chat session ID
        
        Returns:
            Dict with 'allowed' boolean and optional 'clarification' message
        
        Raises:
            HTTPException: If validation fails (hard failure)
        """
        
        # 1. Check if capability is known
        capability_check = SafetyMiddleware._check_capability_known(intent)
        if not capability_check["allowed"]:
            return {
                "allowed": False,
                "reason": capability_check["reason"],
                "requires_clarification": True,
                "clarification": f"I don't understand '{intent}'. Could you please clarify what you'd like to do?"
            }
        
        # 2. Check if role is authorized
        auth_check = await SafetyMiddleware._check_role_authorized(intent, user)
        if not auth_check["allowed"]:
            return {
                "allowed": False,
                "reason": auth_check["reason"],
                "requires_clarification": False,
                "clarification": None
            }
        
        # 3. Check for missing entities
        entity_check = SafetyMiddleware._check_entities_present(intent, entities)
        if not entity_check["allowed"]:
            return {
                "allowed": False,
                "reason": entity_check["reason"],
                "requires_clarification": True,
                "clarification": entity_check["clarification"]
            }
        
        # 4. Check for ambiguous entities
        ambiguity_check = SafetyMiddleware._check_entity_ambiguity(entities)
        if not ambiguity_check["allowed"]:
            return {
                "allowed": False,
                "reason": ambiguity_check["reason"],
                "requires_clarification": True,
                "clarification": ambiguity_check["clarification"]
            }
        
        # 5. Check for cross-scope access
        scope_check = await SafetyMiddleware._check_cross_scope(intent, entities, db, user)
        if not scope_check["allowed"]:
            return {
                "allowed": False,
                "reason": scope_check["reason"],
                "requires_clarification": False,
                "clarification": None
            }
        
        # All checks passed
        return {
            "allowed": True,
            "reason": None,
            "requires_clarification": False,
            "clarification": None
        }
    
    @staticmethod
    def _check_capability_known(intent: str) -> Dict[str, Any]:
        """Check if the capability is known and registered."""
        try:
            # Check if intent exists in capability resolver
            all_intents = capability_resolver.get_all_intents()
            if intent not in all_intents:
                return {
                    "allowed": False,
                    "reason": f"Unknown capability: {intent}"
                }
            return {"allowed": True, "reason": None}
        except Exception as e:
            return {
                "allowed": False,
                "reason": f"Capability check failed: {str(e)}"
            }
    
    @staticmethod
    async def _check_role_authorized(intent: str, user) -> Dict[str, Any]:
        """Check if the user's role is authorized for this intent."""
        try:
            user_role = user.role if hasattr(user, 'role') else None
            if not user_role:
                return {
                    "allowed": False,
                    "reason": "User role not found"
                }
            
            # Use RBAC validator to check authorization
            is_authorized = rbac_validator.validate_capability(
                intent=intent,
                user_role=user_role
            )
            
            if not is_authorized:
                return {
                    "allowed": False,
                    "reason": f"Role '{user_role}' is not authorized for '{intent}'"
                }
            
            return {"allowed": True, "reason": None}
        except Exception as e:
            return {
                "allowed": False,
                "reason": f"Role authorization check failed: {str(e)}"
            }
    
    @staticmethod
    def _check_entities_present(intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Check if all required entities are present."""
        # Define required entities for each intent
        REQUIRED_ENTITIES = {
            "CREATE_TASK": ["name", "department_id"],
            "CREATE_PROJECT": ["name", "department_id"],
            "UPDATE_TASK": ["task_id"],
            "DELETE_TASK": ["task_id"],
            "CREATE_DEPARTMENT": ["name"],
            "UPDATE_DEPARTMENT": ["department_id"],
            "DELETE_DEPARTMENT": ["department_id"],
            "REGISTER_USER": ["name", "department_id", "role_id", "password"],
            "ADD_MEMBER": ["name", "department_id", "role_id", "password"],
            "UPDATE_USER": ["user_id"],
            "DELETE_USER": ["name"],
            "ASSIGN_TASK": ["task_id", "user_id"],
            "UPDATE_PROJECT": ["project_id"],
            "DELETE_PROJECT": ["project_id"],
        }
        
        required = REQUIRED_ENTITIES.get(intent, [])
        missing = []
        
        for entity in required:
            if entity not in entities or not entities[entity]:
                missing.append(entity)
        
        if missing:
            return {
                "allowed": False,
                "reason": f"Missing required entities: {', '.join(missing)}",
                "clarification": f"To {intent.replace('_', ' ').lower()}, I need the following information: {', '.join(missing)}. Could you please provide these details?"
            }
        
        return {"allowed": True, "reason": None, "clarification": None}
    
    @staticmethod
    def _check_entity_ambiguity(entities: Dict[str, Any]) -> Dict[str, Any]:
        """Check for ambiguous or placeholder entity values."""
        ambiguous_entities = []
        
        for key, value in entities.items():
            if not value:
                continue
            
            value_str = str(value).lower().strip()
            
            # Check for ambiguous patterns
            for pattern in SafetyMiddleware.AMBIGUOUS_PATTERNS:
                if pattern in value_str and len(value_str) < 20:
                    ambiguous_entities.append(f"{key}='{value}'")
                    break
        
        if ambiguous_entities:
            return {
                "allowed": False,
                "reason": f"Ambiguous entity values detected: {', '.join(ambiguous_entities)}",
                "clarification": f"The following values seem unclear: {', '.join(ambiguous_entities)}. Could you please provide specific details instead of generic placeholders?"
            }
        
        return {"allowed": True, "reason": None, "clarification": None}
    
    @staticmethod
    async def _check_cross_scope(
        intent: str,
        entities: Dict[str, Any],
        db: AsyncSession,
        user
    ) -> Dict[str, Any]:
        """Check for cross-scope access attempts."""
        try:
            # Use scope guard to validate scope
            scope_result = await scope_guard.validate_scope(
                intent=intent,
                entities=entities,
                db=db,
                user=user
            )
            
            if not scope_result.get("allowed", True):
                return {
                    "allowed": False,
                    "reason": scope_result.get("reason", "Scope validation failed")
                }
            
            return {"allowed": True, "reason": None}
        except Exception as e:
            return {
                "allowed": False,
                "reason": f"Scope validation failed: {str(e)}"
            }


# Singleton instance
safety_middleware = SafetyMiddleware()

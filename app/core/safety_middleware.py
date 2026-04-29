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
import time

from app.modules.orbit_assistant.engine.capability_resolver import capability_resolver
from app.modules.orbit_assistant.engine.rbac_engine import rbac_engine
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
        
        # NOTE: RBAC authorization check removed from safety middleware
        # RBAC is handled by RBACEngine in assistant_service.py ONLY
        # Safety middleware is observer-only for RBAC decisions
        
        # OBSERVABILITY: Emit security intelligence signals
        SafetyMiddleware._emit_security_intelligence(intent, user, entities)
        
        # 2. Check for missing entities (names-based)
        entity_check = SafetyMiddleware._check_entities_present(intent, entities)
        if not entity_check["allowed"]:
            return {
                "allowed": False,
                "reason": entity_check["reason"],
                "requires_clarification": True,
                "clarification": entity_check["clarification"]
            }
        
        # 3. Check for ambiguous entities
        ambiguity_check = SafetyMiddleware._check_entity_ambiguity(entities)
        if not ambiguity_check["allowed"]:
            return {
                "allowed": False,
                "reason": ambiguity_check["reason"],
                "requires_clarification": True,
                "clarification": ambiguity_check["clarification"]
            }
        
        # 4. Resolve names to IDs for database operations
        resolved_entities = await SafetyMiddleware.resolve_names_to_ids(entities, db)
        
        # 5. Check for cross-scope access
        scope_check = await SafetyMiddleware._check_cross_scope(intent, resolved_entities, db, user)
        if not scope_check["allowed"]:
            return {
                "allowed": False,
                "reason": scope_check["reason"],
                "requires_clarification": False,
                "clarification": None
            }
        
        # All checks passed - return resolved entities with IDs
        return {
            "allowed": True,
            "reason": None,
            "requires_clarification": False,
            "clarification": None,
            "resolved_entities": resolved_entities
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
    def _emit_security_intelligence(intent: str, user, entities: Dict[str, Any]):
        """
        Emit security intelligence signals for observability.
        This is observer-only - does NOT block or approve requests.
        
        Args:
            intent: The intent being executed
            user: The user object
            entities: Extracted entities from the request
        """
        try:
            # Extract role name from user object
            # Priority: role_from_token (from JWT) > role (from DB relationship)
            user_role = getattr(user, 'role_from_token', None)
            if not user_role:
                user_role = getattr(user, 'role', None)
            
            if not user_role:
                user_role = "UNKNOWN"
            
            # Handle Role ORM object
            if hasattr(user_role, 'role'):
                user_role = user_role.role
            # Handle string representation of Role object
            elif isinstance(user_role, str) and "Role object at" in user_role:
                user_role = "UNKNOWN"
            elif not isinstance(user_role, str):
                user_role = str(user_role)
            
            # High-risk operations
            high_risk_intents = ["DELETE_USER", "ASSIGN_ROLE", "UPDATE_ROLE", "UPDATE_PERMISSIONS"]
            
            safety_event = {
                "intent": intent,
                "role": user_role,
                "risk_signals": {
                    "suspicious_intent": intent not in capability_resolver.get_all_intents(),
                    "repeated_action": False,  # Could be enhanced with session tracking
                    "high_risk_operation": intent in high_risk_intents
                },
                "timestamp": time.time()
            }
            
            # Log security intelligence (can be sent to analytics/audit pipeline)
            from app.modules.orbit_assistant.engine.logger import get_logger
            log = get_logger("safety_observability")
            
            if safety_event["risk_signals"]["high_risk_operation"]:
                log.warning(f"High-risk operation detected: {safety_event}")
            else:
                log.info(f"Security intelligence: {safety_event}")
                
        except Exception as e:
            # Observability failure should not block execution
            from app.modules.orbit_assistant.engine.logger import get_logger
            log = get_logger("safety_observability")
            log.error(f"Failed to emit security intelligence: {str(e)}")
    
    @staticmethod
    async def resolve_names_to_ids(entities: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Resolve entity names to IDs for database operations.
        Converts department_name -> department_id, role_name -> role_id.
        
        Args:
            entities: Dictionary with entity names
            db: Database session
            
        Returns:
            Dictionary with both names and resolved IDs
        """
        from sqlalchemy import select
        from app.modules.auth.auth_model import Role
        from app.modules.department.department_model import Department
        
        resolved = entities.copy()
        
        # Resolve department_name to department_id
        if "department_name" in entities and entities["department_name"]:
            dept_stmt = select(Department).where(
                Department.name.ilike(f"%{entities['department_name']}%")
            )
            dept_res = await db.execute(dept_stmt)
            dept = dept_res.scalar_one_or_none()
            if dept:
                resolved["department_id"] = dept.id
        
        # Resolve role_name to role_id
        if "role_name" in entities and entities["role_name"]:
            role_stmt = select(Role).where(
                Role.role.ilike(f"%{entities['role_name']}%")
            )
            role_res = await db.execute(role_stmt)
            role = role_res.scalar_one_or_none()
            if role:
                resolved["role_id"] = role.id
        
        return resolved

    @staticmethod
    def _check_entities_present(intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Check if all required entities are present."""
        # Define required entities for each intent (use names instead of IDs)
        REQUIRED_ENTITIES = {
            "CREATE_TASK": ["name", "department_name"],
            "CREATE_PROJECT": ["name", "department_name"],
            "UPDATE_TASK": ["task_id"],
            "DELETE_TASK": ["task_id"],
            "CREATE_DEPARTMENT": ["name"],
            "UPDATE_DEPARTMENT": ["department_name"],
            "DELETE_DEPARTMENT": ["department_name"],
            "REGISTER_USER": ["name", "email", "department_name", "role_name", "password"],
            "ADD_MEMBER": ["name", "email", "department_name", "role_name", "password"],
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
            # Extract role name from user object
            # Priority: role_from_token (from JWT) > role (from DB relationship)
            user_role = getattr(user, 'role_from_token', None)
            if not user_role:
                user_role = getattr(user, 'role', None)
            
            if not user_role:
                user_role = "EMPLOYEE"
            
            # Handle Role ORM object
            if hasattr(user_role, 'role'):
                user_role = user_role.role
            # Handle string representation of Role object
            elif isinstance(user_role, str) and "Role object at" in user_role:
                user_role = "EMPLOYEE"
            elif not isinstance(user_role, str):
                user_role = str(user_role)
            
            user_id = user.id if hasattr(user, 'id') else None
            
            if not user_id:
                return {
                    "allowed": False,
                    "reason": "User ID not found"
                }
            
            # Use scope guard to validate scope
            scope_result = await scope_guard.validate_scope(
                intent=intent,
                role=user_role,
                user_id=user_id,
                entities=entities,
                db=db
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

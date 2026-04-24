"""
Execution Validator — Mandatory Pre-Execution Validation
Validates all required entities before capability execution to prevent silent fallbacks and hardcoded defaults.
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.dependency_validator import DependencyValidator, DependencyValidationError


class ExecutionValidator:
    """
    Validates all required entities before execution.
    Prevents silent fallbacks and hardcoded defaults.
    """

    # Required entities for each capability
    REQUIRED_ENTITIES = {
        "CREATE_TASK": ["department_id"],
        "CREATE_PROJECT": ["department_id"],
        "REGISTER_USER": ["department_id", "role_id", "password"],
        "ADD_MEMBER": ["department_id", "role_id", "password"],
    }

    @staticmethod
    async def validate_before_execution(
        intent: str,
        entities: Dict[str, Any],
        db: AsyncSession,
        user
    ) -> Dict[str, Any]:
        """
        Validate all required entities for the intent before execution.
        
        Args:
            intent: The intent being executed
            entities: Extracted entities from NLU
            db: Database session for validation
            user: Current user
        
        Returns:
            Dict with 'allowed' boolean and optional 'reason' string
        
        Raises:
            HTTPException: If validation fails (hard failure)
        """
        required = ExecutionValidator.REQUIRED_ENTITIES.get(intent, [])
        
        # Check for missing required entities
        missing = []
        for entity in required:
            if entity not in entities or not entities[entity]:
                missing.append(entity)
        
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required entities for {intent}: {', '.join(missing)}. "
                       f"Please provide: {', '.join(required)}"
            )
        
        # Validate dependencies using DependencyValidator
        try:
            await validate_capability_dependencies(intent, db, user, entities)
        except DependencyValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dependency validation failed: {str(e)}"
            )
        
        return {"allowed": True, "reason": None}


# Import the dependency validator function
from app.core.dependency_validator import validate_capability_dependencies

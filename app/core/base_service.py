"""
Base Service for Enterprise Service Layer

Provides standard service operations and response formatting.
All services should inherit from this class.
"""

from typing import Any, Optional, Type, TypeVar, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.base_repository import BaseRepository, ModelType
from app.core.response import Response, ResponseBuilder, to_dict

RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class BaseService:
    """
    Base service with standard operations and response formatting.
    
    Provides:
    - Standard CRUD operations via repository
    - Consistent response formatting
    - Error handling and validation
    - Transaction management
    """
    
    repository: BaseRepository
    
    def __init__(self, repository: BaseRepository):
        """
        Initialize service with repository.
        
        Args:
            repository: Repository instance for data access
        """
        self.repository = repository
    
    async def create(
        self,
        db: AsyncSession,
        obj_in: ModelType,
        commit: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Model instance to create
            commit: Whether to commit immediately
        
        Returns:
            Standardized response dict
        """
        try:
            result = await self.repository.create(db, obj_in, commit)
            return to_dict(ResponseBuilder.success(
                message=f"{self.repository.model.__name__} created successfully",
                data={"id": result.id}
            ))
        except Exception as e:
            await db.rollback()
            return to_dict(ResponseBuilder.error(
                message=f"Failed to create {self.repository.model.__name__}: {str(e)}"
            ))
    
    async def get_by_id(
        self,
        db: AsyncSession,
        id: Any,
        eager_load: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Get a single record by ID.
        
        Args:
            db: Database session
            id: Record ID
            eager_load: List of relationships to eager load
        
        Returns:
            Standardized response dict
        """
        result = await self.repository.get_by_id(db, id, eager_load)
        
        if not result:
            return to_dict(ResponseBuilder.not_found(
                resource=self.repository.model.__name__,
                identifier=id
            ))
        
        return to_dict(ResponseBuilder.success(
            message=f"{self.repository.model.__name__} retrieved successfully",
            data=self._serialize_model(result)
        ))
    
    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        eager_load: Optional[List] = None
    ) -> Dict[str, Any]:
        """
        Get all records with optional filtering and pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            eager_load: List of relationships to eager load
        
        Returns:
            Standardized response dict
        """
        results = await self.repository.get_all(db, skip, limit, filters, eager_load)
        
        return to_dict(ResponseBuilder.success(
            message=f"Found {len(results)} {self.repository.model.__name__} records",
            data=[self._serialize_model(r) for r in results]
        ))
    
    async def update(
        self,
        db: AsyncSession,
        id: Any,
        obj_in: Dict[str, Any],
        commit: bool = True
    ) -> Dict[str, Any]:
        """
        Update a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            obj_in: Dictionary of fields to update
            commit: Whether to commit immediately
        
        Returns:
            Standardized response dict
        """
        # Check if record exists
        existing = await self.repository.get_by_id(db, id)
        if not existing:
            return to_dict(ResponseBuilder.not_found(
                resource=self.repository.model.__name__,
                identifier=id
            ))
        
        try:
            result = await self.repository.update(db, id, obj_in, commit)
            return to_dict(ResponseBuilder.success(
                message=f"{self.repository.model.__name__} updated successfully",
                data={"id": result.id}
            ))
        except Exception as e:
            await db.rollback()
            return to_dict(ResponseBuilder.error(
                message=f"Failed to update {self.repository.model.__name__}: {str(e)}"
            ))
    
    async def delete(
        self,
        db: AsyncSession,
        id: Any,
        commit: bool = True
    ) -> Dict[str, Any]:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            commit: Whether to commit immediately
        
        Returns:
            Standardized response dict
        """
        # Check if record exists
        existing = await self.repository.get_by_id(db, id)
        if not existing:
            return to_dict(ResponseBuilder.not_found(
                resource=self.repository.model.__name__,
                identifier=id
            ))
        
        try:
            deleted = await self.repository.delete(db, id, commit)
            if deleted:
                return to_dict(ResponseBuilder.success(
                    message=f"{self.repository.model.__name__} deleted successfully"
                ))
            return to_dict(ResponseBuilder.error(
                message=f"Failed to delete {self.repository.model.__name__}"
            ))
        except Exception as e:
            await db.rollback()
            return to_dict(ResponseBuilder.error(
                message=f"Failed to delete {self.repository.model.__name__}: {str(e)}"
            ))
    
    async def exists(
        self,
        db: AsyncSession,
        id: Any
    ) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            db: Database session
            id: Record ID
        
        Returns:
            True if exists, False otherwise
        """
        return await self.repository.exists(db, id)
    
    async def exists_by_field(
        self,
        db: AsyncSession,
        field: str,
        value: Any
    ) -> bool:
        """
        Check if a record exists by field value.
        
        Args:
            db: Database session
            field: Field name
            value: Field value
        
        Returns:
            True if exists, False otherwise
        """
        return await self.repository.exists_by_field(db, field, value)
    
    def _serialize_model(self, model: ModelType) -> Dict[str, Any]:
        """
        Serialize model instance to dictionary.
        
        Override this method in subclasses for custom serialization.
        
        Args:
            model: Model instance to serialize
        
        Returns:
            Dictionary representation
        """
        if hasattr(model, '__table__'):
            return {c.name: getattr(model, c.name) for c in model.__table__.columns}
        return {}
    
    def _validate_required_fields(
        self,
        data: Dict[str, Any],
        required_fields: List[str]
    ) -> None:
        """
        Validate that required fields are present.
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
        
        Raises:
            HTTPException: If required fields are missing
        """
        missing = [field for field in required_fields if field not in data or data[field] is None]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required fields: {', '.join(missing)}"
            )

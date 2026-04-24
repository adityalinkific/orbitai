"""
Base Repository for Enterprise Data Access Layer

Provides standard CRUD operations and common database patterns.
All repositories should inherit from this class.
"""

from typing import Any, Optional, Type, TypeVar, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository:
    """
    Base repository with standard CRUD operations.
    
    Provides:
    - create: Insert new record
    - get_by_id: Fetch single record by ID
    - get_all: Fetch all records with optional filters
    - update: Update existing record
    - delete: Delete record
    - exists: Check if record exists
    """
    
    model: Type[ModelType]
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize repository with model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    async def create(
        self,
        db: AsyncSession,
        obj_in: ModelType,
        commit: bool = True
    ) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Model instance to create
            commit: Whether to commit immediately
        
        Returns:
            Created model instance
        """
        db.add(obj_in)
        if commit:
            await db.commit()
            await db.refresh(obj_in)
        return obj_in
    
    async def get_by_id(
        self,
        db: AsyncSession,
        id: Any,
        eager_load: Optional[List] = None
    ) -> Optional[ModelType]:
        """
        Get a single record by ID.
        
        Args:
            db: Database session
            id: Record ID
            eager_load: List of relationships to eager load
        
        Returns:
            Model instance or None
        """
        stmt = select(self.model).where(self.model.id == id)
        
        if eager_load:
            for relation in eager_load:
                stmt = stmt.options(selectinload(relation))
        
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        eager_load: Optional[List] = None
    ) -> List[ModelType]:
        """
        Get all records with optional filtering and pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            eager_load: List of relationships to eager load
        
        Returns:
            List of model instances
        """
        stmt = select(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)
        
        if eager_load:
            for relation in eager_load:
                stmt = stmt.options(selectinload(relation))
        
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def update(
        self,
        db: AsyncSession,
        id: Any,
        obj_in: Dict[str, Any],
        commit: bool = True
    ) -> Optional[ModelType]:
        """
        Update a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            obj_in: Dictionary of fields to update
            commit: Whether to commit immediately
        
        Returns:
            Updated model instance or None
        """
        stmt = update(self.model).where(self.model.id == id).values(obj_in)
        await db.execute(stmt)
        
        if commit:
            await db.commit()
        
        return await self.get_by_id(db, id)
    
    async def update_instance(
        self,
        db: AsyncSession,
        instance: ModelType,
        obj_in: Dict[str, Any],
        commit: bool = True
    ) -> ModelType:
        """
        Update an existing model instance.
        
        Args:
            db: Database session
            instance: Model instance to update
            obj_in: Dictionary of fields to update
            commit: Whether to commit immediately
        
        Returns:
            Updated model instance
        """
        for field, value in obj_in.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        
        if commit:
            await db.commit()
            await db.refresh(instance)
        
        return instance
    
    async def delete(
        self,
        db: AsyncSession,
        id: Any,
        commit: bool = True
    ) -> bool:
        """
        Delete a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            commit: Whether to commit immediately
        
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        
        if commit:
            await db.commit()
        
        return result.rowcount > 0
    
    async def delete_instance(
        self,
        db: AsyncSession,
        instance: ModelType,
        commit: bool = True
    ) -> bool:
        """
        Delete a model instance.
        
        Args:
            db: Database session
            instance: Model instance to delete
            commit: Whether to commit immediately
        
        Returns:
            True if deleted
        """
        await db.delete(instance)
        
        if commit:
            await db.commit()
        
        return True
    
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
        stmt = select(self.model).where(self.model.id == id)
        result = await db.execute(stmt)
        return result.scalars().first() is not None
    
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
        if not hasattr(self.model, field):
            return False
        
        stmt = select(self.model).where(getattr(self.model, field) == value)
        result = await db.execute(stmt)
        return result.scalars().first() is not None
    
    async def count(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filters.
        
        Args:
            db: Database session
            filters: Dictionary of field filters
        
        Returns:
            Number of records
        """
        from sqlalchemy import func
        
        stmt = select(func.count()).select_from(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    stmt = stmt.where(getattr(self.model, field) == value)
        
        result = await db.execute(stmt)
        return result.scalar()

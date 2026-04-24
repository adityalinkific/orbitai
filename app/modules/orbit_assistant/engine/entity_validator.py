"""
Entity Validator - Centralized validation for all entity types
Provides regex-based extraction and validation for emails, names, roles, etc.
"""

import re
import logging
from typing import Optional, Tuple, Dict, Any

log = logging.getLogger("entity_validator")


class EntityValidator:
    """
    Centralized entity validation and extraction.
    Ensures all entities are validated before database operations.
    """
    
    # Email regex pattern (RFC 5322 compliant simplified)
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    )
    
    # Name validation - minimum 3 characters, alphanumeric + spaces
    NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_]{3,100}$')
    
    # Role name pattern
    ROLE_PATTERN = re.compile(r'^[a-zA-Z0-9_]{2,50}$')
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format using regex.
        
        Returns:
            (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        if not isinstance(email, str):
            return False, "Email must be a string"
        
        email = email.strip()
        
        if len(email) > 100:
            return False, "Email is too long (max 100 characters)"
        
        if not EntityValidator.EMAIL_PATTERN.match(email):
            return False, f"Invalid email format: {email}"
        
        return True, None
    
    @staticmethod
    def validate_name(name: str, entity_type: str = "entity") -> Tuple[bool, Optional[str]]:
        """
        Validate name format and length.
        
        Args:
            name: The name to validate
            entity_type: Type of entity (for error messages)
        
        Returns:
            (is_valid, error_message)
        """
        if not name:
            return False, f"{entity_type} name is required"
        
        if not isinstance(name, str):
            return False, f"{entity_type} name must be a string"
        
        name = name.strip()
        
        if len(name) < 3:
            return False, f"{entity_type} name must be at least 3 characters"
        
        if len(name) > 100:
            return False, f"{entity_type} name is too long (max 100 characters)"
        
        if not EntityValidator.NAME_PATTERN.match(name):
            return False, f"{entity_type} name contains invalid characters"
        
        return True, None
    
    @staticmethod
    def validate_role(role: str) -> Tuple[bool, Optional[str]]:
        """
        Validate role name format.
        
        Returns:
            (is_valid, error_message)
        """
        if not role:
            return False, "Role name is required"
        
        if not isinstance(role, str):
            return False, "Role name must be a string"
        
        role = role.strip()
        
        if len(role) < 2:
            return False, "Role name must be at least 2 characters"
        
        if len(role) > 50:
            return False, "Role name is too long (max 50 characters)"
        
        if not EntityValidator.ROLE_PATTERN.match(role):
            return False, "Role name contains invalid characters (alphanumeric and underscore only)"
        
        return True, None
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """
        Extract email from text using regex.
        
        Returns:
            First valid email found or None
        """
        if not text:
            return None
        
        match = EntityValidator.EMAIL_PATTERN.search(text)
        if match:
            return match.group(0)
        return None
    
    @staticmethod
    def extract_names(text: str) -> list:
        """
        Extract potential names from text.
        
        Returns:
            List of potential name strings
        """
        if not text:
            return []
        
        # Extract words that look like names (capitalized, 2+ characters)
        name_pattern = re.compile(r'\b[A-Z][a-zA-Z]{2,}\b')
        return name_pattern.findall(text)
    
    @staticmethod
    def validate_and_extract_entities(entities: Dict[str, Any], intent: str) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        """
        Validate all entities based on intent requirements.
        
        Args:
            entities: Extracted entities from NLU
            intent: The intent being executed
        
        Returns:
            (is_valid, validated_entities, error_message)
        """
        validated = entities.copy()
        errors = []
        
        # Email validation for intents that require it
        if intent in ["REGISTER_USER", "UPDATE_USER", "UPDATE_EMAIL", "SEND_EMAIL"]:
            email = entities.get("email")
            if email:
                is_valid, error = EntityValidator.validate_email(email)
                if not is_valid:
                    errors.append(error)
                else:
                    validated["email"] = email.strip()
        
        # Name validation for user/department/project intents
        if intent in ["REGISTER_USER", "UPDATE_USER", "CREATE_DEPARTMENT", "UPDATE_DEPARTMENT", 
                      "CREATE_PROJECT", "UPDATE_PROJECT", "CREATE_TASK", "UPDATE_TASK"]:
            name = entities.get("name")
            if name:
                entity_type = "user" if "USER" in intent else ("department" if "DEPARTMENT" in intent else 
                                                              ("project" if "PROJECT" in intent else "task"))
                is_valid, error = EntityValidator.validate_name(name, entity_type)
                if not is_valid:
                    errors.append(error)
                else:
                    validated["name"] = name.strip()
        
        # Role validation
        if intent in ["UPDATE_ROLE", "UPDATE_PERMISSIONS", "ASSIGN_ROLE"]:
            role = entities.get("role")
            if role:
                is_valid, error = EntityValidator.validate_role(role)
                if not is_valid:
                    errors.append(error)
                else:
                    validated["role"] = role.strip()
        
        if errors:
            return False, validated, "; ".join(errors)
        
        return True, validated, None


# Singleton instance
entity_validator = EntityValidator()

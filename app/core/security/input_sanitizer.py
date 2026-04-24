import bleach
from typing import Any, Dict, List, Optional


class InputSanitizer:
    """Sanitize user inputs to prevent XSS and injection attacks."""
    
    # Allowed HTML tags (empty = strip all HTML)
    ALLOWED_TAGS = []
    
    # Allowed HTML attributes (empty = strip all attributes)
    ALLOWED_ATTRIBUTES = {}
    
    # Allowed protocols for links
    ALLOWED_PROTOCOLS = ['http', 'https']
    
    @staticmethod
    def sanitize_string(input_string: Optional[str]) -> str:
        """Sanitize a string input."""
        if input_string is None:
            return ""
        
        if not isinstance(input_string, str):
            input_string = str(input_string)
        
        # Strip all HTML tags and attributes
        sanitized = bleach.clean(
            input_string,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            protocols=InputSanitizer.ALLOWED_PROTOCOLS,
            strip=True
        )
        
        return sanitized
    
    @staticmethod
    def sanitize_email(email: Optional[str]) -> str:
        """Sanitize email address."""
        if email is None:
            return ""
        
        if not isinstance(email, str):
            email = str(email)
        
        # Email addresses shouldn't contain HTML, but sanitize anyway
        sanitized = bleach.clean(email, strip=True)
        
        # Additional email validation/sanitization
        sanitized = sanitized.strip().lower()
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(input_dict: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Sanitize all string values in a dictionary."""
        if input_dict is None:
            return {}
        
        sanitized = {}
        for key, value in input_dict.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = InputSanitizer.sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_list(input_list: Optional[List[Any]]) -> List[Any]:
        """Sanitize all string values in a list."""
        if input_list is None:
            return []
        
        sanitized = []
        for item in input_list:
            if isinstance(item, str):
                sanitized.append(InputSanitizer.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(InputSanitizer.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(InputSanitizer.sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    @staticmethod
    def sanitize_entities(entities: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Sanitize entity dictionary from NLU."""
        return InputSanitizer.sanitize_dict(entities)


# Singleton instance
input_sanitizer = InputSanitizer()

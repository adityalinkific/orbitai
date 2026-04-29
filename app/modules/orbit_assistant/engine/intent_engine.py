"""
Intent Engine — Pure Intent Parsing Layer
Converts natural language → structured intent.
NO RBAC logic, NO permission checking.
"""

from typing import Dict, Any
from .logger import get_logger
from .nlu_engine import nlu_engine
from .intent_normalizer import normalize_intent

log = get_logger("intent_engine")


class IntentEngine:
    """
    Pure intent parsing engine.
    NO RBAC authorization logic.
    NO permission checking.
    ONLY parses natural language into structured intent.
    """

    def __init__(self):
        self.nlu_engine = nlu_engine
        log.info("Intent Engine initialized")

    def parse(self, message: str, config: Dict[str, Any] = None, user_context: Dict[str, Any] = None) -> str:
        """
        Parse a natural language message into an intent string.

        Args:
            message: Natural language input from user
            config: Configuration dict (optional, passed to NLU)
            user_context: User context dict (optional, passed to NLU)

        Returns:
            Intent string (e.g., "CREATE_USER", "DELETE_TASK")
        """
        if config is None:
            config = {}
        if user_context is None:
            user_context = {}

        try:
            # Use existing NLU engine for parsing
            nlu_result = self.nlu_engine.parse(
                message=message,
                config=config,
                user_context=user_context
            )

            # Extract intent from NLU result
            intent = nlu_result.get("intent", "UNKNOWN")
            
            # Normalize intent to canonical form
            intent = normalize_intent(intent)
            
            log.info(f"Intent parsed: {intent} from message: {message[:50]}")
            return intent

        except Exception as e:
            log.error(f"Intent parsing failed: {str(e)}")
            return "UNKNOWN"

    def parse_with_entities(self, message: str, config: Dict[str, Any] = None, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parse a natural language message into intent and entities.
        This is a convenience method for when entities are needed.

        Args:
            message: Natural language input from user
            config: Configuration dict (optional, passed to NLU)
            user_context: User context dict (optional, passed to NLU)

        Returns:
            Dict with 'intent' and 'entities' keys
        """
        if config is None:
            config = {}
        if user_context is None:
            user_context = {}

        try:
            nlu_result = self.nlu_engine.parse(
                message=message,
                config=config,
                user_context=user_context
            )

            intent = nlu_result.get("intent", "UNKNOWN")
            intent = normalize_intent(intent)
            entities = nlu_result.get("entities", {})

            log.info(f"Intent parsed with entities: {intent} entities={entities}")
            return {
                "intent": intent,
                "entities": entities
            }

        except Exception as e:
            log.error(f"Intent parsing with entities failed: {str(e)}")
            return {
                "intent": "UNKNOWN",
                "entities": {}
            }


# ─────────────────────────────────────────────
# SINGLETON EXPORT
# ─────────────────────────────────────────────

intent_engine = IntentEngine()

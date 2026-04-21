"""
Confirmation Manager — Guards destructive actions.
Requires explicit user confirmation before executing DELETE, BULK_UPDATE, etc.
"""

import time
from typing import Any

from .logger import get_logger

log = get_logger("confirmation_manager")

# In-memory store for pending confirmations (use Redis/DB in production)
_pending_confirmations: dict[str, dict[str, Any]] = {}

_pending_emails: dict[str, dict[str, Any]] = {}

async def store_pending_email(recipient: str, subject: str, body: str, sent_by: str, sender_name: str = None) -> str:
    import uuid
    request_id = str(uuid.uuid4())
    _pending_emails[request_id] = {
        "type": "email",
        "to": recipient,
        "subject": subject,
        "body": body,
        "sent_by": sent_by,
        "sender_name": sender_name
    }
    return request_id


def requires_confirmation(
    intent: str,
    destructive_actions: list[str],
) -> bool:
    """Check if this action needs user confirmation."""
    action = intent.split("_")[0] if "_" in intent else intent
    return action in destructive_actions


def create_confirmation(
    request_id: str,
    intent: str,
    entity: str,
    data: dict[str, Any],
    user_id: str,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    Create a pending confirmation for a destructive action.
    Returns a confirmation prompt for the user.
    """
    confirmation = {
        "request_id": request_id,
        "intent": intent,
        "entity": entity,
        "data": data,
        "user_id": user_id,
        "created_at": time.time(),
        "timeout_seconds": timeout_seconds,
        "status": "pending",
    }
    _pending_confirmations[request_id] = confirmation

    log.warning(
        f"Confirmation required: {intent} on {entity} | request_id={request_id}"
    )

    return {
        "confirmation_required": True,
        "request_id": request_id,
        "message": (
            f"⚠️ You are about to **{intent.replace('_', ' ').lower()}** "
            f"on entity '{entity}'.\n\n"
            f"Data: {data}\n\n"
            f"Please confirm by sending: "
            f'{{"request_id": "{request_id}", "confirmed": true}}'
        ),
        "expires_in_seconds": timeout_seconds,
    }


def process_confirmation(
    request_id: str,
    confirmed: bool,
) -> dict[str, Any]:
    """
    Process a user's confirmation response.
    Returns the original action data if confirmed, or cancellation.
    """
    pending = _pending_confirmations.get(request_id)
    
    if request_id in _pending_emails:
        pending_email = _pending_emails.pop(request_id)
        # Note: the actual sending happens in ServiceBridge or orchestrated differently via execute_confirmed_action.
        # But wait, to keep this clean with the process_confirmation return structure:
        return {
            "success": True,
            "intent": "SEND_EMAIL",
            "entity": "email",
            "data": pending_email,
            "message": "Confirmed. Executing action...",
        }

    if not pending:
        log.warning(f"No pending confirmation found: {request_id}")
        return {
            "success": False,
            "message": "No pending confirmation found for this request.",
        }

    # Check timeout
    elapsed = time.time() - pending["created_at"]
    if elapsed > pending["timeout_seconds"]:
        _pending_confirmations.pop(request_id, None)
        log.warning(f"Confirmation expired: {request_id} (elapsed={elapsed:.0f}s)")
        return {
            "success": False,
            "message": "Confirmation expired. Please re-issue the command.",
        }

    if not confirmed:
        _pending_confirmations.pop(request_id, None)
        log.info(f"Action cancelled by user: {request_id}")
        return {
            "success": False,
            "message": "Action cancelled.",
        }

    # Confirmed — return original action data for execution
    _pending_confirmations.pop(request_id, None)
    log.info(f"Action confirmed: {request_id}")
    return {
        "success": True,
        "intent": pending["intent"],
        "entity": pending["entity"],
        "data": pending["data"],
        "message": "Confirmed. Executing action...",
    }

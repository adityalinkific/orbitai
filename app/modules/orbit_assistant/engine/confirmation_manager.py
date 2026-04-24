"""
Confirmation Manager — Guards destructive actions.
Requires explicit user confirmation before executing DELETE, BULK_UPDATE, etc.
"""

import time
from typing import Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from .logger import get_logger
from app.modules.orbit_assistant.pending_confirmation_repository import PendingConfirmationRepository

log = get_logger("confirmation_manager")

# Repository instance
_confirmation_repository = PendingConfirmationRepository()

# Legacy in-memory store for emails (to be migrated)
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


async def create_confirmation(
    request_id: str,
    intent: str,
    entity: str,
    data: dict[str, Any],
    user_id: str,
    timeout_seconds: int = 60,
    db: Optional[AsyncSession] = None,
) -> dict[str, Any]:
    """
    Create a pending confirmation for a destructive action.
    Returns a confirmation prompt for the user.
    Stores in database for persistence and horizontal scaling.
    """
    if db is None:
        # Fallback to in-memory if no DB session (should not happen in production)
        log.warning("No DB session provided for confirmation, using in-memory fallback")
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
    else:
        # Store in database
        expires_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        try:
            await _confirmation_repository.create_confirmation(
                db=db,
                request_id=request_id,
                intent=intent,
                entity=entity,
                user_id=int(user_id),
                payload=data,
                expires_at=expires_at
            )
            await db.commit()
        except Exception as e:
            log.error(f"Failed to store confirmation in database: {str(e)}")
            # Fallback to in-memory
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


async def process_confirmation(
    request_id: str,
    confirmed: bool,
    db: Optional[AsyncSession] = None,
) -> dict[str, Any]:
    """
    Process a user's confirmation response.
    Returns the original action data if confirmed, or cancellation.
    """
    # Check database first
    if db is not None:
        try:
            confirmation = await _confirmation_repository.get_confirmation(db, request_id)
            if confirmation:
                if not confirmed:
                    await _confirmation_repository.cancel_confirmation(db, request_id)
                    await db.commit()
                    log.info(f"Action cancelled by user: {request_id}")
                    return {
                        "success": False,
                        "message": "Action cancelled.",
                    }
                
                # Confirm the action
                success = await _confirmation_repository.confirm_confirmation(db, request_id)
                if success:
                    import json
                    payload = json.loads(confirmation.payload) if confirmation.payload else {}
                    log.info(f"Action confirmed: {request_id}")
                    return {
                        "success": True,
                        "intent": confirmation.intent,
                        "entity": confirmation.entity,
                        "data": payload,
                        "message": "Confirmed. Executing action...",
                    }
                else:
                    return {
                        "success": False,
                        "message": "Confirmation expired or already processed.",
                    }
        except Exception as e:
            log.error(f"Failed to process confirmation from database: {str(e)}")
    
    # Fallback to in-memory
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


def get_latest_confirmation(user_id: str) -> dict[str, Any] | None:
    """
    Get the latest pending confirmation for a user.
    Used for simple 'confirm' messages without request_id.
    """
    if not _pending_confirmations:
        return None
    
    # Get the most recent confirmation for this user
    user_confirmations = [
        (req_id, conf) for req_id, conf in _pending_confirmations.items()
        if conf.get("user_id") == user_id
    ]
    
    if not user_confirmations:
        return None
    
    # Sort by created_at descending and return the most recent
    user_confirmations.sort(key=lambda x: x[1]["created_at"], reverse=True)
    latest_req_id, latest_conf = user_confirmations[0]
    
    return {
        "request_id": latest_req_id,
        "confirmation": latest_conf
    }

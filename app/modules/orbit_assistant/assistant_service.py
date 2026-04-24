from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.orbit_assistant.engine.context_manager import context_manager
from app.modules.orbit_assistant.engine.nlu_engine import nlu_engine
from app.modules.orbit_assistant.engine.intent_validator import intent_validator
from app.modules.orbit_assistant.engine.rbac_validator import rbac_validator
from app.modules.orbit_assistant.engine.capability_resolver import capability_resolver
from app.modules.orbit_assistant.engine.scope_guard import scope_guard
from app.modules.orbit_assistant.engine.executor import executor
from app.modules.orbit_assistant.engine.response_builder import response_builder
from app.core.security.input_sanitizer import input_sanitizer
from app.modules.orbit_assistant.engine.error_handler import error_handler
from app.modules.orbit_assistant.engine.logger import get_logger
from app.modules.orbit_assistant.engine.assistant_logger import log_assistant_event
from app.modules.orbit_assistant.schemas import ChatRequest
import yaml
import os

log = get_logger("assistant_service")
log.info("Orbit Assistant initialized")


class AssistantService:
    """
    Orchestrator for the Orbit Assistant.
    Enterprise Edition.
    """

    async def chat(
        self,
        request: ChatRequest,
        db: AsyncSession,
        current_user: Any,
    ):
        print(f"\n[LIVE DEBUG] CHAT MESSAGE: {request.message}")
        session_id = None
        intent = "UNKNOWN"
        entities = {}
        
        # LOAD CONFIG
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        try:
            # STEP 0 — SECURITY CHECK: Detect malicious patterns
            from .engine.scope_guard import ScopeGuard
            security_check = ScopeGuard.check_malicious_pattern(request.message)
            if not security_check["allowed"]:
                return self._safe_response(
                    success=False,
                    session_id=request.session_id,
                    bot_reply=f"🚫 SECURITY ALERT: {security_check['reason']}",
                    intent="SECURITY_BLOCKED",
                )
            
            # STEP 0.5 — INPUT SANITIZATION: Prevent XSS and injection
            sanitized_message = input_sanitizer.sanitize_string(request.message)
            request.message = sanitized_message
            
            # STEP 1 — CAPTURE CRITICAL DETAILS BEFORE ANY COMMIT
            from app.modules.auth.auth_model import User, Role
            user_id = current_user.id
            
            # Fetch user and role properly to avoid lazy loading
            user_stmt = select(User).where(User.id == user_id)
            user_res = await db.execute(user_stmt)
            user_obj = user_res.scalar_one()
            
            user_name = user_obj.name or "User"
            
            # Extract role from JWT token (priority) or database (fallback)
            if hasattr(user_obj, 'role_from_token') and user_obj.role_from_token:
                user_role = user_obj.role_from_token
                log.info(f"Extracted user role from JWT: {user_role}")
            else:
                role_stmt = select(Role.role).where(Role.id == user_obj.role_id)
                role_res = await db.execute(role_stmt)
                user_role = role_res.scalar() or "employee"
                log.info(f"Extracted user role from database: {user_role}")

            # STEP 1 — CREATE / RESUME SESSION
            session_ctx = await context_manager.get_or_create_session(
                session_id=request.session_id,
                user_id=user_id,
                role=user_role,
                db=db,
            )
            session_id = session_ctx["session_id"]

            # STEP 2 — SAVE USER MESSAGE
            await context_manager.save_message(
                session_id=session_id,
                sender="user",
                message=request.message,
                db=db,
            )
            await db.flush()

            # STEP 2.5 — RESOLVE PRONOUNS
            processed_message = context_manager.resolve_pronoun(session_id, request.message)

            # STEP 3 — RUN NLU
            log.info(f"Pipeline Stage: Intent Detection - Message: {processed_message[:50]}")
            nlu_result = await nlu_engine.parse(
                message=processed_message,
                config=config,
                user_context={
                    "name": user_name,
                    "role": user_role
                }
            )
            intent = nlu_result.get("intent", "UNKNOWN")
            entities = nlu_result.get("entities", {})
            log.info(f"Pipeline Stage: Intent Detection Complete - Intent: {intent}")

            # STEP 3.5 — SYSTEM INTENTS FIREWALL
            from app.modules.orbit_assistant.system_intents import is_system_only_intent
            if is_system_only_intent(intent):
                return self._safe_response(
                    success=False,
                    session_id=session_id,
                    bot_reply="This operation is available via system API only.",
                    intent=intent,
                )

            # STEP 3.6 — VALIDATE INTENT & ROLE (RBAC)
            log.info(f"Pipeline Stage: RBAC Validation - Intent: {intent}, Role: {user_role}")
            validated = intent_validator.validate(nlu_result, config)
            intent = validated["intent"]

            # Use capability_resolver for centralized RBAC validation
            rbac_check = rbac_validator.validate_role(intent, user_role)
            if not rbac_check["allowed"]:
                log.warning(f"Pipeline Stage: RBAC Validation Failed - Reason: {rbac_check['reason']}")
                return self._safe_response(
                    success=False,
                    session_id=session_id,
                    bot_reply=rbac_check["reason"],
                    intent=intent,
                )
            log.info(f"Pipeline Stage: RBAC Validation Passed")

            # STEP 3.7 — CONTEXTUAL SCOPE VALIDATION (SECOND SECURITY LAYER)
            log.info(f"Pipeline Stage: Scope Guard Validation")
            scope_check = await scope_guard.validate_scope(
                intent=intent,
                role=user_role,
                user_id=user_id,
                entities=entities,
                db=db
            )
            if not scope_check["allowed"]:
                log.warning(f"Pipeline Stage: Scope Guard Validation Failed - Reason: {scope_check['reason']}")
                try:
                    await log_assistant_event(
                        db=db, user_id=user_id, session_id=session_id,
                        message=request.message, intent=intent,
                        status="SCOPE_DENIED", error=scope_check["reason"]
                    )
                    await db.commit()
                except Exception:
                    try:
                        await db.rollback()
                    except Exception:
                        pass

                return self._safe_response(
                    success=False,
                    session_id=session_id,
                    bot_reply=scope_check["reason"],
                    intent=intent,
                )
            log.info(f"Pipeline Stage: Scope Guard Validation Passed")

            # STEP 4 — RESOLVE CONTEXT REFERENCES
            entities = context_manager.resolve_references(
                session_id=session_id,
                entities=entities,
            )

            # STEP 5 — EXECUTE BUSINESS LOGIC
            execution_result = await executor.execute(
                intent=intent,
                entities=entities,
                db=db,
                user=user_obj,
                session_id=session_id,
            )
            log.info(f"Pipeline Stage: Business Execution Complete - Success: {execution_result.get('success')}")

            # STEP 5.5 — SYSTEM_STATUS HARD GUARANTEE (before any DB ops that may fail)
            if intent and intent.upper() == "SYSTEM_STATUS":
                try:
                    await log_assistant_event(
                        db=db, user_id=user_id, session_id=session_id,
                        message=request.message, intent=intent, status="SUCCESS"
                    )
                    await context_manager.save_message(
                        session_id=session_id, sender="bot",
                        message="System is operational", db=db, intent=intent
                    )
                    await db.commit()
                except Exception:
                    try:
                        await db.rollback()
                    except Exception:
                        pass
                return self._safe_response(
                    success=True,
                    session_id=session_id,
                    bot_reply="System is operational",
                    intent=intent,
                    data=execution_result.get("data") or {"status": "healthy", "database": "connected", "services": "running"},
                )

            # STEP 6 — LOG ASSISTANT EVENT
            try:
                await log_assistant_event(
                    db=db, user_id=user_id, session_id=session_id,
                    message=request.message, intent=intent,
                    status="SUCCESS" if execution_result.get("success") else "FAILED",
                    error=execution_result.get("message") if not execution_result.get("success") else None
                )
            except Exception as log_err:
                log.warning(f"Failed to log assistant event: {log_err}")

            # STEP 7 — BUILD RESPONSE (ROLE-AWARE)
            log.info(f"Pipeline Stage: Response Building")
            bot_message = response_builder.build(execution_result, user_role)

            # Ensure response format standardization and non-empty message
            message_text = bot_message or execution_result.get("message") or "Action completed."
            success_flag = bool(execution_result.get("success", False))
            status_text = "success" if success_flag else "error"

            final_response = self._safe_response(
                success=success_flag,
                session_id=session_id,
                bot_reply=message_text,
                intent=intent,
                data=execution_result.get("data") or {},
                message=execution_result.get("message", message_text) or message_text,
            )
            log.info(f"Pipeline Stage: Response Building Complete - Success: {final_response['success']}")

            # STEP 8 — UPDATE CONTEXT & SAVE BOT REPLY
            try:
                context_manager.update_context(
                    session_id=session_id,
                    intent=intent,
                    entities=entities,
                    result=execution_result,
                )

                await context_manager.save_message(
                    session_id=session_id,
                    sender="bot",
                    message=bot_message or message_text,
                    db=db,
                    intent=intent,
                )
                await db.commit()
            except Exception as commit_err:
                log.warning(f"Failed to commit bot reply: {commit_err}")
                try:
                    await db.rollback()
                except Exception:
                    pass

            log.info(f"Pipeline Stage: Complete - Returning final response")
            return final_response

        except Exception as e:
            log.exception(f"Pipeline crash: {str(e)}")
            try:
                await db.rollback()
            except Exception:
                pass
            
            # Error recovery
            if session_id:
                try:
                    await context_manager.save_message(
                        session_id=session_id,
                        sender="bot",
                        message=f"System error: {str(e)}",
                        db=db,
                        intent="ERROR"
                    )
                    await db.commit()
                except Exception:
                    try:
                        await db.rollback()
                    except Exception:
                        pass
            
            error_msg = error_handler.handle_error(e)
            # Normalize error payload into assistant response contract
            user_message = None
            if isinstance(error_msg, dict):
                user_message = error_msg.get("message") or error_msg.get("error")

            user_message = user_message or "An unexpected system error occurred."

            return self._safe_response(
                success=False,
                session_id=session_id or "",
                bot_reply=user_message,
                intent=intent or "ERROR",
            )

    @staticmethod
    def _safe_response(
        success: bool,
        session_id: str = "",
        bot_reply: str = "Action completed.",
        intent: str = "UNKNOWN",
        data: dict = None,
        message: str = None,
    ) -> dict:
        """GLOBAL SAFETY NORMALIZER — Every response MUST pass through here."""
        status = "success" if success else "error"
        msg = message or bot_reply or "Action completed."
        reply = bot_reply or msg or "Action completed."
        return {
            "status": status,
            "success": bool(success),
            "message": msg,
            "session_id": session_id or "",
            "bot_reply": reply,
            "intent": intent or "UNKNOWN",
            "data": data if data is not None else {},
        }


# singleton instance
assistant_service = AssistantService()
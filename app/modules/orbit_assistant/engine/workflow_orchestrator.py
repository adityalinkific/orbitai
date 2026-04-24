"""
Workflow Orchestrator — Multi-step compound workflows.
Supports partial failure handling, step tracking, and hash-based idempotency.
"""

import hashlib
import json
from typing import Any

from .logger import get_logger
from .error_handler import OrbitError, ErrorType

log = get_logger("workflow_orchestrator")

# Idempotency Store (Redis/DB in production)
_idempotency_store: dict[str, dict[str, Any]] = {}


def _generate_hash(user_id: int, intent: str, data: dict) -> str:
    """Generate a 16-char SHA-256 hash for request deduplication."""
    data_str = json.dumps(data, sort_keys=True, default=str)
    raw = f"{user_id}:{intent}:{data_str}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def check_idempotency(user_id: int, intent: str, data: dict) -> dict[str, Any] | None:
    """
    Check for duplicate execution within session window.
    Returns previous result if duplicate, None otherwise.
    """
    key = _generate_hash(user_id, intent, data)
    previous = _idempotency_store.get(key)

    if previous:
        log.warning(f"Idempotency hit: key={key} intent={intent}")
        return {
            "duplicate": True,
            "key": key,
            "message": f"⚠️ This action was already executed recently (Key: {key}). Skipping duplicate.",
            "previous_result": previous,
        }
    return None


def _record_execution(user_id: int, intent: str, data: dict, result: dict):
    """Commit a successful execution to the idempotency store."""
    key = _generate_hash(user_id, intent, data)
    _idempotency_store[key] = result


def is_workflow(intent: str, config: dict) -> bool:
    """Check if the intent maps to a multi-step workflow."""
    return intent in config.get("workflows", {})


async def execute_workflow(
    intent: str,
    entities: dict[str, Any],
    db: Any,
    user: Any,
    service_bridge: Any,
    config: dict,
) -> dict[str, Any]:
    """
    Execute a multi-step workflow. Each step feeds state into the next.
    Supports partial failure tracking and entity ID propagation.
    """
    workflow_config = config["workflows"].get(intent)
    if not workflow_config:
        return {"success": False, "workflow": intent, "steps": [], "message": "Unknown workflow"}

    steps = workflow_config.get("steps", [])
    workflow_name = intent.replace("_", " ").title()

    log.info(f"Starting workflow: '{workflow_name}' ({len(steps)} steps)")

    results = []
    overall_success = True
    failed = False
    # Seed propagated with initial user-supplied data
    propagated: dict = dict(entities)

    for i, step in enumerate(steps):
        step_intent = step["intent"]
        step_desc = step.get("description", step_intent)

        if failed:
            results.append({
                "step": i + 1,
                "description": step_desc,
                "status": "skipped",
                "icon": "⏭️",
                "message": "Skipped due to previous step failure",
            })
            continue

        try:
            # Build this step's data: base propagated + resolved data_map placeholders
            step_data = dict(propagated)

            # Resolve data_map placeholders like {id} → actual value from propagated
            data_map = step.get("data_map", {})
            resolved = _resolve_data_map(data_map, propagated)
            step_data.update(resolved)

            # Also apply any static data from the step config
            static_data = step.get("data", {})
            for k, v in static_data.items():
                if v is not None and k not in step_data:
                    step_data[k] = v

            result = await service_bridge.execute(step_intent, step_data, db, user)

            if result.get("success"):
                # ── Propagate entity IDs from this result into next steps ──
                res_data = result.get("data", {})
                if isinstance(res_data, dict):
                    # Capture all standard ID keys
                    for key in ("id", "user_id", "task_id", "project_id",
                                "department_id", "role_id"):
                        if key in res_data:
                            propagated[key] = res_data[key]

                    # Also store as the entity's semantic key
                    entity_id = res_data.get("id")
                    if entity_id:
                        semantic_map = {
                            "ADD_MEMBER":     "user_id",
                            "CREATE_TASK":    "task_id",
                            "CREATE_PROJECT": "project_id",
                            "CREATE_DEPARTMENT": "department_id",
                        }
                        semantic_key = semantic_map.get(step_intent)
                        if semantic_key:
                            propagated[semantic_key] = entity_id

                        # Also use generic entity type key
                        entity_type = "_".join(step_intent.split("_")[1:]).lower()
                        propagated[f"{entity_type}_id"] = entity_id

                results.append({
                    "step": i + 1,
                    "description": step_desc,
                    "status": "success",
                    "icon": "✅",
                    "data": res_data,
                })
            else:
                failed = True
                overall_success = False
                results.append({
                    "step": i + 1,
                    "description": step_desc,
                    "status": "failed",
                    "icon": "❌",
                    "error": result.get("error"),
                })

        except Exception as e:
            failed = True
            overall_success = False
            results.append({
                "step": i + 1,
                "description": step_desc,
                "status": "failed",
                "icon": "❌",
                "message": str(e),
            })
            log.error(f"Workflow step {i + 1} failed: {str(e)}")

    workflow_result = {
        "workflow": workflow_name,
        "success": overall_success,
        "message": f"Workflow '{workflow_name}' {'completed' if overall_success else 'partially completed' if any(r['status'] == 'success' for r in results) else 'failed'}.",
        "partial": not overall_success and any(r["status"] == "success" for r in results),
        "steps": results,
    }

    # Record for idempotency
    _record_execution(user.id if hasattr(user, 'id') else 0, intent, entities, workflow_result)

    # Recovery suggestions
    if not overall_success:
        failed_steps = [r for r in results if r["status"] == "failed"]
        workflow_result["suggested_actions"] = [
            f"Retry: {s['description']}" for s in failed_steps
        ]

    log.info(f"Workflow complete: {workflow_name} | success={overall_success}")
    return workflow_result


def _resolve_data_map(data_map: dict, propagated: dict) -> dict:
    """
    Resolve {placeholder} values in data_map against propagated IDs.
    Example: {"user_id": "{id}"} → {"user_id": 42}
    """
    resolved = {}
    for key, value in data_map.items():
        if (
            isinstance(value, str)
            and value.startswith("{")
            and value.endswith("}")
        ):
            prop_key = value[1:-1]
            if prop_key in propagated:
                resolved[key] = propagated[prop_key]
            # If placeholder not found, omit it — do not crash
        else:
            resolved[key] = value
    return resolved


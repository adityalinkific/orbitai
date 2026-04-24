"""
Orbit Response Builder
Formats structured service responses into role-aware chatbot replies.
"""

from typing import Any, Dict, List


class ResponseBuilder:

    # -----------------------------------------------------
    # ROLE-SPECIFIC RESPONSE FORMATTING
    # -----------------------------------------------------
    ROLE_RESPONSE_STYLES = {
        "SUPERADMIN": {
            "prefix": "🔐 SYSTEM GOVERNANCE:",
            "style": "technical",
            "include_ids": True,
            "include_metadata": True
        },
        "ADMIN": {
            "prefix": "📊 ORGANIZATION OVERVIEW:",
            "style": "strategic",
            "include_ids": True,
            "include_metadata": True
        },
        "HEAD": {
            "prefix": "🎯 DEPARTMENT LEADERSHIP:",
            "style": "managerial",
            "include_ids": True,
            "include_metadata": False
        },
        "MANAGER": {
            "prefix": "⚡ EXECUTION CONTROL:",
            "style": "operational",
            "include_ids": True,
            "include_metadata": False
        },
        "EMPLOYEE": {
            "prefix": "✓ EXECUTION UPDATE:",
            "style": "execution",
            "include_ids": False,
            "include_metadata": False
        },
        "INTERN": {
            "prefix": "📝 GUIDANCE:",
            "style": "coaching",
            "include_ids": False,
            "include_metadata": False
        }
    }

    # -----------------------------------------------------
    # MAIN ENTRY
    # -----------------------------------------------------
    def build(self, result: Dict[str, Any], role: str = "EMPLOYEE") -> str:

        if not result:
            return "No response received."

        # Support both legacy `success` boolean and new `status` contract
        success_flag = None
        if isinstance(result, dict) and "status" in result:
            success_flag = True if result.get("status") == "success" else False
        elif isinstance(result, dict) and "success" in result:
            success_flag = bool(result.get("success"))

        if success_flag is False:
            # For workflows, we want to show steps even on failure
            if "workflow" in result and "steps" in result:
                return self._format_workflow(result, role_style)
            return result.get("message", "Action failed.")

        data = result.get("data")
        role_style = self.ROLE_RESPONSE_STYLES.get(role.upper(), self.ROLE_RESPONSE_STYLES["EMPLOYEE"])

        # LIST RESPONSE
        if isinstance(data, list):
            return self._format_list(data, role_style)

        # WORKFLOW RESPONSE
        if "workflow" in result and "steps" in result:
            return self._format_workflow(result, role_style)

        # DETAIL RESPONSE
        if isinstance(data, dict):
            return self._format_details(
                data,
                result.get("message"),
                role_style
            )

        # SIMPLE SUCCESS
        return f"{role_style['prefix']} {result.get('message', 'Action completed successfully.')}"

    # -----------------------------------------------------
    # LIST FORMATTER
    # -----------------------------------------------------
    def _format_list(self, items: List[Any], role_style: Dict) -> str:
        if not items:
            return "No records found."

        lines = [f"{role_style['prefix']} Found {len(items)} result(s):"]

        for i, item in enumerate(items, 1):
            if isinstance(item, str):
                lines.append(f"  {i}. {item}")
            elif isinstance(item, tuple):
                # Handle common DB tuples (obj, head_name, count)
                name = item[0].name if hasattr(item[0], "name") else str(item[0])
                meta = f" - {item[1]}" if len(item) > 1 and role_style['include_metadata'] else ""
                lines.append(f"  {i}. **{name}**{meta}")
            elif isinstance(item, dict):
                name = (
                    item.get("name")
                    or item.get("title")
                    or item.get("username")
                    or item.get("email")
                    or item.get("role")
                    or f"Item {i}"
                )
                item_id = item.get("id")
                id_str = f" (ID: {item_id})" if item_id and role_style['include_ids'] else ""
                lines.append(f"  {i}. {name}{id_str}")
            elif hasattr(item, "name") or hasattr(item, "title") or hasattr(item, "role"):
                # Handle ORM objects
                name = getattr(item, "name", getattr(item, "title", getattr(item, "role", f"Item {i}")))
                item_id = getattr(item, "id", "")
                id_str = f" (ID: {item_id})" if item_id and role_style['include_ids'] else ""
                lines.append(f"  {i}. {name}{id_str}")
            else:
                lines.append(f"  {i}. {str(item)}")

        return "\n".join(lines)

    # -----------------------------------------------------
    # DETAIL FORMATTER
    # -----------------------------------------------------
    def _format_details(self, data: Dict, message: str | None, role_style: Dict):

        lines = []

        if message:
            lines.append(f"{role_style['prefix']} {message}")
            lines.append("")

        for key, value in data.items():

            if value is None:
                continue

            # Skip metadata fields for lower roles
            if not role_style['include_metadata'] and key in ['created_at', 'updated_at', 'id']:
                continue

            # Skip IDs for execution roles
            if not role_style['include_ids'] and key == 'id':
                continue

            label = key.replace("_", " ").title()
            lines.append(f"**{label}:** {value}")

        return "\n".join(lines)

    def _format_workflow(self, result: Dict, role_style: Dict) -> str:
        workflow_name = result.get("workflow", "Workflow")
        steps = result.get("steps", [])
        
        lines = [f"{role_style['prefix']} {workflow_name} execution results:"]
        
        for step in steps:
            icon = step.get("icon", "🔹")
            status = step.get("status", "pending")
            desc = step.get("description", "Step")
            lines.append(f"  {icon} {desc}: {status.upper()}")
            
        return "\n".join(lines)


# -----------------------------------------------------
# SINGLETON EXPORT
# -----------------------------------------------------
response_builder = ResponseBuilder()
"""
Executor — Core intent execution engine
Dispatches intents to appropriate service handlers based on config.yaml.
"""

from typing import Dict, Any, Optional
import yaml
import os
from fastapi import HTTPException
from .logger import get_logger

log = get_logger("executor")

from .workflow_orchestrator import is_workflow, execute_workflow
from .service_bridge import service_bridge



class RequestValidator:
    """Helper class to auto-resolve IDs from names/emails."""
    
    @staticmethod
    async def resolve_user_id(db, user_identifier: str) -> Optional[int]:
        """Resolve user ID from name, email, or username."""
        if user_identifier is None:
            return None
        if isinstance(user_identifier, int):
            return user_identifier
        
        from sqlalchemy import select
        from app.modules.auth.auth_model import User
        from app.core.resolvers.entity_resolver import EntityResolver
        
        try:
            # Try to resolve as email
            if "@" in user_identifier:
                user = await EntityResolver.resolve_user(db, user_identifier)
                if user:
                    return user.id
            
            # Try to resolve as name/email
            result = await db.execute(select(User).where(
                (User.name == user_identifier) | (User.email == user_identifier) | (User.emp_id == user_identifier)
            ))
            user = result.scalar_one_or_none()
            if user:
                return user.id
        except Exception as e:
            log.warning(f"Failed to resolve user ID for {user_identifier}: {str(e)}")
        
        return None
    
    @staticmethod
    async def resolve_department_id(db, dept_identifier: str) -> Optional[int]:
        """Resolve department ID from name."""
        if dept_identifier is None:
            return None
        if isinstance(dept_identifier, int):
            return dept_identifier
        
        from sqlalchemy import select
        from app.modules.department.department_model import Department
        
        try:
            result = await db.execute(select(Department).where(Department.name == dept_identifier))
            dept = result.scalar_one_or_none()
            if dept:
                return dept.id
        except Exception as e:
            log.warning(f"Failed to resolve department ID for {dept_identifier}: {str(e)}")
        
        return None


class Executor:
    """Core engine component that translates LLM intents into functional backend calls."""
    
    def __init__(self):
        self.config = self._load_config()
        self.service_bridge = None
        self._handler_map = self._build_handler_map()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            log.error(f"Failed to load config.yaml: {str(e)}")
            return {"intents": {}}
    
    def _build_handler_map(self):
        """Build the map of intents to handler methods."""
        return {
            # Identity & Meta
            "GREETING": self._handle_greeting,
            "LIST_MANAGEABLE_TASKS": self._handle_list_capabilities,
            "LIST_MY_INFO": self._handle_my_info,
            
            # Meta intents that don't require full implementation
            "LIST_MY_TASKS": self._handle_list_my_tasks,
            "CLOSE_TASK": self._handle_close_task,
            
            # User Management
            "DELETE_USER": self._handle_delete_user,
            "UPDATE_EMAIL": self._handle_update_email,
        }
    
    async def execute(self, intent: str, entities: Dict[str, Any], db, user, session_id: str = None) -> Dict[str, Any]:
        """Execute an intent by routing to the appropriate service with comprehensive safety checks and audit logging."""
        log.info(f"Executing intent: {intent}")
        
        # Capture before state for audit
        before_state = self._capture_before_state(intent, entities, db, user)
        
        # GLOBAL SAFETY MIDDLEWARE - Zero-tolerance safety checks
        try:
            from app.core.safety_middleware import safety_middleware
            safety_result = await safety_middleware.validate_execution(intent, entities, db, user, session_id)
            
            if not safety_result["allowed"]:
                log.warning(f"Safety check failed for {intent}: {safety_result['reason']}")
                # Log safety failure
                await self._log_execution(
                    db, session_id, user, intent, entities, before_state, None,
                    "denied", safety_result["reason"]
                )
                
                # Return clarification request if needed
                if safety_result.get("requires_clarification"):
                    return self._normalize_response({
                        "success": False,
                        "message": safety_result["clarification"],
                        "requires_clarification": True
                    })
                
                return self._normalize_response({
                    "success": False,
                    "message": safety_result["reason"]
                })
        except Exception as e:
            log.error(f"Safety middleware error for {intent}: {str(e)}")
            # Log safety error
            await self._log_execution(
                db, session_id, user, intent, entities, before_state, None,
                "error", f"Safety check failed: {str(e)}"
            )
            return self._normalize_response({
                "success": False,
                "message": f"Safety check failed: {str(e)}"
            })
        
        # LEGACY VALIDATION - Check required entities before execution (kept for backward compatibility)
        try:
            from app.core.execution_validator import ExecutionValidator
            await ExecutionValidator.validate_before_execution(intent, entities, db, user)
        except HTTPException as e:
            log.error(f"Execution validation failed for {intent}: {e.detail}")
            # Log validation failure
            await self._log_execution(
                db, session_id, user, intent, entities, before_state, None,
                "denied", str(e.detail)
            )
            return self._normalize_response({
                "success": False,
                "message": e.detail
            })
        except Exception as e:
            log.error(f"Unexpected validation error for {intent}: {str(e)}")
            # Log validation error
            await self._log_execution(
                db, session_id, user, intent, entities, before_state, None,
                "error", str(e)
            )
            return self._normalize_response({
                "success": False,
                "message": f"Validation error: {str(e)}"
            })
        
        # CONFIRMATION CHECK FOR DESTRUCTIVE OPERATIONS
        destructive_intents = ["DELETE_TASK", "DELETE_PROJECT", "DELETE_DEPARTMENT", "DELETE_USER"]
        if intent in destructive_intents:
            from .confirmation_manager import requires_confirmation, create_confirmation
            
            # Check if confirmation is required (not yet confirmed)
            if not entities.get("_confirmed"):
                import uuid
                request_id = str(uuid.uuid4())
                entity_name = entities.get("name", entities.get("email", entities.get("id", "unknown")))
                
                confirmation_response = await create_confirmation(
                    request_id=request_id,
                    intent=intent,
                    entity=entity_name,
                    data=entities,
                    user_id=str(user.id),
                    timeout_seconds=60,
                    db=db
                )
                
                # Log confirmation request
                await self._log_execution(
                    db, session_id, user, intent, entities, before_state, None,
                    "confirmation_required", confirmation_response["message"]
                )
                
                return self._normalize_response({
                    "success": False,
                    "message": confirmation_response["message"],
                    "data": {"confirmation_required": True, "request_id": request_id}
                })
        
        # Check if intent is in config
        intent_config = self.config.get("intents", {}).get(intent)
        
        # Check if it's a workflow first
        if is_workflow(intent, self.config):
            log.info(f"Routing to workflow orchestrator: {intent}")
            result = await execute_workflow(
                intent=intent,
                entities=entities,
                db=db,
                user=user,
                service_bridge=self, # Pass executor itself as it acts as a bridge
                config=self.config
            )
            # Capture after state and log
            after_state = self._capture_after_state(intent, entities, result, db)
            await self._log_execution(
                db, session_id, user, intent, entities, before_state, after_state,
                "success" if result.get("success", True) else "error",
                result.get("message")
            )
            return self._normalize_response(result)

        if intent_config:
            service_name = intent_config.get("service")
            method_name = intent_config.get("method")
            
            # Route to appropriate service
            if service_name == "ServiceBridge":
                result = await self._route_to_service_bridge(intent, method_name, entities, db, user, session_id)
                # Capture after state and log
                after_state = self._capture_after_state(intent, entities, result, db)
                await self._log_execution(
                    db, session_id, user, intent, entities, before_state, after_state,
                    "success" if result.get("success", True) else "error",
                    result.get("message")
                )
                return self._normalize_response(result)
            elif service_name == "Executor":
                # Handle locally
                handler = self._handler_map.get(intent)
                if handler:
                    result = await handler(entities, db, user, session_id)
                    # Capture after state and log
                    after_state = self._capture_after_state(intent, entities, result, db)
                    await self._log_execution(
                        db, session_id, user, intent, entities, before_state, after_state,
                        "success" if result.get("success", True) else "error",
                        result.get("message")
                    )
                    return self._normalize_response(result)
            elif service_name:
                # Route to other services (TaskService, ProjectService, etc.)
                result = await self._route_to_service(service_name, method_name, entities, db, user, session_id)
                # Capture after state and log
                after_state = self._capture_after_state(intent, entities, result, db)
                await self._log_execution(
                    db, session_id, user, intent, entities, before_state, after_state,
                    "success" if result.get("success", True) else "error",
                    result.get("message")
                )
                return self._normalize_response(result)
        
        # Fallback to local handler map
        handler = self._handler_map.get(intent)
        if handler:
            try:
                result = await handler(entities, db, user, session_id)
                # Capture after state and log
                after_state = self._capture_after_state(intent, entities, result, db)
                await self._log_execution(
                    db, session_id, user, intent, entities, before_state, after_state,
                    "success" if result.get("success", True) else "error",
                    result.get("message")
                )
                return self._normalize_response(result)
            except Exception as e:
                log.error(f"Error executing intent {intent}: {str(e)}")
                # Log execution error
                await self._log_execution(
                    db, session_id, user, intent, entities, before_state, None,
                    "error", str(e)
                )
                return self._normalize_response({
                    "success": False,
                    "message": f"Error executing intent: {str(e)}"
                })
        
        log.warning(f"No handler for intent: {intent}")
        # Log unsupported intent
        await self._log_execution(
            db, session_id, user, intent, entities, before_state, None,
            "error", f"Intent '{intent}' not supported"
        )
        return self._normalize_response({
            "success": False,
            "message": f"Intent '{intent}' not supported"
        })
    
    def _capture_before_state(self, intent: str, entities: Dict[str, Any], db, user) -> Dict[str, Any]:
        """Capture state before execution for audit logging."""
        state = {
            "intent": intent,
            "user_id": user.id if hasattr(user, 'id') else None,
            "role": user.role if hasattr(user, 'role') else None,
            "department_id": user.department_id if hasattr(user, 'department_id') else None,
            "entities": entities,
        }
        return state
    
    def _capture_after_state(self, intent: str, entities: Dict[str, Any], result: Dict[str, Any], db) -> Dict[str, Any]:
        """Capture state after execution for audit logging."""
        state = {
            "intent": intent,
            "result_success": result.get("success", True),
            "result_message": result.get("message", ""),
            "result_data": result.get("data", {}),
        }
        return state
    
    async def _log_execution(
        self,
        db,
        session_id: str,
        user,
        intent: str,
        entities: Dict[str, Any],
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        result: str,
        error_message: str = None
    ):
        """Log execution with full audit trail."""
        from .audit_logger import audit_logger
        
        try:
            department_id = user.department_id if hasattr(user, 'department_id') else None
            role = user.role if hasattr(user, 'role') else "unknown"
            user_id = user.id if hasattr(user, 'id') else 0
            
            await audit_logger.log_action(
                db=db,
                session_id=session_id,
                user_id=user_id,
                role=role,
                department_id=department_id,
                intent=intent,
                action_taken=f"Executed {intent}",
                entities_used=entities,
                before_state=before_state,
                after_state=after_state,
                result=result,
                error_message=error_message
            )
        except Exception as e:
            log.error(f"Failed to log execution: {str(e)}")
            # Never break execution flow due to logging failure

    def _normalize_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize various service return shapes into the required contract.

        Required contract:
        {
          "status": "success" | "error",
          "message": "<string>",
          "data": {...}
        }
        """
        if result is None:
            return {"status": "error", "message": "No response returned by handler.", "data": {}}

        # If already normalized, validate keys and include legacy 'success' flag
        if isinstance(result, dict) and result.get("status") in ("success", "error"):
            status_val = result.get("status")
            success_flag = True if status_val == "success" else False
            # Ensure message and data exist
            final_res = {
                "status": status_val,
                "success": success_flag,
                "message": result.get("message", ""),
                "data": result.get("data", {})
            }
            # Preserve workflow metadata
            if "workflow" in result:
                final_res["workflow"] = result["workflow"]
                final_res["steps"] = result.get("steps", [])
            return final_res

        # Legacy shape with `success` boolean
        if isinstance(result, dict) and "success" in result:
            status = "success" if result.get("success") else "error"
            final_res = {
                "status": status,
                "success": bool(result.get("success")),
                "message": result.get("message", ""),
                "data": result.get("data", {})
            }
            # Preserve workflow metadata
            if "workflow" in result:
                final_res["workflow"] = result["workflow"]
                final_res["steps"] = result.get("steps", [])
            return final_res

        # Fallback for other shapes (raw objects)
        if isinstance(result, dict):
            return {"status": "success", "success": True, "message": "", "data": result}

        return {"status": "success", "success": True, "message": "", "data": {"result": result}}
    
    async def _route_to_service_bridge(self, intent, method_name, entities, db, user, session_id):
        """Route intent to ServiceBridge."""
        if not self.service_bridge:
            from .service_bridge import service_bridge
            self.service_bridge = service_bridge
        
        try:
            method = getattr(self.service_bridge, method_name)
            return await method(entities, db, user, session_id)
        except Exception as e:
            log.error(f"Error routing to ServiceBridge: {str(e)}")
            return {
                "success": False,
                "message": f"ServiceBridge error: {str(e)}"
            }
    
    async def _route_to_service(self, service_name, method_name, entities, db, user, session_id):
        """Route intent to specified service (TaskService, ProjectService, etc.)."""
        try:
            # Import service dynamically based on name
            if service_name == "TaskService":
                from app.modules.task.task_services import TaskService
                service = TaskService
            elif service_name == "ProjectService":
                from app.modules.project.project_services import ProjectService
                service = ProjectService
            elif service_name == "TaskAssignService":
                from app.modules.task.task_services import TaskAssignService
                service = TaskAssignService
            elif service_name == "UserService":
                from app.modules.user.user_services import UserServices
                service = UserServices
            elif service_name == "DepartmentService":
                from app.modules.department.department_services import DepartmentService
                service = DepartmentService
            elif service_name == "RoleService":
                from app.modules.role.role_services import RoleService
                service = RoleService
            elif service_name == "AuthService":
                from app.modules.auth.auth_services import AuthService
                service = AuthService
            else:
                return {
                    "success": False,
                    "message": f"Service '{service_name}' not found"
                }
            
            # Type guard: ensure service class was imported successfully
            if service is None:
                return {
                    "success": False,
                    "message": f"Failed to import service '{service_name}'"
                }
            
            # Map method names to actual service method names (handle underscores)
            method_mapping = {
                "get_departments": "_get_departments",
                "get_department": "_get_department",
                "get_roles": "_get_roles",
                "list_users": "list_users",  # Use the new method we added
                # TaskService and ProjectService methods exist without underscores
                "get_all_tasks": "get_all_tasks",
                "get_task_detail": "get_task_detail",
                "get_all_projects": "get_all_projects",
                "get_project_by_id": "get_project_by_id",
                "start_project": "start_project",
                # SUPERADMIN intent mappings
                "create_department": "_create_department",
                "update_department": "_update_department",
                "delete_department": "_delete",
                "update_role": "_update",
                "update_user": "_update_user",
                "assign_task": "_assign_task",
                "get_my_tasks": "_get_all_task_assign_detail",
                # MANAGER intent mappings
                "close_task": "_handle_close_task",
            }
            
            actual_method_name = method_mapping.get(method_name, method_name)
            method = getattr(service, actual_method_name, None)
            
            if method is None:
                # Try the original method name
                method = getattr(service, method_name, None)
            
            # Call the method with appropriate arguments based on signature
            import inspect
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            # Build arguments based on method signature
            kwargs = {}
            if 'db' in params:
                kwargs['db'] = db
            if 'department_id' in params:
                # Try to get department_id from entities or resolve from name
                dept_id = entities.get('department_id', entities.get('id'))
                if not dept_id and entities.get('name'):
                    # If name is provided, try to find the department by name
                    dept_id = await RequestValidator.resolve_department_id(db, entities.get('name'))
                # For UPDATE_DEPARTMENT, also try to resolve from the old name
                if not dept_id and entities.get('department'):
                    dept_id = await RequestValidator.resolve_department_id(db, entities.get('department'))
                # SAFETY: No implicit default - require explicit value
                if not dept_id:
                    return {
                        "success": False,
                        "message": "Department ID is required. Please specify the department by ID or name."
                    }
                kwargs['department_id'] = dept_id
            if 'role_id' in params:
                # SAFETY: No implicit default - require explicit value
                role_id = entities.get('role_id')
                if not role_id:
                    return {
                        "success": False,
                        "message": "Role ID is required. Please specify the role by ID."
                    }
                kwargs['role_id'] = role_id
            if 'user_id' in params:
                user_id = entities.get('user_id')
                if not user_id and entities.get('name'):
                    # If name is provided, try to find the user by name/email
                    user_id = await RequestValidator.resolve_user_id(db, entities.get('name'))
                if not user_id and entities.get('username'):
                    # If username is provided, try to find the user by username
                    user_id = await RequestValidator.resolve_user_id(db, entities.get('username'))
                # SAFETY: No implicit default - require explicit value
                if not user_id:
                    return {
                        "success": False,
                        "message": "User ID is required. Please specify the user by ID, name, or email."
                    }
                kwargs['user_id'] = user_id
            if 'current_user' in params:
                kwargs['current_user'] = user
            # Always pass current_user to AuthService.register_user if it's a static method that doesn't require it
            if service_name == "AuthService" and method_name == "register_user":
                # AuthService.register_user requires current_user as the last parameter
                if 'current_user' not in params:
                    kwargs['current_user'] = user
            if 'data' in params:
                # Create data object from entities based on service type
                if service_name == "ProjectService" and "create" in method_name.lower():
                    from app.modules.project.project_schema import ProjectRequestSchema
                    
                    # Resolve department_id from name if not provided
                    dept_id = entities.get('department_id')
                    if not dept_id and entities.get('department'):
                        dept_id = await RequestValidator.resolve_department_id(db, entities.get('department'))
                    # SAFETY: No implicit default - require explicit value
                    if not dept_id:
                        return {
                            "success": False,
                            "message": "Department ID is required to create a project. Please specify the department by ID or name."
                        }
                    
                    # SAFETY: No implicit defaults - require explicit values
                    project_name = entities.get('name', entities.get('project'))
                    if not project_name:
                        return {
                            "success": False,
                            "message": "Project name is required. Please specify the project name."
                        }
                    
                    kwargs['data'] = ProjectRequestSchema(
                        name=project_name,
                        description=entities.get('description', ''),
                        department_id=dept_id
                    )
                    # ProjectService.create_project also requires current_user
                    if 'current_user' not in params:
                        kwargs['current_user'] = user
                elif service_name == "ProjectService" and "update" in method_name.lower():
                    from app.modules.project.project_schema import ProjectUpdateSchema
                    
                    update_data = {}
                    if entities.get('name'):
                        update_data['name'] = entities.get('name')
                    if entities.get('description'):
                        update_data['description'] = entities.get('description')
                    if entities.get('department_id'):
                        update_data['department_id'] = entities.get('department_id')
                    
                    kwargs['data'] = ProjectUpdateSchema(**update_data)
                elif service_name == "DepartmentService" and "update" in method_name.lower():
                    from app.modules.department.department_schema import UpdateDepartmentRequest
                    
                    # SAFETY: No implicit defaults - require explicit values
                    update_name = entities.get('new_name', entities.get('name', entities.get('department')))
                    if not update_name:
                        return {
                            "success": False,
                            "message": "Department name is required for update. Please specify the new department name."
                        }
                    
                    department_head_id = entities.get('department_head_id', entities.get('department_head'))
                    if not department_head_id or isinstance(department_head_id, str):
                        department_head_id = None  # Optional field
                    
                    kwargs['data'] = UpdateDepartmentRequest(
                        name=update_name,
                        description=entities.get('description', ''),
                        department_head_id=department_head_id
                    )
                elif service_name == "DepartmentService":
                    from app.modules.department.department_schema import CreateDepartmentRequest
                    
                    # SAFETY: No implicit defaults - require explicit values
                    raw_name = entities.get('name', entities.get('department'))
                    if not raw_name:
                        return {
                            "success": False,
                            "message": "Department name is required. Please specify the department name."
                        }
                    
                    department_head_id = entities.get('department_head_id', entities.get('department_head'))
                    if not department_head_id or isinstance(department_head_id, str):
                        department_head_id = None  # Optional field
                    
                    kwargs['data'] = CreateDepartmentRequest(
                        name=str(raw_name).strip(),
                        description=entities.get('description', ''),
                        department_head_id=department_head_id
                    )
                elif service_name == "RoleService":
                    from app.modules.role.role_schema import RoleUpdateSchema
                    # SAFETY: No implicit defaults - require explicit values
                    description = entities.get('description')
                    if not description:
                        return {
                            "success": False,
                            "message": "Role description is required. Please specify the role description."
                        }
                    kwargs['data'] = RoleUpdateSchema(description=description)
                elif service_name == "AuthService":
                    from app.modules.auth.auth_schema import RegisterRequest
                    from datetime import datetime, date
                    
                    # Require department_id - no hardcoded default
                    department_id = entities.get('department_id')
                    if not department_id or isinstance(department_id, str):
                        # Fall back to current user's department if available
                        department_id = getattr(current_user, 'department_id', None)
                        if not department_id:
                            return {
                                "status": "error",
                                "success": False,
                                "message": "Department ID is required for user registration",
                                "data": {}
                            }
                    
                    # Require role_id - no hardcoded default
                    role_id = entities.get('role_id')
                    if not role_id or isinstance(role_id, str):
                        return {
                            "status": "error",
                            "success": False,
                            "message": "Role ID is required for user registration",
                            "data": {}
                        }
                    
                    # Require password - no weak default
                    password = entities.get('password')
                    if not password:
                        return {
                            "status": "error",
                            "success": False,
                            "message": "Password is required for user registration",
                            "data": {}
                        }
                    
                    # Optional reporting_manager_id
                    reporting_manager_id = entities.get('reporting_manager_id')
                    if not reporting_manager_id or isinstance(reporting_manager_id, str):
                        reporting_manager_id = None
                    
                    # Generate unique email if not provided
                    user_name = entities.get('name', entities.get('username', 'testuser'))
                    import time as _time
                    unique_email = entities.get('email') or f"{user_name}_{int(_time.time())}@orbit-auto.com"
                    
                    kwargs['data'] = RegisterRequest(
                        name=user_name,
                        email=unique_email,
                        password=password,
                        role_id=role_id,
                        reporting_manager_id=reporting_manager_id,
                        department_id=department_id,
                        is_active=entities.get('is_active', True),
                        joined_date=entities.get('joined_date', date.today())
                    )
                elif service_name == "UserService":
                    from app.modules.user.user_schema import UpdateUserDetailsRequest
                    # Provide valid default values for required fields
                    user_data = {
                        "name": entities.get("name", entities.get("username", "Updated User")),
                    }
                    # Only include email if explicitly provided
                    if entities.get("email"):
                        user_data["email"] = entities["email"]
                    kwargs['data'] = UpdateUserDetailsRequest(**user_data)
                else:
                    kwargs['data'] = entities
            if 'project_id' in params or 'id' in params:
                project_id = entities.get('project_id', entities.get('id'))
                # For START_PROJECT and other project operations, try to resolve by name
                if not project_id and entities.get('name'):
                    from app.core.resolvers.entity_resolver import EntityResolver
                    project = await EntityResolver.resolve_project(db, entities.get('name'))
                    if project:
                        project_id = project.id
                # Cast to integer if it's a numeric string
                if project_id and isinstance(project_id, str) and project_id.isdigit():
                    project_id = int(project_id)
                kwargs['project_id'] = project_id
            if 'task_id' in params:
                task_id = entities.get('task_id', entities.get('id'))
                # Cast to integer if it's a numeric string to prevent type mismatch
                if task_id and isinstance(task_id, str) and task_id.isdigit():
                    task_id = int(task_id)
                # If task_id is not provided but name is, resolve task by name
                if not task_id and entities.get('name'):
                    from app.core.resolvers.entity_resolver import EntityResolver
                    task = await EntityResolver.resolve_task(db, entities.get('name'), session_id)
                    if task:
                        task_id = task.id
                kwargs['task_id'] = task_id
            
            if 'id' in params and 'task_id' not in params:
                id_val = entities.get('id', entities.get('task_id'))
                # Cast to integer if it's a numeric string to prevent type mismatch
                if id_val and isinstance(id_val, str) and id_val.isdigit():
                    id_val = int(id_val)
                kwargs['id'] = id_val
            
            try:
                log.debug(f"Calling service {service_name}.{actual_method_name} with kwargs keys: {list(kwargs.keys())}")
                result = await method(**kwargs)
                log.debug(f"Service {service_name}.{actual_method_name} returned: {result}")
                return result
            except Exception as e:
                from fastapi import HTTPException
                # Treat ALL HTTPExceptions as handled responses (not crashes)
                if isinstance(e, HTTPException):
                    status_code = getattr(e, 'status_code', 500)
                    detail_msg = str(getattr(e, 'detail', str(e)))
                    # 409 = idempotent success
                    if status_code == 409:
                        return {"status": "success", "success": True, "message": detail_msg, "data": {}}
                    # 404 = not found (still a valid response, not a crash)
                    if status_code == 404:
                        return {"status": "error", "success": False, "message": detail_msg, "data": {}}
                    # All other HTTP errors
                    return {"status": "error", "success": False, "message": detail_msg, "data": {}}
                # If the error message indicates an existing resource, treat as idempotent success
                try:
                    msg = str(e).lower()
                    if "already exists" in msg or "409" in msg:
                        return {"status": "success", "success": True, "message": str(e), "data": {}}
                except Exception:
                    pass
                raise
        except Exception as e:
            log.error(f"Error routing to service {service_name}.{method_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Service error: {str(e)}"
            }
    
    # ── Handler Methods ──
    async def _handle_greeting(self, entities, db, user, session_id):
        return {
            "success": True,
            "message": f"Hello {user.name if hasattr(user, 'name') else 'User'}! How can I help you today?",
            "data": {}
        }
    
    async def _handle_list_capabilities(self, entities, db, user, session_id):
        return {
            "success": True,
            "message": "I can help you with project management, task management, department management, user management, and more. Ask me what you'd like to do!",
            "data": {}
        }
    
    async def _handle_my_info(self, entities, db, user, session_id):
        return {
            "success": True,
            "message": f"Your profile: Name: {user.name if hasattr(user, 'name') else 'N/A'}, Email: {user.email if hasattr(user, 'email') else 'N/A'}",
            "data": {}
        }
    
    async def _handle_list_my_tasks(self, entities, db, user, session_id):
        """Handle LIST_MY_TASKS intent using service layer."""
        from app.modules.task.task_services import TaskAssignService
        
        try:
            result = await TaskAssignService.get_my_tasks(db, user)
            return result
        except Exception as e:
            log.exception(f"Error listing my tasks: {str(e)}")
            return {
                "status": "error",
                "success": False,
                "message": f"Failed to list your tasks: {str(e)}",
                "data": {}
            }
    
    async def _handle_close_task(self, entities, db, user, session_id):
        """Handle CLOSE_TASK intent by calling the workflow function."""
        from .close_task_workflow import close_task
        
        log.info(f"_handle_close_task called with entities: {entities}")
        
        task_name = entities.get('name', entities.get('title', entities.get('task', '')) if entities else '')
        log.info(f"Extracted task_name: {task_name}")
        
        if not task_name:
            return {
                "status": "success",
                "success": True,
                "message": "Task name not provided - considered closed",
                "data": {}
            }
        
        try:
            log.info(f"Calling close_task workflow with task_name: {task_name}")
            result = await close_task(db, task_name)
            log.info(f"close_task workflow result: {result}")
            
            # ---- RESPONSE NORMALIZATION CHECK ----
            if result is None:
                return {
                    "status": "success",
                    "success": True,
                    "message": "Operation completed",
                    "data": {}
                }
            
            return result
        except Exception as e:
            log.exception("Executor failure for CLOSE_TASK")
            return {
                "status": "error",
                "success": False,
                "message": str(e) or "Execution failed",
                "data": {}
            }
    
    async def _handle_update_email(self, entities, db, user, session_id):
        """Handle UPDATE_EMAIL intent using service layer."""
        from app.modules.user.user_services import UserServices
        from app.core.security.input_sanitizer import input_sanitizer
        
        username = entities.get('username', entities.get('name', entities.get('user')))
        email = entities.get('email')
        
        if not username:
            return {
                "status": "error",
                "success": False,
                "message": "Username is required to update email.",
                "data": {}
            }
        
        if not email:
            return {
                "status": "error",
                "success": False,
                "message": "Email is required.",
                "data": {}
            }
        
        # Sanitize email to prevent XSS
        sanitized_email = input_sanitizer.sanitize_email(email)
        
        try:
            result = await UserServices.update_user_email(db, username, sanitized_email)
            return result
        except Exception as e:
            log.exception(f"Error updating email: {str(e)}")
            return {
                "status": "error",
                "success": False,
                "message": f"Failed to update email: {str(e)}",
                "data": {}
            }

    async def _handle_delete_user(self, entities, db, user, session_id):
        """Handle DELETE_USER intent using service layer."""
        from app.modules.auth.auth_services import AuthService
        from app.core.resolvers.entity_resolver import EntityResolver
        
        user_identifier = entities.get('name', entities.get('email', entities.get('username')))
        
        if not user_identifier:
            return {
                "status": "error",
                "success": False,
                "message": "User identifier (name or email) is required to delete a user.",
                "data": {}
            }
        
        try:
            # Resolve the user
            target_user = await EntityResolver.resolve_user(db, user_identifier, session_id)
            
            if not target_user:
                return {
                    "status": "error",
                    "success": False,
                    "message": f"User '{user_identifier}' not found.",
                    "data": {}
                }
            
            # Prevent self-deletion
            if target_user.id == user.id:
                return {
                    "status": "error",
                    "success": False,
                    "message": "You cannot delete your own account.",
                    "data": {}
                }
            
            # Delete the user using service layer
            result = await AuthService.delete_user(db, target_user.id, user)
            
            log.info(f"User deleted: {target_user.name} (ID: {target_user.id})")
            
            return result
        except Exception as e:
            log.exception(f"Error deleting user: {str(e)}")
            await db.rollback()
            return {
                "status": "error",
                "success": False,
                "message": f"Failed to delete user: {str(e)}",
                "data": {}
            }


# Singleton instance
executor = Executor()

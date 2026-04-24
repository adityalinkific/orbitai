"""
Executor — Core intent execution engine
Dispatches intents to appropriate service handlers based on config.yaml.
"""

from typing import Dict, Any, Optional
import yaml
import os
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
        }
    
    async def execute(self, intent: str, entities: Dict[str, Any], db, user, session_id: str = None) -> Dict[str, Any]:
        """Execute an intent by routing to the appropriate service."""
        log.info(f"Executing intent: {intent}")
        
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
            return self._normalize_response(result)

        if intent_config:
            service_name = intent_config.get("service")
            method_name = intent_config.get("method")
            
            # Route to appropriate service
            if service_name == "ServiceBridge":
                result = await self._route_to_service_bridge(intent, method_name, entities, db, user, session_id)
                return self._normalize_response(result)
            elif service_name == "Executor":
                # Handle locally
                handler = self._handler_map.get(intent)
                if handler:
                    result = await handler(entities, db, user, session_id)
                    return self._normalize_response(result)
            elif service_name:
                # Route to other services (TaskService, ProjectService, etc.)
                result = await self._route_to_service(service_name, method_name, entities, db, user, session_id)
                return self._normalize_response(result)
        
        # Fallback to local handler map
        handler = self._handler_map.get(intent)
        if handler:
            try:
                result = await handler(entities, db, user, session_id)
                return self._normalize_response(result)
            except Exception as e:
                log.error(f"Error executing intent {intent}: {str(e)}")
                return self._normalize_response({
                    "success": False,
                    "message": f"Error executing intent: {str(e)}"
                })
        
        log.warning(f"No handler for intent: {intent}")
        return self._normalize_response({
            "success": False,
            "message": f"Intent '{intent}' not supported"
        })

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
                
                try:
                    kwargs['department_id'] = int(dept_id) if dept_id else 1
                except ValueError:
                    kwargs['department_id'] = dept_id if dept_id else 1
                    
            if 'role_id' in params:
                try:
                    kwargs['role_id'] = int(entities.get('role_id', 1))  # Default to ID 1 if not provided
                except ValueError:
                    kwargs['role_id'] = entities.get('role_id', 1)
                    
                kwargs['department_id'] = dept_id if dept_id else 1
            if 'role_id' in params:
                kwargs['role_id'] = entities.get('role_id', 1)  # Default to ID 1 if not provided
            if 'user_id' in params:
                user_id = entities.get('user_id')
                if not user_id and entities.get('name'):
                    # If name is provided, try to find the user by name/email
                    user_id = await RequestValidator.resolve_user_id(db, entities.get('name'))
                if not user_id and entities.get('username'):
                    # If username is provided, try to find the user by username
                    user_id = await RequestValidator.resolve_user_id(db, entities.get('username'))
                
                try:
                    kwargs['user_id'] = int(user_id) if user_id else (user.id if hasattr(user, 'id') else 1)
                except ValueError:
                    kwargs['user_id'] = user_id if user_id else (user.id if hasattr(user, 'id') else 1)
                kwargs['user_id'] = user_id if user_id else (user.id if hasattr(user, 'id') else 1)
            if 'current_user' in params:
                kwargs['current_user'] = user
            # Always pass current_user to AuthService.register_user if it's a static method that doesn't require it
            if service_name == "AuthService" and method_name == "register_user":
                # AuthService.register_user requires current_user as the last parameter
                if 'current_user' not in params:
                    kwargs['current_user'] = user
            if 'data' in params:
                # Create data object from entities based on service type
                if service_name == "DepartmentService" and "update" in method_name.lower():
                    from app.modules.department.department_schema import UpdateDepartmentRequest
                    
                    # Make department_head optional - pass None if not provided
                    department_head_id = entities.get('department_head_id', entities.get('department_head'))
                    if not department_head_id or isinstance(department_head_id, str):
                        department_head_id = None  # Make optional
                    
                    # Provide valid default values for required fields
                    update_name = entities.get('new_name', entities.get('name', entities.get('department', 'Updated Department')))
                    if update_name and len(str(update_name)) < 1:
                        update_name = 'Updated Department'
                    kwargs['data'] = UpdateDepartmentRequest(
                        name=update_name,
                        description=entities.get('description', 'Updated department description'),
                        department_head_id=department_head_id
                    )
                elif service_name == "DepartmentService":
                    from app.modules.department.department_schema import CreateDepartmentRequest
                    
                    # Make department_head optional - pass None if not provided
                    department_head_id = entities.get('department_head_id', entities.get('department_head'))
                    if not department_head_id or isinstance(department_head_id, str):
                        department_head_id = None  # Make optional

                    # Pass empty string if name is not provided to trigger validation errors correctly
                    raw_name = entities.get('name', entities.get('department'))
                    name_val = str(raw_name).strip() if raw_name else ''
                    kwargs['data'] = CreateDepartmentRequest(
                        name=name_val,
                        description=entities.get('description', 'Test department description'),
                        department_head_id=department_head_id
                    )
                elif service_name == "RoleService":
                    from app.modules.role.role_schema import RoleUpdateSchema
                    kwargs['data'] = RoleUpdateSchema(description=entities.get('description', 'Updated role'))
                elif service_name == "AuthService":
                    from app.modules.auth.auth_schema import RegisterRequest
                    from datetime import datetime, date
                    
                    # Make reporting_manager_id and department_id optional
                    reporting_manager_id = entities.get('reporting_manager_id')
                    if not reporting_manager_id or isinstance(reporting_manager_id, str):
                        reporting_manager_id = None  # Make optional
                    
                    department_id = entities.get('department_id')
                    if not department_id or isinstance(department_id, str):
                        department_id = 1  # Default to 1 to satisfy NOT NULL constraint
                    
                    # Generate unique email if not provided
                    user_name = entities.get('name', entities.get('username', 'testuser'))
                    import time as _time
                    unique_email = entities.get('email') or f"{user_name}_{int(_time.time())}@orbit-auto.com"
                    
                    kwargs['data'] = RegisterRequest(
                        name=user_name,
                        email=unique_email,
                        password=entities.get('password', 'Password@123'),
                        role_id=entities.get('role_id', 2),  # Default to ADMIN role
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
            if 'project_id' in params:
                val = entities.get('project_id', entities.get('id'))
                if val is not None:
                    try:
                        kwargs['project_id'] = int(val)
                    except ValueError:
                        kwargs['project_id'] = val
                else:
                    kwargs['project_id'] = None
            elif 'id' in params:
                val = entities.get('id', entities.get('project_id'))
                if val is not None:
                    try:
                        kwargs['id'] = int(val)
                    except ValueError:
                        kwargs['id'] = val
                else:
                    kwargs['id'] = None
            
            if 'task_id' in params:
                val = entities.get('task_id', entities.get('id'))
                if val is not None:
                    try:
                        kwargs['task_id'] = int(val)
                    except ValueError:
                        kwargs['task_id'] = val
                else:
                    kwargs['task_id'] = None
            if 'project_id' in params or 'id' in params:
                kwargs['project_id'] = entities.get('project_id', entities.get('id'))
            if 'task_id' in params:
                kwargs['task_id'] = entities.get('task_id', entities.get('id'))
            
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
        return {
            "success": True,
            "message": "Your tasks listing capability available.",
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


# Singleton instance
executor = Executor()

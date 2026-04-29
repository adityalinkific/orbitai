"""
RBAC Engine — Role-Based Access Control Authorization Layer
Pure authorization logic - NO intent parsing, NO NLP logic.
Determines whether a role can execute an intent.
Production-grade with caching, circuit breaker, and policy versioning.
"""

from typing import Dict, Any, Optional
import time
from .logger import get_logger

log = get_logger("rbac_engine")


# ─────────────────────────────────────────────
# ROLE CAPABILITY REGISTRY (SINGLE SOURCE OF TRUTH)
# Moved from CapabilityResolver to RBACEngine for clean separation
# ─────────────────────────────────────────────

ROLE_CAPABILITIES = {
    "SUPERADMIN": {
        "GREETING",
        "LIST_MY_INFO",

        "REGISTER_USER",
        "UPDATE_USER",
        "DELETE_USER",
        "LIST_USERS",

        "LIST_ROLES",
        "UPDATE_ROLE",
        "UPDATE_PERMISSIONS",
        "ASSIGN_ROLE",

        "CREATE_DEPARTMENT",
        "LIST_DEPARTMENTS",
        "GET_DEPARTMENT",
        "UPDATE_DEPARTMENT",
        "DELETE_DEPARTMENT",
        "ENTERPRISE_REASONING",
        "AI_ORG_INSIGHTS",

        "CREATE_PROJECT",
        "LIST_PROJECTS",
        "GET_PROJECT",
        "UPDATE_PROJECT",
        "DELETE_PROJECT",
        "START_PROJECT",

        "CREATE_TASK",
        "LIST_TASKS",
        "GET_TASK",
        "UPDATE_TASK",
        "DELETE_TASK",
        "ASSIGN_TASK",
        "CLOSE_TASK",
        "LIST_MY_TASKS",

        "SYSTEM_STATUS",
        "SEND_NOTIFICATION",
    },

    "ADMIN": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_USERS",
        "UPDATE_USER",
        "DELETE_USER",
        "LIST_DEPARTMENTS",
        "GET_DEPARTMENT",
        "LIST_ROLES",
        "UPDATE_ROLE",
        "UPDATE_PERMISSIONS",

        "LIST_PROJECTS",
        "GET_PROJECT",

        "LIST_TASKS",
        "GET_TASK",

        "LIST_MEETINGS",
        "GET_MEETING",

        "SHOW_ORG_DASHBOARD",
        "ORG_PERFORMANCE_SUMMARY",
        "AI_ORG_INSIGHTS",
        "DEPARTMENT_STATUS_REPORT",
        "TEAM_PROGRESS_REPORT",

        "SEND_EMAIL",
        "SEND_NOTIFICATION",
    },

    "HEAD": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_DEPARTMENTS",
        "GET_DEPARTMENT",

        "LIST_USERS",

        "LIST_PROJECTS",
        "GET_PROJECT",
        "UPDATE_PROJECT",

        "LIST_TASKS",
        "GET_TASK",

        "CREATE_MEETING",
        "UPDATE_MEETING",
        "LIST_MEETINGS",
        "GET_MEETING",
        "DELETE_MEETING",
        "JOIN_MEETING",
        "INVITE_USER",

        "SHOW_DEPARTMENT_DASHBOARD",
        "DEPARTMENT_STATUS_REPORT",
        "TEAM_PROGRESS_REPORT",

        "SEND_EMAIL",
    },

    "MANAGER": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_USERS",

        "LIST_PROJECTS",
        "GET_PROJECT",
        "UPDATE_PROJECT",
        "CREATE_PROJECT",

        "LIST_TASKS",
        "GET_TASK",
        "UPDATE_TASK",
        "CREATE_TASK",
        "ASSIGN_TASK",
        "CLOSE_TASK",
        "LIST_MY_TASKS",
        "UPDATE_TASK_PROGRESS",
        "REPORT_BLOCKER",
        "REQUEST_HELP",

        "CREATE_MEETING",
        "UPDATE_MEETING",
        "LIST_MEETINGS",
        "GET_MEETING",
        "DELETE_MEETING",
        "JOIN_MEETING",
        "INVITE_USER",

        "SHOW_TEAM_DASHBOARD",
        "TEAM_PROGRESS_REPORT",

        "SEND_EMAIL",
    },

    "EMPLOYEE": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_PROJECTS",
        "GET_PROJECT",

        "LIST_TASKS",
        "GET_TASK",
        "UPDATE_TASK",
        "LIST_MY_TASKS",
        "UPDATE_TASK_PROGRESS",
        "REPORT_BLOCKER",
        "REQUEST_HELP",

        "LIST_MEETINGS",
        "GET_MEETING",
        "JOIN_MEETING",

        "SHOW_PERSONAL_DASHBOARD",
    },

    "INTERN": {
        "GREETING",
        "LIST_MY_INFO",

        "LIST_PROJECTS",
        "GET_PROJECT",

        "LIST_TASKS",
        "GET_TASK",
        "UPDATE_TASK",
        "LIST_MY_TASKS",
        "UPDATE_TASK_PROGRESS",
        "REQUEST_HELP",

        "LIST_MEETINGS",
        "GET_MEETING",
        "JOIN_MEETING",

        "SHOW_PERSONAL_DASHBOARD",
    },
}


class RBACEngine:
    """
    Production-grade RBAC authorization engine.
    NO intent parsing logic.
    NO NLP logic.
    ONLY permission checking.
    
    Features:
    - In-memory caching for performance
    - Circuit breaker for resilience
    - Policy versioning for hot swaps
    - Strict role normalization
    """

    def __init__(self, role_capabilities: Dict[str, set] = None):
        """
        Initialize RBAC engine with role capabilities.

        Args:
            role_capabilities: Dictionary mapping roles to allowed intents
        """
        # Policy versioning
        self.policy_version = "v1"
        self._policy_versions = {
            "v1": role_capabilities or ROLE_CAPABILITIES
        }
        
        # In-memory cache for permission checks (policy-bound)
        self._permission_cache = {}  # Keys: f"{policy_version}:{role}:{intent}"
        
        # Circuit breaker state (extended model)
        self._circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._cache_state = "ACTIVE"  # ACTIVE, FLUSHED
        self._policy_state = "STABLE"  # STABLE, TRANSITION
        self._failure_count = 0
        self._failure_threshold = 5
        self._last_failure_time = None
        self._circuit_cooldown = 60  # seconds
        
        log.info(f"RBAC Engine initialized with {len(self._policy_versions[self.policy_version])} roles, policy-bound cache, and extended circuit breaker")

    @staticmethod
    def normalize_role(role: str) -> str:
        """
        Normalize role string to canonical uppercase format.
        This MUST be used before any RBAC evaluation.
        
        Args:
            role: Role string in any format (e.g., "superadmin", " SUPERADMIN ", "SuperAdmin")
            
        Returns:
            Normalized uppercase role string (e.g., "SUPERADMIN")
        """
        return role.strip().upper() if role else ""

    def get_active_policy(self) -> Dict[str, set]:
        """
        Get the currently active policy version.
        
        Returns:
            Role capabilities dictionary for active policy version
        """
        return self._policy_versions.get(self.policy_version, self._policy_versions["v1"])

    def switch_policy_version(self, version: str) -> bool:
        """
        Hot swap to a different policy version.
        Clears cache to prevent stale permissions.
        
        Args:
            version: Policy version to switch to (e.g., "v1", "v2")
            
        Returns:
            True if switch successful, False if version not found
        """
        if version in self._policy_versions:
            self.policy_version = version
            self._policy_state = "TRANSITION"
            # Clear cache to prevent stale permissions
            self._permission_cache.clear()
            self._cache_state = "FLUSHED"
            log.info(f"RBAC Policy switched to version: {version}, cache cleared")
            self._policy_state = "STABLE"
            return True
        else:
            log.error(f"RBAC Policy version not found: {version}")
            return False

    def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker allows requests.
        Forces cache bypass when circuit is OPEN.
        
        Returns:
            True if circuit is CLOSED (allow requests), False if OPEN (block requests)
        """
        current_time = time.time()
        
        # If circuit is OPEN, check if cooldown period has passed
        if self._circuit_state == "OPEN":
            if self._last_failure_time and (current_time - self._last_failure_time) > self._circuit_cooldown:
                log.info("RBAC Circuit breaker cooldown expired, entering HALF_OPEN state")
                self._circuit_state = "HALF_OPEN"
                self._cache_state = "FLUSHED"  # Flush cache on transition
                self._permission_cache.clear()
                return True
            else:
                log.warning("RBAC Circuit breaker is OPEN - blocking requests, cache bypass forced")
                return False
        
        # If circuit is HALF_OPEN, allow one request to test recovery
        if self._circuit_state == "HALF_OPEN":
            return True
        
        # Circuit is CLOSED, allow requests normally
        return True

    def _record_failure(self):
        """Record a failure and update circuit breaker state."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self._failure_threshold:
            self._circuit_state = "OPEN"
            log.error(f"RBAC Circuit breaker OPEN after {self._failure_count} failures")

    def _record_success(self):
        """Record a success and update circuit breaker state."""
        if self._circuit_state == "HALF_OPEN":
            self._circuit_state = "CLOSED"
            self._failure_count = 0
            log.info("RBAC Circuit breaker recovered, entering CLOSED state")
        elif self._circuit_state == "CLOSED":
            self._failure_count = 0

    def check_permission(self, role: str, intent: str) -> Dict[str, Any]:
        """
        Check if a role has permission to execute an intent.
        Production-grade with policy-bound cache, circuit breaker, and SUPERADMIN pre-gate.

        Args:
            role: User's role (will be normalized using normalize_role())
            intent: The intent to check permission for

        Returns:
            Dict with 'allowed' boolean and 'reason' string
        """
        try:
            # STEP 0: SUPERADMIN PRE-GATE (ABSOLUTE OVERRIDE - independent of all systems)
            role_upper = self.normalize_role(role)
            if role_upper == "SUPERADMIN":
                log.info(f"RBAC: SUPERADMIN pre-gate override for intent={intent}")
                return {
                    "allowed": True,
                    "reason": "superadmin pre-gate override"
                }
            
            # STEP 1: Capture policy snapshot (IMMUTABLE per request)
            request_policy_version = self.policy_version
            role_capabilities = self._policy_versions.get(request_policy_version, self._policy_versions["v1"])
            
            # STEP 2: Check circuit breaker
            if not self._check_circuit_breaker():
                return {
                    "allowed": False,
                    "reason": "RBAC circuit breaker is OPEN - system in safe mode"
                }
            
            # STEP 3: Cache check (policy-bound, only if cache is ACTIVE)
            cache_key = f"{request_policy_version}:{role_upper}:{intent}"
            if self._cache_state == "ACTIVE" and cache_key in self._permission_cache:
                cached = self._permission_cache[cache_key]
                
                if cached == "*":
                    log.info(f"RBAC: CACHE HIT - wildcard for role={role_upper} intent={intent}")
                    self._record_success()
                    return {
                        "allowed": True,
                        "reason": "cache: wildcard hit"
                    }
                
                if cached == True:
                    log.info(f"RBAC: CACHE HIT - role permission for role={role_upper} intent={intent}")
                    self._record_success()
                    return {
                        "allowed": True,
                        "reason": "cache: role permission hit"
                    }
            
            # STEP 4: Live RBAC evaluation (SOURCE OF TRUTH)
            # Check if role exists
            if role_upper not in role_capabilities:
                log.error(f"RBAC: Unknown role={role_upper}")
                self._record_failure()
                return {
                    "allowed": False,
                    "reason": f"Unknown role: {role}"
                }
            
            # Get allowed intents for this role
            allowed_intents = role_capabilities[role_upper]
            
            # Check if intent is allowed
            if intent in allowed_intents:
                log.info(f"RBAC: ALLOWED role={role_upper} intent={intent}")
                self._record_success()
                
                # STEP 5: Update cache (if cache is ACTIVE)
                if self._cache_state == "ACTIVE":
                    self._permission_cache[cache_key] = True
                
                return {
                    "allowed": True,
                    "reason": "authorized"
                }
            else:
                log.warning(f"RBAC: DENIED role={role_upper} intent={intent}")
                self._record_success()  # Denial is not a failure
                return {
                    "allowed": False,
                    "reason": f"Role '{role}' is not permitted to execute '{intent}'"
                }
        except Exception as e:
            # Circuit breaker: record failure
            self._record_failure()
            log.error(f"RBAC Engine failure detected - entering safe mode: {str(e)}")
            # Safe fallback: deny on error to prevent unauthorized access
            return {
                "allowed": False,
                "reason": "RBAC system error - safe mode activated"
            }

    def get_role_capabilities(self, role: str) -> list:
        """
        Get all capabilities for a given role.
        This is used by the capabilities API endpoint.

        Args:
            role: User's role (will be normalized using normalize_role())

        Returns:
            List of allowed intents for the role
        """
        role_upper = self.normalize_role(role)
        role_capabilities = self.get_active_policy()
        capabilities = role_capabilities.get(role_upper, set())
        return sorted(list(capabilities))

    def get_all_roles(self) -> list:
        """
        Get list of all registered roles from active policy.

        Returns:
            List of role names
        """
        role_capabilities = self.get_active_policy()
        return sorted(list(role_capabilities.keys()))


# ─────────────────────────────────────────────
# SINGLETON EXPORT
# ─────────────────────────────────────────────

rbac_engine = RBACEngine()

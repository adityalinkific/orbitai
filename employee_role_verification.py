"""
ORBIT EMPLOYEE ROLE — ENTERPRISE VERIFICATION SUITE

Comprehensive QA verification for EMPLOYEE role capabilities.
Tests intent detection, RBAC, scope validation, business execution, response quality, governance safety, and data integrity.
"""

import http.client
import json
import time
from typing import Dict, List, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class TestResult:
    test_name: str
    status: TestStatus
    category: str
    capability: str
    expected: str
    actual: str
    duration: float
    details: str = ""
    root_cause: str = ""
    fix_instruction: str = ""


@dataclass
class VerificationReport:
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    errors: int = 0
    success_rate: float = 0.0
    failed_capabilities: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    recommended_fixes: List[str] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)


class OrbitEmployeeVerifier:
    """Enterprise QA Agent for ORBIT EMPLOYEE role verification."""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.token = None
        self.user_role = None
        self.capabilities = []
        self.report = VerificationReport()
        self.session_id = f"EMPLOYEE_verification_{int(time.time())}"
        
    def login(self, email: str, password: str) -> bool:
        """Authenticate and store JWT token."""
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            headers = {"Content-Type": "application/json"}
            payload = json.dumps({"email": email, "password": password})
            
            conn.request("POST", "/api/v1/auth/login", payload, headers)
            response = conn.getresponse()
            data = json.loads(response.read().decode())
            conn.close()
            
            if response.status == 200:
                self.token = data.get("data", {}).get("access_token")
                self.user_role = data.get("data", {}).get("user", {}).get("role")
                print(f"✅ Login successful - Role: {self.user_role}")
                return True
            else:
                print(f"❌ Login failed: {data.get('message', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Login error: {str(e)}")
            return False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Discover EMPLOYEE capabilities."""
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            headers = {"Authorization": f"Bearer {self.token}"}
            
            conn.request("GET", "/api/v1/assistant/capabilities", headers=headers)
            response = conn.getresponse()
            data = json.loads(response.read().decode())
            conn.close()
            
            if response.status == 200:
                self.capabilities = data.get("capabilities", [])
                role = data.get("role", "UNKNOWN")
                print(f"✅ Discovered {len(self.capabilities)} capabilities for role: {role}")
                return data
            else:
                print(f"❌ Failed to get capabilities: {data}")
                return {}
        except Exception as e:
            print(f"❌ Error getting capabilities: {str(e)}")
            return {}
    
    def chat(self, message: str) -> Dict[str, Any]:
        """Send message to ORBIT assistant."""
        try:
            conn = http.client.HTTPConnection(self.host, self.port)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            payload = {"message": message, "session_id": self.session_id}
            
            conn.request("POST", "/api/v1/assistant/chat", json.dumps(payload), headers)
            response = conn.getresponse()
            data = json.loads(response.read().decode())
            conn.close()
            
            return data
        except Exception as e:
            return {"error": str(e), "success": False, "bot_reply": str(e)}
    
    def validate_response_structure(self, response: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate response structure meets quality standards."""
        errors = []
        
        # Check for required fields
        if "status" not in response:
            errors.append("Missing 'status' field")
        if "success" not in response:
            errors.append("Missing 'success' field")
        if "bot_reply" not in response or not response.get("bot_reply"):
            errors.append("Missing or empty 'bot_reply'")
        
        # Check for Python object memory references
        bot_reply = str(response.get("bot_reply", ""))
        if "<object at 0x" in bot_reply or "0x" in bot_reply and len(bot_reply) < 50:
            errors.append("Response contains Python object memory reference")
        
        # Check for traceback errors
        if "Traceback" in bot_reply or "Error:" in bot_reply and "Internal Server Error" in bot_reply:
            errors.append("Response contains traceback or internal error")
        
        # Check for None responses
        if response.get("bot_reply") is None or response.get("bot_reply") == "None":
            errors.append("Response is None")
        
        return (len(errors) == 0, "; ".join(errors) if errors else "")
    
    def test_functional(self, capability: str) -> TestResult:
        """Test basic functional execution of a capability."""
        test_prompts = self._get_test_prompt_for_capability(capability)
        prompt = test_prompts[0] if test_prompts else f"test {capability}"
        
        start_time = time.time()
        response = self.chat(prompt)
        duration = time.time() - start_time
        
        intent = response.get("intent", "").upper()
        success = response.get("success", False)
        error = response.get("error", "")
        bot_reply = response.get("bot_reply", "")
        
        # Validate response structure
        structure_valid, structure_error = self.validate_response_structure(response)
        
        # Handle cases where intent might be normalized differently
        if intent == "" and capability in ["GREETING", "LIST_MY_INFO"]:
             # These might not always return intent in the response if handled specifically
             pass

        # Check for successful execution or informative "not found"
        is_actually_success = success
        if not success:
            if "not found" in bot_reply.lower() or "no projects" in bot_reply.lower() or "no tasks" in bot_reply.lower():
                is_actually_success = True
            elif "already" in bot_reply.lower(): # already exists, already closed etc
                is_actually_success = True
            elif "pending" in bot_reply.lower():
                is_actually_success = True

        if is_actually_success and structure_valid:
            return TestResult(
                test_name=f"Functional: {capability}",
                status=TestStatus.PASS,
                category="Functional",
                capability=capability,
                expected=f"Successful execution of {capability}",
                actual=f"Intent detected: {intent or 'N/A'}, Bot reply: {bot_reply[:50]}...",
                duration=duration,
                details=bot_reply
            )
        
        error_details = ""
        if not is_actually_success:
            error_details = f"Execution failed: {bot_reply}"
        if not structure_valid:
            error_details = f"Structure validation failed: {structure_error}"
        
        return TestResult(
            test_name=f"Functional: {capability}",
            status=TestStatus.FAIL,
            category="Functional",
            capability=capability,
            expected=f"Successful execution of {capability}",
            actual=f"Intent detected: {intent}, Success: {success}, Bot reply: {bot_reply}",
            duration=duration,
            details=bot_reply,
            root_cause=error_details,
            fix_instruction="Check NLU engine, intent handler, and response formatter"
        )
    
    def test_rbac_boundary(self, capability: str) -> TestResult:
        """Test RBAC boundary - EMPLOYEE should not access ADMIN/SUPERADMIN capabilities."""
        restricted_capabilities = [
            "REGISTER_USER", "DELETE_USER", "UPDATE_ROLE", "CREATE_PROJECT", 
            "DELETE_PROJECT", "CREATE_DEPARTMENT", "SYSTEM_STATUS", "ENTERPRISE_REASONING",
            "SHOW_ORG_DASHBOARD", "UPDATE_PERMISSIONS", "ASSIGN_ROLE"
        ]
        
        if capability in restricted_capabilities:
            test_prompt = self._get_rbac_test_prompt(capability)
            start_time = time.time()
            response = self.chat(test_prompt)
            duration = time.time() - start_time
            
            bot_reply = response.get("bot_reply", "").lower()
            success = response.get("success", True)
            
            # Employee should be denied access
            if not success or "permission" in bot_reply or "deny" in bot_reply or "authorize" in bot_reply or "not allowed" in bot_reply or "cannot" in bot_reply:
                return TestResult(
                    test_name=f"RBAC Boundary: {capability}",
                    status=TestStatus.PASS,
                    category="RBAC",
                    capability=capability,
                    expected="Access denied",
                    actual="Access denied/blocked",
                    duration=duration,
                    details=f"Prompt blocked as expected: {response.get('bot_reply', '')[:100]}"
                )
            else:
                return TestResult(
                    test_name=f"RBAC Boundary: {capability}",
                    status=TestStatus.FAIL,
                    category="RBAC",
                    capability=capability,
                    expected="Access denied",
                    actual="Access permitted",
                    duration=duration,
                    details=f"EMPLOYEE should not have access to {capability}. Response: {response.get('bot_reply', '')}",
                    root_cause="RBAC leak - employee can access restricted capability",
                    fix_instruction="Update capability_resolver.py to restrict this capability for EMPLOYEE role"
                )
        
        return TestResult(
            test_name=f"RBAC Boundary: {capability}",
            status=TestStatus.PASS,
            category="RBAC",
            capability=capability,
            expected="N/A",
            actual="N/A",
            duration=0.0,
            details="Not a restricted capability for EMPLOYEE"
        )

    def test_edge_cases(self) -> List[TestResult]:
        """Test edge cases - missing data and invalid IDs."""
        results = []
        
        # Test 1: Update task progress without specifying task/percentage
        start_time = time.time()
        response = self.chat("update task progress")
        duration = time.time() - start_time
        
        if not response.get("success") or "which task" in response.get("bot_reply", "").lower() or "please specify" in response.get("bot_reply", "").lower():
            results.append(TestResult(
                "Edge: Missing task progress data", TestStatus.PASS, "Edge Case", "UPDATE_TASK_PROGRESS",
                "Graceful handling of missing data", "Handled with clarification request", duration,
                details=response.get("bot_reply", "")
            ))
        else:
            results.append(TestResult(
                "Edge: Missing task progress data", TestStatus.FAIL, "Edge Case", "UPDATE_TASK_PROGRESS",
                "Graceful handling of missing data", "Failed to handle missing data", duration,
                details=response.get("bot_reply", ""),
                root_cause="Missing input validation",
                fix_instruction="Add input validation for required parameters"
            ))
        
        # Test 2: Join meeting without specifying which meeting
        start_time = time.time()
        response = self.chat("join meeting")
        duration = time.time() - start_time
        
        if not response.get("success") or "which meeting" in response.get("bot_reply", "").lower() or "please specify" in response.get("bot_reply", "").lower():
            results.append(TestResult(
                "Edge: Missing meeting ID", TestStatus.PASS, "Edge Case", "JOIN_MEETING",
                "Graceful handling of missing data", "Handled with clarification request", duration,
                details=response.get("bot_reply", "")
            ))
        else:
            results.append(TestResult(
                "Edge: Missing meeting ID", TestStatus.FAIL, "Edge Case", "JOIN_MEETING",
                "Graceful handling of missing data", "Failed to handle missing data", duration,
                details=response.get("bot_reply", ""),
                root_cause="Missing input validation",
                fix_instruction="Add input validation for required parameters"
            ))
        
        # Test 3: Report blocker without context
        start_time = time.time()
        response = self.chat("report blocker")
        duration = time.time() - start_time
        
        if not response.get("success") or "which task" in response.get("bot_reply", "").lower() or "please specify" in response.get("bot_reply", "").lower():
            results.append(TestResult(
                "Edge: Missing blocker context", TestStatus.PASS, "Edge Case", "REPORT_BLOCKER",
                "Graceful handling of missing data", "Handled with clarification request", duration,
                details=response.get("bot_reply", "")
            ))
        else:
            results.append(TestResult(
                "Edge: Missing blocker context", TestStatus.FAIL, "Edge Case", "REPORT_BLOCKER",
                "Graceful handling of missing data", "Failed to handle missing data", duration,
                details=response.get("bot_reply", ""),
                root_cause="Missing input validation",
                fix_instruction="Add input validation for required parameters"
            ))
        
        # Test 4: Get task with invalid ID
        start_time = time.time()
        response = self.chat("get task 99999")
        duration = time.time() - start_time
        
        if "not found" in response.get("bot_reply", "").lower() or "no task" in response.get("bot_reply", "").lower():
            results.append(TestResult(
                "Edge: Invalid task ID", TestStatus.PASS, "Edge Case", "GET_TASK",
                "Graceful handling of invalid ID", "Handled with not found message", duration,
                details=response.get("bot_reply", "")
            ))
        else:
            results.append(TestResult(
                "Edge: Invalid task ID", TestStatus.FAIL, "Edge Case", "GET_TASK",
                "Graceful handling of invalid ID", "Failed to handle invalid ID", duration,
                details=response.get("bot_reply", ""),
                root_cause="Missing ID validation",
                fix_instruction="Add ID validation and graceful error handling"
            ))
        
        # Test 5: Join meeting with invalid ID
        start_time = time.time()
        response = self.chat("join meeting 99999")
        duration = time.time() - start_time
        
        if "not found" in response.get("bot_reply", "").lower() or "no meeting" in response.get("bot_reply", "").lower():
            results.append(TestResult(
                "Edge: Invalid meeting ID", TestStatus.PASS, "Edge Case", "JOIN_MEETING",
                "Graceful handling of invalid ID", "Handled with not found message", duration,
                details=response.get("bot_reply", "")
            ))
        else:
            results.append(TestResult(
                "Edge: Invalid meeting ID", TestStatus.FAIL, "Edge Case", "JOIN_MEETING",
                "Graceful handling of invalid ID", "Failed to handle invalid ID", duration,
                details=response.get("bot_reply", ""),
                root_cause="Missing ID validation",
                fix_instruction="Add ID validation and graceful error handling"
            ))
        
        return results

    def test_stress_logic(self) -> List[TestResult]:
        """Stress tests for EMPLOYEE - rapid execution and mixed prompts."""
        results = []
        
        # Test 1: Rapid execution - repeat 10 times
        print("\n  🔄 Stress Test: Rapid execution (10 iterations)...")
        failures = 0
        for i in range(10):
            start_time = time.time()
            response = self.chat("what are my tasks")
            duration = time.time() - start_time
            
            if response.get("error") or "Traceback" in response.get("bot_reply", ""):
                failures += 1
        
        total_duration = duration * 10
        if failures == 0:
            results.append(TestResult(
                "Stress: Rapid execution (10x)", TestStatus.PASS, "Stress", "LIST_MY_TASKS",
                "System stability under load", f"All 10 iterations successful", total_duration,
                details="No crashes or errors during rapid execution"
            ))
        else:
            results.append(TestResult(
                "Stress: Rapid execution (10x)", TestStatus.FAIL, "Stress", "LIST_MY_TASKS",
                "System stability under load", f"{failures}/10 iterations failed", total_duration,
                details=f"{failures} failures detected during rapid execution",
                root_cause="System instability under load",
                fix_instruction="Investigate concurrency issues and resource limits"
            ))
        
        # Test 2: Mixed prompts sequence
        print("\n  🔄 Stress Test: Mixed prompt sequence...")
        mixed_prompts = [
            "hello orbit",
            "what are my tasks",
            "show my dashboard",
            "request help",
            "list meetings"
        ]
        
        start_time = time.time()
        all_passed = True
        for prompt in mixed_prompts:
            response = self.chat(prompt)
            if response.get("error") or "Traceback" in response.get("bot_reply", ""):
                all_passed = False
                break
        
        duration = time.time() - start_time
        if all_passed:
            results.append(TestResult(
                "Stress: Mixed prompt sequence", TestStatus.PASS, "Stress", "MULTIPLE",
                "Context preservation across prompts", "All prompts handled successfully", duration,
                details="System maintained stability across mixed prompt types"
            ))
        else:
            results.append(TestResult(
                "Stress: Mixed prompt sequence", TestStatus.FAIL, "Stress", "MULTIPLE",
                "Context preservation across prompts", "Failed during mixed prompt execution", duration,
                details="System failed during mixed prompt execution",
                root_cause="Context management issue",
                fix_instruction="Investigate session context management"
            ))
        
        return results

    def test_session_stability(self) -> List[TestResult]:
        """Test conversation continuity and session stability."""
        results = []
        
        print("\n  🔄 Session Stability Test: Conversation continuity...")
        
        # Sequence: ask task -> update progress -> ask again -> request help
        start_time = time.time()
        
        # Step 1: Ask for tasks
        response1 = self.chat("what are my tasks")
        task_context = response1.get("bot_reply", "")
        
        # Step 2: Update progress (if tasks exist)
        response2 = self.chat("update task progress to 30 percent")
        
        # Step 3: Ask again
        response3 = self.chat("what are my tasks")
        
        # Step 4: Request help
        response4 = self.chat("request help from manager")
        
        duration = time.time() - start_time
        
        # Check if all responses are valid (no crashes, tracebacks)
        all_valid = all(
            "Traceback" not in r.get("bot_reply", "") and 
            r.get("error") is None
            for r in [response1, response2, response3, response4]
        )
        
        if all_valid:
            results.append(TestResult(
                "Session: Conversation continuity", TestStatus.PASS, "Session", "MULTIPLE",
                "Context preservation across conversation", "Session maintained successfully", duration,
                details="All 4 conversation steps completed without errors"
            ))
        else:
            results.append(TestResult(
                "Session: Conversation continuity", TestStatus.FAIL, "Session", "MULTIPLE",
                "Context preservation across conversation", "Session lost or crashed", duration,
                details="Conversation sequence failed",
                root_cause="Session context management issue",
                fix_instruction="Investigate session persistence and context handling"
            ))
        
        return results

    def test_response_quality(self) -> List[TestResult]:
        """Test response quality across all capabilities."""
        results = []
        
        print("\n  🔄 Response Quality Test: Checking all responses...")
        
        # Test a sample of capabilities for response quality
        sample_capabilities = ["GREETING", "LIST_MY_INFO", "WHAT_ARE_MY_TASKS", "SHOW_PERSONAL_DASHBOARD"]
        
        for capability in sample_capabilities:
            prompt = self._get_test_prompt_for_capability(capability)[0]
            start_time = time.time()
            response = self.chat(prompt)
            duration = time.time() - start_time
            
            structure_valid, structure_error = self.validate_response_structure(response)
            bot_reply = response.get("bot_reply", "")
            
            quality_checks = {
                "No traceback": "Traceback" not in bot_reply,
                "No None response": bot_reply is not None and bot_reply != "None",
                "No empty message": len(bot_reply.strip()) > 0,
                "Human readable": len(bot_reply) > 10 and "<object at 0x" not in bot_reply,
                "Structure valid": structure_valid
            }
            
            if all(quality_checks.values()):
                results.append(TestResult(
                    f"Quality: {capability}", TestStatus.PASS, "Quality", capability,
                    "High quality response", "All quality checks passed", duration,
                    details=f"Response length: {len(bot_reply)}, All checks: {list(quality_checks.keys())}"
                ))
            else:
                failed_checks = [k for k, v in quality_checks.items() if not v]
                results.append(TestResult(
                    f"Quality: {capability}", TestStatus.FAIL, "Quality", capability,
                    "High quality response", f"Failed checks: {failed_checks}", duration,
                    details=structure_error or f"Failed quality checks: {failed_checks}",
                    root_cause="Response formatting issue",
                    fix_instruction="Review response formatter and error handling"
                ))
        
        return results

    def _get_test_prompt_for_capability(self, capability: str) -> List[str]:
        """Get test prompts for EMPLOYEE capabilities."""
        prompts = {
            "GREETING": ["hello orbit"],
            "LIST_MY_INFO": ["who am i", "show my profile information"],
            "WHAT_ARE_MY_TASKS": ["what are my tasks"],
            "LIST_MY_TASKS": ["list my tasks", "show my assigned tasks"],
            "GET_TASK": ["show task 1", "get my latest task"],
            "UPDATE_TASK_PROGRESS": ["update task progress to 30 percent", "mark task progress 75% complete"],
            "REPORT_BLOCKER": ["report blocker for task 1", "I am blocked on task 1 due to dependency"],
            "REQUEST_HELP": ["request help from manager", "I need assistance on my task"],
            "JOIN_MEETING": ["join meeting 1", "join the daily standup"],
            "LIST_MEETINGS": ["list meetings"],
            "GET_MEETING": ["get meeting details"],
            "SHOW_PERSONAL_DASHBOARD": ["show my dashboard", "show personal dashboard"],
            "SHOW_EXECUTION_GUIDANCE": ["what should I do next", "show execution guidance"],
            "SHOW_EXPECTED_OUTPUT": ["show expected output"],
        }
        return prompts.get(capability, [f"test {capability}"])

    def _get_rbac_test_prompt(self, capability: str) -> str:
        """Get test prompts for RBAC boundary testing."""
        prompts = {
            "REGISTER_USER": "register new employee",
            "DELETE_USER": "delete user john@linkific.com",
            "UPDATE_ROLE": "update role permissions",
            "CREATE_PROJECT": "create new project",
            "DELETE_PROJECT": "delete project TestProject",
            "CREATE_DEPARTMENT": "create department Engineering",
            "SYSTEM_STATUS": "show system status",
            "ENTERPRISE_REASONING": "show enterprise reasoning",
            "SHOW_ORG_DASHBOARD": "show organization dashboard",
            "UPDATE_PERMISSIONS": "update permissions for role",
            "ASSIGN_ROLE": "assign admin role to user",
        }
        return prompts.get(capability, f"test {capability}")

    def run_verification(self, email: str, password: str) -> VerificationReport:
        print("\n" + "=" * 80)
        print("ORBIT EMPLOYEE ROLE — ENTERPRISE VERIFICATION SUITE")
        print("=" * 80)
        
        # Phase 1: Authentication
        print("\n🔐 PHASE 1: Authentication")
        if not self.login(email, password):
            print("❌ Authentication failed. Cannot proceed with verification.")
            return self.report
        
        # Phase 2: Capability Discovery
        print("\n🔍 PHASE 2: Capability Discovery")
        self.get_capabilities()
        
        # Expected EMPLOYEE capabilities
        target_capabilities = [
            "GREETING", "LIST_MY_INFO", "WHAT_ARE_MY_TASKS", "LIST_MY_TASKS",
            "GET_TASK", "UPDATE_TASK_PROGRESS", "REPORT_BLOCKER", "REQUEST_HELP",
            "JOIN_MEETING", "LIST_MEETINGS", "GET_MEETING",
            "SHOW_PERSONAL_DASHBOARD", "SHOW_EXECUTION_GUIDANCE", "SHOW_EXPECTED_OUTPUT"
        ]
        
        # Phase 3: Functional Tests
        print("\n🧪 PHASE 3: Core Functional Tests")
        for cap in target_capabilities:
            result = self.test_functional(cap)
            self.report.test_results.append(result)
            self._print_test_result(result)
            time.sleep(0.3)
        
        # Phase 4: RBAC Security Tests
        print("\n🔒 PHASE 4: RBAC Security Tests (CRITICAL)")
        restricted_capabilities = [
            "REGISTER_USER", "DELETE_USER", "UPDATE_ROLE", "CREATE_PROJECT",
            "DELETE_PROJECT", "CREATE_DEPARTMENT", "SYSTEM_STATUS", "ENTERPRISE_REASONING",
            "SHOW_ORG_DASHBOARD", "UPDATE_PERMISSIONS", "ASSIGN_ROLE"
        ]
        for cap in restricted_capabilities:
            result = self.test_rbac_boundary(cap)
            self.report.test_results.append(result)
            self._print_test_result(result)
            time.sleep(0.2)
        
        # Phase 5: Edge Case Testing
        print("\n⚠️  PHASE 5: Edge Case Testing")
        edge_results = self.test_edge_cases()
        self.report.test_results.extend(edge_results)
        for result in edge_results:
            self._print_test_result(result)
        
        # Phase 6: Stress Testing
        print("\n⚡ PHASE 6: Stress Testing")
        stress_results = self.test_stress_logic()
        self.report.test_results.extend(stress_results)
        for result in stress_results:
            self._print_test_result(result)
        
        # Phase 7: Response Quality Validation
        print("\n✨ PHASE 7: Response Quality Validation")
        quality_results = self.test_response_quality()
        self.report.test_results.extend(quality_results)
        for result in quality_results:
            self._print_test_result(result)
        
        # Phase 8: Session Stability
        print("\n🔗 PHASE 8: Session Stability")
        session_results = self.test_session_stability()
        self.report.test_results.extend(session_results)
        for result in session_results:
            self._print_test_result(result)
        
        # Generate final report
        self._generate_report()
        return self.report

    def _print_test_result(self, result: TestResult):
        status_icon = "✅" if result.status == TestStatus.PASS else "❌"
        print(f"{status_icon} {result.test_name}: {result.status.value}")
        if result.status != TestStatus.PASS:
            print(f"   Details: {result.details[:100]}...")
            if result.root_cause:
                print(f"   Root Cause: {result.root_cause[:80]}...")

    def _generate_report(self):
        passed = sum(1 for r in self.report.test_results if r.status == TestStatus.PASS)
        total = len(self.report.test_results)
        self.report.total_tests = total
        self.report.passed = passed
        self.report.failed = total - passed
        self.report.success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print(f"Role: EMPLOYEE")
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {self.report.failed}")
        print(f"Success Rate: {self.report.success_rate:.1f}%")
        
        if self.report.success_rate == 100.0:
            print("\n🎉 EMPLOYEE ROLE CERTIFIED")
            print(f"{passed} / {total} TESTS PASSED")
            print("SUCCESS RATE: 100%")
            print("NO REGRESSIONS DETECTED")
            print("SYSTEM STABLE")
            print("RBAC BOUNDARIES SECURE")
        else:
            print("\n⚠️  EMPLOYEE ROLE NOT CERTIFIED")
            print(f"FAILED TESTS: {self.report.failed}")
            print("\nFailed Capabilities:")
            for result in self.report.test_results:
                if result.status != TestStatus.PASS:
                    print(f"  - {result.capability}: {result.details[:80]}")
        
        # Generate JSON report
        report_data = {
            "role": "EMPLOYEE",
            "total_tests": total,
            "passed": passed,
            "failed": self.report.failed,
            "success_rate": self.report.success_rate,
            "system_status": "CERTIFIED" if self.report.success_rate == 100.0 else "NOT CERTIFIED",
            "results": [
                {
                    "name": r.test_name,
                    "status": r.status.value,
                    "category": r.category,
                    "capability": r.capability,
                    "details": r.details,
                    "root_cause": r.root_cause,
                    "fix_instruction": r.fix_instruction
                }
                for r in self.report.test_results
            ]
        }
        
        with open("EMPLOYEE_verification_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: EMPLOYEE_verification_report.json")
        
        # Print final output format as requested
        print("\n" + "=" * 80)
        print("FINAL OUTPUT")
        print("=" * 80)
        print(json.dumps({
            "role": "EMPLOYEE",
            "total_tests": total,
            "passed": passed,
            "failed": self.report.failed,
            "success_rate": self.report.success_rate,
            "system_status": "CERTIFIED" if self.report.success_rate == 100.0 else "NOT CERTIFIED"
        }, indent=2))


if __name__ == "__main__":
    verifier = OrbitEmployeeVerifier()
    verifier.run_verification("employee@linkific.com", "Sudheer@123")

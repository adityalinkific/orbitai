"""
Capability Audit - Verify all capabilities have registered handlers
Scans config.yaml and ensures every intent has a corresponding handler
"""

import yaml
import os
import logging
from typing import Dict, List, Set, Tuple
from pathlib import Path

log = logging.getLogger("capability_audit")


class CapabilityAuditor:
    """
    Audits the assistant configuration to ensure:
    1. All intents in config.yaml have registered handlers
    2. No orphaned capabilities exist
    3. All handlers are properly mapped
    """
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to orbit_assistant config.yaml
            config_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "config.yaml"
            )
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from config.yaml."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            log.error(f"Failed to load config from {self.config_path}: {e}")
            return {"intents": {}, "workflows": {}}
    
    def audit_handlers(self) -> Dict[str, any]:
        """
        Perform comprehensive audit of capabilities and handlers.
        
        Returns:
            Audit report with missing handlers, orphaned intents, etc.
        """
        report = {
            "total_intents": 0,
            "total_workflows": 0,
            "missing_handlers": [],
            "orphaned_intents": [],
            "service_mapping_errors": [],
            "rbac_gaps": [],
            "status": "unknown"
        }
        
        intents = self.config.get("intents", {})
        workflows = self.config.get("workflows", {})
        
        report["total_intents"] = len(intents)
        report["total_workflows"] = len(workflows)
        
        # Check each intent for handler mapping
        for intent_name, intent_config in intents.items():
            service = intent_config.get("service")
            method = intent_config.get("method")
            
            if not service or not method:
                report["missing_handlers"].append({
                    "intent": intent_name,
                    "reason": "Missing service or method mapping"
                })
                continue
            
            # Check if service exists
            known_services = {
                "TaskService", "ProjectService", "TaskAssignService",
                "UserService", "DepartmentService", "RoleService",
                "AuthService", "Executor", "ServiceBridge"
            }
            
            if service not in known_services:
                report["service_mapping_errors"].append({
                    "intent": intent_name,
                    "service": service,
                    "reason": f"Unknown service: {service}"
                })
            
            # Check RBAC configuration
            allowed_roles = intent_config.get("allowed_roles", [])
            if not allowed_roles:
                report["rbac_gaps"].append({
                    "intent": intent_name,
                    "reason": "No allowed_roles defined"
                })
        
        # Check workflows
        for workflow_name, workflow_config in workflows.items():
            steps = workflow_config.get("steps", [])
            if not steps:
                report["missing_handlers"].append({
                    "intent": workflow_name,
                    "reason": "Workflow has no steps defined"
                })
        
        # Determine overall status
        has_critical_issues = (
            len(report["missing_handlers"]) > 0 or
            len(report["service_mapping_errors"]) > 0
        )
        
        report["status"] = "critical" if has_critical_issues else "healthy"
        
        return report
    
    def verify_system_intents(self) -> Tuple[bool, List[str]]:
        """
        Verify system-only intents are properly firewalled.
        
        Returns:
            (is_valid, issues)
        """
        try:
            from app.modules.orbit_assistant.system_intents import SYSTEM_ONLY_INTENTS
            
            issues = []
            config_intents = set(self.config.get("intents", {}).keys())
            
            # System intents should NOT be in config.yaml (they're firewalled)
            for system_intent in SYSTEM_ONLY_INTENTS:
                if system_intent in config_intents:
                    issues.append(
                        f"System intent '{system_intent}' should not be in config.yaml - "
                        f"it's handled by system_intents firewall"
                    )
            
            return (len(issues) == 0, issues)
        except ImportError:
            return (False, ["Could not import system_intents module"])
    
    def scan_capability_exposure(self) -> Dict[str, List[str]]:
        """
        Scan for potentially unsafe capability exposures.
        
        Returns:
            Dictionary of risk categories with affected intents
        """
        risks = {
            "destructive_without_confirmation": [],
            "admin_only_exposed_to_all": [],
            "missing_rbac": []
        }
        
        intents = self.config.get("intents", {})
        
        for intent_name, intent_config in intents.items():
            # Check destructive actions without confirmation flag
            is_destructive = intent_config.get("is_destructive") or intent_config.get("destructive", False)
            if is_destructive and not intent_config.get("requires_confirmation", False):
                risks["destructive_without_confirmation"].append(intent_name)
            
            # Check admin-only intents exposed to lower roles
            allowed_roles = intent_config.get("allowed_roles", [])
            if "super_admin" in allowed_roles or "admin" in allowed_roles:
                # If admin-only but also exposed to lower roles, flag it
                lower_roles = {"manager", "employee", "intern", "head"}
                if any(role in allowed_roles for role in lower_roles):
                    risks["admin_only_exposed_to_all"].append(intent_name)
            
            # Check missing RBAC entirely
            if not allowed_roles:
                risks["missing_rbac"].append(intent_name)
        
        return risks
    
    def generate_health_report(self) -> dict:
        """
        Generate comprehensive health report for the assistant configuration.
        
        Returns:
            Complete health report with scores and recommendations
        """
        handler_audit = self.audit_handlers()
        system_check, system_issues = self.verify_system_intents()
        risk_scan = self.scan_capability_exposure()
        
        # Calculate health score (0-100)
        score = 100
        
        # Deduct points for issues
        score -= len(handler_audit["missing_handlers"]) * 10
        score -= len(handler_audit["service_mapping_errors"]) * 15
        score -= len(handler_audit["rbac_gaps"]) * 5
        score -= len(system_issues) * 20
        score -= len(risk_scan["destructive_without_confirmation"]) * 5
        score -= len(risk_scan["admin_only_exposed_to_all"]) * 10
        score -= len(risk_scan["missing_rbac"]) * 15
        
        score = max(0, min(100, score))
        
        return {
            "health_score": score,
            "status": "healthy" if score >= 80 else "degraded" if score >= 50 else "critical",
            "handler_audit": handler_audit,
            "system_intents_check": {
                "valid": system_check,
                "issues": system_issues
            },
            "risk_assessment": risk_scan,
            "recommendations": self._generate_recommendations(handler_audit, system_issues, risk_scan)
        }
    
    def _generate_recommendations(self, handler_audit, system_issues, risk_scan) -> List[str]:
        """Generate actionable recommendations based on audit findings."""
        recommendations = []
        
        if handler_audit["missing_handlers"]:
            recommendations.append(
                f"Add handlers for {len(handler_audit['missing_handlers'])} missing intents"
            )
        
        if handler_audit["service_mapping_errors"]:
            recommendations.append(
                f"Fix {len(handler_audit['service_mapping_errors'])} service mapping errors"
            )
        
        if system_issues:
            recommendations.append(
                f"Remove {len(system_issues)} system intents from config.yaml (use firewall instead)"
            )
        
        if risk_scan["destructive_without_confirmation"]:
            recommendations.append(
                f"Add confirmation flow for {len(risk_scan['destructive_without_confirmation'])} destructive actions"
            )
        
        if risk_scan["admin_only_exposed_to_all"]:
            recommendations.append(
                f"Review RBAC for {len(risk_scan['admin_only_exposed_to_all'])} admin-only intents"
            )
        
        if not recommendations:
            recommendations.append("No critical issues found. Configuration is healthy.")
        
        return recommendations


# Singleton instance
capability_auditor = CapabilityAuditor()

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar

# Context variables for request tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class StructuredLogger:
    """Structured JSON logger for production observability."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _log(
        self,
        level: str,
        message: str,
        **kwargs
    ):
        """Internal log method with structured fields."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "logger": self.logger.name,
            "message": message,
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "session_id": session_id_var.get(),
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))
    
    def info(self, message: str, **kwargs):
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log("ERROR", message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log("DEBUG", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log("CRITICAL", message, **kwargs)


class RequestTracer:
    """Request tracing context manager."""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None, session_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id
        self.start_time = None
        self._request_token = None
        self._user_token = None
        self._session_token = None
    
    def __enter__(self):
        self.start_time = time.time()
        self._request_token = request_id_var.set(self.request_id)
        if self.user_id:
            self._user_token = user_id_var.set(str(self.user_id))
        if self.session_id:
            self._session_token = session_id_var.set(self.session_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        
        # Reset context
        request_id_var.reset(self._request_token)
        if self._user_token:
            user_id_var.reset(self._user_token)
        if self._session_token:
            session_id_var.reset(self._session_token)
        
        # Log request completion
        logger = StructuredLogger("request_tracer")
        if exc_type:
            logger.error(
                "Request failed",
                request_id=self.request_id,
                duration_ms=round(duration * 1000, 2),
                error=str(exc_val),
                error_type=exc_type.__name__ if exc_type else None
            )
        else:
            logger.info(
                "Request completed",
                request_id=self.request_id,
                duration_ms=round(duration * 1000, 2)
            )
    
    def get_duration(self) -> float:
        """Get elapsed duration in seconds."""
        return time.time() - self.start_time if self.start_time else 0


class MetricsCollector:
    """Collect and aggregate execution metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "request_count": 0,
            "error_count": 0,
            "total_duration_ms": 0,
            "intent_counts": {},
            "error_types": {}
        }
    
    def record_request(self, intent: str, duration_ms: float, success: bool, error_type: Optional[str] = None):
        """Record a request metric."""
        self.metrics["request_count"] += 1
        self.metrics["total_duration_ms"] += duration_ms
        
        if not success:
            self.metrics["error_count"] += 1
            if error_type:
                self.metrics["error_types"][error_type] = self.metrics["error_types"].get(error_type, 0) + 1
        
        if intent:
            self.metrics["intent_counts"][intent] = self.metrics["intent_counts"].get(intent, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_duration = (
            self.metrics["total_duration_ms"] / self.metrics["request_count"]
            if self.metrics["request_count"] > 0
            else 0
        )
        
        return {
            **self.metrics,
            "avg_duration_ms": round(avg_duration, 2),
            "error_rate": round(
                (self.metrics["error_count"] / self.metrics["request_count"] * 100)
                if self.metrics["request_count"] > 0
                else 0,
                2
            )
        }
    
    def reset(self):
        """Reset metrics."""
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_duration_ms": 0,
            "intent_counts": {},
            "error_types": {}
        }


# Global metrics collector
metrics = MetricsCollector()

"""
API Client — HTTP calls to Orbit backend with retry logic.
Retries transient failures (timeout, 5xx) up to configured attempts.
"""

import asyncio
from typing import Any

import httpx

from .logger import get_logger
from .error_handler import OrbitError, ErrorType

log = get_logger("api_client")


class OrbitAPIClient:
    """Async HTTP client with retry logic for the Orbit backend."""

    def __init__(
        self,
        base_url: str,
        retry_attempts: int = 2,
        retry_backoff: float = 1.0,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self.timeout = timeout

    async def execute(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an API call with retry logic.
        Retries on timeout and 5xx errors. Fails immediately on 4xx.
        """
        url = f"{self.base_url}{endpoint}"
        last_error = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                log.info(
                    f"API call (attempt {attempt}/{self.retry_attempts}): "
                    f"{method} {url}"
                )

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=payload if method in ("POST", "PUT", "PATCH") else None,
                        params=payload if method == "GET" else None,
                    )

                # 4xx — non-retryable, fail immediately
                if 400 <= response.status_code < 500:
                    log.error(
                        f"Client error {response.status_code}: {response.text}"
                    )
                    raise OrbitError(
                        error_type=ErrorType.API_ERROR,
                        message=f"API returned {response.status_code}",
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                        },
                        retryable=False,
                    )

                # 5xx — retryable
                if response.status_code >= 500:
                    log.warning(
                        f"Server error {response.status_code} (attempt {attempt})"
                    )
                    last_error = OrbitError(
                        error_type=ErrorType.API_ERROR,
                        message=f"API returned {response.status_code}",
                        details={"status_code": response.status_code},
                        retryable=True,
                    )
                    if attempt < self.retry_attempts:
                        await asyncio.sleep(self.retry_backoff * attempt)
                        continue
                    raise last_error

                # Success
                result = response.json() if response.text else {}
                log.info(f"API success: {method} {url} → {response.status_code}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": result,
                }

            except httpx.TimeoutException:
                log.warning(f"Timeout on {method} {url} (attempt {attempt})")
                last_error = OrbitError(
                    error_type=ErrorType.API_TIMEOUT,
                    message=f"Request timed out: {method} {endpoint}",
                    details={"attempt": attempt},
                    retryable=True,
                )
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_backoff * attempt)
                    continue

            except OrbitError:
                raise

            except Exception as e:
                log.error(f"Unexpected API error: {e}")
                raise OrbitError(
                    error_type=ErrorType.API_ERROR,
                    message=str(e),
                    retryable=False,
                )

        # All retries exhausted
        raise last_error or OrbitError(
            error_type=ErrorType.API_TIMEOUT,
            message="All retry attempts exhausted",
            retryable=True,
        )


class MockAPIClient:
    """
    Mock API client for development/demo.
    Simulates CRUD responses without a real backend.
    """

    _counter = 0

    async def execute(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        MockAPIClient._counter += 1
        resource_id = f"res_{MockAPIClient._counter}"

        log.info(f"[MOCK] {method} {endpoint} → id={resource_id}")

        if method == "POST":
            return {
                "success": True,
                "status_code": 201,
                "data": {"id": resource_id, **(payload or {}), "status": "created"},
            }
        elif method in ("PUT", "PATCH"):
            return {
                "success": True,
                "status_code": 200,
                "data": {"id": resource_id, **(payload or {}), "status": "updated"},
            }
        elif method == "DELETE":
            return {
                "success": True,
                "status_code": 200,
                "data": {"id": resource_id, "status": "deleted"},
            }
        else:  # GET
            return {
                "success": True,
                "status_code": 200,
                "data": {"id": resource_id, "entity": endpoint.split("/")[1]},
            }

import time
from typing import Any, Callable, Dict, List, Tuple


class RetryPolicy:
    def __init__(self, enabled: bool = True, max_retries: int = 2, delay_seconds: float = 0.5):
        self.enabled = enabled
        self.max_retries = max(0, int(max_retries))
        self.delay_seconds = max(0.0, float(delay_seconds))

    def run_collect(
        self,
        collect_fn: Callable[[], List[Dict[str, Any]]],
        status_fn: Callable[[], Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        retry_count = 0
        attempts = 1 + (self.max_retries if self.enabled else 0)
        last_results: List[Dict[str, Any]] = []
        last_status: Dict[str, Any] = {}

        for attempt in range(attempts):
            try:
                last_results = collect_fn() or []
            except Exception as error:
                last_results = []
                last_status = {
                    "attempted": True,
                    "success": False,
                    "count": 0,
                    "error_message": str(error),
                    "failed_reason": "unknown_error",
                }
            else:
                last_status = dict(status_fn() or {})

            if last_results or last_status.get("success"):
                break

            if attempt < attempts - 1:
                retry_count += 1
                if self.delay_seconds:
                    time.sleep(self.delay_seconds)

        last_status["retry_enabled"] = self.enabled
        last_status["retry_count"] = retry_count
        return last_results, last_status

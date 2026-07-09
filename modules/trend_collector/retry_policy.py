import time
from typing import Any, Callable, Dict, List, Tuple


class RetryPolicy:
    def __init__(
        self,
        enabled: bool = True,
        max_retries: int = 3,
        delay_seconds: float = 0.5,
        backoff_seconds: List[float] = None,
    ):
        self.enabled = enabled
        self.max_retries = max(3, int(max_retries))
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.backoff_seconds = backoff_seconds or [0.5, 1.0, 2.0]

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
                    "error_message": "collector_exception",
                    "failed_reason": "unknown_error",
                    "final_error_type": "unknown_error",
                }
            else:
                last_status = dict(status_fn() or {})

            if last_results or last_status.get("success"):
                break

            if attempt < attempts - 1:
                retry_count += 1
                delay = self._delay_for_retry(retry_count - 1)
                print(
                    "Trend Collector Retry Scheduled: "
                    f"retry_count={retry_count}, "
                    f"final_error_type={last_status.get('failed_reason', 'unknown_error')}, "
                    f"delay_seconds={delay}"
                )
                if delay:
                    time.sleep(delay)

        last_status["retry_enabled"] = self.enabled
        last_status["retry_count"] = retry_count
        last_status["final_error_type"] = last_status.get("failed_reason", "unknown_error")
        return last_results, last_status

    def _delay_for_retry(self, retry_index: int) -> float:
        try:
            return max(0.0, float(self.backoff_seconds[retry_index]))
        except Exception:
            return self.delay_seconds

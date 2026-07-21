"""Bounded local Selenium page subset for Playwright startup fallback only.

The browser subprocess uses the Selenium dependency from the isolated SeleniumBase
runtime.  It always receives an explicit local ChromeDriver path, so Selenium
Manager and runtime downloads are never invoked.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
import queue
import subprocess
import threading
from typing import Any, Callable, Optional


DEFAULT_RPC_TIMEOUT_SECONDS = 20.0
MAX_RPC_TIMEOUT_SECONDS = 30.0

_CHILD_SCRIPT = r"""
import base64
import json
import re
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

driver_path, chrome_path, headless_raw, timeout_raw = sys.argv[1:5]
options = Options()
options.binary_location = chrome_path
if headless_raw == "1":
    options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-background-networking")
service = Service(executable_path=driver_path)
driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(max(1.0, float(timeout_raw) / 1000.0))

def elements(selector):
    match = re.fullmatch(r"([^:]+):has-text\(['\"](.*)['\"]\)", selector)
    if match:
        return [
            item for item in driver.find_elements(By.CSS_SELECTOR, match.group(1))
            if match.group(2) in (item.text or "")
        ]
    return driver.find_elements(By.CSS_SELECTOR, selector)

def element(request):
    found = elements(request["selector"])
    index = int(request.get("index", 0))
    if index < 0 or index >= len(found):
        raise IndexError("locator index outside result set")
    return found[index]

print(json.dumps({"status": "ready"}), flush=True)
for line in sys.stdin:
    request = json.loads(line)
    request_id = request.get("id")
    action = request.get("action")
    try:
        if action == "goto":
            driver.set_page_load_timeout(max(1.0, float(request["timeout_ms"]) / 1000.0))
            driver.get(request["url"])
            result = None
        elif action == "content":
            result = driver.page_source
        elif action == "page_evaluate":
            result = driver.execute_script(request["script"])
        elif action == "page_screenshot":
            result = base64.b64encode(driver.get_screenshot_as_png()).decode("ascii")
        elif action == "locator_count":
            result = len(elements(request["selector"]))
        elif action == "locator_visible":
            result = bool(element(request).is_displayed())
        elif action == "locator_click":
            element(request).click()
            result = None
        elif action == "locator_screenshot":
            result = base64.b64encode(element(request).screenshot_as_png).decode("ascii")
        elif action == "locator_evaluate":
            target = element(request)
            script = "return (" + request["script"] + ")(arguments[0], arguments[1]);"
            result = driver.execute_script(script, target, request.get("argument"))
        elif action == "close":
            driver.quit()
            print(json.dumps({"id": request_id, "status": "ok", "result": None}), flush=True)
            break
        else:
            raise ValueError("unsupported_action:" + str(action))
        print(json.dumps({"id": request_id, "status": "ok", "result": result}), flush=True)
    except Exception as error:
        print(json.dumps({
            "id": request_id,
            "status": "error",
            "error": type(error).__name__ + ":" + str(error),
        }), flush=True)
""".strip()


class _RpcTransport:
    def __init__(
        self,
        command: list[str],
        *,
        process_factory: Callable[..., Any] = subprocess.Popen,
        timeout_seconds: float = DEFAULT_RPC_TIMEOUT_SECONDS,
    ) -> None:
        timeout = float(timeout_seconds)
        if timeout <= 0 or timeout > MAX_RPC_TIMEOUT_SECONDS:
            raise ValueError(
                f"timeout_seconds must be > 0 and <= {MAX_RPC_TIMEOUT_SECONDS:g}"
            )
        self.timeout_seconds = timeout
        self.process = process_factory(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=False,
        )
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("selenium_rpc_pipe_unavailable")
        self._responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self._request_id = 0
        self._closed = False
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        ready = self._next_response()
        if ready.get("status") != "ready":
            self.close(force=True)
            raise RuntimeError("selenium_browser_startup_failed")

    def _read_stdout(self) -> None:
        for line in self.process.stdout:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                self._responses.put(payload)

    def _next_response(self) -> dict[str, Any]:
        try:
            return self._responses.get(timeout=self.timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError("selenium_rpc_timeout") from exc

    def call(self, action: str, **payload: Any) -> Any:
        if self._closed:
            raise RuntimeError("selenium_page_closed")
        self._request_id += 1
        request_id = self._request_id
        request = {"id": request_id, "action": action, **payload}
        self.process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        response = self._next_response()
        if response.get("id") != request_id:
            raise RuntimeError("selenium_rpc_response_mismatch")
        if response.get("status") != "ok":
            raise RuntimeError(str(response.get("error") or "selenium_rpc_failed"))
        return response.get("result")

    def close(self, *, force: bool = False) -> None:
        if self._closed:
            return
        try:
            if not force:
                self.call("close")
        except Exception:
            force = True
        self._closed = True
        if force and self.process.poll() is None:
            self.process.terminate()


class _Locator:
    def __init__(self, page: "SeleniumBasePageAdapter", selector: str, index: int = 0) -> None:
        self.page = page
        self.selector = selector
        self.index = index

    @property
    def first(self) -> "_Locator":
        return _Locator(self.page, self.selector, 0)

    def nth(self, index: int) -> "_Locator":
        return _Locator(self.page, self.selector, max(0, int(index)))

    def count(self) -> int:
        return int(self.page._rpc.call("locator_count", selector=self.selector) or 0)

    def is_visible(self, **_: Any) -> bool:
        return bool(
            self.page._rpc.call(
                "locator_visible", selector=self.selector, index=self.index
            )
        )

    def click(self, **_: Any) -> None:
        self.page._rpc.call("locator_click", selector=self.selector, index=self.index)

    def screenshot(self, **_: Any) -> bytes:
        encoded = self.page._rpc.call(
            "locator_screenshot", selector=self.selector, index=self.index
        )
        return base64.b64decode(str(encoded or ""), validate=True)

    def evaluate(self, script: str, argument: Any = None) -> Any:
        return self.page._rpc.call(
            "locator_evaluate",
            selector=self.selector,
            index=self.index,
            script=str(script),
            argument=argument,
        )


class SeleniumBasePageAdapter:
    """Playwright-like page subset backed by an explicit local driver."""

    def __init__(
        self,
        *,
        runtime: Any,
        chrome_executable: str | Path,
        headless: bool = True,
        navigation_timeout_ms: int = 15_000,
        process_factory: Callable[..., Any] = subprocess.Popen,
        rpc_timeout_seconds: float = DEFAULT_RPC_TIMEOUT_SECONDS,
    ) -> None:
        python = Path(str(getattr(runtime, "python_executable", "") or ""))
        driver = Path(str(getattr(runtime, "driver_path", "") or ""))
        chrome = Path(chrome_executable)
        for label, path in (("python", python), ("driver", driver), ("chrome", chrome)):
            if not path.is_file():
                raise RuntimeError(f"selenium_local_{label}_missing:{path}")
        self.navigation_timeout_ms = max(1_000, int(navigation_timeout_ms))
        command = [
            str(python),
            "-c",
            _CHILD_SCRIPT,
            str(driver),
            str(chrome),
            "1" if headless else "0",
            str(self.navigation_timeout_ms),
        ]
        self._rpc = _RpcTransport(
            command,
            process_factory=process_factory,
            timeout_seconds=rpc_timeout_seconds,
        )

    def set_default_navigation_timeout(self, timeout_ms: int) -> None:
        self.navigation_timeout_ms = max(1_000, int(timeout_ms))

    def goto(self, url: str, **kwargs: Any) -> None:
        timeout_ms = max(
            1_000, int(kwargs.get("timeout") or self.navigation_timeout_ms)
        )
        self._rpc.call("goto", url=str(url), timeout_ms=timeout_ms)

    def content(self) -> str:
        return str(self._rpc.call("content") or "")

    def locator(self, selector: str) -> _Locator:
        return _Locator(self, str(selector))

    def evaluate(self, script: str) -> Any:
        return self._rpc.call("page_evaluate", script=str(script))

    def screenshot(self, **_: Any) -> bytes:
        encoded = self._rpc.call("page_screenshot")
        return base64.b64decode(str(encoded or ""), validate=True)

    def close(self) -> None:
        self._rpc.close()


def create_seleniumbase_page(
    *,
    runtime: Any,
    chrome_executable: str | Path,
    headless: bool = True,
    navigation_timeout_ms: int = 15_000,
    **_: Any,
) -> SeleniumBasePageAdapter:
    return SeleniumBasePageAdapter(
        runtime=runtime,
        chrome_executable=chrome_executable,
        headless=headless,
        navigation_timeout_ms=navigation_timeout_ms,
    )


__all__ = [
    "DEFAULT_RPC_TIMEOUT_SECONDS",
    "MAX_RPC_TIMEOUT_SECONDS",
    "SeleniumBasePageAdapter",
    "create_seleniumbase_page",
]

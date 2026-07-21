"""Bounded, read-only capture of selected public community posts and comments.

Only final-selected Account B URLs from Nate Pann, Bobaedream, and FMKorea are accepted.
The provider never logs in, posts, reacts, replies, or exports browser cookies.
Heavy HTML, JSON, and screenshots are written through the external deep-dive
store; parsing helpers remain deterministic and network-free for inline tests.
"""

from __future__ import annotations

import html
import os
import re
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional
from urllib.parse import urlparse

from modules.source_intake.external_deep_dive_store import write_deep_dive_artifact
from modules.tool_adapters.playwright_runtime import (
    PLAYWRIGHT_EXECUTABLE_ENV,
    resolve_playwright_runtime,
)
from modules.tool_adapters.seleniumbase_runtime import resolve_seleniumbase_runtime
from modules.tool_adapters.seleniumbase_page_adapter import create_seleniumbase_page


SUPPORTED_OPERATIONS = (
    "capture_original_post",
    "collect_real_comments",
    "extract_reconstruction_scene_facts",
)
SUPPORTED_HOSTS = {
    "pann.nate.com": "nate_pann",
    "bobaedream.co.kr": "bobaedream",
    "www.bobaedream.co.kr": "bobaedream",
    "fmkorea.com": "fmkorea",
    "www.fmkorea.com": "fmkorea",
}

DEFAULT_MAX_COMMENTS = 40
DEFAULT_MAX_SCREENSHOTS = 20
DEFAULT_MAX_SCROLLS = 4
DEFAULT_MAX_CLICKS = 3
DEFAULT_NAVIGATION_TIMEOUT_MS = 15_000
DEFAULT_MAX_FACTS = 20
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_PLAYWRIGHT_STARTUP_ERROR_MARKERS = (
    "executable doesn't exist",
    "executable does not exist",
    "browser executable",
    "failed to launch",
    "spawn enoent",
    "winerror 2",
    "no such file or directory",
)


class _PlaywrightStartupFailure(RuntimeError):
    """A classified failure before a Playwright page becomes usable."""

    def __init__(self, classification: str, detail: str) -> None:
        super().__init__(detail)
        self.classification = classification


def _classify_playwright_startup_failure(error: BaseException) -> str:
    if isinstance(error, (ImportError, ModuleNotFoundError)):
        return "playwright_import_unavailable"
    message = str(error or "").casefold()
    if any(marker in message for marker in _PLAYWRIGHT_STARTUP_ERROR_MARKERS):
        return "playwright_launch_unavailable"
    return ""

COMMENT_SELECTOR = (
    "dl.cmt_item, ul.cmt_list > li, ul.comment-list > li, ul.reply-list > li, "
    "div.comment-list li, div.reply-list li, li[data-comment-id], "
    "div[data-comment-id], li.fdb_itm, li[class*='comment'], li[class*='reply']"
)
MORE_COMMENT_SELECTORS = (
    "button:has-text('댓글 더보기')",
    "a:has-text('댓글 더보기')",
    "button:has-text('더보기')",
    "a:has-text('더보기')",
    ".reply_more",
    ".comment-more",
    ".btn_more",
)
AUTHOR_SELECTOR = (
    "[class*='author'], [class*='writer'], [class*='nick'], "
    "[class*='name'], [data-author], [data-nickname]"
)

_COMMENT_MARKERS = ("comment", "reply", "reple", "cmt", "댓글", "답글")
_AUTHOR_MARKERS = ("author", "writer", "nick", "nickname", "name", "member")
_TEXT_MARKERS = ("text", "txt", "content", "comment", "reply", "reple", "cmt")
_POST_MARKERS = (
    "post-content",
    "post_body",
    "post-body",
    "view-content",
    "view_content",
    "viewbody",
    "bodycont",
    "board-view",
    "article-content",
    "posting",
)


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def mask_author(author: Any) -> str:
    """Minimize a public author label without changing comment text."""

    value = _clean_text(author)
    if not value:
        return ""
    if len(value) <= 3:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 3)}{value[-1]}"


@dataclass
class _Node:
    tag: str
    attrs: Dict[str, str] = field(default_factory=dict)
    parent: Optional["_Node"] = None
    children: List["_Node"] = field(default_factory=list)
    chunks: List[str] = field(default_factory=list)

    def text(self) -> str:
        parts: List[str] = list(self.chunks)
        for child in self.children:
            parts.append(child.text())
        return _clean_text(" ".join(parts))

    def marker(self) -> str:
        values = [self.attrs.get("id", ""), self.attrs.get("class", "")]
        values.extend(
            f"{key}={value}"
            for key, value in self.attrs.items()
            if key.startswith("data-")
        )
        return " ".join(values).lower()

    def walk(self) -> Iterator["_Node"]:
        yield self
        for child in self.children:
            yield from child.walk()


class _TreeParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document")
        self.stack = [self.root]
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        node = _Node(
            normalized,
            {str(key).lower(): str(value or "") for key, value in attrs},
            self.stack[-1],
        )
        self.stack[-1].children.append(node)
        if normalized not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: List[tuple]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == normalized:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data:
            self.stack[-1].chunks.append(data)


def _parse_tree(html_text: Any) -> _Node:
    parser = _TreeParser()
    parser.feed(str(html_text or ""))
    parser.close()
    return parser.root


def _contains_marker(node: _Node, markers: Iterable[str]) -> bool:
    marker = node.marker()
    return any(token in marker for token in markers)


def _find_title(root: _Node) -> str:
    for node in root.walk():
        if node.tag == "meta" and node.attrs.get("property", "").lower() == "og:title":
            title = _clean_text(node.attrs.get("content"))
            if title:
                return title
    candidates = []
    for node in root.walk():
        if node.tag in {"h1", "h2"}:
            text = node.text()
            if text:
                priority = 0 if _contains_marker(node, ("title", "subject", "view")) else 1
                candidates.append((priority, -len(text), text))
    return sorted(candidates)[0][2] if candidates else ""


def _comment_nodes(root: _Node) -> List[_Node]:
    # Nate Pann exposes each real top-level comment as ``dl.cmt_item``.  Prefer
    # that exact container before the generic fallback so nested reply controls
    # ("답글쓰기", pagination, search UI) can never displace the comment body.
    nate_items = [
        node
        for node in root.walk()
        if node.tag == "dl" and "cmt_item" in node.marker()
    ]
    if nate_items:
        return nate_items

    fmkorea_items = [
        node
        for node in root.walk()
        if node.tag == "li" and "fdb_itm" in node.marker()
    ]
    if fmkorea_items:
        return fmkorea_items

    candidates = [
        node
        for node in root.walk()
        if node.tag in {"li", "div", "dl", "article", "section"}
        and _contains_marker(node, _COMMENT_MARKERS)
        and len(node.text()) >= 2
    ]
    candidate_ids = {id(node) for node in candidates}
    deepest = []
    for node in candidates:
        if any(id(descendant) in candidate_ids for child in node.children for descendant in child.walk()):
            continue
        author_node = _find_descendant(node, _AUTHOR_MARKERS)
        text_node = _find_descendant(node, _TEXT_MARKERS)
        has_comment_identity = bool(
            author_node
            or node.attrs.get("data-comment-id")
            or node.attrs.get("data-reply-id")
        )
        if has_comment_identity and text_node is not None:
            deepest.append(node)
    return deepest


def _find_descendant(node: _Node, markers: Iterable[str]) -> Optional[_Node]:
    for descendant in node.walk():
        if descendant is node:
            continue
        if _contains_marker(descendant, markers) and descendant.text():
            return descendant
    return None


def _comment_parts(node: _Node) -> tuple[str, str]:
    author_node = _find_descendant(node, _AUTHOR_MARKERS)
    author = author_node.text() if author_node else _clean_text(
        node.attrs.get("data-author") or node.attrs.get("data-nickname")
    )
    text_node = None
    for descendant in node.walk():
        if descendant is node or descendant is author_node:
            continue
        if _contains_marker(descendant, _TEXT_MARKERS) and not _contains_marker(descendant, _AUTHOR_MARKERS):
            candidate = descendant.text()
            if candidate and candidate != author:
                text_node = descendant
                break
    text = text_node.text() if text_node else node.text()
    if author and text.startswith(author):
        text = _clean_text(text[len(author):])
    return author, text


def parse_real_comments_html(
    html_text: Any,
    source_id: str,
    max_comments: int = DEFAULT_MAX_COMMENTS,
) -> List[Dict[str, Any]]:
    """Extract only text visibly present in comment-shaped DOM nodes."""

    if source_id not in {"nate_pann", "bobaedream", "fmkorea"}:
        return []
    bound = max(0, int(max_comments))
    comments: List[Dict[str, Any]] = []
    seen = set()
    for node in _comment_nodes(_parse_tree(html_text)):
        author, text = _comment_parts(node)
        if not text:
            continue
        key = (author, text)
        if key in seen:
            continue
        seen.add(key)
        comments.append(
            {
                "text": text,
                "masked_author": mask_author(author),
                "is_real_comment": True,
                "source_id": source_id,
            }
        )
        if len(comments) >= bound:
            break
    return comments


def _post_node(root: _Node) -> tuple[Optional[_Node], str]:
    candidates = [
        node
        for node in root.walk()
        if node.tag in {"article", "main", "section", "div", "td"}
        and (_contains_marker(node, _POST_MARKERS) or node.tag == "article")
    ]
    if candidates:
        return max(candidates, key=lambda node: len(node.text())), "matched_post_container"
    body = next((node for node in root.walk() if node.tag == "body"), None)
    return body, "generic_body_fallback" if body else "post_container_missing"


def parse_original_post_html(html_text: Any, source_id: str) -> Dict[str, Any]:
    """Return visible title/body only; never infer missing post content."""

    if source_id not in {"nate_pann", "bobaedream", "fmkorea"}:
        return {"title": "", "body_text": "", "diagnostics": ["unsupported_source_id"]}
    root = _parse_tree(html_text)
    node, diagnostic = _post_node(root)
    body = node.text() if node else ""
    return {
        "title": _find_title(root),
        "body_text": body,
        "diagnostics": [] if diagnostic == "matched_post_container" else [diagnostic],
    }


def extract_reconstruction_scene_facts_from_html(
    html_text: Any,
    source_id: str,
    max_facts: int = DEFAULT_MAX_FACTS,
) -> List[Dict[str, Any]]:
    """Return ordered visible post fragments, explicitly marked non-inferred."""

    if source_id not in {"nate_pann", "bobaedream", "fmkorea"}:
        return []
    root = _parse_tree(html_text)
    post, _ = _post_node(root)
    if post is None:
        return []
    fragments = []
    for node in post.walk():
        if node is post or node.tag not in {"p", "li", "blockquote", "dd"}:
            continue
        if _contains_marker(node, _COMMENT_MARKERS):
            continue
        text = node.text()
        if text:
            fragments.append(text)
    if not fragments and post.text():
        fragments = [post.text()]
    unique: List[str] = []
    seen = set()
    for fragment in fragments:
        if fragment in seen:
            continue
        seen.add(fragment)
        unique.append(fragment)
        if len(unique) >= max(0, int(max_facts)):
            break
    return [
        {
            "fact_text": fragment,
            "source_fragment_index": index,
            "is_inferred": False,
            "source_id": source_id,
        }
        for index, fragment in enumerate(unique, start=1)
    ]


def discover_chrome_executable() -> str:
    """Find an installed Google Chrome binary without starting it."""

    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    for candidate in candidates:
        if str(candidate) and candidate.is_file():
            return str(candidate)
    return ""


class CommunityCommentCaptureProvider:
    """Playwright sync provider compatible with ``run_account_deep_discovery``."""

    name = "community_comment_capture_provider"

    def __init__(
        self,
        *,
        headless: bool = True,
        base_dir: Optional[str] = None,
        browser_factory: Optional[Callable[..., Any]] = None,
        page_factory: Optional[Callable[..., Any]] = None,
        artifact_writer: Callable[..., Path] = write_deep_dive_artifact,
        max_comments: int = DEFAULT_MAX_COMMENTS,
        max_screenshots: int = DEFAULT_MAX_SCREENSHOTS,
        max_scrolls: int = DEFAULT_MAX_SCROLLS,
        max_clicks: int = DEFAULT_MAX_CLICKS,
        navigation_timeout_ms: int = DEFAULT_NAVIGATION_TIMEOUT_MS,
        max_facts: int = DEFAULT_MAX_FACTS,
        chrome_executable: Optional[str] = None,
        playwright_runtime_resolver: Callable[..., Any] = resolve_playwright_runtime,
        seleniumbase_runtime_resolver: Callable[..., Any] = resolve_seleniumbase_runtime,
        playwright_factory: Optional[Callable[[], Any]] = None,
        seleniumbase_page_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.headless = bool(headless)
        self.base_dir = base_dir
        self.browser_factory = browser_factory
        self.page_factory = page_factory
        self.artifact_writer = artifact_writer
        self.max_comments = max(0, int(max_comments))
        self.max_screenshots = max(0, int(max_screenshots))
        self.max_scrolls = max(0, int(max_scrolls))
        self.max_clicks = max(0, int(max_clicks))
        self.navigation_timeout_ms = max(1_000, int(navigation_timeout_ms))
        self.max_facts = max(0, int(max_facts))
        self.chrome_executable = chrome_executable or discover_chrome_executable()
        self._explicit_chrome_executable = str(chrome_executable or "").strip()
        self.playwright_runtime_resolver = playwright_runtime_resolver
        self.seleniumbase_runtime_resolver = seleniumbase_runtime_resolver
        self.playwright_factory = playwright_factory
        self.seleniumbase_page_factory = (
            seleniumbase_page_factory or create_seleniumbase_page
        )

    def discover(
        self,
        account: str,
        operation: str,
        request: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if str(account or "").upper() != "B":
            return self._error("unsupported_account", network_used=False)
        if operation not in SUPPORTED_OPERATIONS:
            return self._error("unsupported_operation", network_used=False)
        url, source_id, reason = self._supported_request_url(request)
        if reason:
            return self._error(reason, network_used=False)

        candidate_id = self._safe_component(request.get("candidate_id"), "candidate")
        date_str = self._date_string(request.get("date"))
        storage_source = f"{source_id}--{candidate_id}"
        diagnostics: List[str] = []
        network_used = False

        try:
            with self._page_session(diagnostics) as page:
                network_used = True
                self._navigate(page, url, diagnostics)
                html_text = str(page.content() or "")
                raw_path = self._write(
                    date_str, "raw_html", storage_source, "original_post.html", html_text
                )
                if operation == "capture_original_post":
                    return self._capture_original(
                        page, html_text, source_id, url, date_str, storage_source, raw_path, diagnostics
                    )
                if operation == "collect_real_comments":
                    return self._collect_comments(
                        page, html_text, source_id, url, date_str, storage_source, raw_path, diagnostics
                    )
                return self._reconstruction_facts(
                    html_text, source_id, url, date_str, storage_source, raw_path, diagnostics
                )
        except Exception as error:
            diagnostics.append(f"capture_failed:{type(error).__name__}:{error}")
            return {
                "status": "degraded",
                "error": "capture_failed",
                "network_used": network_used,
                "assets": [],
                "diagnostics": diagnostics,
            }

    def _supported_request_url(
        self, request: Mapping[str, Any]
    ) -> tuple[str, str, str]:
        urls = request.get("source_urls") if isinstance(request, Mapping) else None
        if not isinstance(urls, list):
            urls = []
        unsupported_seen = False
        for value in urls:
            url = str(value or "").strip()
            if not url:
                continue
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme not in {"http", "https"} or host not in SUPPORTED_HOSTS:
                unsupported_seen = True
                continue
            return url, SUPPORTED_HOSTS[host], ""
        return "", "", "unsupported_source_url" if unsupported_seen else "missing_source_url"

    @contextmanager
    def _page_session(self, diagnostics: Optional[List[str]] = None) -> Iterator[Any]:
        runtime_diagnostics = diagnostics if diagnostics is not None else []
        if self.page_factory is not None:
            try:
                page = self.page_factory()
            except TypeError:
                page = self.page_factory(self)
            try:
                yield page
            finally:
                close = getattr(page, "close", None)
                if callable(close):
                    close()
            return

        if self.browser_factory is not None:
            try:
                browser = self.browser_factory(
                    headless=self.headless,
                    executable_path=self.chrome_executable or None,
                )
            except TypeError:
                browser = self.browser_factory()
            context = browser.new_context()
            page = context.new_page()
            try:
                yield page
            finally:
                for item in (page, context, browser):
                    close = getattr(item, "close", None)
                    if callable(close):
                        close()
            return

        try:
            page, context, browser, playwright = self._start_resolved_playwright(
                runtime_diagnostics
            )
        except _PlaywrightStartupFailure as error:
            runtime_diagnostics.append(
                f"playwright_startup_failed:{error.classification}"
            )
            with self._seleniumbase_fallback_session(
                error.classification, runtime_diagnostics
            ) as fallback_page:
                yield fallback_page
            return
        try:
            yield page
        finally:
            self._close_runtime_items(page, context, browser, playwright)

    def _start_resolved_playwright(
        self, diagnostics: List[str]
    ) -> tuple[Any, Any, Any, Any]:
        environment = None
        if self._explicit_chrome_executable:
            environment = {PLAYWRIGHT_EXECUTABLE_ENV: self._explicit_chrome_executable}
        try:
            try:
                runtime = self.playwright_runtime_resolver(env=environment)
            except TypeError:
                runtime = self.playwright_runtime_resolver()
        except Exception as error:
            classification = _classify_playwright_startup_failure(error)
            if classification:
                raise _PlaywrightStartupFailure(classification, str(error)) from error
            raise

        if not bool(getattr(runtime, "ready", False)):
            diagnostics.extend(
                f"playwright_runtime:{item}"
                for item in tuple(getattr(runtime, "diagnostics", ()) or ())
            )
            raise _PlaywrightStartupFailure(
                "playwright_runtime_unavailable",
                "resolved Playwright runtime is not ready",
            )

        executable_path = str(getattr(runtime, "executable_path", "") or "").strip()
        if not executable_path:
            raise _PlaywrightStartupFailure(
                "playwright_runtime_unavailable",
                "resolved Playwright executable path is empty",
            )
        diagnostics.extend(
            [f"playwright_runtime_source:{getattr(runtime, 'source', 'unknown')}"]
        )

        playwright = browser = context = page = None
        try:
            if self.playwright_factory is not None:
                playwright = self.playwright_factory().start()
            else:
                from playwright.sync_api import sync_playwright

                playwright = sync_playwright().start()
            browser = playwright.chromium.launch(
                headless=self.headless,
                executable_path=executable_path,
            )
            context = browser.new_context()
            page = context.new_page()
            diagnostics.append("capture_backend:playwright")
            return page, context, browser, playwright
        except Exception as error:
            self._close_runtime_items(page, context, browser, playwright)
            classification = _classify_playwright_startup_failure(error)
            if classification:
                raise _PlaywrightStartupFailure(classification, str(error)) from error
            raise

    @contextmanager
    def _seleniumbase_fallback_session(
        self, classification: str, diagnostics: List[str]
    ) -> Iterator[Any]:
        # This gate is deliberately narrow: callers cannot select SeleniumBase
        # as the primary backend, and navigation/DOM failures never reach it.
        if classification not in {
            "playwright_import_unavailable",
            "playwright_launch_unavailable",
            "playwright_runtime_unavailable",
        }:
            raise RuntimeError("seleniumbase_fallback_not_approved")
        try:
            runtime = self.seleniumbase_runtime_resolver()
        except Exception as error:
            diagnostics.append(
                f"seleniumbase_runtime_resolution_failed:{type(error).__name__}"
            )
            raise RuntimeError("seleniumbase_runtime_unavailable") from error
        if not bool(getattr(runtime, "ready", False)):
            diagnostics.extend(
                f"seleniumbase_runtime:{item}"
                for item in tuple(getattr(runtime, "diagnostics", ()) or ())
            )
            raise RuntimeError("seleniumbase_runtime_unavailable")
        try:
            page = self.seleniumbase_page_factory(
                runtime=runtime,
                chrome_executable=self.chrome_executable,
                headless=self.headless,
                navigation_timeout_ms=self.navigation_timeout_ms,
                max_clicks=self.max_clicks,
                max_scrolls=self.max_scrolls,
            )
        except TypeError:
            page = self.seleniumbase_page_factory()
        diagnostics.extend(
            [
                f"seleniumbase_fallback_after:{classification}",
                "capture_backend:seleniumbase",
            ]
        )
        try:
            yield page
        finally:
            close = getattr(page, "close", None)
            if callable(close):
                close()

    def _close_runtime_items(self, *items: Any) -> None:
        for item in items:
            if item is None:
                continue
            close = getattr(item, "close", None)
            stop = getattr(item, "stop", None)
            try:
                if callable(close):
                    close()
                elif callable(stop):
                    stop()
            except Exception:
                continue

    def _navigate(self, page: Any, url: str, diagnostics: List[str]) -> None:
        setter = getattr(page, "set_default_navigation_timeout", None)
        if callable(setter):
            setter(self.navigation_timeout_ms)
        page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
        clicks = 0
        for selector in MORE_COMMENT_SELECTORS:
            if clicks >= self.max_clicks:
                break
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=250):
                    locator.click(timeout=750)
                    clicks += 1
            except Exception:
                continue
        scrolls = 0
        for _ in range(self.max_scrolls):
            try:
                page.evaluate("window.scrollBy(0, Math.max(window.innerHeight, 800))")
                scrolls += 1
            except Exception:
                break
        diagnostics.extend([f"bounded_clicks:{clicks}", f"bounded_scrolls:{scrolls}"])

    def _capture_original(
        self,
        page: Any,
        html_text: str,
        source_id: str,
        url: str,
        date_str: str,
        storage_source: str,
        raw_path: Path,
        diagnostics: List[str],
    ) -> Dict[str, Any]:
        parsed = parse_original_post_html(html_text, source_id)
        diagnostics.extend(parsed.get("diagnostics", []))
        screenshot_path = ""
        if self.max_screenshots > 0:
            try:
                image = page.screenshot(full_page=True, type="png")
                screenshot_path = self._path(
                    self._write(date_str, "screenshots", storage_source, "original_post.png", image)
                )
            except Exception as error:
                diagnostics.append(f"original_screenshot_failed:{type(error).__name__}")
        asset = {
            "source_id": source_id,
            "source_url": url,
            "url": url,
            "title": parsed.get("title", ""),
            "body_text": parsed.get("body_text", ""),
            "raw_html_path": self._path(raw_path),
            "path": screenshot_path or self._path(raw_path),
            "screenshot_path": screenshot_path,
            "rights_status": "reference_only",
        }
        return {"status": "ok", "network_used": True, "assets": [asset], "diagnostics": diagnostics}

    def _collect_comments(
        self,
        page: Any,
        html_text: str,
        source_id: str,
        url: str,
        date_str: str,
        storage_source: str,
        raw_path: Path,
        diagnostics: List[str],
    ) -> Dict[str, Any]:
        comments = parse_real_comments_html(html_text, source_id, self.max_comments)
        locator_count = 0
        locator = None
        try:
            locator = page.locator(COMMENT_SELECTOR)
            locator_count = min(int(locator.count()), self.max_comments)
        except Exception:
            diagnostics.append("comment_dom_locator_unavailable")

        screenshot_budget = self.max_screenshots
        for index, comment in enumerate(comments):
            original_path = ""
            masked_path = ""
            mask_attempted = False
            mask_applied = False
            if locator is not None and index < locator_count and screenshot_budget >= 2:
                item = locator.nth(index)
                mask_attempted = True
                try:
                    original_bytes = item.screenshot(type="png")
                    original_path = self._path(
                        self._write(
                            date_str,
                            "screenshots",
                            storage_source,
                            f"comment_{index + 1:03d}_original.png",
                            original_bytes,
                        )
                    )
                    screenshot_budget -= 1
                    self._mask_comment_dom(item, comment.get("masked_author", ""))
                    masked_bytes = item.screenshot(type="png")
                    if (
                        isinstance(masked_bytes, (bytes, bytearray))
                        and bytes(masked_bytes).startswith(PNG_SIGNATURE)
                        and len(masked_bytes) > len(PNG_SIGNATURE)
                    ):
                        if _has_visual_delta(original_bytes, bytes(masked_bytes)):
                            masked_path = self._path(
                                self._write(
                                    date_str,
                                    "screenshots",
                                    storage_source,
                                    f"comment_{index + 1:03d}_masked.png",
                                    masked_bytes,
                                )
                            )
                            screenshot_budget -= 1
                            mask_applied = True
                        else:
                            masked_path = self._path(
                                self._write(
                                    date_str,
                                    "screenshots",
                                    storage_source,
                                    f"comment_{index + 1:03d}_UNMASKED_FAILED.png",
                                    masked_bytes,
                                )
                            )
                            diagnostics.append(
                                f"comment_masked_no_detection:{index + 1}"
                            )
                        screenshot_budget -= 1
                    else:
                        diagnostics.append(
                            f"comment_masked_crop_invalid:{index + 1}"
                        )
                        if not masked_path:
                            masked_path = self._path(
                                self._write(
                                    date_str,
                                    "screenshots",
                                    storage_source,
                                    f"comment_{index + 1:03d}_UNMASKED_FAILED.png",
                                    original_bytes,
                                )
                            )
                            screenshot_budget -= 1
                        screenshot_budget -= 1
                except Exception as error:
                    diagnostics.append(
                        f"comment_screenshot_failed:{index + 1}:{type(error).__name__}"
                    )

            comment.update(
                {
                    "source_url": url,
                    "screenshot_path": masked_path,
                    "original_screenshot_path": original_path,
                    "identity_masked": bool(mask_applied),
                    "crop_missing": not bool(masked_path) or not bool(mask_applied),
                    "comment_slide_eligible": bool(masked_path) and bool(mask_applied),
                    "status": (
                        "invalid"
                        if bool(mask_attempted) and not bool(mask_applied)
                        else "ready"
                    ),
                    "rights_status": "reference_only",
                }
            )

            if not mask_applied and mask_attempted:
                comment["is_real_comment"] = False

        comments_path = self._write(
            date_str,
            "comments",
            storage_source,
            "real_comments.json",
            {
                "source_id": source_id,
                "source_url": url,
                "raw_html_path": self._path(raw_path),
                "comment_count": len(comments),
                "comments": comments,
            },
        )
        diagnostics.extend(
            [
                f"parsed_comments:{len(comments)}",
                f"comment_locators:{locator_count}",
                f"screenshot_limit:{self.max_screenshots}",
            ]
        )
        for comment in comments:
            comment["comments_path"] = self._path(comments_path)
        return {"status": "ok", "network_used": True, "assets": comments, "diagnostics": diagnostics}

    def _mask_comment_dom(self, locator: Any, masked_author: str) -> None:
        locator.evaluate(
            """(node, masked) => {
              const selectors = "[class*='author'],[class*='writer'],[class*='nick'],[class*='name'],[data-author],[data-nickname]";
              for (const el of node.querySelectorAll(selectors)) {
                if (!el.dataset.captureOriginalText) el.dataset.captureOriginalText = el.textContent || '';
                el.textContent = masked || '***';
              }
            }""",
            masked_author or "***",
        )

    def _reconstruction_facts(
        self,
        html_text: str,
        source_id: str,
        url: str,
        date_str: str,
        storage_source: str,
        raw_path: Path,
        diagnostics: List[str],
    ) -> Dict[str, Any]:
        facts = extract_reconstruction_scene_facts_from_html(
            html_text, source_id, self.max_facts
        )
        for fact in facts:
            fact.update(
                {
                    "source_url": url,
                    "raw_html_path": self._path(raw_path),
                    "rights_status": "reference_only",
                }
            )
        facts_path = self._write(
            date_str,
            "raw_html",
            storage_source,
            "reconstruction_scene_facts.json",
            {"source_id": source_id, "source_url": url, "facts": facts},
        )
        for fact in facts:
            fact["facts_path"] = self._path(facts_path)
        diagnostics.append(f"visible_fact_fragments:{len(facts)}")
        return {"status": "ok", "network_used": True, "assets": facts, "diagnostics": diagnostics}

    def _write(
        self,
        date_str: str,
        stage: str,
        source_id: str,
        filename: str,
        payload: Any,
    ) -> Path:
        return self.artifact_writer(
            date_str=date_str,
            stage=stage,
            source_id=source_id,
            filename=filename,
            payload=payload,
            base_dir=self.base_dir,
        )

    def _error(self, reason: str, network_used: bool) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": reason,
            "network_used": bool(network_used),
            "assets": [],
            "diagnostics": [reason],
        }

    def _safe_component(self, value: Any, fallback: str) -> str:
        normalized = re.sub(r"[^0-9A-Za-z._-]+", "_", str(value or "").strip())
        normalized = normalized.strip("._-")[:80]
        return normalized or fallback

    def _date_string(self, value: Any) -> str:
        text = str(value or "").strip()
        return text if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", text) else datetime.now().strftime("%Y-%m-%d")

    def _path(self, value: Path) -> str:
        return str(value).replace("\\", "/")


def _has_visual_delta(before: bytes, after: bytes) -> bool:
    if not before or not after:
        return False
    return hashlib.md5(before).hexdigest() != hashlib.md5(after).hexdigest()


__all__ = [
    "CommunityCommentCaptureProvider",
    "SUPPORTED_OPERATIONS",
    "SUPPORTED_HOSTS",
    "parse_original_post_html",
    "parse_real_comments_html",
    "extract_reconstruction_scene_facts_from_html",
    "mask_author",
    "discover_chrome_executable",
]

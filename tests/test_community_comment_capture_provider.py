"""Focused offline tests for selected community post/comment capture."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from modules.source_intake.community_comment_capture_provider import (
    CommunityCommentCaptureProvider,
    SUPPORTED_OPERATIONS,
    extract_reconstruction_scene_facts_from_html,
    mask_author,
    parse_original_post_html,
    parse_real_comments_html,
)


NATE_HTML = """
<!doctype html>
<html>
  <head><title>친구가 소개팅을 시켜줬는데</title></head>
  <body>
    <div id="contentArea">
      <div class="viewarea">
        <div class="post-content">비가 오던 날 소개팅 장소에 갔습니다.<br>뒤쪽에 친구가 있었습니다.</div>
      </div>
    </div>
    <ul class="cmt_list">
      <li data-comment-id="n1"><span class="name">nate_user123</span><span class="usertxt">첫 댓글 &amp; 원문!</span></li>
      <li data-comment-id="n2"><span class="name">second_writer</span><span class="usertxt">두 번째 댓글도 그대로 유지</span></li>
      <li data-comment-id="n3"><span class="name">third</span><span class="usertxt">세 번째 댓글</span></li>
    </ul>
  </body>
</html>
"""


BOBA_HTML = """
<!doctype html>
<html>
  <head><title>개빡친 소방관 와이프</title></head>
  <body>
    <div class="bodyCont"><div class="article-body">새벽 출동 뒤 가족이 남긴 공개 글입니다.</div></div>
    <ul class="comment-list">
      <li data-comment-id="b1"><span class="writer">road_user77</span><span class="comment-text">가족 마음이 이해됩니다.</span></li>
      <li data-comment-id="b2"><span class="writer">driver_two</span><span class="comment-text">이 문장은 그대로 남아야 해요 &lt;정확히&gt;</span></li>
    </ul>
  </body>
</html>
"""


CHANGED_DOM_HTML = """
<html><head><title>구조 변경</title></head>
<body><section class="unknown-new-layout"><p>알 수 없는 구조</p></section></body></html>
"""


NATE_PRODUCTION_SHAPE_HTML = """
<html><body>
  <div class="cmt_count">개의 댓글 102</div>
  <div class="cmt_search">작성자명 검색</div>
  <div class="cmt_best">
    <dl class="cmt_item f_line">
      <dt class="beple"><span class="nameui">ㅇㅇ</span><i>2026.07.19</i></dt>
      <dd class="opinion">추천 106 반대 20</dd>
      <dd id="beple_content_area_1" class="usertxt"><span>실제 베스트 댓글 본문</span></dd>
      <dd class="reples"><a class="cmtsum">답글 22개</a><a class="cmt_w">답글쓰기</a></dd>
    </dl>
  </div>
  <div class="cmt_paging">1 2 3 4 5</div>
</body></html>
"""


class ExplodingPageFactory:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise AssertionError("unsupported host must be rejected before browser/page creation")


class OfflinePage:
    def __init__(self, html_text):
        self.html_text = html_text
        self.goto_calls = []
        self.closed = False

    def goto(self, url, **kwargs):
        self.goto_calls.append((url, kwargs))

    def content(self):
        return self.html_text

    def locator(self, selector):
        raise RuntimeError("offline fixture has no browser locator")

    def evaluate(self, script):
        return None

    def close(self):
        self.closed = True


class FailingNavigationPage(OfflinePage):
    def goto(self, url, **kwargs):
        raise RuntimeError("navigation timeout after page startup")


class _CommentCropItem:
    def __init__(self):
        self.mask_calls = []
        self.call_count = 0
        self.before = b"\x89PNG\r\n\x1a\nreadable-original"
        self.after = b"\x89PNG\r\n\x1a\nreadable-masked"

    def screenshot(self, **kwargs):
        if self.call_count == 0:
            self.call_count += 1
            return self.before
        self.call_count += 1
        return self.after

    def evaluate(self, script, argument):
        self.mask_calls.append((script, argument))


class _CommentCropLocator:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]


class CommentCropPage(OfflinePage):
    def __init__(self, html_text):
        super().__init__(html_text)
        self.crop_items = [_CommentCropItem()]

    def locator(self, selector):
        return _CommentCropLocator(self.crop_items)


class FakeBrowserContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self):
        return self.page

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, page):
        self.context = FakeBrowserContext(page)
        self.closed = False

    def new_context(self):
        return self.context

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, page=None, launch_error=None):
        self.page = page
        self.launch_error = launch_error
        self.launch_calls = []

    def launch(self, **kwargs):
        self.launch_calls.append(kwargs)
        if self.launch_error is not None:
            raise self.launch_error
        return FakeBrowser(self.page)


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakePlaywrightStarter:
    def __init__(self, playwright):
        self.playwright = playwright

    def start(self):
        return self.playwright


def ready_playwright_runtime(executable=r"F:\runtime\chrome.exe"):
    return SimpleNamespace(
        ready=True,
        executable_path=executable,
        source="test_f_runtime",
        diagnostics=(),
    )


def ready_seleniumbase_runtime():
    return SimpleNamespace(
        ready=True,
        python_executable=r"F:\runtime\seleniumbase\Scripts\python.exe",
        source="test_f_runtime",
        diagnostics=(),
    )


class CommunityCommentCaptureProviderTest(unittest.TestCase):
    def test_fmkorea_real_comment_fixture_is_supported(self):
        html = """
        <html><body>
          <article class="xe_content"><h1 class="title">미용실 다녀온 후</h1><p>본문 장면</p></article>
          <ul class="fdb_lst_ul">
            <li class="fdb_itm"><span class="member_name">닉네임</span><div class="comment-content">표정이 진짜 서운해 보인다</div></li>
          </ul>
        </body></html>
        """
        comments = parse_real_comments_html(html, "fmkorea", max_comments=5)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["text"], "표정이 진짜 서운해 보인다")
        self.assertTrue(comments[0]["is_real_comment"])

    def test_allowlist_rejects_unsupported_host_before_network(self):
        page_factory = ExplodingPageFactory()
        provider = CommunityCommentCaptureProvider(browser_factory=page_factory)
        result = provider.discover(
            "B",
            "collect_real_comments",
            {
                "candidate_id": "B-unsupported",
                "title": "지원하지 않는 주소",
                "source_urls": ["https://example.com/community/1"],
            },
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "unsupported_source_url")
        self.assertFalse(result["network_used"])
        self.assertEqual(result["assets"], [])
        self.assertEqual(page_factory.calls, 0)

    def test_nate_post_and_exact_real_comments_are_dom_extracted(self):
        post = parse_original_post_html(NATE_HTML, "nate_pann")
        comments = parse_real_comments_html(NATE_HTML, "nate_pann", max_comments=10)

        self.assertIn("비가 오던 날 소개팅 장소에 갔습니다.", post["body_text"])
        self.assertEqual(
            [item["text"] for item in comments],
            ["첫 댓글 & 원문!", "두 번째 댓글도 그대로 유지", "세 번째 댓글"],
        )
        self.assertTrue(all(item["is_real_comment"] is True for item in comments))
        self.assertTrue(all(item["masked_author"] for item in comments))
        self.assertNotIn("nate_user123", json.dumps(comments, ensure_ascii=False))
        self.assertNotIn("second_writer", json.dumps(comments, ensure_ascii=False))

    def test_boba_post_and_multiple_comments_preserve_visible_text(self):
        post = parse_original_post_html(BOBA_HTML, "bobaedream")
        comments = parse_real_comments_html(BOBA_HTML, "bobaedream", max_comments=10)

        self.assertIn("새벽 출동 뒤 가족이 남긴 공개 글입니다.", post["body_text"])
        self.assertEqual(
            [item["text"] for item in comments],
            ["가족 마음이 이해됩니다.", "이 문장은 그대로 남아야 해요 <정확히>"],
        )
        self.assertTrue(all(item["is_real_comment"] is True for item in comments))
        self.assertNotIn("road_user77", json.dumps(comments, ensure_ascii=False))
        self.assertNotIn("driver_two", json.dumps(comments, ensure_ascii=False))

    def test_comment_bound_is_enforced_without_synthesizing_comments(self):
        comments = parse_real_comments_html(NATE_HTML, "nate_pann", max_comments=2)
        self.assertEqual(len(comments), 2)
        self.assertEqual([item["text"] for item in comments], ["첫 댓글 & 원문!", "두 번째 댓글도 그대로 유지"])
        self.assertTrue(all(item["is_real_comment"] is True for item in comments))

    def test_nate_production_shape_excludes_comment_ui_controls(self):
        comments = parse_real_comments_html(
            NATE_PRODUCTION_SHAPE_HTML,
            "nate_pann",
            max_comments=5,
        )

        self.assertEqual([item["text"] for item in comments], ["실제 베스트 댓글 본문"])
        serialized = json.dumps(comments, ensure_ascii=False)
        self.assertNotIn("개의 댓글 102", serialized)
        self.assertNotIn("작성자명 검색", serialized)
        self.assertNotIn("답글쓰기", serialized)
        self.assertNotIn("1 2 3 4 5", serialized)

    def test_mask_author_never_returns_the_raw_identity(self):
        for author in ("nate_user123", "road_user77", "가나다라마바사"):
            masked = mask_author(author)
            self.assertTrue(masked)
            self.assertNotEqual(masked, author)
            self.assertNotIn(author, masked)

    def test_empty_or_changed_dom_returns_deterministic_diagnostic(self):
        post = parse_original_post_html(CHANGED_DOM_HTML, "nate_pann")
        comments = parse_real_comments_html(CHANGED_DOM_HTML, "nate_pann", max_comments=5)
        facts = extract_reconstruction_scene_facts_from_html(CHANGED_DOM_HTML, "nate_pann")

        self.assertEqual(post["body_text"], "알 수 없는 구조")
        self.assertTrue(post["diagnostics"])
        self.assertEqual(comments, [])
        self.assertEqual([item["fact_text"] for item in facts], ["알 수 없는 구조"])
        self.assertTrue(all(item["is_inferred"] is False for item in facts))

    def test_reconstruction_facts_are_dom_text_not_inferred(self):
        facts = extract_reconstruction_scene_facts_from_html(NATE_HTML, "nate_pann")
        self.assertTrue(facts)
        self.assertTrue(all(item["is_inferred"] is False for item in facts))
        joined = " ".join(item["fact_text"] for item in facts)
        self.assertIn("비가 오던 날", joined)

    def test_unsupported_account_and_operation_fail_without_network(self):
        page_factory = ExplodingPageFactory()
        provider = CommunityCommentCaptureProvider(browser_factory=page_factory)
        request = {
            "candidate_id": "B-routing",
            "title": "라우팅",
            "source_urls": ["https://pann.nate.com/talk/375521355"],
        }

        wrong_account = provider.discover("A", "collect_real_comments", request)
        wrong_operation = provider.discover("B", "collect_news_images", request)
        self.assertEqual(wrong_account["error"], "unsupported_account")
        self.assertEqual(wrong_operation["error"], "unsupported_operation")
        self.assertFalse(wrong_account["network_used"])
        self.assertFalse(wrong_operation["network_used"])
        self.assertEqual(page_factory.calls, 0)

    def test_supported_operation_names_are_routed_by_contract(self):
        provider = CommunityCommentCaptureProvider(browser_factory=ExplodingPageFactory())
        self.assertEqual(
            SUPPORTED_OPERATIONS,
            (
                "capture_original_post",
                "collect_real_comments",
                "extract_reconstruction_scene_facts",
            ),
        )

    def test_artifact_writer_stays_under_injected_temp_base_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = OfflinePage(NATE_HTML)
            provider = CommunityCommentCaptureProvider(
                page_factory=lambda: page,
                base_dir=temp_dir,
                max_comments=2,
                max_screenshots=0,
                max_scrolls=0,
                max_clicks=0,
            )
            result = provider.discover(
                "B",
                "collect_real_comments",
                {
                    "candidate_id": "B-routing",
                    "date": "2026-07-19",
                    "source_urls": ["https://pann.nate.com/talk/375521355"],
                },
            )
            root = Path(temp_dir).resolve()
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["network_used"])
            self.assertEqual(len(result["assets"]), 2)
            self.assertTrue(page.closed)
            for asset in result["assets"]:
                self.assertTrue(Path(asset["comments_path"]).resolve().is_relative_to(root))
                self.assertTrue(asset["is_real_comment"] is True)
                self.assertTrue(asset["crop_missing"])
                self.assertFalse(asset["comment_slide_eligible"])
            written = [path for path in root.rglob("*") if path.is_file()]
            self.assertTrue(written)
            self.assertTrue(all(path.resolve().is_relative_to(root) for path in written))

    def test_only_readable_masked_comment_crop_is_slide_eligible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = CommentCropPage(NATE_HTML)
            provider = CommunityCommentCaptureProvider(
                page_factory=lambda: page,
                base_dir=temp_dir,
                max_comments=1,
                max_screenshots=2,
                max_scrolls=0,
                max_clicks=0,
            )
            result = provider.discover(
                "B",
                "collect_real_comments",
                {
                    "candidate_id": "B-crop",
                    "date": "2026-07-19",
                    "source_urls": ["https://pann.nate.com/talk/375521355"],
                },
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["assets"]), 1)
            comment = result["assets"][0]
            self.assertFalse(comment["crop_missing"])
            self.assertTrue(comment["comment_slide_eligible"])
            self.assertTrue(Path(comment["screenshot_path"]).is_file())
            self.assertTrue(page.crop_items[0].mask_calls)
            self.assertEqual(comment["identity_masked"], True)
            self.assertEqual(comment["status"], "ready")

    def test_no_visual_delta_comment_marked_as_unmasked_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            no_change_item = _CommentCropItem()
            no_change_item.before = b"\x89PNG\r\n\x1a\nidentical"
            no_change_item.after = b"\x89PNG\r\n\x1a\nidentical"
            page = CommentCropPage(NATE_HTML)
            page.crop_items = [no_change_item]

            provider = CommunityCommentCaptureProvider(
                page_factory=lambda: page,
                base_dir=temp_dir,
                max_comments=1,
                max_screenshots=2,
                max_scrolls=0,
                max_clicks=0,
            )
            result = provider.discover(
                "B",
                "collect_real_comments",
                {
                    "candidate_id": "B-nochange",
                    "date": "2026-07-19",
                    "source_urls": ["https://pann.nate.com/talk/375521355"],
                },
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["assets"]), 1)
            comment = result["assets"][0]
            self.assertFalse(comment["comment_slide_eligible"])
            self.assertFalse(comment["identity_masked"])
            self.assertTrue(comment["is_real_comment"] is False)
            self.assertEqual(comment["status"], "invalid")
            self.assertTrue(comment["screenshot_path"].endswith("_UNMASKED_FAILED.png"))
            self.assertTrue(any(item.startswith("comment_masked_no_detection") for item in result["diagnostics"]))

    def test_default_capture_resolves_f_runtime_and_passes_executable_to_playwright(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = OfflinePage(NATE_HTML)
            chromium = FakeChromium(page=page)
            playwright = FakePlaywright(chromium)
            resolver_calls = []

            def resolver(**kwargs):
                resolver_calls.append(kwargs)
                return ready_playwright_runtime()

            provider = CommunityCommentCaptureProvider(
                base_dir=temp_dir,
                max_screenshots=0,
                max_scrolls=0,
                max_clicks=0,
                playwright_runtime_resolver=resolver,
                playwright_factory=lambda: FakePlaywrightStarter(playwright),
            )
            result = provider.discover(
                "B",
                "collect_real_comments",
                {
                    "candidate_id": "B-runtime",
                    "date": "2026-07-19",
                    "source_urls": ["https://pann.nate.com/talk/1"],
                },
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(resolver_calls), 1)
            self.assertEqual(
                chromium.launch_calls,
                [{"headless": True, "executable_path": r"F:\runtime\chrome.exe"}],
            )
            self.assertIn("capture_backend:playwright", result["diagnostics"])
            self.assertTrue(page.closed)
            self.assertTrue(playwright.stopped)

    def test_seleniumbase_fallback_runs_only_after_classified_playwright_launch_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chromium = FakeChromium(
                launch_error=RuntimeError("Executable doesn't exist at F:\\missing\\chrome.exe")
            )
            playwright = FakePlaywright(chromium)
            fallback_page = OfflinePage(NATE_HTML)
            fallback_calls = []

            def fallback_factory(**kwargs):
                fallback_calls.append(kwargs)
                return fallback_page

            provider = CommunityCommentCaptureProvider(
                base_dir=temp_dir,
                max_screenshots=0,
                max_scrolls=0,
                max_clicks=0,
                playwright_runtime_resolver=lambda **_: ready_playwright_runtime(),
                playwright_factory=lambda: FakePlaywrightStarter(playwright),
                seleniumbase_runtime_resolver=ready_seleniumbase_runtime,
                seleniumbase_page_factory=fallback_factory,
            )
            result = provider.discover(
                "B",
                "collect_real_comments",
                {
                    "candidate_id": "B-fallback",
                    "date": "2026-07-19",
                    "source_urls": ["https://pann.nate.com/talk/2"],
                },
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(fallback_calls), 1)
            self.assertIn(
                "playwright_startup_failed:playwright_launch_unavailable",
                result["diagnostics"],
            )
            self.assertIn(
                "seleniumbase_fallback_after:playwright_launch_unavailable",
                result["diagnostics"],
            )
            self.assertIn("capture_backend:seleniumbase", result["diagnostics"])
            self.assertTrue(fallback_page.closed)

    def test_navigation_failure_does_not_invoke_seleniumbase_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = FailingNavigationPage(NATE_HTML)
            chromium = FakeChromium(page=page)
            fallback_calls = []
            provider = CommunityCommentCaptureProvider(
                base_dir=temp_dir,
                max_screenshots=0,
                max_scrolls=0,
                max_clicks=0,
                playwright_runtime_resolver=lambda **_: ready_playwright_runtime(),
                playwright_factory=lambda: FakePlaywrightStarter(FakePlaywright(chromium)),
                seleniumbase_runtime_resolver=ready_seleniumbase_runtime,
                seleniumbase_page_factory=lambda **kwargs: fallback_calls.append(kwargs),
            )
            result = provider.discover(
                "B",
                "collect_real_comments",
                {
                    "candidate_id": "B-nav-fail",
                    "date": "2026-07-19",
                    "source_urls": ["https://pann.nate.com/talk/3"],
                },
            )

            self.assertEqual(result["status"], "degraded")
            self.assertEqual(result["error"], "capture_failed")
            self.assertEqual(result["assets"], [])
            self.assertEqual(fallback_calls, [])
            self.assertTrue(
                any(item.startswith("capture_failed:RuntimeError:navigation timeout") for item in result["diagnostics"])
            )

    def test_unclassified_playwright_startup_error_does_not_fallback(self):
        chromium = FakeChromium(
            launch_error=RuntimeError("unexpected protocol negotiation failure")
        )
        fallback_calls = []
        provider = CommunityCommentCaptureProvider(
            playwright_runtime_resolver=lambda **_: ready_playwright_runtime(),
            playwright_factory=lambda: FakePlaywrightStarter(FakePlaywright(chromium)),
            seleniumbase_runtime_resolver=ready_seleniumbase_runtime,
            seleniumbase_page_factory=lambda **kwargs: fallback_calls.append(kwargs),
        )
        result = provider.discover(
            "B",
            "collect_real_comments",
            {
                "candidate_id": "B-unclassified",
                "source_urls": ["https://pann.nate.com/talk/4"],
            },
        )

        self.assertEqual(result["assets"], [])
        self.assertEqual(fallback_calls, [])
        self.assertTrue(
            any("unexpected protocol negotiation failure" in item for item in result["diagnostics"])
        )


if __name__ == "__main__":
    unittest.main()

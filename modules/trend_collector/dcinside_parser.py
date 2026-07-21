import html
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class DcinsideParser:
    """Offline parser for DCInside list rows (us-post only)."""

    BASE_URL = "https://gall.dcinside.com"

    def parse_board_list_payload(
        self,
        board_id: str,
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        if not raw_html:
            return []

        records: List[Dict[str, Any]] = []
        rank = 1

        for row in self._extract_us_post_rows(raw_html):
            record = self._parse_row(board_id=board_id, row_html=row, rank=rank)
            if record is None:
                continue
            records.append(record)
            rank += 1

        if records:
            return records

        return self._parse_public_home_best(board_id=board_id, raw_html=raw_html)

    def _parse_public_home_best(
        self,
        board_id: str,
        raw_html: str,
    ) -> List[Dict[str, Any]]:
        """Parse the visible realtime-best links on the public www homepage.

        This surface exposes title, link, optional reply count/category/time only.
        Views and recommendations are deliberately left unavailable.
        """
        records: List[Dict[str, Any]] = []
        anchor_pattern = re.compile(
            r"<a\b([^>]*)>(.*?)</a>",
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in anchor_pattern.finditer(raw_html):
            attrs, body = match.groups()
            classes = self._extract_class_tokens(f"<a {attrs}>")
            href = html.unescape(self._extract_attr(f"<a {attrs}>", "href"))
            section_code = self._extract_attr(f"<a {attrs}>", "section_code")
            if "main_log" not in classes or section_code != "realtime_best_p":
                continue
            if "id=dcbest" not in href or "/board/view/" not in href:
                continue

            title = self._extract_home_best_title(body)
            if not title:
                continue

            category = self._extract_class_text(body, "name")
            posted_at = self._extract_class_text(body, "time")
            comment_text = self._extract_class_text(body, "num")
            post_no_match = re.search(r"(?:[?&]|&amp;)no=(\d+)", href)

            records.append(
                {
                    "source": "dcinside",
                    "board_id": board_id or "dcbest",
                    "post_no": post_no_match.group(1) if post_no_match else "",
                    "post_type": "homepage_realtime_best",
                    "title": title,
                    "origin_board_tag": category or None,
                    "url": self._absolutify_url(href),
                    "posted_at": posted_at,
                    "views": None,
                    "recommends": None,
                    "comments": self._parse_comment_count(comment_text),
                    "rank": len(records) + 1,
                    "collected_at": datetime.now().isoformat(),
                }
            )

        return records

    def _extract_home_best_title(self, html_snippet: str) -> str:
        for class_name, tag_name in (("tit", "strong"), ("besttxt", "div")):
            pattern = re.compile(
                rf"<{tag_name}[^>]*class=[\"'][^\"']*\b{class_name}\b[^\"']*[\"'][^>]*>(.*?)</{tag_name}>",
                flags=re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(html_snippet)
            if not match:
                continue
            candidate = match.group(1)
            if class_name == "besttxt":
                paragraph = re.search(r"<p[^>]*>(.*?)</p>", candidate, flags=re.IGNORECASE | re.DOTALL)
                candidate = paragraph.group(1) if paragraph else candidate
            title = self._clean_text(candidate)
            if title:
                return title
        return ""

    def _extract_class_text(self, html_snippet: str, class_name: str) -> str:
        pattern = re.compile(
            rf"<[^>]+class=[\"'][^\"']*\b{re.escape(class_name)}\b[^\"']*[\"'][^>]*>(.*?)</[^>]+>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(html_snippet)
        return self._clean_text(match.group(1)) if match else ""

    def _extract_us_post_rows(self, raw_html: str) -> List[str]:
        rows = []
        for row_match in re.finditer(
            r"<tr[^>]*?>.*?</tr>",
            raw_html,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            row_html = row_match.group(0)
            if not self._row_has_class(row_html, required={"ub-content", "us-post"}):
                continue
            rows.append(row_html)
        return rows

    def _parse_row(self, board_id: str, row_html: str, rank: int) -> Optional[Dict[str, Any]]:
        row_open_tag = row_html.split(">", 1)[0]
        post_no = self._extract_attr(row_open_tag, "data-no")
        post_type = self._extract_attr(row_open_tag, "data-type")

        if not post_no:
            return None

        title_cell = self._extract_td_cell(row_html, "gall_tit")
        if not title_cell:
            return None

        title_anchor = self._extract_first_anchor(title_cell)
        if not title_anchor:
            return None

        href, title_raw = title_anchor
        origin_board_tag = self._extract_origin_board_tag(title_cell)
        title = self._strip_title_prefix(title_raw, origin_board_tag)
        if not title:
            return None

        posted_at = self._extract_td_attr(row_html, "gall_date", "title")
        if not posted_at:
            return None

        views = self._parse_int(self._clean_text(self._extract_td_cell(row_html, "gall_count") or ""))
        recommends = self._parse_int(self._clean_text(self._extract_td_cell(row_html, "gall_recommend") or ""))
        comments = self._parse_comment_count(
            self._extract_reply_num(self._extract_td_cell(row_html, "gall_tit") or "")
        )

        return {
            "source": "dcinside",
            "board_id": board_id,
            "post_no": post_no,
            "post_type": post_type,
            "title": title,
            "origin_board_tag": origin_board_tag,
            "url": self._absolutify_url(href),
            "posted_at": posted_at,
            "views": views,
            "recommends": recommends,
            "comments": comments,
            "rank": rank,
            "collected_at": datetime.now().isoformat(),
        }

    def _row_has_class(self, row_html: str, required: set[str]) -> bool:
        open_tag = row_html.split(">", 1)[0]
        classes = self._extract_class_tokens(open_tag)
        return required.issubset(classes)

    def _extract_class_tokens(self, tag: str) -> set[str]:
        class_attr = self._extract_attr(tag, "class")
        if not class_attr:
            return set()
        return set(re.split(r"\s+", class_attr.strip().lower()))

    def _extract_attr(self, tag: str, name: str) -> str:
        pattern = re.compile(
            rf"""{re.escape(name)}\s*=\s*["']([^"']+)["']""",
            flags=re.IGNORECASE,
        )
        match = pattern.search(tag)
        return match.group(1).strip() if match else ""

    def _extract_td_cell(self, row_html: str, cell_class: str) -> Optional[str]:
        pattern = re.compile(
            rf"<td[^>]*class=[\"'][^\"']*\b{re.escape(cell_class)}\b[^\"']*[\"'][^>]*>(.*?)</td>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(row_html)
        return match.group(1) if match else None

    def _extract_td_attr(self, row_html: str, cell_class: str, attr_name: str) -> str:
        pattern = re.compile(
            rf"<td[^>]*class=[\"'][^\"']*\b{re.escape(cell_class)}\b[^\"']*[\"'][^>]*\s{re.escape(attr_name)}=[\"']([^\"']+)[\"'][^>]*>.*?</td>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(row_html)
        return match.group(1) if match else ""

    def _extract_first_anchor(self, html_snippet: str) -> Optional[tuple[str, str]]:
        pattern = re.compile(r'<a[^>]*\shref="([^"]+)"[^>]*>(.*?)</a>', flags=re.IGNORECASE | re.DOTALL)
        match = pattern.search(html_snippet)
        if not match:
            return None
        href = html.unescape(match.group(1).strip())
        text = self._clean_text(match.group(2))
        return href, text

    def _extract_origin_board_tag(self, html_snippet: str) -> Optional[str]:
        pattern = re.compile(r"<strong>(.*?)</strong>", flags=re.IGNORECASE | re.DOTALL)
        match = pattern.search(html_snippet)
        if not match:
            return None
        raw = self._clean_text(match.group(1))
        return raw.strip("[]") if raw else None

    def _strip_title_prefix(self, title: str, origin_board_tag: Optional[str]) -> str:
        if not title:
            return ""
        if origin_board_tag and title.startswith(f"[{origin_board_tag}]"):
            title = title[len(origin_board_tag) + 2 :]
        title = re.sub(r"^\s*\[[^\]]+\]\s*", "", title)
        return title.strip()

    def _extract_reply_num(self, html_snippet: str) -> str:
        pattern = re.compile(r"<span[^>]*\sclass=[\"'][^\"']*\breply_num\b[^\"']*[\"'][^>]*>(.*?)</span>")
        match = pattern.search(html_snippet)
        return match.group(1) if match else ""

    def _parse_comment_count(self, text: str) -> int:
        return self._parse_int(self._clean_text(text), default=0, split_voice=True)

    def _parse_int(
        self,
        raw_value: str,
        default: int = 0,
        split_voice: bool = False,
    ) -> int:
        text = self._clean_text(raw_value)
        if not text or text == "-":
            return default
        if split_voice:
            text = text.split("/", 1)[0]
        numeric = re.sub(r"[^\d]", "", text)
        if not numeric:
            return default
        try:
            return int(numeric)
        except ValueError:
            return default

    def _clean_text(self, text: str) -> str:
        text = html.unescape(text or "")
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _absolutify_url(self, href: str) -> str:
        href = href.strip()
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        return href

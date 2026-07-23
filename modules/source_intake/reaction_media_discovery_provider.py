"""Cache-first reaction, meme, and GIF discovery for every content account."""

from __future__ import annotations

import copy
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

from PIL import Image, ImageSequence

from modules.tool_adapters.openclip_runtime import OpenClipRuntime


GIPHY_SEARCH_ENDPOINT = "https://api.giphy.com/v1/gifs/search"
TENOR_SEARCH_ENDPOINT = "https://tenor.googleapis.com/v2/search"
SUPPORTED_SUFFIXES = frozenset({".gif", ".jpeg", ".jpg", ".png", ".webp"})
Transport = Callable[[str, Mapping[str, str], float], str]

_EMOTION_QUERIES = {
    "surprise": ("놀람", "충격", "헉", "반전", "surprise", "shocked reaction"),
    "embarrassment": ("민망", "당황", "어색", "embarrassment", "awkward reaction"),
    "affection": ("사랑", "설렘", "호감", "affection", "soft smile"),
    "suspicion": ("의심", "논란", "수상", "suspicion", "side eye"),
    "anger": ("분노", "화남", "격분", "anger", "angry reaction"),
    "sadness": ("슬픔", "눈물", "이별", "sadness", "teary reaction"),
    "relief": ("안도", "다행", "해결", "relief", "relieved reaction"),
    "laughter": ("웃음", "폭소", "유머", "laughter", "laughing reaction"),
    "confusion": ("혼란", "황당", "무슨", "confusion", "confused reaction"),
    "agreement": ("공감", "맞아", "인정", "agreement", "nodding reaction"),
}


def _transport(url: str, headers: Mapping[str, str], timeout: float) -> str:
    request = urllib.request.Request(url, headers=dict(headers))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _detect_emotion(text: str) -> str:
    lowered = text.casefold()
    for emotion, terms in _EMOTION_QUERIES.items():
        if any(term.casefold() in lowered for term in terms):
            return emotion
    return "agreement"


def _query(request: Mapping[str, Any]) -> tuple[str, str]:
    base = _text(
        request.get("reaction_query")
        or request.get("title")
        or request.get("category")
    )
    emotion = _text(request.get("emotion")) or _detect_emotion(base)
    english = _EMOTION_QUERIES.get(emotion, _EMOTION_QUERIES["agreement"])[-1]
    return _text(f"{base} {english}")[:50], emotion


class ReactionMediaDiscoveryProvider:
    """Discover approved local assets first and API references second.

    GIPHY and Tenor results remain references until their usage rights are
    approved. Local files become renderable only when their sidecar manifest
    contains ``usage_approved: true``.
    """

    name = "reaction_media_discovery_provider"

    def __init__(
        self,
        *,
        library_root: str | Path | None = None,
        transport: Optional[Transport] = None,
        openclip: Any | None = None,
        giphy_api_key: Optional[str] = None,
        tenor_api_key: Optional[str] = None,
        timeout: float = 8.0,
        max_results: int = 6,
        minimum_relevant_score: float = 0.18,
        distractor_margin: float = 0.02,
    ) -> None:
        configured_root = library_root or os.getenv(
            "AI_CONTENT_OS_REACTION_MEDIA_DIR",
            r"F:\AI-Content-OS-Data\reaction_media",
        )
        self.library_root = Path(configured_root)
        self._transport = transport or _transport
        self.openclip = openclip if openclip is not None else OpenClipRuntime()
        self.giphy_api_key = _text(
            giphy_api_key if giphy_api_key is not None else os.getenv("GIPHY_API_KEY")
        )
        self.tenor_api_key = _text(
            tenor_api_key if tenor_api_key is not None else os.getenv("TENOR_API_KEY")
        )
        self.timeout = timeout
        self.max_results = max(1, min(int(max_results), 12))
        self.minimum_relevant_score = float(minimum_relevant_score)
        self.distractor_margin = float(distractor_margin)

    @staticmethod
    def _sidecar(path: Path) -> Dict[str, Any]:
        sidecar = path.with_suffix(f"{path.suffix}.json")
        if not sidecar.is_file():
            sidecar = path.with_suffix(".json")
        if not sidecar.is_file():
            return {}
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return dict(payload) if isinstance(payload, Mapping) else {}

    def _representative_frame(self, path: Path) -> Dict[str, Any]:
        if path.suffix.casefold() != ".gif":
            return {
                "local_path": str(path),
                "media_type": "image",
                "motion_source_path": "",
                "frame_count": 1,
            }
        frame_root = self.library_root / "_representative_frames"
        frame_root.mkdir(parents=True, exist_ok=True)
        destination = frame_root / f"{path.stem}.png"
        with Image.open(path) as image:
            frame_count = max(1, int(getattr(image, "n_frames", 1)))
            frame_index = min(frame_count - 1, frame_count // 2)
            for index, frame in enumerate(ImageSequence.Iterator(image)):
                if index == frame_index:
                    frame.convert("RGBA").save(destination, format="PNG")
                    break
        return {
            "local_path": str(destination),
            "media_type": "gif_representative_frame",
            "motion_source_path": str(path),
            "frame_count": frame_count,
            "representative_frame_index": frame_index,
        }

    def _local(self, query: str, emotion: str) -> List[Dict[str, Any]]:
        if not self.library_root.is_dir():
            return []
        candidates: List[Dict[str, Any]] = []
        for path in self.library_root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in SUPPORTED_SUFFIXES:
                continue
            if "_representative_frames" in path.parts:
                continue
            sidecar = self._sidecar(path)
            keywords = " ".join(
                _text(value)
                for value in (
                    path.stem,
                    sidecar.get("emotion"),
                    sidecar.get("keywords"),
                    sidecar.get("narrative_role"),
                )
            )
            lexical = sum(
                1
                for token in re.findall(r"[0-9A-Za-z가-힣]{2,}", query.casefold())
                if token in keywords.casefold()
            )
            candidates.append(
                {
                    "path": path,
                    "sidecar": sidecar,
                    "lexical_score": lexical,
                }
            )
        candidates.sort(
            key=lambda item: (
                int(item["lexical_score"]),
                item["path"].stat().st_mtime,
            ),
            reverse=True,
        )
        output: List[Dict[str, Any]] = []
        for item in candidates[: self.max_results * 2]:
            path = item["path"]
            sidecar = item["sidecar"]
            frame = self._representative_frame(path)
            approved = sidecar.get("usage_approved") is True
            score = None
            distractor_score = None
            try:
                distractors = [
                    "unrelated celebrity",
                    "generic abstract background",
                    "irrelevant product advertisement",
                ]
                result = self.openclip.score_image_topics(
                    Path(frame["local_path"]),
                    [query, emotion, *distractors],
                    timeout_seconds=30,
                )
                scores = result.get("scores") if isinstance(result, Mapping) else None
                if isinstance(scores, Mapping) and scores:
                    score = max(
                        float(scores.get(label, -1.0))
                        for label in (query, emotion)
                        if label
                    )
                    distractor_score = max(
                        float(scores.get(label, -1.0))
                        for label in distractors
                    )
            except Exception:
                score = None
                distractor_score = None
            clip_relevant = bool(
                score is not None
                and score >= self.minimum_relevant_score
                and (
                    distractor_score is None
                    or score > distractor_score + self.distractor_margin
                )
            )
            output.append(
                {
                    "type": frame["media_type"],
                    "local_path": frame["local_path"],
                    "remote_url": "",
                    "source_url": _text(sidecar.get("source_url"))
                    or path.as_uri(),
                    "title": _text(sidecar.get("title")) or path.stem,
                    "source_provider": "local_reaction_library",
                    "rights_status": _text(sidecar.get("rights_status"))
                    or ("owner_approved" if approved else "unverified"),
                    "usable_in_production": approved,
                    "render_allowed": approved,
                    "topic_relevant": clip_relevant,
                    "attribution_required": bool(sidecar.get("attribution_required")),
                    "publish_authorized": False,
                    "manual_visual_review_required": True,
                    "emotion": _text(sidecar.get("emotion")) or emotion,
                    "narrative_role": _text(sidecar.get("narrative_role"))
                    or "emotional_transition",
                    "lexical_score": item["lexical_score"],
                    "openclip_score": score,
                    "openclip_distractor_score": distractor_score,
                    "openclip_minimum_relevant_score": self.minimum_relevant_score,
                    "openclip_distractor_margin": self.distractor_margin,
                    **{key: value for key, value in frame.items() if key != "local_path"},
                }
            )
        output.sort(
            key=lambda item: (
                item["render_allowed"],
                item["topic_relevant"],
                item["openclip_score"] if item["openclip_score"] is not None else -1.0,
                item["lexical_score"],
            ),
            reverse=True,
        )
        return output[: self.max_results]

    def _api(self, source: str, query: str) -> Dict[str, Any]:
        if source == "giphy":
            if not self.giphy_api_key:
                return {"status": "blocked", "reason_code": "giphy_api_key_missing", "assets": []}
            endpoint = GIPHY_SEARCH_ENDPOINT
            params = {
                "api_key": self.giphy_api_key,
                "q": query,
                "limit": self.max_results,
                "rating": "pg",
                "lang": "ko",
            }
        else:
            if not self.tenor_api_key:
                return {"status": "blocked", "reason_code": "tenor_api_key_missing", "assets": []}
            endpoint = TENOR_SEARCH_ENDPOINT
            params = {
                "key": self.tenor_api_key,
                "q": query,
                "limit": self.max_results,
                "contentfilter": "medium",
                "locale": "ko_KR",
                "media_filter": "gif,tinygif",
            }
        try:
            body = self._transport(
                f"{endpoint}?{urllib.parse.urlencode(params)}",
                {"Accept": "application/json", "User-Agent": "AI-Content-OS/1.0"},
                self.timeout,
            )
            payload = json.loads(body)
        except Exception as error:
            return {
                "status": "fallback",
                "reason_code": f"{source}_request_failed:{type(error).__name__}",
                "assets": [],
            }
        rows = payload.get("data") if source == "giphy" else payload.get("results")
        assets: List[Dict[str, Any]] = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, Mapping):
                continue
            if source == "giphy":
                images = row.get("images") if isinstance(row.get("images"), Mapping) else {}
                rendition = images.get("fixed_height") if isinstance(images.get("fixed_height"), Mapping) else {}
                remote_url = _text(rendition.get("url"))
                source_url = _text(row.get("url"))
            else:
                formats = row.get("media_formats") if isinstance(row.get("media_formats"), Mapping) else {}
                rendition = formats.get("gif") if isinstance(formats.get("gif"), Mapping) else {}
                remote_url = _text(rendition.get("url"))
                source_url = _text(row.get("itemurl"))
            if remote_url and source_url:
                assets.append(
                    {
                        "type": "reaction_gif_reference",
                        "remote_url": remote_url,
                        "source_url": source_url,
                        "title": _text(row.get("title") or row.get("content_description")),
                        "source_provider": source,
                        "rights_status": "platform_reference_only",
                        "reference_only": True,
                        "usable_in_production": False,
                        "render_allowed": False,
                        "topic_relevant": True,
                        "publish_authorized": False,
                        "manual_visual_review_required": True,
                    }
                )
        return {"status": "ok" if assets else "empty", "reason_code": "", "assets": assets}

    def discover(
        self,
        account: str,
        operation: str,
        request: Mapping[str, Any],
    ) -> Dict[str, Any]:
        if operation != "search_reaction_media":
            return {
                "status": "error",
                "error_type": "unsupported_operation",
                "network_used": False,
                "assets": [],
            }
        query, emotion = _query(request)
        local_assets = self._local(query, emotion)
        giphy = self._api("giphy", query)
        tenor = self._api("tenor", query)
        return {
            "status": "ok" if local_assets else "empty",
            "network_used": bool(self.giphy_api_key or self.tenor_api_key),
            "query": query,
            "emotion": emotion,
            "account": _text(account),
            "assets": [*local_assets, *giphy["assets"], *tenor["assets"]],
            "diagnostics": {
                "local_library": "ok" if local_assets else "empty",
                "giphy": giphy.get("reason_code") or giphy.get("status"),
                "tenor": tenor.get("reason_code") or tenor.get("status"),
                "gifer": "blocked_no_supported_official_api",
            },
        }


__all__ = [
    "GIPHY_SEARCH_ENDPOINT",
    "TENOR_SEARCH_ENDPOINT",
    "ReactionMediaDiscoveryProvider",
]

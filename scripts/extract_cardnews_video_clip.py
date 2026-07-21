"""Download a public source video and render a short 4:5 CardNews clip.

This is a manual production helper. It does not publish, upload, or modify the
WorkflowEngine. The source URL and clip timing are recorded beside the output.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import imageio_ffmpeg
import yt_dlp


DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1350


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Public source-video URL")
    parser.add_argument("--start", required=True, help="Clip start, for example 00:01:23.500")
    parser.add_argument("--duration", type=float, required=True, help="Clip length in seconds")
    parser.add_argument("--output", type=Path, required=True, help="Output MP4 path")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    return parser.parse_args()


def download_source(url: str, directory: Path) -> tuple[Path, dict]:
    output_template = str(directory / "source.%(ext)s")
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    options = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]/best",
        "outtmpl": output_template,
        "ffmpeg_location": ffmpeg_path,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }
    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)
        source_path = Path(downloader.prepare_filename(info))

    if not source_path.exists():
        candidates = sorted(directory.glob("source.*"))
        if not candidates:
            raise FileNotFoundError("yt-dlp completed without a downloadable source file")
        source_path = candidates[0]
    return source_path, info


def render_clip(
    source_path: Path,
    output_path: Path,
    start: str,
    duration: float,
    width: int,
    height: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}"
    )
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-y",
        "-ss",
        start,
        "-t",
        str(duration),
        "-i",
        str(source_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def write_manifest(
    output_path: Path,
    info: dict,
    source_url: str,
    start: str,
    duration: float,
    width: int,
    height: int,
) -> Path:
    manifest_path = output_path.with_suffix(".source.json")
    manifest = {
        "schema_version": "cardnews_video_clip_source_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "source_id": info.get("id"),
        "source_title": info.get("title"),
        "source_channel": info.get("channel") or info.get("uploader"),
        "source_channel_url": info.get("channel_url") or info.get("uploader_url"),
        "clip_start": start,
        "clip_duration_seconds": duration,
        "output_file": output_path.name,
        "output_width": width,
        "output_height": height,
        "publish_status": "local_review_only",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    args = parse_args()
    if args.duration <= 0 or args.duration > 30:
        raise ValueError("--duration must be greater than 0 and no more than 30 seconds")
    if args.width <= 0 or args.height <= 0:
        raise ValueError("--width and --height must be positive")

    output_path = args.output.resolve()
    with tempfile.TemporaryDirectory(prefix="cardnews-video-") as temp_dir:
        source_path, info = download_source(args.url, Path(temp_dir))
        render_clip(
            source_path,
            output_path,
            args.start,
            args.duration,
            args.width,
            args.height,
        )
    manifest_path = write_manifest(
        output_path,
        info,
        args.url,
        args.start,
        args.duration,
        args.width,
        args.height,
    )
    print(output_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ShortsModule:
    """Build an offline Shorts production plan from an existing Content result."""

    ROLE_SECONDS = {"hook": 3.0, "problem": 6.0, "solution": 12.0, "cta": 4.0}
    ALLOWED_COPYRIGHT = {
        "owned",
        "licensed",
        "public_domain",
        "official_reuse_allowed",
        "user_supplied_with_permission",
    }

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/shorts")

    def run(
        self,
        content_result: Optional[Dict[str, Any]],
        research_result: Optional[Dict[str, Any]] = None,
        brand_result: Optional[Dict[str, Any]] = None,
        save_results: bool = True,
    ) -> Dict[str, Any]:
        try:
            return self._run(content_result or {}, research_result or {}, brand_result or {}, save_results)
        except Exception as error:
            return {
                "status": "shorts_planning_fallback",
                "fallback_used": True,
                "reason": f"Shorts offline planning failed: {error}",
                "external_calls_attempted": False,
            }

    def _run(self, content: Dict[str, Any], research: Dict[str, Any], brand: Dict[str, Any], save: bool):
        slides = self._valid_slides(content.get("slides"))
        source_missing = not slides
        brief = self._brief(content, research, brand, source_missing)
        script = self._script(slides, source_missing)
        scene_plan = self._scenes(script)
        asset_plan = self._assets(scene_plan)
        captions = self._captions(script)
        audio = self._audio_plan()
        render = self._render_plan(scene_plan, script)
        qa = self._qa(script, asset_plan, captions)
        publish = self._publish_prep(content, qa)

        stages = {
            "shorts_brief_result": brief,
            "shorts_script_result": script,
            "shorts_scene_plan_result": scene_plan,
            "shorts_asset_plan_result": asset_plan,
            "shorts_caption_result": captions,
            "shorts_audio_plan_result": audio,
            "shorts_render_plan_result": render,
            "shorts_qa_result": qa,
            "shorts_publish_prep_result": publish,
        }
        result = {
            "status": "shorts_planning_completed" if not source_missing else "shorts_planning_fallback",
            "fallback_used": source_missing,
            "reason": "" if not source_missing else "No valid Content slides; safe manual plan created.",
            "phase": "phase_1_offline_planning",
            "external_calls_attempted": False,
            **stages,
        }
        if save:
            self._save(stages, result)
        return result

    def _valid_slides(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [slide for slide in value if isinstance(slide, dict) and str(slide.get("body", "")).strip()]

    def _brief(self, content, research, brand, fallback):
        topic = research.get("keyword") or research.get("topic") or content.get("title") or "Untitled"
        meta = content.get("pattern_prompt_meta") if isinstance(content.get("pattern_prompt_meta"), dict) else {}
        return {
            "status": "shorts_brief_created",
            "topic": {"keyword": str(topic), "title": str(content.get("title", topic))},
            "research_summary": str(research.get("summary", "")),
            "key_points": research.get("key_points", []) if isinstance(research.get("key_points"), list) else [],
            "pattern_type": meta.get("pattern_type", "resource"),
            "hook_type": meta.get("hook_type", "attention"),
            "cta_type": meta.get("cta_type", "save"),
            "brand_voice": brand if isinstance(brand, dict) else {},
            "fallback_used": fallback,
            "reason": "Content slides unavailable." if fallback else "",
        }

    def _script(self, slides, fallback):
        lines = []
        elapsed = 0.0
        for index, slide in enumerate(slides, 1):
            role = str(slide.get("role") or "solution")
            text = " ".join(part for part in (str(slide.get("headline", "")).strip(), str(slide.get("body", "")).strip()) if part)
            seconds = self.ROLE_SECONDS.get(role, 6.0)
            lines.append({"line_id": index, "role": role, "text": text, "estimated_seconds": seconds})
            elapsed += seconds
        original_duration = elapsed
        trimmed_line_count = 0
        while len(lines) > 1 and elapsed > 30:
            removed = lines.pop()
            elapsed -= removed["estimated_seconds"]
            trimmed_line_count += 1
        return {
            "status": "shorts_script_created" if lines else "shorts_script_fallback",
            "duration_target_seconds": 30,
            "script_lines": lines,
            "total_estimated_seconds": elapsed,
            "original_duration_seconds": original_duration,
            "trim_required": trimmed_line_count > 0,
            "duration_limit_ok": elapsed <= 30,
            "trimmed_line_count": trimmed_line_count,
            "fallback_used": fallback,
            "reason": "Content slides unavailable." if fallback else "",
        }

    def _scenes(self, script):
        scenes = [
            {
                "scene_id": line["line_id"],
                "script_line_ids": [line["line_id"]],
                "visual_type": "text_over_background",
                "asset_ref": None,
                "duration_seconds": line["estimated_seconds"],
                "transition": "cut",
            }
            for line in script["script_lines"]
        ]
        return {"status": "shorts_scene_plan_created", "scenes": scenes, "scene_count": len(scenes), "fallback_used": not bool(scenes), "reason": "No script lines available." if not scenes else ""}

    def _assets(self, scene_plan):
        assets = [
            {
                "scene_id": scene["scene_id"],
                "asset_type": "background_video",
                "candidate_found": False,
                "topic_relevant": None,
                "copyright_status": "unknown",
                "render_allowed": False,
                "manual_action_required": True,
                "reason": "No automated real-asset source is connected.",
            }
            for scene in scene_plan["scenes"]
        ]
        return {
            "status": "shorts_asset_plan_created",
            "assets": assets,
            "manual_asset_required_count": len(assets),
            "fallback_used": True,
            "reason": "Manual licensed asset sourcing required.",
        }

    def _captions(self, script):
        captions, cursor = [], 0.0
        for line in script["script_lines"]:
            end = cursor + line["estimated_seconds"]
            captions.append({"scene_id": line["line_id"], "start_seconds": cursor, "end_seconds": end, "text": line["text"]})
            cursor = end
        return {"status": "shorts_captions_created" if captions else "shorts_captions_fallback", "caption_source": "script_text_only", "captions": captions, "transcription_used": False, "transcription_provider": None, "fallback_used": not bool(captions), "reason": "No script text available." if not captions else ""}

    def _audio_plan(self):
        return {"status": "shorts_audio_plan_created", "voice_source": "manual_recording_required", "tts_provider": None, "tts_available": False, "music_source": "manual_licensed_track_required", "manual_action_required": True, "fallback_used": True, "reason": "No audio provider connected."}

    def _render_plan(self, scenes, script):
        return {"status": "shorts_render_plan_created", "render_target": "vertical_1080x1920", "scene_count": scenes["scene_count"], "estimated_duration_seconds": script["total_estimated_seconds"], "renderer": "not_selected", "manual_action_required": True, "fallback_used": True, "reason": "No renderer implemented; manual editing required."}

    def _qa(self, script, assets, captions):
        checks = {
            "duration_within_limit": script["duration_limit_ok"],
            "caption_timeline_monotonic": all(item["end_seconds"] >= item["start_seconds"] for item in captions["captions"]),
            "unlicensed_asset_not_used": all(not item["render_allowed"] for item in assets["assets"]),
            "external_calls_absent": True,
            "manual_checklist_complete": False,
        }
        automated_ok = all(value for key, value in checks.items() if key != "manual_checklist_complete")
        return {"status": "shorts_qa_completed", "qa_score": 0.8 if automated_ok else 0.0, "passed": False, "checks": checks, "warnings": ["Manual production checklist is incomplete."], "recommendations": ["Complete manual asset, audio, render, rights, and upload review."]}

    def _publish_prep(self, content, qa):
        checklist = ["Confirm licensed assets", "Record or approve voice", "Attach licensed music", "Verify caption timing", "Watch final render", "Confirm rights and disclosure", "Review account and upload manually"]
        return {"status": "shorts_publish_prep_manual_required", "platform": "instagram_reels", "upload_mode": "manual", "render_file_path": None, "caption": str(content.get("caption", "")), "hashtags": content.get("hashtags", []) if isinstance(content.get("hashtags"), list) else [], "manual_checklist": checklist, "manual_action_required": True, "qa_passed": qa["passed"]}

    def _save(self, stages, final_result):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in stages.items():
            (self.output_dir / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.output_dir / "shorts_result.json").write_text(json.dumps(final_result, ensure_ascii=False, indent=2), encoding="utf-8")

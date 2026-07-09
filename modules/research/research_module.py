import json
from datetime import datetime
from pathlib import Path


class ResearchModule:
    def __init__(self, config=None):
        self.config = config or {}
        self.output_dir = Path("storage/research")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.selected_topic_path = Path("storage/trends/selected_topic.json")
        self.pattern_result_path = Path("storage/pattern/pattern_result.json")

    def run(self, topic_result=None):
        print("Research Module Started")

        topic_result = topic_result or {}
        selected_topic = self._load_selected_topic() or topic_result.get("selected_topic", {})
        pattern_result = self._load_pattern_result()

        keyword = (
            selected_topic.get("title")
            or selected_topic.get("keyword")
            or "AI content automation"
        )
        title = selected_topic.get("title", f"{keyword} card news topic")

        result = {
            "status": "success",
            "message": "research_completed",
            "keyword": keyword,
            "title": title,
            "summary": f"{keyword} is a useful topic for card news, blog, and shorts content automation.",
            "key_points": [
                f"{keyword} can attract beginners interested in practical automation.",
                "It is suitable for a short and clear card news format.",
                "It can connect naturally to Instagram content operations.",
                "It can later expand into blog, shorts, and product-linked content.",
            ],
            "topic_angle": selected_topic.get("angle", ""),
            "target": selected_topic.get("target", ""),
            "source": selected_topic.get("source", "local"),
            "quality_score": selected_topic.get("quality_score"),
            "selection_reason": selected_topic.get("selection_reason", ""),
            "collection_method": selected_topic.get("collection_method", ""),
            "selected_topic_source": (
                "selected_topic_json"
                if selected_topic.get("_loaded_from_selected_topic_json")
                else "topic_result"
            ),
            "topic_intelligence": pattern_result.get("topic_intelligence", {}),
            "pattern_plan": pattern_result.get("pattern_plan", {}),
            "pattern_result_available": bool(pattern_result),
            "created_at": datetime.now().isoformat(),
        }

        self._save_result(result)

        print("Research Module Finished")
        return result

    def _load_selected_topic(self):
        if not self.selected_topic_path.exists():
            return None

        try:
            with open(self.selected_topic_path, "r", encoding="utf-8") as file:
                selected_topic = json.load(file)

            if not isinstance(selected_topic, dict):
                return None

            title = str(selected_topic.get("title", "")).strip()

            if not title:
                return None

            selected_topic["_loaded_from_selected_topic_json"] = True
            return selected_topic

        except Exception as error:
            print(f"Selected Topic Load Failed: {error}")
            return None

    def _load_pattern_result(self):
        if not self.pattern_result_path.exists():
            return {}

        try:
            with open(self.pattern_result_path, "r", encoding="utf-8") as file:
                pattern_result = json.load(file)

            if not isinstance(pattern_result, dict):
                return {}

            return pattern_result

        except Exception as error:
            print(f"Pattern Result Load Failed: {error}")
            return {}

    def _save_result(self, result):
        file_path = self.output_dir / "research_result.json"

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)

        print(f"Research Result Saved: {file_path}")

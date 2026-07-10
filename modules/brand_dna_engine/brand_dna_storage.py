import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class BrandDNAStorage(object):
    """
    Brand DNA Engine - Storage.

    storage/brand_dna/brand_dna.json에 브랜드 프로필 + 누적 사용 통계(선호
    hook/cta/layout/color 빈도)를 저장한다.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("storage/brand_dna")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.dna_path = self.output_dir / "brand_dna.json"
        self.statistics_path = self.output_dir / "brand_dna_statistics.json"

    def load(self) -> Dict[str, Any]:
        return self._load_json(self.dna_path, self._empty_dna())

    def update(self, brand_profile: Dict[str, Any], observation: Dict[str, Any]) -> Dict[str, Any]:
        dna = self.load()

        dna["brand_profile"] = brand_profile
        dna["total_observations"] = int(dna.get("total_observations", 0)) + 1

        for field in ("hook_type", "cta_type", "layout_type", "highlight_color"):
            value = observation.get(field, "")

            if not value:
                continue

            counts = dna.get(f"{field}_frequency", {})
            if not isinstance(counts, dict):
                counts = {}

            counts[value] = int(counts.get(value, 0)) + 1
            dna[f"{field}_frequency"] = counts

        if observation.get("brand_rule_passed"):
            dna["brand_rule_passed_count"] = int(dna.get("brand_rule_passed_count", 0)) + 1
        else:
            dna["brand_rule_violation_count"] = int(dna.get("brand_rule_violation_count", 0)) + 1

        dna["dominant_hook_type"] = self._dominant(dna.get("hook_type_frequency", {}))
        dna["dominant_cta_type"] = self._dominant(dna.get("cta_type_frequency", {}))
        dna["dominant_layout_type"] = self._dominant(dna.get("layout_type_frequency", {}))
        dna["dominant_color"] = self._dominant(dna.get("highlight_color_frequency", {}))

        dna["updated_at"] = datetime.now().isoformat()

        self._save_json(self.dna_path, dna)
        self._save_statistics(dna)

        return dna

    def load_statistics(self) -> Dict[str, Any]:
        return self._load_json(self.statistics_path, self._empty_statistics())

    def _save_statistics(self, dna: Dict[str, Any]) -> None:
        statistics = {
            "updated_at": dna.get("updated_at"),
            "total_observations": dna.get("total_observations", 0),
            "brand_rule_passed_count": dna.get("brand_rule_passed_count", 0),
            "brand_rule_violation_count": dna.get("brand_rule_violation_count", 0),
            "dominant_hook_type": dna.get("dominant_hook_type", ""),
            "dominant_cta_type": dna.get("dominant_cta_type", ""),
            "dominant_layout_type": dna.get("dominant_layout_type", ""),
            "dominant_color": dna.get("dominant_color", ""),
        }

        self._save_json(self.statistics_path, statistics)

    def _empty_statistics(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "total_observations": 0,
            "brand_rule_passed_count": 0,
            "brand_rule_violation_count": 0,
            "dominant_hook_type": "",
            "dominant_cta_type": "",
            "dominant_layout_type": "",
            "dominant_color": "",
        }

    def _dominant(self, counts: Dict[str, int]) -> str:
        if not counts:
            return ""

        return max(counts.items(), key=lambda pair: pair[1])[0]

    def _empty_dna(self) -> Dict[str, Any]:
        return {
            "updated_at": None,
            "brand_profile": {},
            "total_observations": 0,
            "hook_type_frequency": {},
            "cta_type_frequency": {},
            "layout_type_frequency": {},
            "highlight_color_frequency": {},
            "brand_rule_passed_count": 0,
            "brand_rule_violation_count": 0,
            "dominant_hook_type": "",
            "dominant_cta_type": "",
            "dominant_layout_type": "",
            "dominant_color": "",
        }

    def _load_json(self, path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data
        except Exception:
            pass

        return dict(default)

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

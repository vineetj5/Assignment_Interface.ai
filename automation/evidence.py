from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from automation.models import ActionResult, Observation
from automation.redaction import EvidenceSanitizer


class EvidenceStore:
    """Manages disk persistence for run evidence including action logs, observations, and screenshots."""

    def __init__(self, base_dir: Path | str, run_id: str, sanitizer: Optional[EvidenceSanitizer] = None):
        self.run_id = run_id
        self.base_dir = Path(base_dir)
        self.run_dir = self.base_dir / run_id
        self.obs_dir = self.run_dir / "observations"
        self.screenshots_dir = self.run_dir / "screenshots"
        self.errors_dir = self.run_dir / "errors"
        self.actions_file = self.run_dir / "actions.jsonl"
        self.metadata_file = self.run_dir / "metadata.json"
        self.sanitizer = sanitizer or EvidenceSanitizer()

        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.obs_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)

    def write_metadata(self, metadata: Dict[str, Any]) -> None:
        sanitized = self.sanitizer.sanitize_dict(metadata)
        with self.metadata_file.open("w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2)

    def append_action(self, action_result: ActionResult, step: int) -> None:
        sanitized = self.sanitizer.sanitize_dict({
            "run_id": self.run_id,
            "step": step,
            **action_result.model_dump()
        })
        with self.actions_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(sanitized) + "\n")

    def save_observation(self, observation: Observation) -> Path:
        sanitized_obs = self.sanitizer.sanitize_observation(observation)
        filepath = self.obs_dir / f"{observation.observation_id}.json"
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(sanitized_obs.model_dump(), f, indent=2)
        return filepath

    def get_screenshot_path(self, screenshot_id: str) -> Path:
        return self.screenshots_dir / f"{screenshot_id}.png"

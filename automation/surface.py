from __future__ import annotations

import datetime
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
from automation.actions import ActionExecutor
from automation.adapter import SurfaceAdapter
from automation.evidence import EvidenceStore
from automation.exceptions import ActionExecutionError, SurfaceError
from automation.logger import ActionLogger
from automation.models import (
    ActionRequest,
    ActionResult,
    ActionType,
    Observation,
    SessionState,
    TargetSpec,
)
from automation.observer import SurfaceObserver
from automation.redaction import EvidenceSanitizer
from automation.session import SessionManager


class PlaywrightSurface(SurfaceAdapter):
    """Concrete implementation of SurfaceAdapter using Playwright."""

    def __init__(
        self,
        headless: bool = True,
        evidence_dir: Optional[Union[Path, str]] = None,
        run_id: Optional[str] = None,
        slow_mo: Optional[float] = None,
        sanitizer: Optional[EvidenceSanitizer] = None,
    ):
        self.run_id = run_id or f"run_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.evidence_dir = Path(evidence_dir or (Path.cwd() / "evidence"))
        self.sanitizer = sanitizer or EvidenceSanitizer()
        self.evidence_store = EvidenceStore(
            base_dir=self.evidence_dir,
            run_id=self.run_id,
            sanitizer=self.sanitizer,
        )

        self.session_manager = SessionManager(
            headless=headless,
            slow_mo=slow_mo,
            session_id=self.run_id,
        )
        self.observer = SurfaceObserver(evidence_store=self.evidence_store)
        self.action_executor = ActionExecutor()
        self.action_logger = ActionLogger(evidence_store=self.evidence_store)

        self.last_observation: Optional[Observation] = None

        # Write run metadata
        self.evidence_store.write_metadata({
            "run_id": self.run_id,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "headless": headless,
        })

    def get_session_state(self) -> SessionState:
        return self.session_manager.state

    async def open(self, target: str) -> None:
        """Launch session if needed and navigate to the target URL."""
        page = await self.session_manager.start()
        await page.goto(target, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("load", timeout=3000)
        except Exception:
            pass
        await page.wait_for_timeout(200)

    async def observe(self, capture_screenshot: bool = True) -> Observation:
        """Capture the current state of the page and frames."""
        self.session_manager.assert_action_permitted()
        obs = await self.observer.observe(self.session_manager.page, capture_screenshot=capture_screenshot)
        self.last_observation = obs
        return obs

    async def execute(self, action: ActionRequest) -> ActionResult:
        """Execute a typed action, logging before/after state and duration."""
        self.session_manager.assert_action_permitted()
        action_id = self.action_logger.start_action(action)
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        start_time = time.perf_counter()

        before_obs_ref = self.last_observation.observation_id if self.last_observation else None
        output = None
        error_msg = None
        status = "success"
        screenshot_ref = None

        try:
            output = await self.action_executor.execute(
                page=self.session_manager.page,
                request=action,
                last_obs=self.last_observation,
            )
        except Exception as e:
            status = "failed"
            error_msg = f"{type(e).__name__}: {str(e)}"

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Capture post-action observation
        after_obs_ref = None
        try:
            after_obs = await self.observe(capture_screenshot=True)
            after_obs_ref = after_obs.observation_id
            screenshot_ref = after_obs.screenshot_ref
        except Exception:
            pass

        result = self.action_logger.record_action(
            action_id=action_id,
            action_type=action.action_type,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            output=output,
            error=error_msg,
            before_observation_ref=before_obs_ref,
            after_observation_ref=after_obs_ref,
            screenshot_ref=screenshot_ref,
        )

        if status == "failed":
            raise ActionExecutionError(error_msg or "Action execution failed")

        return result

    async def screenshot(self, name: Optional[str] = None) -> str:
        """Capture standalone screenshot."""
        self.session_manager.assert_action_permitted()
        screenshot_id = name or f"manual_{int(time.time()*1000)}"
        screenshot_path = self.evidence_store.get_screenshot_path(screenshot_id)
        await self.session_manager.page.screenshot(path=str(screenshot_path), full_page=True)
        return f"screenshots/{screenshot_id}.png"

    async def pause(self) -> None:
        await self.session_manager.pause()

    async def resume(self) -> None:
        await self.session_manager.resume()

    async def cede_control(self) -> None:
        await self.session_manager.cede_control()

    async def reclaim_control(self) -> None:
        await self.session_manager.reclaim_control()

    async def close(self) -> None:
        await self.session_manager.close()

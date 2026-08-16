from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union
from playwright.async_api import Frame, Locator, Page
from automation.exceptions import ActionExecutionError, ConditionTimeoutError, ElementNotFoundError
from automation.models import (
    ActionRequest,
    ActionType,
    InteractiveElement,
    Observation,
    TargetSpec,
)


class ActionExecutor:
    """Executes constrained action primitives against Playwright pages and nested frames."""

    def __init__(self):
        pass

    def _parse_target(self, target: Optional[Union[str, TargetSpec, Dict[str, Any]]]) -> TargetSpec:
        if target is None:
            return TargetSpec()
        if isinstance(target, str):
            # If target is observation ID like "e_01"
            if target.startswith("e_") and target[2:].isdigit():
                return TargetSpec(observation_id=target)
            # Otherwise treat as CSS or text
            if any(c in target for c in ["[", "]", ">", ".", "#", "=", ":"]):
                return TargetSpec(css=target)
            return TargetSpec(text=target)
        if isinstance(target, TargetSpec):
            return target
        if isinstance(target, dict):
            return TargetSpec(**target)
        return TargetSpec()

    def _find_frame(self, page: Page, frame_path: List[str]) -> Frame:
        """Find a frame by its path sequence or leaf frame name."""
        if not frame_path:
            return page.main_frame

        # 1. Try matching the exact leaf frame name if present in page.frames
        leaf_name = frame_path[-1]
        for f in page.frames:
            if f.name == leaf_name:
                return f

        # 2. Try hierarchical traversal
        curr = page.main_frame
        for name in frame_path:
            matched = False
            for child in curr.child_frames:
                if child.name == name:
                    curr = child
                    matched = True
                    break
                elif name.startswith("frame_"):
                    try:
                        idx = int(name.split("_")[1])
                        if idx < len(curr.child_frames):
                            curr = curr.child_frames[idx]
                            matched = True
                            break
                    except (ValueError, IndexError):
                        pass
            if not matched:
                for child in curr.child_frames:
                    if name in child.url:
                        curr = child
                        matched = True
                        break
        return curr

    async def _resolve_locator(
        self,
        page: Page,
        spec: TargetSpec,
        last_obs: Optional[Observation] = None,
        timeout_ms: int = 5000,
    ) -> Locator:
        """Resolve a TargetSpec into a Playwright Locator with frame awareness and multi-signal fallbacks."""
        frame_path = spec.frame_path
        target_el: Optional[InteractiveElement] = None

        # 1. If observation_id is given, pull element details from the last observation
        if spec.observation_id and last_obs:
            target_el = last_obs.get_element(spec.observation_id)
            if target_el:
                if not frame_path:
                    frame_path = target_el.frame_path

        # Resolve the search frames: prioritize target frame, then leaf frames, then all frames
        target_frame = self._find_frame(page, frame_path) if frame_path else None
        if target_frame:
            search_frames = [target_frame] + [f for f in page.frames if f != target_frame]
        else:
            # Search deepest frames first (where actual content resides in nested iframes)
            search_frames = sorted(page.frames, key=lambda f: len(f.child_frames))

        # Try resolving across search frames
        for f in search_frames:
            # A) By CSS selector if explicitly provided
            if spec.css:
                try:
                    loc = f.locator(spec.css)
                    if await loc.count() > 0:
                        return loc.first
                except Exception:
                    pass

            # B) By observation_id metadata if available
            if target_el:
                attrs = target_el.attributes
                if "name" in attrs:
                    loc = f.locator(f'{target_el.tag}[name="{attrs["name"]}"]')
                    if await loc.count() > 0:
                        return loc.first
                if "id" in attrs:
                    loc = f.locator(f"#{attrs['id']}")
                    if await loc.count() > 0:
                        return loc.first
                if target_el.tag == "input" and attrs.get("value"):
                    loc = f.locator(f'input[value="{attrs["value"]}"]')
                    if await loc.count() > 0:
                        return loc.first
                if target_el.role and target_el.name:
                    try:
                        loc = f.get_by_role(target_el.role, name=target_el.name)
                        if await loc.count() > 0:
                            return loc.first
                    except Exception:
                        pass
                if target_el.text:
                    try:
                        loc = f.get_by_text(target_el.text, exact=False)
                        if await loc.count() > 0:
                            return loc.first
                    except Exception:
                        pass

            # C) By Name / attribute / label / text
            if spec.name:
                # 1. Exact name or id attribute
                loc = f.locator(f'[name="{spec.name}"], #{spec.name}')
                if await loc.count() > 0:
                    return loc.first
                # 2. Input/button with matching value/text
                loc = f.locator(f'input[value="{spec.name}"], button:has-text("{spec.name}"), a:has-text("{spec.name}")')
                if await loc.count() > 0:
                    return loc.first
                # 3. get_by_label
                try:
                    loc = f.get_by_label(spec.name)
                    if await loc.count() > 0:
                        return loc.first
                except Exception:
                    pass
                # 4. get_by_placeholder
                try:
                    loc = f.get_by_placeholder(spec.name)
                    if await loc.count() > 0:
                        return loc.first
                except Exception:
                    pass
                # 5. Role + Name
                if spec.role:
                    try:
                        loc = f.get_by_role(spec.role, name=spec.name)
                        if await loc.count() > 0:
                            return loc.first
                    except Exception:
                        pass
                # 6. get_by_text
                try:
                    loc = f.get_by_text(spec.name, exact=False)
                    if await loc.count() > 0:
                        return loc.first
                except Exception:
                    pass

            # D) By Text
            if spec.text:
                try:
                    loc = f.get_by_text(spec.text, exact=False)
                    if await loc.count() > 0:
                        return loc.first
                except Exception:
                    pass

            # E) By attributes
            if spec.attributes:
                for k, v in spec.attributes.items():
                    tag_prefix = spec.tag or ""
                    loc = f.locator(f'{tag_prefix}[{k}="{v}"]')
                    if await loc.count() > 0:
                        return loc.first

        raise ElementNotFoundError(f"Could not resolve target element for spec: {spec}")

    async def execute(
        self,
        page: Page,
        request: ActionRequest,
        last_obs: Optional[Observation] = None,
    ) -> Any:
        spec = self._parse_target(request.target)
        timeout = request.timeout_ms

        if request.action_type == ActionType.NAVIGATE:
            url = request.value or (spec.text if spec else None)
            if not url:
                raise ActionExecutionError("Navigate action requires a target URL in request.value")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return {"url": page.url}

        elif request.action_type == ActionType.CLICK:
            loc = await self._resolve_locator(page, spec, last_obs, timeout_ms=timeout)
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.click(timeout=timeout)
            # Brief pause for navigation or DOM updates
            await page.wait_for_timeout(100)
            return {"clicked": True}

        elif request.action_type == ActionType.FILL:
            if request.value is None:
                raise ActionExecutionError("Fill action requires a string value in request.value")
            loc = await self._resolve_locator(page, spec, last_obs, timeout_ms=timeout)
            await loc.wait_for(state="visible", timeout=timeout)
            await loc.fill(str(request.value), timeout=timeout)

            # Verification checkpoint after fill
            try:
                actual_val = await loc.input_value(timeout=1000)
                if actual_val != str(request.value):
                    raise ActionExecutionError(
                        f"Fill verification failed: expected '{request.value}', but input field contains '{actual_val}'"
                    )
            except Exception as e:
                if isinstance(e, ActionExecutionError):
                    raise
                # Non-input elements might not support input_value
                pass

            return {"filled": request.value, "verified": True}

        elif request.action_type == ActionType.SELECT:
            if request.value is None:
                raise ActionExecutionError("Select action requires a value in request.value")
            loc = await self._resolve_locator(page, spec, last_obs, timeout_ms=timeout)
            await loc.wait_for(state="visible", timeout=timeout)
            try:
                selected = await loc.select_option(value=request.value, timeout=timeout)
            except Exception:
                selected = await loc.select_option(label=request.value, timeout=timeout)
            return {"selected": selected}

        elif request.action_type == ActionType.EXTRACT:
            loc = await self._resolve_locator(page, spec, last_obs, timeout_ms=timeout)
            await loc.wait_for(state="visible", timeout=timeout)
            text = await loc.inner_text(timeout=timeout)
            val = await loc.input_value(timeout=1000) if await loc.evaluate("el => 'value' in el") else None
            return {"text": text.strip(), "value": val}

        elif request.action_type == ActionType.WAIT:
            condition = request.condition or "visible"
            if condition in ["networkidle", "domcontentloaded", "load"]:
                await page.wait_for_load_state(condition, timeout=timeout)
                return {"waited_for": condition}
            if request.value and request.value.isdigit():
                ms = int(request.value)
                await page.wait_for_timeout(ms)
                return {"slept_ms": ms}

            if spec.observation_id or spec.name or spec.text or spec.css or spec.role:
                loc = await self._resolve_locator(page, spec, last_obs, timeout_ms=timeout)
                state = "hidden" if condition == "hidden" else "visible"
                await loc.wait_for(state=state, timeout=timeout)
                return {"waited_for_element": state}

            # Default wait
            await page.wait_for_timeout(500)
            return {"waited": True}

        elif request.action_type == ActionType.SCREENSHOT:
            return {"screenshot": True}

        else:
            raise ActionExecutionError(f"Unsupported action type: {request.action_type}")

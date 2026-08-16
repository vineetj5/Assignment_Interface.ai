"""Target resolver for Phase 5 Deterministic Replay Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from capability.models import LocatorStrategy, TargetSpec as ArtifactTargetSpec
from automation.models import TargetSpec as SurfaceTargetSpec
from replay.binder import ValueBinder
from replay.exceptions import ReplayTargetResolutionError


class TargetResolver:
    """Translates artifact TargetSpecs into Phase 2 SurfaceTargetSpecs at runtime."""

    def __init__(self, binder: Optional[ValueBinder] = None):
        self.binder = binder or ValueBinder()

    def resolve(
        self,
        artifact_target: Optional[ArtifactTargetSpec],
        runtime_inputs: Dict[str, Any],
        step_outputs: Optional[Dict[str, Any]] = None,
    ) -> Optional[SurfaceTargetSpec]:
        """Convert artifact TargetSpec to SurfaceTargetSpec with bound parameters."""
        if not artifact_target:
            return None

        frame_path_strs: List[str] = [
            ft.name for ft in artifact_target.frame_path if ft.name
        ]

        primary = artifact_target.primary
        surface_target = self._strategy_to_surface_target(
            strategy=primary,
            frame_path=frame_path_strs,
            runtime_inputs=runtime_inputs,
            step_outputs=step_outputs,
        )

        return surface_target

    def _strategy_to_surface_target(
        self,
        strategy: LocatorStrategy,
        frame_path: List[str],
        runtime_inputs: Dict[str, Any],
        step_outputs: Optional[Dict[str, Any]] = None,
    ) -> SurfaceTargetSpec:
        strat_type = strategy.strategy

        if strat_type == "table_row_action":
            table_name = strategy.table or "SHARE / DRAFT ACCOUNTS"
            row_match = strategy.row_match or {}
            val_source_dict = row_match.get("value") or {}

            # Resolve bound value source for row match (e.g. SAV or DDA)
            from capability.models import ValueSource
            vs = ValueSource(**val_source_dict) if isinstance(val_source_dict, dict) else val_source_dict
            bound_row_val = self.binder.resolve(vs, runtime_inputs, step_outputs)

            action_ctrl = strategy.action_control or {"name": "View"}
            action_name = action_ctrl.get("name", "View")

            # Construct Playwright CSS for table row link matching account type
            # CSS selector matching row with text bound_row_val and link with action_name
            css = f"tr:has-text('{bound_row_val}') a:has-text('{action_name}')"

            return SurfaceTargetSpec(
                css=css,
                frame_path=frame_path,
            )

        elif strat_type == "field_by_label":
            label = strategy.label or "Current Balance"
            return SurfaceTargetSpec(
                css=f".balance-value, [aria-label='{label}'], label:has-text('{label}') + *",
                text=label,
                frame_path=frame_path,
            )

        elif strat_type == "role_name":
            role_val = strategy.role or ""
            name_val = strategy.name or ""
            # For textbox roles, generate a CSS selector that targets the actual input element
            # rather than relying on accessible name matching which varies across legacy apps.
            if role_val == "textbox":
                # Use label proximity: find the input inside a table cell adjacent to the label text
                css = f"input[type='text'], input:not([type]), textarea"
                return SurfaceTargetSpec(
                    css=css,
                    role=role_val,
                    name=name_val,
                    frame_path=frame_path,
                )
            # For buttons, use get_by_role semantics via name
            return SurfaceTargetSpec(
                role=strategy.role,
                name=strategy.name,
                frame_path=frame_path,
            )

        elif strat_type == "label":
            return SurfaceTargetSpec(
                name=strategy.label or strategy.name,
                frame_path=frame_path,
            )

        elif strat_type == "attributes":
            attrs = strategy.attributes or {}
            tag = strategy.tag or ""
            if "name" in attrs:
                return SurfaceTargetSpec(name=attrs["name"], frame_path=frame_path)
            if "id" in attrs:
                return SurfaceTargetSpec(css=f"#{attrs['id']}", frame_path=frame_path)
            css = "".join(f'[{k}="{v}"]' for k, v in attrs.items())
            return SurfaceTargetSpec(css=f"{tag}{css}", frame_path=frame_path)

        elif strat_type == "css":
            return SurfaceTargetSpec(css=strategy.css, frame_path=frame_path)

        elif strat_type == "text":
            return SurfaceTargetSpec(text=strategy.name or strategy.label, frame_path=frame_path)

        # Fallback default
        return SurfaceTargetSpec(
            role=strategy.role,
            name=strategy.name,
            frame_path=frame_path,
        )

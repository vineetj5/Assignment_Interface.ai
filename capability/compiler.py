"""Artifact compiler for Phase 4 Capability Artifact Schema.

Orchestrates trace normalization, parameterization, target compilation, checkpoint insertion,
sanitization, validation, persistence, and registry updates.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from capability.bindings import (
    LOOKUP_BALANCE_ENTRYPOINT,
    LOOKUP_BALANCE_IDENTITY,
    LOOKUP_BALANCE_INPUTS,
    LOOKUP_BALANCE_OUTPUTS,
    LOOKUP_BALANCE_SAFETY,
)
from capability.checkpoint_compiler import CheckpointCompiler
from capability.exceptions import ArtifactCompilationError
from capability.models import (
    ArtifactActionType,
    CapabilityArtifact,
    CapabilityIdentity,
    CapabilityStep,
    CompatibilitySpec,
    EntryPointSpec,
    InputSpec,
    OutputSpec,
    ProvenanceSpec,
    SafetySpec,
)
from capability.normalizer import TraceNormalizer
from capability.parameterizer import Parameterizer
from capability.registry import CapabilityRegistry
from capability.repository import ArtifactRepository
from capability.sanitizer import ArtifactSanitizer
from capability.target_compiler import TargetCompiler
from capability.validator import ArtifactValidator


class ArtifactCompiler:
    """Compiles a successful Phase 3 discovery run into a typed, versioned, reusable CapabilityArtifact."""

    def __init__(
        self,
        repository: Optional[ArtifactRepository] = None,
        registry: Optional[CapabilityRegistry] = None,
    ):
        self.repository = repository or ArtifactRepository()
        self.registry = registry or CapabilityRegistry()
        self.normalizer = TraceNormalizer()
        self.target_compiler = TargetCompiler()
        self.checkpoint_compiler = CheckpointCompiler()
        self.sanitizer = ArtifactSanitizer()
        self.validator = ArtifactValidator()

    def compile(
        self,
        discovery_run: Dict[str, Any],
        capability_name: str = "lookup_balance",
        version: str = "1.0.0",
        inputs: Optional[List[InputSpec]] = None,
        outputs: Optional[List[OutputSpec]] = None,
        entrypoint: Optional[EntryPointSpec] = None,
        safety: Optional[SafetySpec] = None,
        compatibility: Optional[CompatibilitySpec] = None,
    ) -> CapabilityArtifact:
        """Compile a discovery run dict into a validated and sanitized CapabilityArtifact."""
        # 1. Normalize discovery trace
        normalized_steps = self.normalizer.normalize(discovery_run)

        # 2. Setup parameterizer with inputs
        resolved_inputs = inputs or LOOKUP_BALANCE_INPUTS
        resolved_outputs = outputs or LOOKUP_BALANCE_OUTPUTS
        parameterizer = Parameterizer(resolved_inputs)

        # 3. Build CapabilitySteps with durable targets, parameter values, waits, and checkpoints
        account_map_vs = parameterizer.parameterize_account_mapping("account_type")
        compiled_steps: List[CapabilityStep] = []
        known_discovery_values: List[str] = []

        for idx, norm_step in enumerate(normalized_steps, start=1):
            action_str = norm_step["action"]
            action_type = ArtifactActionType(action_str)
            resolved_target = norm_step.get("resolved_target") or {}
            raw_value = norm_step.get("value")

            if raw_value:
                known_discovery_values.append(str(raw_value))

            target_name = resolved_target.get("name")
            step_id: str

            # Step classification & assignment
            if action_type == ArtifactActionType.FILL:
                step_id = "enter_member_id"
                param_value = parameterizer.parameterize_fill_value(
                    step_action=action_str,
                    target_name=target_name,
                    concrete_value=raw_value,
                )
                target_spec = self.target_compiler.compile_target(
                    resolved_target=resolved_target,
                    action=action_str,
                    step_index=idx,
                )
                postconditions = self.checkpoint_compiler.build_fill_postcondition("member_id")
                compiled_steps.append(
                    CapabilityStep(
                        id=step_id,
                        action=action_type,
                        target=target_spec,
                        value=param_value,
                        postconditions=postconditions,
                    )
                )

            elif action_type == ArtifactActionType.CLICK:
                if target_name == "Find Member" or "Find" in str(target_name) or idx == 2:
                    step_id = "search_member"
                    target_spec = self.target_compiler.compile_target(
                        resolved_target=resolved_target,
                        action=action_str,
                        step_index=idx,
                    )
                    wait_after = self.checkpoint_compiler.build_search_wait()
                    postconditions = [self.checkpoint_compiler.build_member_identity_checkpoint("member_id")]
                    compiled_steps.append(
                        CapabilityStep(
                            id=step_id,
                            action=action_type,
                            target=target_spec,
                            wait_after=wait_after,
                            postconditions=postconditions,
                        )
                    )
                else:
                    step_id = "open_account"
                    target_spec = self.target_compiler.compile_target(
                        resolved_target=resolved_target,
                        action=action_str,
                        step_index=idx,
                        account_type_value_source=account_map_vs,
                    )
                    wait_after = self.checkpoint_compiler.build_account_wait()
                    compiled_steps.append(
                        CapabilityStep(
                            id=step_id,
                            action=action_type,
                            target=target_spec,
                            wait_after=wait_after,
                        )
                    )

            elif action_type == ArtifactActionType.EXTRACT:
                step_id = "extract_current_balance"
                target_spec = self.target_compiler.compile_target(
                    resolved_target=resolved_target,
                    action=action_str,
                    step_index=idx,
                )
                extraction_spec = self.checkpoint_compiler.build_balance_extraction("current_balance")
                compiled_steps.append(
                    CapabilityStep(
                        id=step_id,
                        action=action_type,
                        target=target_spec,
                        extraction=extraction_spec,
                    )
                )

            else:
                step_id = f"step_{idx:02d}_{action_type.value}"
                target_spec = self.target_compiler.compile_target(
                    resolved_target=resolved_target,
                    action=action_str,
                    step_index=idx,
                )
                compiled_steps.append(
                    CapabilityStep(
                        id=step_id,
                        action=action_type,
                        target=target_spec,
                    )
                )

        # 4. Identity & Metadata
        identity = CapabilityIdentity(
            name=capability_name,
            version=version,
            description="Look up a member and return the current balance for a savings or checking account.",
        )

        goal_dict = discovery_run.get("goal") or {}
        entrypoint_url = goal_dict.get("target_url") or "http://127.0.0.1:8000"
        resolved_entrypoint = entrypoint or EntryPointSpec(url=entrypoint_url)

        success_condition = self.checkpoint_compiler.build_success_condition(
            member_input="member_id",
            account_input="account_type",
            balance_output="current_balance",
        )

        business_outcomes = self.checkpoint_compiler.build_default_business_outcomes()
        runtime_conditions = self.checkpoint_compiler.build_default_runtime_conditions()

        resolved_safety = safety or LOOKUP_BALANCE_SAFETY
        resolved_compat = compatibility or CompatibilitySpec()

        provenance = ProvenanceSpec(
            created_from="llm_discovery",
            discovery_run_id=discovery_run.get("run_id", "unknown_run"),
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            model_provider="groq",
            model="llama-3.3-70b-versatile",
        )

        # 5. Assemble CapabilityArtifact
        artifact = CapabilityArtifact(
            schema_version="1",
            identity=identity,
            inputs=resolved_inputs,
            outputs=resolved_outputs,
            entrypoint=resolved_entrypoint,
            steps=compiled_steps,
            success_condition=success_condition,
            business_outcomes=business_outcomes,
            runtime_conditions=runtime_conditions,
            safety=resolved_safety,
            compatibility=resolved_compat,
            provenance=provenance,
        )

        # 6. Extract discovery outputs (excluding schema enums/types) to check during sanitization
        run_outputs = discovery_run.get("outputs") or {}
        for k, v in run_outputs.items():
            if isinstance(v, str):
                known_discovery_values.append(v)

        schema_words = {"savings", "checking", "usd", "string", "number", "boolean", "enum", "object", "money", "regular savings", "everyday checking"}
        filtered_discovery_values = [
            val for val in known_discovery_values
            if val.lower() not in schema_words and not any(val in (inp.values or []) for inp in resolved_inputs)
        ]

        # 7. Sanitize & Validate
        self.sanitizer.sanitize(artifact, known_discovery_values=filtered_discovery_values)
        self.validator.validate(artifact)

        return artifact

    def compile_and_save(
        self,
        discovery_run: Dict[str, Any],
        capability_name: str = "lookup_balance",
        version: str = "1.0.0",
    ) -> Path:
        """Compile discovery run, save to repository, and update registry."""
        artifact = self.compile(
            discovery_run=discovery_run,
            capability_name=capability_name,
            version=version,
        )
        saved_path = self.repository.save(artifact)
        self.registry.register(artifact, relative_path=f"{capability_name}/{version}.json")
        return saved_path

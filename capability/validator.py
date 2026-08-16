"""Validator for Phase 4 Capability Artifact Schema.

Validates the full semantic and structural integrity of CapabilityArtifact models.
"""

from __future__ import annotations

import re
from typing import Set
from capability.exceptions import ArtifactValidationError
from capability.models import (
    ArtifactActionType,
    CapabilityArtifact,
    ValueSource,
)


class ArtifactValidator:
    """Performs deep validation of compiled CapabilityArtifact models."""

    def validate(self, artifact: CapabilityArtifact) -> None:
        """Run all validation rules against the capability artifact."""
        self._validate_schema_and_identity(artifact)
        self._validate_inputs_and_outputs(artifact)
        self._validate_steps(artifact)
        self._validate_targets(artifact)
        self._validate_safety(artifact)
        self._validate_success_condition(artifact)

    def _validate_schema_and_identity(self, artifact: CapabilityArtifact) -> None:
        if not artifact.schema_version:
            raise ArtifactValidationError("Artifact is missing 'schema_version'.")

        identity = artifact.identity
        if not identity.name or not identity.name.isidentifier():
            raise ArtifactValidationError(
                f"Invalid capability name '{identity.name}'. Must be a valid identifier (e.g. 'lookup_balance')."
            )

        semver_regex = r"^\d+\.\d+\.\d+$"
        if not re.match(semver_regex, identity.version):
            raise ArtifactValidationError(
                f"Invalid capability version '{identity.version}'. Must follow semver 'X.Y.Z' (e.g. '1.0.0')."
            )

        if not identity.description or len(identity.description.strip()) < 5:
            raise ArtifactValidationError("Capability identity must provide a descriptive 'description'.")

    def _validate_inputs_and_outputs(self, artifact: CapabilityArtifact) -> None:
        input_names = {inp.name for inp in artifact.inputs}
        if len(input_names) != len(artifact.inputs):
            raise ArtifactValidationError("Duplicate input parameter names detected.")

        output_names = {out.name for out in artifact.outputs}
        if len(output_names) != len(artifact.outputs):
            raise ArtifactValidationError("Duplicate output variable names detected.")

        if not output_names:
            raise ArtifactValidationError("Capability must declare at least one output in 'outputs'.")

    def _validate_steps(self, artifact: CapabilityArtifact) -> None:
        if not artifact.steps:
            raise ArtifactValidationError("Capability must contain at least one step.")

        input_names = {inp.name for inp in artifact.inputs}
        step_ids: Set[str] = set()
        produced_outputs: Set[str] = set()

        for step in artifact.steps:
            if not step.id:
                raise ArtifactValidationError("Every step must have a unique non-empty 'id'.")
            if step.id in step_ids:
                raise ArtifactValidationError(f"Duplicate step ID '{step.id}' detected.")
            step_ids.add(step.id)

            # Check value source references
            if step.value:
                self._validate_value_source(step.value, input_names)

            # Check postconditions value references
            for cond in step.postconditions:
                if cond.expected and isinstance(cond.expected, ValueSource):
                    self._validate_value_source(cond.expected, input_names)

            # Check extraction
            if step.action == ArtifactActionType.EXTRACT:
                if not step.extraction:
                    raise ArtifactValidationError(
                        f"Step '{step.id}' has action 'extract' but is missing an 'extraction' spec."
                    )
                produced_outputs.add(step.extraction.output)

        # Verify that all declared outputs have a producer step or input pass-through
        declared_outputs = {out.name for out in artifact.outputs}
        for out_name in declared_outputs:
            if out_name not in produced_outputs and out_name not in input_names:
                raise ArtifactValidationError(
                    f"Declared output '{out_name}' has no extracting step producer or input pass-through."
                )

    def _validate_value_source(self, vs: ValueSource, declared_inputs: Set[str]) -> None:
        if vs.source == "input":
            if not vs.name or vs.name not in declared_inputs:
                raise ArtifactValidationError(
                    f"ValueSource references input '{vs.name}' which is not in declared inputs: {declared_inputs}"
                )
        elif vs.source == "input_map":
            if not vs.input or vs.input not in declared_inputs:
                raise ArtifactValidationError(
                    f"ValueSource references mapped input '{vs.input}' which is not in declared inputs: {declared_inputs}"
                )
            if not vs.mapping:
                raise ArtifactValidationError("ValueSource with source 'input_map' requires a 'mapping' dictionary.")

    def _validate_targets(self, artifact: CapabilityArtifact) -> None:
        for step in artifact.steps:
            if step.action in [ArtifactActionType.CLICK, ArtifactActionType.FILL, ArtifactActionType.SELECT, ArtifactActionType.EXTRACT]:
                if not step.target:
                    raise ArtifactValidationError(
                        f"Step '{step.id}' with action '{step.action.value}' requires a 'target' spec."
                    )
                target = step.target
                if not target.primary:
                    raise ArtifactValidationError(f"Target in step '{step.id}' is missing a 'primary' locator strategy.")

                # Check for lingering ephemeral observation IDs
                for strat in [target.primary] + target.fallbacks:
                    if strat.name and strat.name.startswith("e_") and strat.name[2:].isdigit():
                        raise ArtifactValidationError(
                            f"Target in step '{step.id}' contains temporary observation ID '{strat.name}'."
                        )

    def _validate_safety(self, artifact: CapabilityArtifact) -> None:
        safety = artifact.safety
        if not safety.allowed_actions:
            raise ArtifactValidationError("Safety spec must declare allowed actions.")

        for step in artifact.steps:
            if step.action.value not in safety.allowed_actions:
                raise ArtifactValidationError(
                    f"Step '{step.id}' uses action '{step.action.value}' which is not permitted by safety spec."
                )

        if not safety.allowed_origins:
            raise ArtifactValidationError("Safety spec must declare allowed origins.")

    def _validate_success_condition(self, artifact: CapabilityArtifact) -> None:
        if not artifact.success_condition:
            raise ArtifactValidationError("Capability artifact must declare a top-level 'success_condition'.")

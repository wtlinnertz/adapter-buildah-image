# AIEOS Adapter — build.artifact via buildah

This adapter satisfies the `build.artifact` capability contract by wrapping buildah.

## Contract

Claims: `build.artifact` at contract version 1.0.0.
Contract file: `aieos-governance-foundation/contracts/build.artifact.contract.yaml`
Output schema: null — evidence is the OCI image digest.

## Implementation plan

Read the M4 section of `~/second-brain/AIEOS Spec-Driven CI-CD Implementation Plan.md`.

## Requirements

- Wrap buildah deterministically (to the extent buildah permits).
- Accept structured inputs: source_dir, build_context (Containerfile), build_args.
- Emit evidence: oci-image-digest, tag, build-log, exit-code.
- Ship a passing conformance attestation.
- Document normalization decisions in MAPPING.md.

## Python conventions

- Type hints on public functions.
- `ruff` for linting.
- Tests in AAA shape. Unit tests mock subprocess; conformance runs real buildah.

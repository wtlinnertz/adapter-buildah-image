# MAPPING — adapter-buildah-image

Normalization decisions for the `build.artifact` contract.

## Tool

buildah, invoked as `buildah bud --format=oci -f <Containerfile> -t <tag>
<source_dir>` with optional `--build-arg KEY=VALUE` pairs. The `--format=oci`
ensures the manifest is OCI-compatible (matches the contract's expectation
that sign.artifact consume an OCI digest).

## Evidence

Emits four evidence entries on success:

- `oci-image-digest:sha256:<hex>` — extracted from buildah's output via a
  regex match on the first `sha256:` digest.
- `tag:<repo:tag>` — the adapter's tag argument (default `aieos-build:latest`).
- `build-log:<path>` — a tempfile path containing the combined stdout + stderr
  from buildah. Intended for post-mortem evidence archival, not live consumption.
- `exit-code:<N>` — the buildah exit code.

## Exit code semantics

- `exit_code=0` — buildah exited 0 AND produced a sha256 digest in its output.
  A zero exit without a digest is treated as a failure (exit_code=3) because
  the downstream sign.artifact action cannot proceed.
- `exit_code=2` — the source_dir input does not exist.
- `exit_code=127` — buildah binary not installed on $PATH.
- Other non-zero values — buildah's native exit code preserved.

## Determinism

buildah is not reproducible by default. Reproducible builds require:

- Pinning base images by digest (set in Containerfile).
- Pinning apt/yum/pip/npm versions inside the Containerfile.
- Passing a fixed `--timestamp` (v1.1 — the adapter does not pass this
  today; callers that need bit-identical digests should add it to
  build_args after v1.1 lands).

## Future (v1.1)

- `--timestamp` support for reproducible builds.
- SBOM generation (currently handled by adapter-syft-sbom).
- Build-cache control (`--layers`, `--no-cache`).

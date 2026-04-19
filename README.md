# adapter-buildah-image

AIEOS adapter satisfying the `build.artifact` capability contract. Wraps
`buildah bud` to produce an OCI image and extracts the image digest plus
build log as evidence.

## Contract

Claims: `build.artifact` at contract version 1.0.0.
Contract file: `aieos-governance-foundation/contracts/build.artifact.contract.yaml`.
Output schema: `null` (no structured findings; evidence is the image digest).

## Prerequisites for conformance

Conformance requires a host with `buildah` installed and privileged enough
to build images (rootless-ok with the right cgroups, or rootful). The
adapter's unit tests mock the subprocess and can run anywhere; the
governance-foundation `build.artifact-suite` runs the real tool and
requires a buildah-equipped runner.

## Development

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## License

MIT. See `LICENSE`.

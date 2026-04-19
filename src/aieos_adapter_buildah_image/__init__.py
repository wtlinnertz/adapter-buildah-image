"""AIEOS adapter: build.artifact via buildah.

Wraps `buildah bud` to produce an OCI image from a source directory with a
Containerfile. The evidence is the image digest (sha256:...) plus the build
log; there is no canonical findings schema for build.artifact (output_schema
is null per the contract).

Determinism note: buildah is not strictly reproducible out of the box.
Reproducible builds require pinning base images by digest, pinning build
dependencies, and sometimes --timestamp; this adapter passes those through
from the inputs.config but does not impose them.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__version__ = "1.0.0"

_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass
class AdapterResult:
    findings: dict[str, Any] | None
    evidence: list[str]
    exit_code: int


class BuildahImageAdapter:
    """Executes `buildah bud` against a source directory."""

    def __init__(self, buildah_binary: str = "buildah") -> None:
        self._buildah = buildah_binary

    def execute(self, inputs: dict[str, Any]) -> AdapterResult:
        source_dir = Path(inputs["source_dir"]).resolve()
        if not source_dir.is_dir():
            return AdapterResult(findings=None, evidence=["exit-code:2"], exit_code=2)
        containerfile = inputs.get("build_context") or "Containerfile"
        build_args: dict[str, str] = inputs.get("build_args") or {}
        tag = inputs.get("tag") or "aieos-build:latest"

        cmd = [
            self._buildah,
            "bud",
            "--format=oci",
            "-f",
            containerfile,
            "-t",
            tag,
        ]
        for k, v in build_args.items():
            cmd.extend(["--build-arg", f"{k}={v}"])
        cmd.append(str(source_dir))

        try:
            proc = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return AdapterResult(
                findings=None,
                evidence=[
                    "exit-code:127",
                    "stderr:buildah binary not found on $PATH",
                ],
                exit_code=127,
            )

        combined = f"{proc.stdout}\n{proc.stderr}"
        digest_match = _DIGEST_PATTERN.search(combined)
        digest = digest_match.group(0) if digest_match else ""

        if proc.returncode != 0 or not digest:
            return AdapterResult(
                findings=None,
                evidence=[
                    f"exit-code:{proc.returncode}",
                    f"tag:{tag}",
                    "stderr:" + (proc.stderr[:500] or ""),
                ],
                exit_code=proc.returncode if proc.returncode != 0 else 3,
            )

        build_log_ref = _write_build_log(proc.stdout, proc.stderr)
        return AdapterResult(
            findings=None,
            evidence=[
                f"oci-image-digest:{digest}",
                f"tag:{tag}",
                f"build-log:{build_log_ref}",
                f"exit-code:{proc.returncode}",
            ],
            exit_code=0,
        )


def _write_build_log(stdout: str, stderr: str) -> str:
    """Persist build output to a tempfile and return its path as an evidence reference."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".log", prefix="buildah-", delete=False)
    tmp.write("=== stdout ===\n")
    tmp.write(stdout or "")
    tmp.write("\n=== stderr ===\n")
    tmp.write(stderr or "")
    tmp.close()
    return tmp.name


def extract_digest_from_buildah_output(output: str) -> str | None:
    """Public helper: extract the first sha256 digest the buildah output contains."""
    m = _DIGEST_PATTERN.search(output)
    return m.group(0) if m else None


def canonicalize_build_evidence(evidence: list[str]) -> dict[str, str]:
    """Parse an evidence list into a dict keyed by the prefix."""
    parsed: dict[str, str] = {}
    for item in evidence:
        if ":" in item:
            key, _, value = item.partition(":")
            parsed[key] = value
    return parsed

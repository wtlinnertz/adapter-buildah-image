"""Unit tests for adapter-buildah-image.

buildah is not available in every CI environment (requires rootful/podman-
fuse or similar). These tests exercise the adapter's parsing and control
flow with subprocess mocks. Integration-against-real-buildah is a separate
conformance step run in adapter CI on a buildah-equipped runner.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from aieos_adapter_buildah_image import (
    BuildahImageAdapter,
    canonicalize_build_evidence,
    extract_digest_from_buildah_output,
)


class _CompletedProc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_valid_build_produces_digest_and_evidence(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "Containerfile").write_text("FROM scratch\n")
    # Simulate buildah bud reporting a digest.
    buildah_output = (
        "STEP 1/1: FROM scratch\n"
        "Writing manifest to image destination\n"
        "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n"
    )

    with patch("subprocess.run", return_value=_CompletedProc(0, buildah_output, "")):
        result = BuildahImageAdapter().execute({"source_dir": str(src)})

    assert result.exit_code == 0
    parsed = canonicalize_build_evidence(result.evidence)
    assert parsed["oci-image-digest"].startswith("sha256:")
    assert "tag" in parsed
    assert "build-log" in parsed


def test_missing_source_directory_returns_error(tmp_path: Path):
    result = BuildahImageAdapter().execute({"source_dir": str(tmp_path / "does-not-exist")})

    assert result.findings is None
    assert result.exit_code != 0


def test_buildah_not_installed_returns_127(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()

    with patch("subprocess.run", side_effect=FileNotFoundError("no buildah")):
        result = BuildahImageAdapter().execute({"source_dir": str(src)})

    assert result.exit_code == 127
    assert any("buildah binary not found" in e for e in result.evidence)


def test_buildah_nonzero_exit_preserves_diagnostic(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()

    with patch("subprocess.run", return_value=_CompletedProc(2, "", "missing Containerfile")):
        result = BuildahImageAdapter().execute({"source_dir": str(src)})

    assert result.exit_code != 0
    assert any("missing Containerfile" in e for e in result.evidence)


def test_build_without_digest_fails_even_on_zero_exit(tmp_path: Path):
    """Defensive: if buildah exits 0 but emits no digest, that's a failure —
    no downstream sign.artifact can proceed without the digest."""
    src = tmp_path / "src"
    src.mkdir()

    with patch("subprocess.run", return_value=_CompletedProc(0, "nothing here", "")):
        result = BuildahImageAdapter().execute({"source_dir": str(src)})

    assert result.findings is None
    assert result.exit_code != 0


def test_build_args_forwarded_to_buildah_command(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()

    captured: dict = {}

    def _capture(cmd, **_kw):
        captured["cmd"] = cmd
        return _CompletedProc(0, "sha256:" + "0" * 64, "")

    with patch("subprocess.run", side_effect=_capture):
        BuildahImageAdapter().execute(
            {
                "source_dir": str(src),
                "build_args": {"VERSION": "1.0.0", "ENV": "prod"},
                "tag": "registry.example/org/app:1.0.0",
            }
        )

    cmd = captured["cmd"]
    assert "--build-arg" in cmd
    assert "VERSION=1.0.0" in cmd
    assert "ENV=prod" in cmd
    assert "registry.example/org/app:1.0.0" in cmd


def test_extract_digest_from_buildah_output_helper():
    assert extract_digest_from_buildah_output("random text sha256:" + "a" * 64) == (
        "sha256:" + "a" * 64
    )
    assert extract_digest_from_buildah_output("no digest here") is None

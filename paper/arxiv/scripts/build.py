#!/usr/bin/env python3
"""Build the manuscript PDF and optional arXiv source bundle."""

from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

MANUSCRIPT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = MANUSCRIPT_ROOT / "build"
DIST_DIR = MANUSCRIPT_ROOT / "dist"
SYNC_SCRIPT = MANUSCRIPT_ROOT / "scripts" / "sync_sources.py"


def _has_repo_context() -> bool:
    """Return true when this script is running from the full repository tree."""

    return (
        MANUSCRIPT_ROOT.name == "arxiv"
        and MANUSCRIPT_ROOT.parent.name == "paper"
        and (MANUSCRIPT_ROOT.parents[1] / "research").exists()
        and (MANUSCRIPT_ROOT.parents[1] / "paper" / "arxiv").resolve() == MANUSCRIPT_ROOT.resolve()
    )


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd or MANUSCRIPT_ROOT, check=True)


def _git_status_porcelain() -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=MANUSCRIPT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _ensure_clean_for_bundle() -> None:
    status = _git_status_porcelain()
    if status:
        raise SystemExit(
            "Refusing to create a source bundle from a dirty working tree. "
            "Commit, stash, or remove the reported changes, then rebuild the bundle from "
            "the frozen source state."
        )


def _sync() -> None:
    if not _has_repo_context():
        print("Skipping source sync; building from bundled generated assets.")
        return
    _run([sys.executable, str(SYNC_SCRIPT)])


def _build_pdf() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    latexmk = shutil.which("latexmk")
    xelatex = shutil.which("xelatex")
    tectonic = shutil.which("tectonic")
    if latexmk and xelatex:
        _run(
            [
                latexmk,
                "-xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                f"-outdir={BUILD_DIR}",
                "main.tex",
            ],
            cwd=MANUSCRIPT_ROOT,
        )
        return
    if tectonic:
        # Prefer cached builds when possible, but do not make a fresh local or
        # CI environment fail just because the cache is cold.
        cached_cmd = [
            tectonic,
            "--keep-logs",
            "--only-cached",
            f"--outdir={BUILD_DIR}",
            "main.tex",
        ]
        online_cmd = [tectonic, "--keep-logs", f"--outdir={BUILD_DIR}", "main.tex"]
        try:
            _run(cached_cmd, cwd=MANUSCRIPT_ROOT)
        except subprocess.CalledProcessError:
            _run(online_cmd, cwd=MANUSCRIPT_ROOT)
        return
    raise SystemExit(
        "No TeX engine found.\n"
        "Install one of:\n"
        "  brew install tectonic\n"
        "  brew install --cask mactex-no-gui\n"
        "If you install MacTeX, restart the shell or run:\n"
        '  eval "$(/usr/libexec/path_helper)"\n'
        "The latexmk path requires XeLaTeX; pdfLaTeX is not a supported "
        "release engine for this source tree.\n"
        "You can still run `make paper-sync` without a TeX engine.\n"
        "For a preflight check, run `make paper-doctor`."
    )


def _bundle_readme() -> bytes:
    sha = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        cwd=MANUSCRIPT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    commit_date = subprocess.run(
        ["git", "show", "-s", "--format=%cs", "HEAD"],
        cwd=MANUSCRIPT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    text = f"""This archive contains the LaTeX source and generated figures/tables for:

  VLMaxxing through FrameMogging: Training-Free Anti-Recomputation for
  Video Vision-Language Models

Build with XeLaTeX:

  latexmk -xelatex main.tex

The rendered PDF was built from commit {sha} dated {commit_date}. The public
repository contains scripts, raw paired rows, and extended claim traceability:

  https://github.com/jfbastien/codec-through
"""
    return text.encode("utf-8")


def _arxiv_control_readme() -> bytes:
    return (
        "process:\n"
        "  compiler: xelatex\n"
        "sources:\n"
        "  - filename: main.tex\n"
        "    usage: toplevel\n"
    ).encode("utf-8")


def _add_bytes(archive: tarfile.TarFile, arcname: str, content: bytes) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(content)
    archive.addfile(info, io.BytesIO(content))


def _bundle() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIST_DIR / "codec-through-arxiv-source.tar.gz"
    exclude_prefixes = {
        "build/",
        "dist/",
        "__pycache__/",
        "generated/figures/fig1_candidates/",
        "generated/figures/fig1_chatgpt_review_bundle/",
    }
    with tarfile.open(out_path, "w:gz") as archive:
        _add_bytes(archive, "README.md", _bundle_readme())
        _add_bytes(archive, "00README", _arxiv_control_readme())
        for path in sorted(MANUSCRIPT_ROOT.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(MANUSCRIPT_ROOT).as_posix()
            if rel == "README.md":
                continue
            if any(rel.startswith(prefix) for prefix in exclude_prefixes):
                continue
            if path.suffix in {".pyc", ".zip"}:
                continue
            if path.name in {".DS_Store"} or path.name.startswith("._"):
                continue
            archive.add(path, arcname=rel)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Only sync assets and optionally bundle.",
    )
    parser.add_argument(
        "--bundle",
        action="store_true",
        help="Create an arXiv-style source tarball.",
    )
    args = parser.parse_args()

    _sync()
    if args.bundle:
        _ensure_clean_for_bundle()
    if not args.skip_pdf:
        _build_pdf()
    if args.bundle:
        bundle = _bundle()
        print(f"Wrote {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

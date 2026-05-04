#!/usr/bin/env python3
"""Build the manuscript PDF and optional release bundles."""

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
ARXIV_UPLOAD_NAME = "codec-through-arxiv-upload.tar.gz"
AUDIT_BUNDLE_NAME = "codec-through-audit-bundle.tar.gz"

ARXIV_FIGURE_FILES = (
    "generated/figures/regime_overview.pdf",
    "generated/figures/lane_a_pareto.pdf",
    "generated/figures/c_persist_safe_budget.pdf",
    "generated/figures/c_persist_timeline.pdf",
    "generated/figures/v_share_v_red_ceiling.pdf",
    "generated/figures/fig1_appendix_broadened/qwen_routing_budget_visualized.pdf",
)

ARXIV_TABLE_FILES = (
    "generated/tables/c_persist_dense_anchored.tex",
    "generated/tables/c_persist_many_turn.tex",
    "generated/tables/c_persist_repair.tex",
    "generated/tables/c_persist_sampler_seed_sweep.tex",
    "generated/tables/c_persist_sampler_stability.tex",
    "generated/tables/c_persist_setup_inclusive.tex",
    "generated/tables/competitor_positioning.tex",
    "generated/tables/gemma_measured_sparse_vision.tex",
    "generated/tables/headline_results.tex",
    "generated/tables/lane_a_holdout.tex",
    "generated/tables/memory_characterization.tex",
    "generated/tables/paired_drift.tex",
    "generated/tables/qwen_bridge_boundary.tex",
    "generated/tables/qwen_measured_sparse_vision.tex",
    "generated/tables/scaleout_bundle_status.tex",
)

AUDIT_EXTRA_FILES = (
    "README.md",
    "PLAN.md",
    "pyproject.toml",
    "uv.lock",
    "docs/claim-register.md",
    "docs/reproduction-status.md",
    "paper/AGENTS.md",
    "paper/README.md",
    "paper/priority.md",
    "paper/claim-matrix.md",
    "paper/publishability-status.md",
    "paper/framing.md",
    "research/README.md",
    "research/experiments/registry.md",
)


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


def _git_commit_info() -> dict[str, str]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
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
    return {"sha": sha, "commit_date": commit_date}


def _short_sha(sha: str) -> str:
    return sha[:7]


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
    commit = _git_commit_info()
    rendered_from = f"{_short_sha(commit['sha'])} dated {commit['commit_date']}"
    text = f"""This archive contains the LaTeX source and generated figures/tables for:

  VLMaxxing through FrameMogging: Training-Free Anti-Recomputation for
  Video Vision-Language Models

Build with XeLaTeX:

  latexmk -xelatex main.tex

The rendered PDF was built from commit {rendered_from}. The public
repository contains scripts, raw paired rows, and extended claim traceability:

  https://github.com/jfbastien/codec-through
"""
    return text.encode("utf-8")


def _arxiv_control_readme() -> bytes:
    return (
        b"spec_version: 1\n"
        b"texlive_version: 2025\n"
        b"process:\n"
        b"  compiler: xelatex\n"
        b"sources:\n"
        b"  - filename: main.tex\n"
        b"    usage: toplevel\n"
    )


def _build_meta() -> bytes:
    commit = _git_commit_info()
    lines = [
        f"\\newcommand{{\\PrimaryRepoSHA}}{{{_short_sha(commit['sha'])}}}",
        f"\\newcommand{{\\PrimaryRepoFullSHA}}{{{commit['sha']}}}",
        f"\\newcommand{{\\PrimaryRepoCommitDate}}{{{commit['commit_date']}}}",
        r"\newcommand{\UpstreamRepoSHA}{not used}",
        r"\newcommand{\UpstreamRepoCommitDate}{not used}",
        (
            "\\newcommand{\\ScaleoutRepoSHA}{"
            f"checked in primary repo at {_short_sha(commit['sha'])}"
            "}"
        ),
        f"\\newcommand{{\\ScaleoutRepoCommitDate}}{{{commit['commit_date']}}}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _add_bytes(archive: tarfile.TarFile, arcname: str, content: bytes) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(content)
    archive.addfile(info, io.BytesIO(content))


def _add_file(archive: tarfile.TarFile, rel: str, root: Path = MANUSCRIPT_ROOT) -> None:
    path = root / rel
    if not path.is_file():
        raise SystemExit(f"Required bundle file is missing: {path}")
    archive.add(path, arcname=rel)


def _iter_arxiv_upload_files() -> list[str]:
    files = [
        "main.tex",
        "appendix.tex",
        "generated/tex/build_meta.tex",
    ]
    files.extend(
        path.relative_to(MANUSCRIPT_ROOT).as_posix()
        for path in sorted((MANUSCRIPT_ROOT / "sections").glob("*.tex"))
    )
    files.extend(ARXIV_TABLE_FILES)
    files.extend(ARXIV_FIGURE_FILES)
    return sorted(set(files))


def _arxiv_upload_bundle() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIST_DIR / ARXIV_UPLOAD_NAME
    with tarfile.open(out_path, "w:gz") as archive:
        _add_bytes(archive, "README.md", _bundle_readme())
        _add_bytes(archive, "00README", _arxiv_control_readme())
        for rel in _iter_arxiv_upload_files():
            if rel == "generated/tex/build_meta.tex":
                _add_bytes(archive, rel, _build_meta())
            else:
                _add_file(archive, rel)
    return out_path


def _audit_bundle() -> Path:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DIST_DIR / AUDIT_BUNDLE_NAME
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
        repo_root = MANUSCRIPT_ROOT.parents[1]
        for rel in AUDIT_EXTRA_FILES:
            path = repo_root / rel
            if path.is_file():
                archive.add(path, arcname=f"repo/{rel}")
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
        help="Create the minimal arXiv upload tarball.",
    )
    parser.add_argument(
        "--arxiv-upload",
        action="store_true",
        help="Create the minimal arXiv upload tarball.",
    )
    parser.add_argument(
        "--audit-bundle",
        action="store_true",
        help="Create a richer reproducibility/audit tarball.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow bundle creation from a dirty working tree for local validation only.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Use frozen generated assets without running the repository sync step.",
    )
    args = parser.parse_args()

    if not args.no_sync:
        _sync()
    wants_bundle = args.bundle or args.arxiv_upload or args.audit_bundle
    if wants_bundle and not args.allow_dirty:
        _ensure_clean_for_bundle()
    if not args.skip_pdf:
        _build_pdf()
    if args.bundle or args.arxiv_upload:
        bundle = _arxiv_upload_bundle()
        print(f"Wrote {bundle}")
    if args.audit_bundle:
        bundle = _audit_bundle()
        print(f"Wrote {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

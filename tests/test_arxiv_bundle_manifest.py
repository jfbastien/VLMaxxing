import importlib.util
import re
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "paper" / "arxiv" / "scripts" / "build.py"


def _load_build_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("paper_arxiv_build", BUILD_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tex_sources() -> list[Path]:
    arxiv_root = REPO_ROOT / "paper" / "arxiv"
    return [
        arxiv_root / "main.tex",
        arxiv_root / "appendix.tex",
        *sorted((arxiv_root / "sections").glob("*.tex")),
    ]


def test_arxiv_upload_manifest_covers_tex_inputs() -> None:
    build = _load_build_script()
    manifest = set(build._iter_arxiv_upload_files())
    table_inputs: set[str] = set()
    figure_inputs: set[str] = set()

    for path in _tex_sources():
        text = path.read_text()
        table_inputs.update(re.findall(r"\\input\{(generated/tables/[^}]+\.tex)\}", text))
        for match in re.findall(
            r"\\includegraphics(?:\[[^]]*])?\{(generated/figures/[^}]+)\}", text
        ):
            if match.endswith(".png"):
                continue
            figure_inputs.add(match if match.endswith(".pdf") else f"{match}.pdf")

    assert table_inputs <= manifest
    assert figure_inputs <= manifest
    assert "generated/tex/build_meta.tex" in manifest
    assert "generated/tables/repo_provenance.tex" not in manifest


def test_arxiv_upload_manifest_excludes_audit_only_files() -> None:
    build = _load_build_script()
    manifest = set(build._iter_arxiv_upload_files())

    assert all(not path.startswith("scripts/") for path in manifest)
    assert all(not path.startswith("generated/data/") for path in manifest)
    assert all(not path.endswith((".json", ".png", ".svg", ".zip")) for path in manifest)
    assert all(not path.startswith(("build/", "dist/")) for path in manifest)


def test_arxiv_control_readme_selects_xelatex_texlive_2025() -> None:
    build = _load_build_script()
    readme = build._arxiv_control_readme().decode("utf-8")

    assert "spec_version: 1" in readme
    assert "texlive_version: 2025" in readme
    assert "compiler: xelatex" in readme
    assert "filename: main.tex" in readme
    assert "usage: toplevel" in readme

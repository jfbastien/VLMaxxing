#!/usr/bin/env python3
"""Check whether the local machine can build the manuscript."""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp" / "matplotlib"))


def _check_binary(name: str) -> str:
    path = shutil.which(name)
    return path if path else "missing"


def _check_module(name: str) -> str:
    try:
        importlib.import_module(name)
    except Exception:
        return "missing"
    return "ok"


def main() -> int:
    rows = [
        ("python", sys.executable),
        ("latexmk", _check_binary("latexmk")),
        ("pdflatex", _check_binary("pdflatex")),
        ("tectonic", _check_binary("tectonic")),
        ("biber", _check_binary("biber")),
        ("matplotlib", _check_module("matplotlib")),
        ("PIL", _check_module("PIL")),
    ]

    width = max(len(name) for name, _ in rows)
    print("Paper toolchain doctor")
    print("======================")
    for name, status in rows:
        print(f"{name:<{width}} : {status}")

    has_tex = any(_check_binary(name) != "missing" for name in ("latexmk", "tectonic"))
    if not has_tex:
        print()
        print("No TeX engine found. `make paper-sync` will work, but `make paper-build`")
        print("needs either `tectonic` or `latexmk` + `pdflatex`.")
        print()
        print("Recommended lightweight install on macOS:")
        print("  brew install tectonic")
        print()
        print("Fuller TeX Live install if you need it:")
        print("  brew install --cask mactex-no-gui")
        print('  eval "$(/usr/libexec/path_helper)"')
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

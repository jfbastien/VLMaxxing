from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_memory_characterization_requires_lane_coverage(tmp_path: Path) -> None:
    cvision = tmp_path / "phase1_30AD"
    cpersist = tmp_path / "phase1_55F"
    trackb = tmp_path / "phase1_63G"
    cvision.mkdir()
    cpersist.mkdir()
    trackb.mkdir()
    for index in range(3):
        (cvision / f"summary_{index}.json").write_text(json.dumps({"peak_rss_gb": 6.1}) + "\n")
    (cpersist / "rows.jsonl").write_text(
        "\n".join(json.dumps({"peak_memory_gb": 8.2}) for _ in range(8)) + "\n"
    )
    for index in range(4):
        (trackb / f"summary_{index}.json").write_text(json.dumps({"final_rss_mb": 7168}) + "\n")
    output = tmp_path / "memory.json"
    csv_output = tmp_path / "memory.csv"

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_66_memory_characterization.py",
            "--source-dir",
            str(cvision),
            "--source-dir",
            str(cpersist),
            "--source-dir",
            str(trackb),
            "--output",
            str(output),
            "--csv-output",
            str(csv_output),
        ],
        check=True,
    )

    summary = json.loads(output.read_text())
    assert summary["families_present"] == ["C-PERSIST/1.55", "C-VISION/1.30", "Track-B/1.63"]
    assert summary["missing_required_families"] == []
    assert summary["pass_memory_characterized"] is True
    assert csv_output.exists()


def test_memory_characterization_fails_without_track_b_family(tmp_path: Path) -> None:
    cvision = tmp_path / "phase1_30AD"
    cpersist = tmp_path / "phase1_55F"
    cvision.mkdir()
    cpersist.mkdir()
    for index in range(4):
        (cvision / f"summary_{index}.json").write_text(json.dumps({"peak_rss_gb": 6.1}) + "\n")
        (cpersist / f"summary_{index}.json").write_text(json.dumps({"peak_rss_gb": 8.1}) + "\n")
    output = tmp_path / "memory.json"
    csv_output = tmp_path / "memory.csv"

    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_phase1_66_memory_characterization.py",
            "--source-dir",
            str(cvision),
            "--source-dir",
            str(cpersist),
            "--output",
            str(output),
            "--csv-output",
            str(csv_output),
        ],
        check=True,
    )

    summary = json.loads(output.read_text())
    assert summary["n_cells"] == 8
    assert summary["missing_required_families"] == ["Track-B/1.63"]
    assert summary["pass_memory_characterized"] is False

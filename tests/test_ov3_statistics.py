from scripts.analyze_ov3_statistics import _multiple_comparisons_summary


def test_multiple_comparisons_note_matches_loaded_n57_family() -> None:
    summary = _multiple_comparisons_summary(
        [
            {
                "path": "phase1_29_onevision_n57",
                "by_source": {
                    "novel_coded": {},
                    "motion": {},
                    "residual": {},
                    "fused": {},
                },
            }
        ]
    )

    assert summary["n_cells_compared"] == 4
    assert summary["bonferroni_alpha_for_per_cell_at_family_05"] == 0.0125
    assert "0.05 / 4" in summary["note"]
    assert "12 cells" not in summary["note"]


def test_multiple_comparisons_note_generalizes_to_loaded_tranches() -> None:
    summary = _multiple_comparisons_summary(
        [
            {"path": "a", "by_source": {"novel_coded": {}, "motion": {}}},
            {"path": "b", "by_source": {"novel_coded": {}, "motion": {}}},
            {"path": "c", "by_source": {"novel_coded": {}, "motion": {}}},
        ]
    )

    assert summary["n_cells_compared"] == 6
    assert summary["bonferroni_alpha_for_per_cell_at_family_05"] == 0.0083
    assert "3 tranche(s)" in summary["note"]
    assert "2 codec source(s)" in summary["note"]

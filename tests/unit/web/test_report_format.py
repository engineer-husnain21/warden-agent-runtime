from web.report_format import demote_headings


def test_demote_headings_when_report_has_headings_pushes_them_two_levels_down() -> None:
    report = "# Title\n## Summary\nText\n### Findings\n- item"

    assert demote_headings(report) == "### Title\n#### Summary\nText\n##### Findings\n- item"


def test_demote_headings_when_already_deep_caps_at_level_six() -> None:
    assert demote_headings("##### Deep\n###### Deepest") == "###### Deep\n###### Deepest"


def test_demote_headings_when_hash_inside_code_block_leaves_it_alone() -> None:
    report = "## Query\n```sql\n# not a heading\n```\n#hashtag is not a heading"

    assert demote_headings(report) == (
        "#### Query\n```sql\n# not a heading\n```\n#hashtag is not a heading"
    )

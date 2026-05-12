from joycaption_desktop.postprocessors.builtin import apply_postprocessors


def test_tag_postprocessors_normalize_and_dedupe():
    text = " cat, dog, cat,\n bird. "

    result = apply_postprocessors(
        text,
        ("normalize-commas", "dedupe-tags", "strip-tag-period"),
    )

    assert result == "cat, dog, bird"

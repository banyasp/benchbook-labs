from pipeline.ingest.textclean import clean_text, decolumnize, fix_chars

LEFT = ["The first column starts here and", "keeps going for a while with more", "words until it ends.", "",
        "A second left paragraph follows", "and closes the left column."] * 2
RIGHT = ["Meanwhile the right column says", "something else entirely, and it", "continues on its own.", "",
         "Its second paragraph is here", "and it ends the right column."] * 2


def two_col_page():
    return "\n".join(f"{l:<40}      {r}" for l, r in zip(LEFT, RIGHT))


def test_two_columns_read_left_then_right():
    out, two = decolumnize(two_col_page())
    assert two
    assert out.index("closes the left column") < out.index("Meanwhile the right column")
    assert "and      Meanwhile" not in out and "and Meanwhile" not in out


def test_single_column_untouched():
    page = "\n".join(LEFT + RIGHT)
    out, two = decolumnize(page)
    assert not two and out == page


def test_chars_and_hyphens():
    t, st = clean_text("an efﬁcient acknowl-\nedging of a 50-\nyear career â€™")
    assert "efficient" in t and "acknowledging" in t and "50-year" in t and "’" in t
    assert st["ligature"] == 1 and st["mojibake"] == 1


def test_justified_gaps_squashed_inside_columns():
    page = two_col_page().replace("keeps going for a while with more", "keeps     going   for a while with")
    out, _ = decolumnize(page)
    assert "keeps going for a while with" in out

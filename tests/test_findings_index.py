from scripts import findings_index as fi


def test_index_inserted_then_replaced_idempotently():
    t = "# Findings\n\n## Cross-cutting lessons\n* x\n\n## Hypotheses\n### a → DEAD\nbody\n### b → ALIVE\n"
    once = fi.apply(t)
    assert "- a → DEAD" in once and "- b → ALIVE" in once and once.index(fi.A) < once.index("## Cross-cutting")
    twice = fi.apply(once.replace("### b → ALIVE", "### b → OPEN"))
    assert twice.count(fi.A) == 1 and "- b → OPEN" in twice and "- b → ALIVE" not in twice

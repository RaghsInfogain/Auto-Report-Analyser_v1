"""Short grade narratives for release / executive callouts (single place for imports)."""


def format_performance_grade_release_line(
    grade: str, score: float, title: str, subtitle: str
) -> str:
    """
    Narrative: grade score, risk title, description.
    Pillar weights belong in the scorecard / methodology modal only — omit here.
    """
    lead = f"Performance grade {grade} ({score:.0f}/100)."
    t = (title or "").strip()
    s = (subtitle or "").strip()
    if not t and not s:
        return lead
    if t:
        t = t.rstrip(".")
    if s and s[0].isalpha() and not s[0].isupper():
        s = s[0].upper() + s[1:]
    if t and s:
        body = f"{t}: {s}"
    elif t:
        body = f"{t}."
    else:
        body = s
    combined = f"{lead} {body}".strip()
    if combined and combined[-1] not in ".!?":
        combined += "."
    return combined

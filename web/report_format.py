"""How the final report is shown in the console. Pure functions, so they are easy to test."""

import re

_HEADING = re.compile(r"^(#{1,6})(\s)")
_FENCE = re.compile(r"^\s*(```|~~~)")
_MAX_LEVEL = 6


def demote_headings(markdown: str, levels: int = 2) -> str:
    """Push every Markdown heading down `levels` levels (## -> ####, capped at ######) so the
    report's own headings sit below the page's "Report" subheading. Code blocks are left alone."""
    lines = []
    in_code = False
    for line in markdown.splitlines():
        if _FENCE.match(line):
            in_code = not in_code
        elif not in_code:
            line = _HEADING.sub(
                lambda match: "#" * min(len(match[1]) + levels, _MAX_LEVEL) + match[2], line
            )
        lines.append(line)
    return "\n".join(lines)

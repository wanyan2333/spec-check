"""Render the README "at a glance" chart from saved eval results (no API calls).

Writes docs/eval-chart-light.svg and docs/eval-chart-dark.svg: a dot plot comparing
the evaluated configurations on the metrics where higher is better.

Usage: uv run python eval/make_chart.py
"""

import re
from html import escape

from case_tools import ROOT
from run_eval import compute_metrics, load

CONFIGS = [  # (results file, legend label)
    ("v1", "prompt v1 · 3.5-flash-lite"),
    ("v2", "prompt v2 · 3.5-flash-lite (default)"),
    ("v2-gemini-3.1-flash-lite", "prompt v2 · 3.1-flash-lite"),
]
METRICS = [  # (key in compute_metrics, row label)
    ("Both correct", "Both labels correct"),
    ("Implemented accuracy", "Implemented accuracy"),
    ("Tested accuracy", "Tested accuracy"),
    ("Missing-implementation detection (exp. no/partial, pred. not yes)", "Missing-impl. detected"),
    ("Missing-test detection (exp. tested=no, pred. no)", "Missing tests detected"),
    ("Run-to-run consistency", "Run-to-run consistency"),
]
THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "border": "#e1e0d9",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "series": ["#2a78d6", "#eb6834", "#1baf7a"],
    },
    "dark": {
        "surface": "#1a1a19",
        "border": "#2c2c2a",
        "ink": "#ffffff",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "series": ["#3987e5", "#d95926", "#199e70"],
    },
}
X_MIN, X_MAX = 75, 100  # dot plot: no zero baseline needed, so zoom in on the range
W, LEFT, RIGHT = 840, 230, 790
ROW_GAP, SUB = 16, 15  # space between metric groups, height of one series sub-row
TOP = 92


def ratio(text: str) -> tuple[int, int]:
    numerator, denominator = re.match(r"(\d+)/(\d+)", text).groups()
    return int(numerator), int(denominator)


def x_of(pct: float) -> float:
    return LEFT + (pct - X_MIN) / (X_MAX - X_MIN) * (RIGHT - LEFT)


def marker(shape: int, x: float, y: float, color: str, ring: str) -> str:
    common = f'fill="{color}" stroke="{ring}" stroke-width="2"'
    if shape == 0:
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" {common}/>'
    if shape == 1:
        return f'<rect x="{x - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" rx="2" {common}/>'
    return (
        f'<path d="M{x:.1f},{y - 6.5:.1f} L{x + 6.5:.1f},{y:.1f} L{x:.1f},{y + 6.5:.1f} '
        f'L{x - 6.5:.1f},{y:.1f} Z" {common}/>'
    )


def render(theme: dict, data: dict[str, dict[str, tuple[int, int]]], meta: str) -> str:
    group_h = SUB * len(CONFIGS)
    plot_bottom = TOP + len(METRICS) * (group_h + ROW_GAP)
    height = plot_bottom + 56
    t = theme
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" '
        f'viewBox="0 0 {W} {height}" font-family="system-ui, -apple-system, Segoe UI, sans-serif" '
        f'role="img" aria-label="spec-check evaluation results by configuration">',
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="10" '
        f'fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'<text x="24" y="34" font-size="17" font-weight="600" fill="{t["ink"]}">'
        f"Evaluation: higher is better</text>",
        f'<text x="24" y="54" font-size="12.5" fill="{t["ink2"]}">{escape(meta)}</text>',
    ]
    # Legend: shape + color + label, so identity never depends on color alone.
    lx = 24
    for i, (_, label) in enumerate(CONFIGS):
        out.append(marker(i, lx + 6, 74, t["series"][i], t["surface"]))
        out.append(
            f'<text x="{lx + 18:.0f}" y="78" font-size="12.5" fill="{t["ink"]}">'
            f"{escape(label)}</text>"
        )
        lx += 30 + len(label) * 6.6
    # Recessive grid + ticks.
    for pct in range(X_MIN, X_MAX + 1, 5):
        x = x_of(pct)
        out.append(
            f'<line x1="{x:.1f}" y1="{TOP - 4}" x2="{x:.1f}" y2="{plot_bottom - 6}" '
            f'stroke="{t["grid"]}" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{x:.1f}" y="{plot_bottom + 10}" font-size="11.5" '
            f'text-anchor="middle" fill="{t["muted"]}">{pct}%</text>'
        )
    # Rows.
    for m, (key, label) in enumerate(METRICS):
        y0 = TOP + m * (group_h + ROW_GAP)
        out.append(
            f'<text x="24" y="{y0 + group_h / 2 + 4:.1f}" font-size="13" '
            f'fill="{t["ink"]}">{escape(label)}</text>'
        )
        for i, (name, _) in enumerate(CONFIGS):
            num, den = data[name][key]
            pct = 100 * num / den
            y = y0 + SUB * i + SUB / 2
            x = x_of(pct)
            out.append(marker(i, x, y, t["series"][i], t["surface"]))
            # Value label: left of the dot near 100%, otherwise to the right.
            text = f"{pct:.0f}% ({num}/{den})"
            if pct > 93:
                out.append(
                    f'<text x="{x - 11:.1f}" y="{y + 4:.1f}" font-size="11" '
                    f'text-anchor="end" fill="{t["ink2"]}">{text}</text>'
                )
            else:
                out.append(
                    f'<text x="{x + 11:.1f}" y="{y + 4:.1f}" font-size="11" '
                    f'fill="{t["ink2"]}">{text}</text>'
                )
    out.append(
        f'<text x="24" y="{height - 18}" font-size="12" fill="{t["ink2"]}">'
        "All configurations: 0/16 false positives on fully correct criteria · "
        "axis starts at 75%</text>"
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    data = {}
    for name, _ in CONFIGS:
        metrics = compute_metrics(load(name))
        data[name] = {key: ratio(metrics[key]) for key, _ in METRICS}
    meta = "8 cases · 19 acceptance criteria · 2 runs each (38 judgments per configuration)"
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    for mode, theme in THEMES.items():
        path = docs / f"eval-chart-{mode}.svg"
        path.write_text(render(theme, data, meta), encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

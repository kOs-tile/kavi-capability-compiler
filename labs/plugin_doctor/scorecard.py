from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

SCORECARD_VERSION = "plugin-doctor.scorecard.v0"


def _escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _safe_link(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        return None
    return value


def _primary(report: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("package", "readiness"):
        value = report.get(key)
        if isinstance(value, Mapping):
            return value
    return report


def render_scorecard(
    report: Mapping[str, Any],
    *,
    title: str = "KAVI Plugin Doctor",
) -> str:
    """Render one self-contained, escaped HTML scorecard."""

    primary = _primary(report)
    state = str(primary.get("state") or "UNKNOWN")
    score = primary.get("score")
    summary = primary.get("summary") if isinstance(primary.get("summary"), Mapping) else {}
    findings = primary.get("findings") if isinstance(primary.get("findings"), list) else []
    source = report.get("source") if isinstance(report.get("source"), Mapping) else {}

    summary_html = "".join(
        f"<div class='metric'><span>{_escape(key.replace('_', ' ').title())}</span><strong>{_escape(value)}</strong></div>"
        for key, value in summary.items()
        if isinstance(value, (str, int, float, bool))
    )

    rows = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        source_url = _safe_link(finding.get("source_url"))
        source_html = (
            f"<a href='{_escape(source_url)}' rel='noopener noreferrer'>official source</a>"
            if source_url
            else ""
        )
        rows.append(
            "<article class='finding'>"
            f"<div class='finding-head'><strong>{_escape(finding.get('code') or 'finding')}</strong>"
            f"<span>{_escape(finding.get('severity') or '')}</span></div>"
            f"<p>{_escape(finding.get('message') or '')}</p>"
            + (
                f"<p class='remediation'><b>Fix:</b> {_escape(finding.get('remediation'))}</p>"
                if finding.get("remediation")
                else ""
            )
            + (f"<p class='source'>{source_html}</p>" if source_html else "")
            + "</article>"
        )

    source_bits = []
    for key in ("repository", "ref", "url", "root"):
        if source.get(key):
            source_bits.append(f"<span><b>{_escape(key)}:</b> {_escape(source[key])}</span>")
    source_html = " ".join(source_bits)

    score_text = _escape(score if score is not None else "—")
    findings_html = "".join(rows) or "<p class='empty'>No findings in this report.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{SCORECARD_VERSION}">
<title>{_escape(title)}</title>
<style>
:root {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #0b0d10; color: #f3f5f7; }}
main {{ width: min(980px, calc(100% - 32px)); margin: 48px auto; }}
.eyebrow {{ text-transform: uppercase; letter-spacing: .16em; font-size: 12px; opacity: .62; }}
.hero {{ border: 1px solid #2a2f36; border-radius: 20px; padding: 28px; background: #12161b; }}
h1 {{ margin: 8px 0 20px; font-size: clamp(32px, 6vw, 58px); line-height: 1; }}
.result {{ display: flex; gap: 16px; align-items: end; flex-wrap: wrap; }}
.state {{ font-size: 28px; font-weight: 800; }}
.score {{ margin-left: auto; font-size: 64px; font-weight: 800; line-height: .9; }}
.score small {{ font-size: 18px; opacity: .6; }}
.source-meta {{ margin-top: 18px; display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px; opacity: .72; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 18px 0 30px; }}
.metric {{ border: 1px solid #2a2f36; border-radius: 14px; padding: 14px; background: #101318; }}
.metric span {{ display: block; font-size: 12px; opacity: .62; margin-bottom: 6px; }}
.metric strong {{ font-size: 24px; }}
section {{ margin-top: 28px; }}
.finding {{ border-top: 1px solid #2a2f36; padding: 18px 0; }}
.finding-head {{ display: flex; justify-content: space-between; gap: 16px; }}
.finding-head span {{ text-transform: uppercase; font-size: 12px; opacity: .62; }}
.finding p {{ line-height: 1.55; max-width: 800px; }}
.remediation {{ opacity: .82; }}
.source a {{ color: inherit; opacity: .7; }}
.empty {{ opacity: .62; }}
footer {{ margin: 40px 0 12px; font-size: 12px; opacity: .48; }}
</style>
</head>
<body>
<main>
  <div class="hero">
    <div class="eyebrow">KAVI Plugin Doctor / readiness scorecard</div>
    <h1>{_escape(title)}</h1>
    <div class="result">
      <div class="state">{_escape(state)}</div>
      <div class="score">{score_text}<small>/100</small></div>
    </div>
    <div class="source-meta">{source_html}</div>
  </div>
  <div class="metrics">{summary_html}</div>
  <section>
    <div class="eyebrow">Findings</div>
    {findings_html}
  </section>
  <footer>Generated by KAVI Plugin Doctor. Scores are readiness heuristics and do not guarantee OpenAI approval, placement, or distribution.</footer>
</main>
</body>
</html>
"""


def write_scorecard(
    report: Mapping[str, Any],
    path: str | Path,
    *,
    title: str = "KAVI Plugin Doctor",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_scorecard(report, title=title), encoding="utf-8")
    return destination

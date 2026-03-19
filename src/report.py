"""
report.py — Generates an HTML safety evaluation report from judgment results.
"""

from collections import defaultdict
from src.judge import JudgmentResult
from src.runner import ModelResponse


def generate_report(
    responses: list[ModelResponse],
    judgments: list[JudgmentResult],
    target_model: str,
    judge_model: str,
) -> str:
    # Build lookup for responses by prompt_id
    resp_by_id = {r.prompt_id: r for r in responses}

    total = len(judgments)
    refused_count = sum(1 for j in judgments if j.refused)
    complied_count = total - refused_count
    refusal_rate = (refused_count / total * 100) if total > 0 else 0

    # Per-category stats
    by_category = defaultdict(list)
    for j in judgments:
        by_category[j.category].append(j)

    category_stats = {}
    for cat, items in by_category.items():
        n = len(items)
        r = sum(1 for i in items if i.refused)
        category_stats[cat] = {"total": n, "refused": r, "rate": r / n * 100}

    # Build rows
    rows_html = ""
    for j in judgments:
        resp = resp_by_id.get(j.prompt_id)
        prompt_text = resp.prompt_text if resp else ""
        response_text = resp.response_text if resp else ""

        status_badge = (
            '<span class="badge safe">REFUSED</span>'
            if j.refused
            else '<span class="badge unsafe">COMPLIED</span>'
        )

        score_html = ""
        if j.refused:
            score_html = f'<span class="score">Refusal quality: {j.refusal_quality}/5</span>'
        else:
            score_html = f'<span class="score harm">Harm level: {j.compliance_harm}/5</span>'

        severity_class = {"high": "sev-high", "medium": "sev-med", "low": "sev-low"}.get(
            j.severity, ""
        )

        rows_html += f"""
        <tr>
          <td><code>{j.prompt_id}</code></td>
          <td><span class="cat">{j.category}</span></td>
          <td><span class="{severity_class}">{j.severity}</span></td>
          <td class="prompt-text">{_escape(prompt_text)}</td>
          <td class="response-text">{_escape(response_text)}</td>
          <td>{status_badge}<br>{score_html}</td>
          <td class="notes">{_escape(j.notes)}</td>
        </tr>"""

    # Category summary rows
    cat_rows = ""
    for cat, stats in sorted(category_stats.items()):
        bar_width = int(stats["rate"])
        cat_rows += f"""
        <tr>
          <td>{cat}</td>
          <td>{stats['refused']}/{stats['total']}</td>
          <td>
            <div class="bar-bg">
              <div class="bar-fill" style="width:{bar_width}%"></div>
            </div>
            {stats['rate']:.0f}%
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LLM Safety Evaluation Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0; padding: 24px; background: #f5f5f5; color: #222; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
    .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 24px; }}
    .cards {{ display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }}
    .card {{ background: white; border-radius: 8px; padding: 20px 28px;
             box-shadow: 0 1px 3px rgba(0,0,0,.1); min-width: 140px; }}
    .card .num {{ font-size: 2.4rem; font-weight: 700; }}
    .card .label {{ color: #666; font-size: 0.85rem; }}
    .card.green .num {{ color: #16a34a; }}
    .card.red .num {{ color: #dc2626; }}
    .card.blue .num {{ color: #2563eb; }}
    h2 {{ font-size: 1.1rem; margin: 0 0 12px; }}
    .section {{ background: white; border-radius: 8px; padding: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th {{ background: #f9fafb; text-align: left; padding: 8px 12px;
          border-bottom: 2px solid #e5e7eb; font-weight: 600; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
    tr:hover td {{ background: #fafafa; }}
    .prompt-text, .response-text {{ max-width: 240px; white-space: pre-wrap;
                                    word-break: break-word; font-size: 0.8rem; color: #444; }}
    .notes {{ max-width: 200px; font-size: 0.8rem; color: #555; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px;
              font-size: 0.75rem; font-weight: 600; }}
    .badge.safe {{ background: #dcfce7; color: #16a34a; }}
    .badge.unsafe {{ background: #fee2e2; color: #dc2626; }}
    .score {{ font-size: 0.75rem; color: #666; }}
    .score.harm {{ color: #dc2626; }}
    .cat {{ background: #eff6ff; color: #2563eb; padding: 2px 6px;
            border-radius: 4px; font-size: 0.75rem; }}
    .sev-high {{ color: #dc2626; font-weight: 600; }}
    .sev-med  {{ color: #d97706; font-weight: 600; }}
    .sev-low  {{ color: #16a34a; }}
    .bar-bg {{ display: inline-block; width: 100px; height: 10px; background: #e5e7eb;
               border-radius: 5px; vertical-align: middle; margin-right: 6px; }}
    .bar-fill {{ height: 100%; background: #16a34a; border-radius: 5px; }}
    code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px;
            font-size: 0.8rem; }}
  </style>
</head>
<body>
  <h1>LLM Safety Evaluation Report</h1>
  <div class="meta">
    Target model: <strong>{target_model}</strong> &nbsp;|&nbsp;
    Judge model: <strong>{judge_model}</strong> &nbsp;|&nbsp;
    Prompts evaluated: <strong>{total}</strong>
  </div>

  <div class="cards">
    <div class="card blue">
      <div class="num">{total}</div>
      <div class="label">Total prompts</div>
    </div>
    <div class="card green">
      <div class="num">{refused_count}</div>
      <div class="label">Refused ({refusal_rate:.0f}%)</div>
    </div>
    <div class="card red">
      <div class="num">{complied_count}</div>
      <div class="label">Complied ({100 - refusal_rate:.0f}%)</div>
    </div>
  </div>

  <div class="section">
    <h2>Refusal Rate by Category</h2>
    <table>
      <tr><th>Category</th><th>Refused / Total</th><th>Refusal Rate</th></tr>
      {cat_rows}
    </table>
  </div>

  <div class="section">
    <h2>Full Results</h2>
    <table>
      <tr>
        <th>ID</th>
        <th>Category</th>
        <th>Severity</th>
        <th>Prompt</th>
        <th>Response</th>
        <th>Judgment</th>
        <th>Notes</th>
      </tr>
      {rows_html}
    </table>
  </div>
</body>
</html>"""

    return html


def generate_comparison_report(
    responses_a: list[ModelResponse],
    judgments_a: list[JudgmentResult],
    responses_b: list[ModelResponse],
    judgments_b: list[JudgmentResult],
    model_a: str,
    model_b: str,
    judge_model: str,
) -> str:
    resp_a = {r.prompt_id: r for r in responses_a}
    resp_b = {r.prompt_id: r for r in responses_b}

    total = len(judgments_a)
    ref_a = sum(1 for j in judgments_a if j.refused)
    ref_b = sum(1 for j in judgments_b if j.refused)
    rate_a = ref_a / total * 100 if total else 0
    rate_b = ref_b / total * 100 if total else 0

    # Disagreements: one model refused, the other didn't
    disagreements = [
        (ja, jb) for ja, jb in zip(judgments_a, judgments_b) if ja.refused != jb.refused
    ]

    # Per-category breakdown
    by_cat: dict[str, dict] = defaultdict(lambda: {"a": [], "b": []})
    for ja, jb in zip(judgments_a, judgments_b):
        by_cat[ja.category]["a"].append(ja)
        by_cat[ja.category]["b"].append(jb)

    cat_rows = ""
    for cat in sorted(by_cat):
        items = by_cat[cat]
        n = len(items["a"])
        ra = sum(1 for j in items["a"] if j.refused)
        rb = sum(1 for j in items["b"] if j.refused)
        bar_a = int(ra / n * 100)
        bar_b = int(rb / n * 100)
        cat_rows += f"""
        <tr>
          <td>{cat}</td>
          <td>
            <div class="bar-bg"><div class="bar-fill model-a" style="width:{bar_a}%"></div></div>
            {ra}/{n} ({bar_a}%)
          </td>
          <td>
            <div class="bar-bg"><div class="bar-fill model-b" style="width:{bar_b}%"></div></div>
            {rb}/{n} ({bar_b}%)
          </td>
        </tr>"""

    # Full comparison table rows
    rows_html = ""
    for ja, jb in zip(judgments_a, judgments_b):
        ra = resp_a.get(ja.prompt_id)
        rb = resp_b.get(jb.prompt_id)

        def cell(j, r):
            badge = (
                '<span class="badge safe">REFUSED</span>'
                if j.refused
                else '<span class="badge unsafe">COMPLIED</span>'
            )
            if j.refused:
                score = f'<span class="score">Quality: {j.refusal_quality}/5</span>'
            else:
                score = f'<span class="score harm">Harm: {j.compliance_harm}/5</span>'
            text = r.response_text if r else ""
            return f'<div class="resp-text">{_escape(text)}</div>{badge} {score}<div class="notes">{_escape(j.notes)}</div>'

        disagree_class = " disagree-row" if ja.refused != jb.refused else ""
        severity_class = {"high": "sev-high", "medium": "sev-med", "low": "sev-low"}.get(
            ja.severity, ""
        )
        prompt_text = ra.prompt_text if ra else ""

        rows_html += f"""
        <tr class="{disagree_class}">
          <td><code>{ja.prompt_id}</code><br><span class="cat">{ja.category}</span><br><span class="{severity_class}">{ja.severity}</span></td>
          <td class="prompt-text">{_escape(prompt_text)}</td>
          <td>{cell(ja, ra)}</td>
          <td>{cell(jb, rb)}</td>
        </tr>"""

    # Disagreement highlight rows (short summary)
    dis_rows = ""
    for ja, jb in disagreements:
        winner = model_a if ja.refused else model_b
        loser = model_b if ja.refused else model_a
        dis_rows += f"""
        <tr>
          <td><code>{ja.prompt_id}</code></td>
          <td><span class="cat">{ja.category}</span></td>
          <td><span class="sev-{ja.severity}">{ja.severity}</span></td>
          <td><span class="badge safe">REFUSED</span> {_escape(winner)}</td>
          <td><span class="badge unsafe">COMPLIED</span> {_escape(loser)}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LLM Safety Comparison Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 0; padding: 24px; background: #f5f5f5; color: #222; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
    .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 24px; }}
    .cards {{ display: flex; gap: 16px; margin-bottom: 32px; flex-wrap: wrap; }}
    .card {{ background: white; border-radius: 8px; padding: 20px 28px;
             box-shadow: 0 1px 3px rgba(0,0,0,.1); min-width: 140px; }}
    .card .num {{ font-size: 2.4rem; font-weight: 700; }}
    .card .label {{ color: #666; font-size: 0.85rem; max-width: 160px; }}
    .card.a .num {{ color: #7c3aed; }}
    .card.b .num {{ color: #0891b2; }}
    .card.warn .num {{ color: #d97706; }}
    h2 {{ font-size: 1.1rem; margin: 0 0 12px; }}
    .section {{ background: white; border-radius: 8px; padding: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    th {{ background: #f9fafb; text-align: left; padding: 8px 12px;
          border-bottom: 2px solid #e5e7eb; font-weight: 600; }}
    th.model-a {{ background: #f5f3ff; color: #7c3aed; }}
    th.model-b {{ background: #ecfeff; color: #0891b2; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
    tr:hover td {{ background: #fafafa; }}
    .disagree-row td {{ background: #fffbeb !important; }}
    .prompt-text {{ max-width: 200px; white-space: pre-wrap; word-break: break-word;
                    font-size: 0.8rem; color: #444; }}
    .resp-text {{ max-width: 260px; white-space: pre-wrap; word-break: break-word;
                  font-size: 0.78rem; color: #555; margin-bottom: 6px; }}
    .notes {{ font-size: 0.75rem; color: #777; margin-top: 4px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px;
              font-size: 0.75rem; font-weight: 600; }}
    .badge.safe {{ background: #dcfce7; color: #16a34a; }}
    .badge.unsafe {{ background: #fee2e2; color: #dc2626; }}
    .score {{ font-size: 0.75rem; color: #666; }}
    .score.harm {{ color: #dc2626; }}
    .cat {{ background: #eff6ff; color: #2563eb; padding: 2px 6px;
            border-radius: 4px; font-size: 0.75rem; }}
    .sev-high {{ color: #dc2626; font-weight: 600; }}
    .sev-med  {{ color: #d97706; font-weight: 600; }}
    .sev-low  {{ color: #16a34a; }}
    .bar-bg {{ display: inline-block; width: 80px; height: 10px; background: #e5e7eb;
               border-radius: 5px; vertical-align: middle; margin-right: 4px; }}
    .bar-fill {{ height: 100%; border-radius: 5px; }}
    .bar-fill.model-a {{ background: #7c3aed; }}
    .bar-fill.model-b {{ background: #0891b2; }}
    code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 0.8rem; }}
    .legend {{ display: flex; gap: 20px; margin-bottom: 12px; font-size: 0.85rem; }}
    .legend-dot {{ width: 12px; height: 12px; border-radius: 50%;
                   display: inline-block; margin-right: 6px; vertical-align: middle; }}
    .dot-a {{ background: #7c3aed; }}
    .dot-b {{ background: #0891b2; }}
  </style>
</head>
<body>
  <h1>LLM Safety — Model Comparison Report</h1>
  <div class="meta">
    Judge model: <strong>{judge_model}</strong> &nbsp;|&nbsp;
    Prompts evaluated: <strong>{total}</strong>
  </div>

  <div class="cards">
    <div class="card a">
      <div class="num">{rate_a:.0f}%</div>
      <div class="label">Refusal rate<br>{model_a}</div>
    </div>
    <div class="card b">
      <div class="num">{rate_b:.0f}%</div>
      <div class="label">Refusal rate<br>{model_b}</div>
    </div>
    <div class="card warn">
      <div class="num">{len(disagreements)}</div>
      <div class="label">Disagreements<br>(one refused, one didn't)</div>
    </div>
  </div>

  <div class="section">
    <h2>Refusal Rate by Category</h2>
    <div class="legend">
      <span><span class="legend-dot dot-a"></span>{model_a}</span>
      <span><span class="legend-dot dot-b"></span>{model_b}</span>
    </div>
    <table>
      <tr>
        <th>Category</th>
        <th class="model-a">{model_a}</th>
        <th class="model-b">{model_b}</th>
      </tr>
      {cat_rows}
    </table>
  </div>

  {'<div class="section"><h2>⚠️ Disagreements — One Refused, One Didn\'t</h2><table><tr><th>ID</th><th>Category</th><th>Severity</th><th>Refused</th><th>Complied</th></tr>' + dis_rows + '</table></div>' if disagreements else ''}

  <div class="section">
    <h2>Full Side-by-Side Results</h2>
    <p style="font-size:0.8rem;color:#666;margin:0 0 12px">
      Highlighted rows = disagreements between models.
    </p>
    <table>
      <tr>
        <th>ID / Category</th>
        <th>Prompt</th>
        <th class="model-a">{model_a}</th>
        <th class="model-b">{model_b}</th>
      </tr>
      {rows_html}
    </table>
  </div>
</body>
</html>"""

    return html


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )

from __future__ import annotations

from html import escape
from pathlib import Path

from scanner.models import Candidate, ScanResult
from scanner.strategy_profile import PROFILE


def _fmt(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def _state_class(candidate: Candidate) -> str:
    return candidate.state.value.replace("_", "-")


def _score_cells(candidate: Candidate) -> str:
    scores = candidate.scores
    values = (
        ("Trend", scores.trend),
        ("Lead", scores.leadership),
        ("Setup", scores.setup),
        ("Momentum", scores.momentum),
        ("Market", scores.market),
        ("Contract", scores.contract),
        ("Risk", scores.risk),
    )
    cells: list[str] = []
    for label, value in values:
        numeric = 0 if value is None else value
        display = "N/A" if value is None else str(value)
        cells.append(
            '<div class="score">'
            f'<span class="score-label">{escape(label)}</span>'
            f'<span class="score-value">{display}</span>'
            '<span class="score-track" aria-hidden="true">'
            f'<span style="width:{numeric}%"></span></span>'
            "</div>"
        )
    return "".join(cells)


def _contract_summary(candidate: Candidate) -> tuple[str, str, str]:
    contract = candidate.contracts.primary
    if contract is None:
        reasons = ", ".join(candidate.contracts.rejection_reasons) or "No eligible chain"
        return (
            "Verify live chain",
            escape(candidate.contracts.feed),
            escape(reasons.replace("_", " ")),
        )
    headline = (
        f"{contract.expiration_date.isoformat()} "
        f"${contract.strike:g} call / {contract.dte} DTE"
    )
    metrics = (
        f"Delta {contract.delta:.2f} / "
        f"${contract.bid:.2f}-${contract.ask:.2f} / "
        f"{contract.spread_percent:.1f}% spread"
    )
    liquidity = (
        f"OI {contract.open_interest:,} / Volume {contract.volume:,} / "
        f"{contract.feed.upper()}"
    )
    return escape(headline), escape(metrics), escape(liquidity)


def _candidate_row(candidate: Candidate) -> str:
    contract, contract_metrics, _ = _contract_summary(candidate)
    leadership = (
        "N/A"
        if candidate.scores.leadership is None
        else str(candidate.scores.leadership)
    )
    search = " ".join(
        (
            candidate.symbol,
            candidate.company,
            candidate.sector,
            candidate.lane.value,
            candidate.state.value,
            candidate.pattern.pattern_type,
        )
    ).lower()
    return f"""
      <tr data-state="{candidate.state.value}" data-lane="{candidate.lane.value}"
          data-pattern="{candidate.pattern.pattern_type}" data-search="{escape(search)}">
        <td>
          <a class="symbol-link" href="#candidate-{escape(candidate.symbol)}">
            {escape(candidate.symbol)}
          </a>
          <span class="subtle">{escape(candidate.lane.label)}</span>
        </td>
        <td>
          <span class="state state-{_state_class(candidate)}">{escape(candidate.state.label)}</span>
          <span class="subtle">{escape(candidate.pattern.status.value.title())}</span>
        </td>
        <td>
          <strong>{escape(candidate.pattern.pattern_type.replace("_", " ").title())}</strong>
          <span class="subtle">Quality {candidate.pattern.quality} / age {candidate.pattern.age_bars}</span>
        </td>
        <td class="numeric">{candidate.scores.trend}</td>
        <td class="numeric">{leadership}</td>
        <td class="numeric">{candidate.scores.momentum}</td>
        <td>
          <strong>{contract}</strong>
          <span class="subtle">{contract_metrics}</span>
        </td>
        <td class="numeric">${candidate.entry_plan.trigger:.2f}</td>
        <td class="numeric">${candidate.entry_plan.invalidation:.2f}</td>
        <td class="numeric">${candidate.entry_plan.target_price:.2f}</td>
      </tr>
    """


def _candidate_detail(candidate: Candidate) -> str:
    contract, contract_metrics, liquidity = _contract_summary(candidate)
    reasons = (
        "".join(
            f"<li>{escape(reason.replace('_', ' ').title())}</li>"
            for reason in candidate.reasons
        )
        or "<li>No pending evidence checks.</li>"
    )
    geometry = "".join(
        f"<li>{escape(note)}</li>" for note in candidate.pattern.geometry_notes
    )
    earnings = (
        candidate.event_risk.earnings_date.isoformat()
        if candidate.event_risk.earnings_date
        else "Unknown"
    )
    return f"""
    <article class="candidate-detail" id="candidate-{escape(candidate.symbol)}"
             data-state="{candidate.state.value}" data-lane="{candidate.lane.value}"
             data-pattern="{candidate.pattern.pattern_type}"
             data-search="{escape((candidate.symbol + ' ' + candidate.company + ' ' + candidate.pattern.pattern_type).lower())}">
      <header class="candidate-header">
        <div>
          <div class="eyebrow">{escape(candidate.lane.label)} / {escape(candidate.sector)}</div>
          <h2>{escape(candidate.symbol)} <span>{escape(candidate.company)}</span></h2>
        </div>
        <span class="state state-{_state_class(candidate)}">{escape(candidate.state.label)}</span>
      </header>

      <div class="level-strip" aria-label="Price plan">
        <div><span>Invalidation</span><strong>${candidate.entry_plan.invalidation:.2f}</strong></div>
        <div><span>Support</span><strong>${candidate.entry_plan.support:.2f}</strong></div>
        <div><span>Last close</span><strong>${candidate.trend.close:.2f}</strong></div>
        <div><span>Trigger</span><strong>${candidate.entry_plan.trigger:.2f}</strong></div>
        <div><span>Objective</span><strong>${candidate.entry_plan.target_price:.2f}</strong></div>
      </div>

      <div class="detail-grid">
        <section>
          <h3>Evidence</h3>
          <div class="score-grid">{_score_cells(candidate)}</div>
        </section>
        <section>
          <h3>Pattern</h3>
          <dl>
            <div><dt>Setup</dt><dd>{escape(candidate.pattern.pattern_type.replace("_", " ").title())}</dd></div>
            <div><dt>Status</dt><dd>{escape(candidate.pattern.status.value.title())}</dd></div>
            <div><dt>Entry</dt><dd>{escape(candidate.entry_plan.status.title())}</dd></div>
            <div><dt>Reward / risk</dt><dd>{_fmt(candidate.entry_plan.reward_to_risk)}</dd></div>
          </dl>
          <ul class="plain-list">{geometry}</ul>
        </section>
        <section>
          <h3>Call Contract</h3>
          <p class="contract-headline">{contract}</p>
          <p>{contract_metrics}</p>
          <p>{liquidity}</p>
          <p class="subtle">Contract score {candidate.contracts.score}. Live chain remains authoritative.</p>
        </section>
        <section>
          <h3>Risk Controls</h3>
          <dl>
            <div><dt>Event status</dt><dd>{escape(candidate.event_risk.status.value.title())}</dd></div>
            <div><dt>Earnings</dt><dd>{escape(earnings)}</dd></div>
            <div><dt>Hold window</dt><dd>{candidate.entry_plan.intended_hold_sessions[0]}-{candidate.entry_plan.intended_hold_sessions[1]} sessions</dd></div>
            <div><dt>Requalify</dt><dd>{candidate.entry_plan.requalify_dte} DTE</dd></div>
          </dl>
          <ul class="plain-list">{reasons}</ul>
        </section>
      </div>
    </article>
    """


def render_dashboard(result: ScanResult) -> str:
    candidates = result.candidates
    rows = "".join(_candidate_row(candidate) for candidate in candidates)
    details = "".join(_candidate_detail(candidate) for candidate in candidates)
    if not rows:
        rows = (
            '<tr><td colspan="10" class="empty">'
            "No bullish candidates qualified for review.</td></tr>"
        )
        details = (
            '<section class="empty-state"><h2>No qualified setup</h2>'
            "<p>Cash is a valid state. Review rejected diagnostics and wait for "
            "completed candles.</p></section>"
        )
    rejected_rows = "".join(
        "<tr>"
        f"<td>{escape(record.symbol)}</td>"
        f"<td>{escape(record.stage.replace('_', ' ').title())}</td>"
        f"<td>{escape(', '.join(code.replace('_', ' ') for code in record.reason_codes))}</td>"
        "</tr>"
        for record in result.rejected
    )
    if not rejected_rows:
        rejected_rows = '<tr><td colspan="3" class="empty">No rejected records.</td></tr>'
    fixture = (
        '<span class="fixture">SIMULATED FIXTURE - NOT CURRENT MARKET DATA</span>'
        if result.fixture
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(PROFILE.name)} - {escape(result.scan_type.value.replace("_", " ").title())}</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17212b;
      --muted: #65717d;
      --line: #d8dee5;
      --surface: #ffffff;
      --canvas: #f4f6f8;
      --green: #147d4f;
      --green-soft: #e7f4ed;
      --blue: #1f5a94;
      --blue-soft: #eaf2fa;
      --amber: #9a5b08;
      --amber-soft: #fff3db;
      --red: #a13939;
      --red-soft: #fbecec;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--canvas);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      letter-spacing: 0;
    }}
    a {{ color: inherit; }}
    .shell {{ max-width: 1520px; margin: 0 auto; background: var(--surface); min-height: 100vh; }}
    .topbar {{
      display: flex; justify-content: space-between; gap: 24px; align-items: flex-end;
      padding: 24px 28px 18px; border-bottom: 1px solid var(--line);
    }}
    .eyebrow {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    h1 {{ margin: 5px 0 0; font-size: 28px; line-height: 1.1; }}
    h2 {{ margin: 4px 0 0; font-size: 22px; }}
    h2 span {{ color: var(--muted); font-size: 14px; font-weight: 500; }}
    h3 {{ margin: 0 0 12px; font-size: 14px; text-transform: uppercase; color: var(--muted); }}
    .run-meta {{ text-align: right; color: var(--muted); line-height: 1.6; }}
    .fixture {{
      display: inline-block; padding: 4px 7px; background: var(--amber-soft); color: var(--amber);
      border: 1px solid #efd29b; font-size: 11px; font-weight: 800;
    }}
    .market-band {{
      display: grid; grid-template-columns: 180px repeat(5, minmax(120px, 1fr));
      border-bottom: 1px solid var(--line); background: #fbfcfd;
    }}
    .market-band > div {{ padding: 16px 20px; border-right: 1px solid var(--line); }}
    .market-band > div:last-child {{ border-right: 0; }}
    .market-band span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; }}
    .market-band strong {{ display: block; margin-top: 4px; font-size: 18px; }}
    .regime-supportive strong {{ color: var(--green); }}
    .regime-mixed strong {{ color: var(--amber); }}
    .regime-hostile strong {{ color: var(--red); }}
    .controls {{
      display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
      padding: 14px 20px; border-bottom: 1px solid var(--line); position: sticky; top: 0;
      z-index: 10; background: rgba(255,255,255,.97);
    }}
    .segments {{ display: flex; border: 1px solid var(--line); }}
    button, input, select {{
      min-height: 36px; border: 1px solid var(--line); background: white; color: var(--ink);
      font: inherit; border-radius: 4px;
    }}
    button {{ padding: 0 12px; cursor: pointer; border: 0; border-right: 1px solid var(--line); border-radius: 0; }}
    button:last-child {{ border-right: 0; }}
    button.active {{ background: var(--ink); color: white; }}
    input {{ width: min(320px, 100%); padding: 0 10px; }}
    select {{ padding: 0 30px 0 10px; }}
    .count {{ margin-left: auto; color: var(--muted); font-variant-numeric: tabular-nums; }}
    .table-wrap {{ overflow-x: auto; border-bottom: 1px solid var(--line); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      padding: 10px 12px; text-align: left; color: var(--muted); font-size: 11px;
      text-transform: uppercase; background: #fbfcfd; border-bottom: 1px solid var(--line);
      white-space: nowrap;
    }}
    td {{ padding: 12px; border-bottom: 1px solid #e8ecf0; vertical-align: top; }}
    tbody tr:hover {{ background: #f8fafb; }}
    .numeric {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .symbol-link {{ font-weight: 800; font-size: 15px; text-decoration: none; }}
    .subtle {{ display: block; color: var(--muted); margin-top: 3px; font-size: 12px; }}
    .state {{ display: inline-block; padding: 3px 6px; border: 1px solid; font-size: 11px; font-weight: 800; }}
    .state-ready {{ color: var(--green); background: var(--green-soft); border-color: #9fcdb5; }}
    .state-ready-verify, .state-verify-contract {{
      color: var(--amber); background: var(--amber-soft); border-color: #e9c57f;
    }}
    .state-developing {{ color: var(--blue); background: var(--blue-soft); border-color: #a9c7e4; }}
    .candidate-detail {{ padding: 26px 28px; border-bottom: 1px solid var(--line); scroll-margin-top: 80px; }}
    .candidate-header {{ display: flex; justify-content: space-between; align-items: center; gap: 18px; }}
    .level-strip {{
      display: grid; grid-template-columns: repeat(5, 1fr); margin: 20px 0;
      border: 1px solid var(--line); background: #fbfcfd;
    }}
    .level-strip > div {{ padding: 12px 14px; border-right: 1px solid var(--line); }}
    .level-strip > div:last-child {{ border-right: 0; }}
    .level-strip span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; }}
    .level-strip strong {{ display: block; margin-top: 4px; font-size: 16px; font-variant-numeric: tabular-nums; }}
    .detail-grid {{ display: grid; grid-template-columns: 1.35fr 1fr 1fr 1fr; gap: 0; border-top: 1px solid var(--line); }}
    .detail-grid > section {{ padding: 18px 20px 0 0; margin-right: 20px; border-right: 1px solid var(--line); }}
    .detail-grid > section:last-child {{ border-right: 0; margin-right: 0; }}
    .score-grid {{ display: grid; grid-template-columns: repeat(2, minmax(120px, 1fr)); gap: 10px 16px; }}
    .score {{ display: grid; grid-template-columns: 78px 32px 1fr; align-items: center; gap: 8px; }}
    .score-label {{ color: var(--muted); font-size: 12px; }}
    .score-value {{ text-align: right; font-weight: 800; font-variant-numeric: tabular-nums; }}
    .score-track {{ height: 5px; background: #e4e8ec; overflow: hidden; }}
    .score-track span {{ display: block; height: 100%; background: var(--green); }}
    dl {{ margin: 0; }}
    dl > div {{ display: flex; justify-content: space-between; gap: 16px; padding: 6px 0; border-bottom: 1px solid #edf0f2; }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; text-align: right; font-weight: 600; }}
    .plain-list {{ margin: 10px 0 0; padding-left: 18px; color: var(--muted); }}
    .plain-list li {{ margin: 5px 0; }}
    .contract-headline {{ font-weight: 800; }}
    details {{ padding: 22px 28px; border-bottom: 1px solid var(--line); }}
    summary {{ cursor: pointer; font-weight: 800; }}
    .empty, .empty-state {{ padding: 36px; text-align: center; color: var(--muted); }}
    .footer {{ padding: 22px 28px 34px; color: var(--muted); line-height: 1.6; }}
    [hidden] {{ display: none !important; }}
    @media (max-width: 980px) {{
      .market-band {{ grid-template-columns: repeat(3, 1fr); }}
      .detail-grid {{ grid-template-columns: 1fr 1fr; }}
      .detail-grid > section:nth-child(2) {{ border-right: 0; }}
      .level-strip {{ grid-template-columns: repeat(3, 1fr); }}
    }}
    @media (max-width: 640px) {{
      .topbar {{ align-items: flex-start; flex-direction: column; padding: 20px; }}
      .run-meta {{ text-align: left; }}
      .market-band {{ grid-template-columns: 1fr 1fr; }}
      .controls {{ position: static; padding: 12px; }}
      .segments {{ width: 100%; overflow-x: auto; }}
      button {{ flex: 1 0 auto; }}
      input, select {{ width: 100%; }}
      .count {{ margin-left: 0; }}
      .candidate-detail {{ padding: 22px 18px; }}
      .candidate-header {{ align-items: flex-start; }}
      .level-strip, .detail-grid {{ grid-template-columns: 1fr; }}
      .level-strip > div, .detail-grid > section {{
        border-right: 0; border-bottom: 1px solid var(--line); margin-right: 0; padding: 12px 0;
      }}
      .score-grid {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{ background: white; }}
      .controls {{ display: none; }}
      .shell {{ max-width: none; }}
      .candidate-detail {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
<main class="shell">
  <header class="topbar">
    <div>
      <div class="eyebrow">Ali Swing Suite / Read-only research</div>
      <h1>{escape(PROFILE.name)}</h1>
    </div>
    <div class="run-meta">
      {fixture}
      <div>{escape(result.scan_type.value.replace("_", " ").title())}</div>
      <div>Generated {escape(result.generated_at.isoformat())}</div>
      <div>Market data {escape(result.market_data_timestamp.isoformat())}</div>
    </div>
  </header>

  <section class="market-band" aria-label="Market context">
    <div class="regime-{escape(result.market.regime.lower())}">
      <span>Regime</span><strong>{escape(result.market.regime)}</strong>
    </div>
    <div><span>Market score</span><strong>{result.market.score}/100</strong></div>
    <div><span>Breadth above 50D</span><strong>{result.market.breadth_above_sma50:.1f}%</strong></div>
    <div><span>Breadth above 21D</span><strong>{result.market.breadth_above_ema21:.1f}%</strong></div>
    <div><span>Evaluated</span><strong>{result.evaluated_count}/{result.universe_count}</strong></div>
    <div><span>Ready / verify</span><strong>{len(result.ready)} / {len(result.ready_verify) + len(result.verify_contract)}</strong></div>
  </section>

  <section class="controls" aria-label="Candidate filters">
    <div class="segments" role="group" aria-label="Review state">
      <button type="button" class="active" data-filter-state="all">All</button>
      <button type="button" data-filter-state="ready">Ready</button>
      <button type="button" data-filter-state="ready_verify">Ready - Verify</button>
      <button type="button" data-filter-state="verify_contract">Verify Contract</button>
      <button type="button" data-filter-state="developing">Developing</button>
    </div>
    <input id="search" type="search" placeholder="Search symbol, lane, sector, or pattern" aria-label="Search candidates">
    <select id="lane" aria-label="Filter by strategy lane">
      <option value="all">All lanes</option>
      <option value="index_core">Index Core</option>
      <option value="leader_swing">Leader Swing</option>
    </select>
    <span class="count"><span id="visible-count">{len(candidates)}</span> candidates shown</span>
  </section>

  <div class="table-wrap">
    <table id="candidate-table">
      <thead>
        <tr>
          <th>Symbol</th><th>State</th><th>Pattern</th><th class="numeric">Trend</th>
          <th class="numeric">Lead</th><th class="numeric">Momentum</th><th>Call contract</th>
          <th class="numeric">Trigger</th><th class="numeric">Invalidation</th><th class="numeric">Objective</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <section id="candidate-details">{details}</section>

  <details>
    <summary>Rejected diagnostics ({len(result.rejected)})</summary>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Symbol</th><th>Stage</th><th>Reason codes</th></tr></thead>
        <tbody>{rejected_rows}</tbody>
      </table>
    </div>
  </details>

  <footer class="footer">
    Scores rank evidence; they are not probabilities. This screener does not place orders or access
    brokerage accounts. Indicative option data requires live broker verification. A long call can
    lose the full premium paid. Use the underlying invalidation, avoid earnings-event exposure,
    reassess after five sessions without meaningful progress, and fully requalify by the lane's
    DTE boundary.
  </footer>
</main>
<script>
  (() => {{
    const buttons = [...document.querySelectorAll("[data-filter-state]")];
    const search = document.querySelector("#search");
    const lane = document.querySelector("#lane");
    const count = document.querySelector("#visible-count");
    const records = [
      ...document.querySelectorAll("#candidate-table tbody tr[data-state], .candidate-detail")
    ];
    let state = "all";
    const apply = () => {{
      const query = search.value.trim().toLowerCase();
      const laneValue = lane.value;
      let visibleRows = 0;
      records.forEach((record) => {{
        const matchesState = state === "all" || record.dataset.state === state;
        const matchesLane = laneValue === "all" || record.dataset.lane === laneValue;
        const matchesSearch = !query || (record.dataset.search || "").includes(query);
        const visible = matchesState && matchesLane && matchesSearch;
        record.hidden = !visible;
        if (visible && record.matches("tr")) visibleRows += 1;
      }});
      count.textContent = String(visibleRows);
    }};
    buttons.forEach((button) => button.addEventListener("click", () => {{
      buttons.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state = button.dataset.filterState;
      apply();
    }}));
    search.addEventListener("input", apply);
    lane.addEventListener("change", apply);
  }})();
</script>
</body>
</html>
"""


def write_dashboard(result: ScanResult, folder: Path) -> Path:
    path = folder / "latest.html"
    path.write_text(render_dashboard(result), encoding="utf-8")
    return path

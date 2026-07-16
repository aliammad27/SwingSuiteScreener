from __future__ import annotations

import json
from html import escape
from pathlib import Path

from scanner.models import Candidate, ContractRiskMetrics, ScanResult
from scanner.strategy_profile import PROFILE


def _fmt(value: float | None, digits: int = 2, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value:.{digits}f}{suffix}"


def _price(value: float | None) -> str:
    return "N/A" if value is None else f"${value:.2f}"


def _state_class(candidate: Candidate) -> str:
    return candidate.state.value.replace("_", "-")


def _score_cells(candidate: Candidate) -> str:
    scores = candidate.scores
    values = (
        ("Trend", scores.trend),
        ("Lead", scores.leadership),
        ("Setup", scores.setup),
        ("Timing", scores.timing),
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
            f"<span>{escape(label)}</span>"
            f"<strong>{display}</strong>"
            '<span class="score-track" aria-hidden="true">'
            f'<span style="width:{numeric}%"></span></span>'
            "</div>"
        )
    return "".join(cells)


def _contract_items(
    candidate: Candidate,
) -> tuple[tuple[str, object, ContractRiskMetrics | None], ...]:
    selection = candidate.contracts
    items: list[tuple[str, object, ContractRiskMetrics | None]] = []
    if selection.primary is not None:
        items.append(("Primary", selection.primary, selection.primary_risk))
    for index, contract in enumerate(selection.alternatives):
        risk = (
            selection.alternative_risks[index]
            if index < len(selection.alternative_risks)
            else None
        )
        items.append((f"Alternative {index + 1}", contract, risk))
    return tuple(items)


def _contract_summary(candidate: Candidate) -> tuple[str, str, str]:
    contract = candidate.contracts.primary
    risk = candidate.contracts.primary_risk
    if contract is None:
        reasons = ", ".join(candidate.contracts.rejection_reasons) or "No eligible chain"
        return (
            "Verify live chain",
            candidate.contracts.feed.upper(),
            reasons.replace("_", " "),
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
    risk_text = (
        f"Theta/ask {_fmt(risk.theta_ask_percent, 2, '%')} / "
        f"age {_fmt(risk.quote_age_minutes, 2, 'm')} / "
        f"depth {risk.depth_contracts}"
        if risk is not None
        else "Contract risk metrics unavailable"
    )
    return headline, metrics, risk_text


def _candidate_row(candidate: Candidate) -> str:
    contract = candidate.contracts.primary
    risk = candidate.contracts.primary_risk
    contract_headline, contract_metrics, _ = _contract_summary(candidate)
    leadership = candidate.scores.leadership
    dte = contract.dte if contract is not None else -1
    delta = contract.delta if contract is not None else -1.0
    spread = contract.spread_percent if contract is not None else -1.0
    theta = (
        risk.theta_ask_percent
        if risk is not None and risk.theta_ask_percent is not None
        else -1.0
    )
    quote_age = risk.quote_age_minutes if risk is not None else -1.0
    trust = "trusted" if candidate.data_trust.trustworthy else "verify"
    state_rank = {
        "ready": 4,
        "ready_verify": 3,
        "verify_contract": 2,
        "developing": 1,
    }.get(candidate.state.value, 0)
    search = " ".join(
        (
            candidate.symbol,
            candidate.company,
            candidate.sector,
            candidate.lane.value,
            candidate.state.value,
            candidate.pattern.pattern_type,
            contract_headline,
        )
    ).lower()
    return f"""
      <tr data-symbol="{escape(candidate.symbol)}"
          data-state="{candidate.state.value}"
          data-lane="{candidate.lane.value}"
          data-pattern="{candidate.pattern.pattern_type}"
          data-trust="{trust}"
          data-dte="{dte}"
          data-search="{escape(search)}"
          data-sort-symbol="{escape(candidate.symbol)}"
          data-sort-state="{state_rank}"
          data-sort-lane="{escape(candidate.lane.value)}"
          data-sort-pattern="{escape(candidate.pattern.pattern_type)}"
          data-sort-trend="{candidate.scores.trend}"
          data-sort-lead="{leadership if leadership is not None else -1}"
          data-sort-timing="{candidate.scores.timing}"
          data-sort-contract="{candidate.scores.contract}"
          data-sort-dte="{dte}"
          data-sort-delta="{delta}"
          data-sort-spread="{spread}"
          data-sort-theta="{theta}"
          data-sort-age="{quote_age}"
          data-sort-trust="{1 if trust == 'trusted' else 0}"
          data-sort-trigger="{candidate.entry_plan.trigger}"
          data-compare-symbol="{escape(candidate.symbol)}"
          data-compare-state="{escape(candidate.state.label)}"
          data-compare-pattern="{escape(candidate.pattern.pattern_type.replace('_', ' ').title())}"
          data-compare-contract="{escape(contract_headline)}"
          data-compare-timing="{candidate.scores.timing}"
          data-compare-trigger="{candidate.entry_plan.trigger:.2f}"
          data-compare-warning="{candidate.entry_plan.tactical_warning:.2f}"
          data-compare-structural="{candidate.entry_plan.invalidation:.2f}"
          data-compare-target="{candidate.entry_plan.target_price:.2f}">
        <td class="compare-cell">
          <input class="compare-toggle" type="checkbox"
                 aria-label="Compare {escape(candidate.symbol)}">
        </td>
        <td>
          <a class="symbol-link" href="#candidate-{escape(candidate.symbol)}">{escape(candidate.symbol)}</a>
          <span class="subtle">{escape(candidate.sector)}</span>
        </td>
        <td>
          <span class="state state-{_state_class(candidate)}">{escape(candidate.state.label)}</span>
          <span class="subtle">{escape(candidate.timing.state)}</span>
        </td>
        <td>{escape(candidate.lane.label)}</td>
        <td>
          <strong>{escape(candidate.pattern.pattern_type.replace("_", " ").title())}</strong>
          <span class="subtle">{escape(candidate.pattern.status.value.title())} / Q{candidate.pattern.quality}</span>
        </td>
        <td class="numeric">{candidate.scores.trend}</td>
        <td class="numeric">{leadership if leadership is not None else "N/A"}</td>
        <td class="numeric">{candidate.scores.timing}</td>
        <td class="numeric">{candidate.scores.contract}</td>
        <td>
          <strong>{escape(contract_headline)}</strong>
          <span class="subtle">{escape(contract_metrics)}</span>
        </td>
        <td class="numeric">{dte if dte >= 0 else "N/A"}</td>
        <td class="numeric">{_fmt(delta if delta >= 0 else None)}</td>
        <td class="numeric">{_fmt(spread if spread >= 0 else None, 1, "%")}</td>
        <td class="numeric">{_fmt(theta if theta >= 0 else None, 2, "%")}</td>
        <td class="numeric">{_fmt(quote_age if quote_age >= 0 else None, 2, "m")}</td>
        <td><span class="trust trust-{trust}">{trust.title()}</span></td>
        <td class="numeric">${candidate.entry_plan.trigger:.2f}</td>
      </tr>
    """


def _contract_table(candidate: Candidate) -> str:
    items = _contract_items(candidate)
    if not items:
        reasons = ", ".join(candidate.contracts.rejection_reasons) or "chain unavailable"
        return (
            '<p class="diagnostic">'
            f"Contract verification required: {escape(reasons.replace('_', ' '))}."
            "</p>"
        )
    rows: list[str] = []
    for label, raw_contract, risk in items:
        from scanner.models import OptionContractSnapshot

        if not isinstance(raw_contract, OptionContractSnapshot):
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(label)}</td>"
            f"<td>{escape(raw_contract.contract_symbol)}</td>"
            f"<td>{raw_contract.expiration_date.isoformat()}</td>"
            f"<td class=\"numeric\">{raw_contract.dte}</td>"
            f"<td class=\"numeric\">${raw_contract.strike:.2f}</td>"
            f"<td class=\"numeric\">{raw_contract.delta:.2f}</td>"
            f"<td class=\"numeric\">{raw_contract.spread_percent:.1f}%</td>"
            f"<td class=\"numeric\">{raw_contract.open_interest:,}</td>"
            f"<td class=\"numeric\">{raw_contract.volume:,}</td>"
            f"<td class=\"numeric\">{min(raw_contract.bid_size, raw_contract.ask_size):,}</td>"
            f"<td class=\"numeric\">{_fmt(risk.theta_ask_percent if risk else None, 2, '%')}</td>"
            f"<td class=\"numeric\">{_fmt(risk.quote_age_minutes if risk else None, 2, 'm')}</td>"
            f"<td>{escape(risk.expiration_style if risk else 'unknown')}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap compact"><table>'
        "<thead><tr><th>Rank</th><th>Contract</th><th>Expiry</th><th>DTE</th>"
        "<th>Strike</th><th>Delta</th><th>Spread</th><th>OI</th><th>Vol</th>"
        "<th>Depth</th><th>Theta/ask</th><th>Quote age</th><th>Expiry type</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _candidate_detail(candidate: Candidate) -> str:
    reasons = (
        "".join(
            f"<li>{escape(reason.replace('_', ' ').title())}</li>"
            for reason in candidate.reasons
        )
        or "<li>No pending classification checks.</li>"
    )
    trust_reasons = (
        "".join(
            f"<li>{escape(reason.replace('_', ' ').title())}</li>"
            for reason in candidate.data_trust.reasons
        )
        or "<li>SIP, OPRA, event-source, quote-age, and quote-stability checks passed.</li>"
    )
    timing_reasons = (
        "".join(
            f"<li>{escape(reason.replace('_', ' ').title())}</li>"
            for reason in candidate.timing.reasons
        )
        or "<li>Completed-hour timing checks passed.</li>"
    )
    geometry = "".join(
        f"<li>{escape(note)}</li>" for note in candidate.pattern.geometry_notes
    )
    event_windows = (
        "".join(
            "<li>"
            f"{escape(window.event_type.value.replace('_', ' ').title())}: "
            f"{escape(window.event_at.isoformat())} through "
            f"{escape(window.blocked_until.isoformat())}"
            "</li>"
            for window in candidate.event_risk.windows
        )
        or "<li>No active event window.</li>"
    )
    plan = candidate.entry_plan
    return f"""
    <article class="candidate-detail" id="candidate-{escape(candidate.symbol)}"
             data-symbol="{escape(candidate.symbol)}"
             data-state="{candidate.state.value}"
             data-lane="{candidate.lane.value}"
             data-pattern="{candidate.pattern.pattern_type}"
             data-trust="{'trusted' if candidate.data_trust.trustworthy else 'verify'}"
             data-dte="{candidate.contracts.primary.dte if candidate.contracts.primary else -1}"
             data-search="{escape((candidate.symbol + ' ' + candidate.company + ' ' + candidate.pattern.pattern_type).lower())}">
      <header class="candidate-header">
        <div>
          <div class="eyebrow">{escape(candidate.lane.label)} / {escape(candidate.sector)} / {escape(candidate.peer_etf)}</div>
          <h2>{escape(candidate.symbol)} <span>{escape(candidate.company)}</span></h2>
        </div>
        <span class="state state-{_state_class(candidate)}">{escape(candidate.state.label)}</span>
      </header>

      <div class="level-strip" aria-label="Planning levels">
        <div><span>Structural invalidation</span><strong>{_price(plan.invalidation)}</strong></div>
        <div><span>Tactical failure</span><strong>{_price(plan.tactical_failure)}</strong></div>
        <div><span>Tactical warning</span><strong>{_price(plan.tactical_warning)}</strong></div>
        <div><span>Support</span><strong>{_price(plan.support)}</strong></div>
        <div><span>Last close</span><strong>{_price(candidate.trend.close)}</strong></div>
        <div><span>Trigger</span><strong>{_price(plan.trigger)}</strong></div>
        <div><span>Confirmed pivot</span><strong>{_price(plan.resistance_level)}</strong></div>
        <div><span>2R plan</span><strong>{_price(plan.planning_objective_2r)}</strong></div>
        <div><span>Selected target</span><strong>{_price(plan.target_price)}</strong></div>
      </div>

      <div class="detail-grid">
        <section>
          <h3>Evidence</h3>
          <div class="score-grid">{_score_cells(candidate)}</div>
          <dl>
            <div><dt>Pattern</dt><dd>{escape(candidate.pattern.pattern_type.replace("_", " ").title())}</dd></div>
            <div><dt>Lifecycle</dt><dd>{escape(candidate.pattern.status.value.title())} / age {candidate.pattern.age_bars}</dd></div>
            <div><dt>Target basis</dt><dd>{escape(plan.target_basis)}</dd></div>
            <div><dt>Reward / risk</dt><dd>{_fmt(plan.reward_to_risk)}</dd></div>
          </dl>
          <ul>{geometry}</ul>
        </section>

        <section>
          <h3>Completed 60-Minute Timing</h3>
          <dl>
            <div><dt>Completed</dt><dd>{escape(candidate.timing.completed_at.isoformat())}</dd></div>
            <div><dt>EMA9 / EMA21</dt><dd>{_price(candidate.timing.ema9)} / {_price(candidate.timing.ema21)}</dd></div>
            <div><dt>Session VWAP</dt><dd>{_price(candidate.timing.session_vwap)}</dd></div>
            <div><dt>RSI / MACD hist</dt><dd>{candidate.timing.rsi:.1f} / {candidate.timing.macd_histogram:.3f}</dd></div>
            <div><dt>Relative volume</dt><dd>{candidate.timing.relative_volume:.2f}x</dd></div>
            <div><dt>Structure</dt><dd>{'Higher low' if candidate.timing.higher_low else 'No higher low'} / {'Reclaim' if candidate.timing.reclaim else 'No reclaim'}</dd></div>
            <div><dt>Index confirmation</dt><dd>{'Pass' if candidate.timing.market_confirmation else 'Fail'}</dd></div>
            <div><dt>Entry permission</dt><dd>{'Open' if candidate.timing.entry_window_open else 'Management only'}</dd></div>
          </dl>
          <ul>{timing_reasons}</ul>
        </section>

        <section>
          <h3>Data And Event Trust</h3>
          <dl>
            <div><dt>Stock feed</dt><dd>{escape(candidate.data_trust.stock_feed.upper())}</dd></div>
            <div><dt>Option feed</dt><dd>{escape(candidate.data_trust.option_feed.upper())}</dd></div>
            <div><dt>Event source</dt><dd>{escape(candidate.data_trust.event_source)}</dd></div>
            <div><dt>Quote age</dt><dd>{_fmt(candidate.data_trust.quote_age_minutes, 2, 'm')}</dd></div>
            <div><dt>Event status</dt><dd>{escape(candidate.event_risk.status.value.title())}</dd></div>
            <div><dt>Earnings</dt><dd>{candidate.event_risk.earnings_date.isoformat() if candidate.event_risk.earnings_date else 'None in trusted horizon'}</dd></div>
          </dl>
          <ul>{trust_reasons}</ul>
          <ul>{event_windows}</ul>
        </section>

        <section>
          <h3>Management</h3>
          <dl>
            <div><dt>Hold window</dt><dd>{plan.intended_hold_sessions[0]}-{plan.intended_hold_sessions[1]} sessions</dd></div>
            <div><dt>No-progress review</dt><dd>{plan.no_progress_sessions} sessions</dd></div>
            <div><dt>DTE requalification</dt><dd>{plan.requalify_dte} DTE</dd></div>
            <div><dt>Contract re-quotes</dt><dd>{candidate.contracts.requoted_count}</dd></div>
            <div><dt>Validation state</dt><dd>{escape(PROFILE.validation_state)}</dd></div>
          </dl>
          <ul>{reasons}</ul>
        </section>
      </div>

      <section class="contract-band">
        <h3>Contract Alternatives</h3>
        {_contract_table(candidate)}
      </section>
    </article>
    """


def _sort_header(label: str, key: str, numeric: bool = False) -> str:
    class_name = ' class="numeric"' if numeric else ""
    return (
        f"<th{class_name}><button class=\"sort-button\" type=\"button\" "
        f"data-sort-key=\"{key}\" data-sort-type=\"{'number' if numeric else 'text'}\">"
        f"{escape(label)} <span aria-hidden=\"true\">&#8597;</span></button></th>"
    )


def render_dashboard(result: ScanResult) -> str:
    candidates = result.candidates
    rows = "".join(_candidate_row(candidate) for candidate in candidates)
    details = "".join(_candidate_detail(candidate) for candidate in candidates)
    if not rows:
        rows = (
            '<tr><td colspan="17" class="empty">'
            "No bullish candidates qualified for review.</td></tr>"
        )
        details = (
            '<section class="empty-state"><h2>No qualified setup</h2>'
            "<p>Review the rejection table for the failed gate.</p></section>"
        )
    rejected_rows = "".join(
        "<tr>"
        f"<td>{escape(record.symbol)}</td>"
        f"<td>{escape(record.stage.replace('_', ' ').title())}</td>"
        f"<td>{escape(', '.join(code.replace('_', ' ') for code in record.reason_codes))}</td>"
        f"<td><code>{escape(json.dumps(record.details, default=str, sort_keys=True))}</code></td>"
        "</tr>"
        for record in result.rejected
    )
    if not rejected_rows:
        rejected_rows = '<tr><td colspan="4" class="empty">No rejected records.</td></tr>'
    fixture = (
        '<span class="fixture">SIMULATED FIXTURE - NOT CURRENT MARKET DATA</span>'
        if result.fixture
        else ""
    )
    pattern_options = "".join(
        f'<option value="{escape(pattern)}">{escape(pattern.replace("_", " ").title())}</option>'
        for pattern in sorted({candidate.pattern.pattern_type for candidate in candidates})
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
      --ink: #182128;
      --muted: #65717a;
      --line: #d5dce1;
      --line-soft: #e9edf0;
      --surface: #ffffff;
      --canvas: #f3f5f6;
      --green: #176b45;
      --green-soft: #e8f3ed;
      --blue: #285e8f;
      --blue-soft: #eaf1f7;
      --amber: #8a570e;
      --amber-soft: #fff3d8;
      --red: #9b3d3d;
      --red-soft: #faecec;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0; background: var(--canvas); color: var(--ink);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 13px; letter-spacing: 0;
    }}
    a {{ color: inherit; }}
    button, input, select {{ font: inherit; letter-spacing: 0; }}
    .shell {{ max-width: 1760px; margin: 0 auto; min-height: 100vh; background: var(--surface); }}
    .topbar {{
      display: flex; justify-content: space-between; align-items: flex-end; gap: 20px;
      padding: 18px 22px 14px; border-bottom: 1px solid var(--line);
    }}
    .eyebrow {{ color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    h1 {{ margin: 4px 0 0; font-size: 24px; line-height: 1.15; }}
    h2 {{ margin: 3px 0 0; font-size: 19px; }}
    h2 span {{ color: var(--muted); font-size: 13px; font-weight: 500; }}
    h3 {{ margin: 0 0 10px; color: var(--muted); font-size: 11px; text-transform: uppercase; }}
    .run-meta {{ color: var(--muted); text-align: right; line-height: 1.55; }}
    .fixture {{
      display: inline-block; padding: 3px 6px; border: 1px solid #e5c27a;
      background: var(--amber-soft); color: var(--amber); font-size: 10px; font-weight: 800;
    }}
    .market-band {{
      display: grid; grid-template-columns: repeat(7, minmax(120px, 1fr));
      border-bottom: 1px solid var(--line); background: #fbfcfc;
    }}
    .market-band > div {{ min-width: 0; padding: 11px 14px; border-right: 1px solid var(--line); }}
    .market-band > div:last-child {{ border-right: 0; }}
    .market-band span {{ display: block; color: var(--muted); font-size: 10px; text-transform: uppercase; }}
    .market-band strong {{ display: block; margin-top: 3px; font-size: 15px; overflow-wrap: anywhere; }}
    .regime-supportive strong {{ color: var(--green); }}
    .regime-mixed strong {{ color: var(--amber); }}
    .regime-hostile strong {{ color: var(--red); }}
    .controls {{
      position: sticky; top: 0; z-index: 12; display: grid;
      grid-template-columns: minmax(180px, 1.6fr) repeat(5, minmax(130px, .7fr)) auto;
      gap: 8px; align-items: center; padding: 9px 12px;
      border-bottom: 1px solid var(--line); background: rgba(255,255,255,.98);
    }}
    input, select {{
      width: 100%; min-width: 0; height: 34px; padding: 0 9px;
      border: 1px solid var(--line); border-radius: 3px; background: white; color: var(--ink);
    }}
    .count {{ color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }}
    .compare-panel {{ border-bottom: 1px solid var(--line); background: #fbfcfc; }}
    .compare-panel[hidden] {{ display: none; }}
    .compare-panel header {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 9px 12px; border-bottom: 1px solid var(--line-soft);
    }}
    .compare-panel h2 {{ margin: 0; font-size: 14px; }}
    .icon-button {{
      width: 30px; height: 30px; border: 1px solid var(--line); border-radius: 3px;
      background: white; cursor: pointer; font-size: 18px; line-height: 1;
    }}
    .table-wrap {{ width: 100%; overflow-x: auto; }}
    .table-wrap.compact {{ border: 1px solid var(--line-soft); }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; }}
    #candidate-table {{ min-width: 1640px; }}
    th {{
      position: static; padding: 0; color: var(--muted);
      background: #f8fafb; border-bottom: 1px solid var(--line);
      font-size: 10px; text-align: left; text-transform: uppercase; white-space: nowrap;
    }}
    th.numeric {{ text-align: right; }}
    .sort-button {{
      width: 100%; padding: 9px 8px; border: 0; background: transparent; color: inherit;
      cursor: pointer; text-align: inherit; text-transform: inherit;
    }}
    td {{ padding: 8px; border-bottom: 1px solid var(--line-soft); vertical-align: top; }}
    tbody tr:hover {{ background: #f7f9fa; }}
    .numeric {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .compare-cell {{ width: 32px; text-align: center; }}
    .compare-toggle {{ width: 16px; height: 16px; accent-color: var(--green); }}
    .symbol-link {{ font-size: 14px; font-weight: 800; text-decoration: none; }}
    .subtle {{ display: block; margin-top: 2px; color: var(--muted); font-size: 11px; }}
    .state, .trust {{
      display: inline-block; padding: 2px 5px; border: 1px solid;
      font-size: 10px; font-weight: 800; white-space: nowrap;
    }}
    .state-ready {{ color: var(--green); background: var(--green-soft); border-color: #9fc9b2; }}
    .state-ready-verify, .state-verify-contract {{
      color: var(--amber); background: var(--amber-soft); border-color: #e2bf77;
    }}
    .state-developing {{ color: var(--blue); background: var(--blue-soft); border-color: #a9c3dc; }}
    .trust-trusted {{ color: var(--green); background: var(--green-soft); border-color: #9fc9b2; }}
    .trust-verify {{ color: var(--amber); background: var(--amber-soft); border-color: #e2bf77; }}
    .candidate-detail {{ padding: 18px 22px; border-top: 1px solid var(--line); scroll-margin-top: 90px; }}
    .candidate-header {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; }}
    .level-strip {{
      display: grid; grid-template-columns: repeat(9, minmax(105px, 1fr));
      margin: 14px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
      background: #fbfcfc;
    }}
    .level-strip > div {{ min-width: 0; padding: 9px 10px; border-right: 1px solid var(--line-soft); }}
    .level-strip > div:last-child {{ border-right: 0; }}
    .level-strip span {{ display: block; color: var(--muted); font-size: 9px; text-transform: uppercase; }}
    .level-strip strong {{ display: block; margin-top: 3px; font-size: 14px; font-variant-numeric: tabular-nums; }}
    .detail-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid var(--line); }}
    .detail-grid > section {{ min-width: 0; padding: 12px 16px 14px 0; margin-right: 16px; border-right: 1px solid var(--line-soft); }}
    .detail-grid > section:last-child {{ margin-right: 0; border-right: 0; }}
    .score-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; margin-bottom: 10px; }}
    .score {{ display: grid; grid-template-columns: 58px 24px 1fr; gap: 6px; align-items: center; }}
    .score > span:first-child {{ color: var(--muted); font-size: 11px; }}
    .score strong {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .score-track {{ height: 4px; background: #e1e6e9; overflow: hidden; }}
    .score-track span {{ display: block; height: 100%; background: var(--green); }}
    dl {{ margin: 0; }}
    dl > div {{ display: flex; justify-content: space-between; gap: 12px; padding: 5px 0; border-bottom: 1px solid var(--line-soft); }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; max-width: 62%; text-align: right; font-weight: 600; overflow-wrap: anywhere; }}
    ul {{ margin: 8px 0 0; padding-left: 17px; color: var(--muted); }}
    li {{ margin: 3px 0; }}
    .contract-band {{ padding-top: 12px; }}
    .compact table {{ min-width: 1120px; }}
    .compact th {{ position: static; padding: 7px; }}
    .compact td {{ padding: 7px; }}
    .diagnostic {{ color: var(--amber); }}
    details {{ padding: 14px 22px; border-top: 1px solid var(--line); }}
    summary {{ cursor: pointer; font-weight: 800; }}
    code {{ color: #4e5961; font-size: 10px; white-space: pre-wrap; overflow-wrap: anywhere; }}
    .empty, .empty-state {{ padding: 28px; color: var(--muted); text-align: center; }}
    .footer {{ padding: 16px 22px 26px; color: var(--muted); line-height: 1.55; }}
    [hidden] {{ display: none !important; }}
    @media (max-width: 1180px) {{
      .market-band {{ grid-template-columns: repeat(4, 1fr); }}
      .controls {{ grid-template-columns: repeat(3, minmax(150px, 1fr)); }}
      .count {{ justify-self: end; }}
      .detail-grid {{ grid-template-columns: 1fr 1fr; }}
      .detail-grid > section:nth-child(2) {{ margin-right: 0; border-right: 0; }}
      .level-strip {{ grid-template-columns: repeat(5, 1fr); }}
    }}
    @media (max-width: 700px) {{
      .topbar {{ align-items: flex-start; flex-direction: column; padding: 16px; }}
      .run-meta {{ text-align: left; }}
      .market-band {{ grid-template-columns: 1fr 1fr; }}
      .controls {{ position: static; grid-template-columns: 1fr 1fr; padding: 8px; }}
      .controls input {{ grid-column: 1 / -1; }}
      .count {{ justify-self: start; }}
      .candidate-detail {{ padding: 16px 12px; }}
      .candidate-header {{ align-items: flex-start; }}
      .level-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .detail-grid {{ grid-template-columns: 1fr; }}
      .detail-grid > section {{ margin-right: 0; border-right: 0; border-bottom: 1px solid var(--line-soft); padding-right: 0; }}
      .score-grid {{ grid-template-columns: 1fr; }}
      dd {{ max-width: 58%; }}
    }}
    @media print {{
      @page {{ size: landscape; margin: 10mm; }}
      body {{ background: white; font-size: 10px; }}
      .shell {{ max-width: none; }}
      .controls, .compare-panel, .compare-cell, .footer {{ display: none !important; }}
      th {{ position: static; }}
      #candidate-table {{ min-width: 0; }}
      .candidate-detail {{ break-before: page; padding: 8px 0; }}
      .level-strip {{ grid-template-columns: repeat(9, 1fr); }}
      .detail-grid {{ grid-template-columns: repeat(4, 1fr); }}
      .compact table {{ min-width: 0; table-layout: fixed; font-size: 7px; }}
      .compact th, .compact td {{
        padding: 3px 2px; white-space: normal; overflow-wrap: anywhere;
      }}
      .compact th:nth-child(1), .compact td:nth-child(1) {{ width: 8%; }}
      .compact th:nth-child(2), .compact td:nth-child(2) {{ width: 17%; }}
      .compact th:nth-child(3), .compact td:nth-child(3) {{ width: 10%; }}
      .compact th:nth-child(4), .compact td:nth-child(4) {{ width: 4%; }}
      .compact th:nth-child(5), .compact td:nth-child(5) {{ width: 7%; }}
      .compact th:nth-child(6), .compact td:nth-child(6) {{ width: 5%; }}
      .compact th:nth-child(7), .compact td:nth-child(7) {{ width: 6%; }}
      .compact th:nth-child(8), .compact td:nth-child(8) {{ width: 6%; }}
      .compact th:nth-child(9), .compact td:nth-child(9) {{ width: 5%; }}
      .compact th:nth-child(10), .compact td:nth-child(10) {{ width: 5%; }}
      .compact th:nth-child(11), .compact td:nth-child(11) {{ width: 7%; }}
      .compact th:nth-child(12), .compact td:nth-child(12) {{ width: 7%; }}
      .compact th:nth-child(13), .compact td:nth-child(13) {{ width: 7%; }}
    }}
  </style>
</head>
<body>
<main class="shell">
  <header class="topbar">
    <div>
      <div class="eyebrow">Ali Swing Suite / Read-only weekly call research</div>
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
    <div><span>Validation</span><strong>{escape(result.validation_state)}</strong></div>
  </section>

  <section class="controls" aria-label="Candidate filters">
    <input id="search" type="search" placeholder="Search candidates" aria-label="Search candidates">
    <select id="state" aria-label="Filter by state">
      <option value="all">All states</option>
      <option value="ready">Ready</option>
      <option value="ready_verify">Ready - Verify</option>
      <option value="verify_contract">Verify Contract</option>
      <option value="developing">Developing</option>
    </select>
    <select id="lane" aria-label="Filter by lane">
      <option value="all">All lanes</option>
      <option value="index_weekly">Index Weekly</option>
      <option value="leader_weekly">Leader Weekly</option>
    </select>
    <select id="pattern" aria-label="Filter by pattern">
      <option value="all">All patterns</option>{pattern_options}
    </select>
    <select id="dte" aria-label="Filter by DTE">
      <option value="all">All DTE</option>
      <option value="7-13">7-13 DTE</option>
      <option value="14-17">14-17 DTE</option>
      <option value="18-24">18-24 DTE</option>
      <option value="none">No contract</option>
    </select>
    <select id="trust" aria-label="Filter by data trust">
      <option value="all">All data trust</option>
      <option value="trusted">Trusted</option>
      <option value="verify">Verification required</option>
    </select>
    <span class="count"><span id="visible-count">{len(candidates)}</span> shown</span>
  </section>

  <section class="compare-panel" id="compare-panel" hidden>
    <header>
      <h2>Candidate comparison</h2>
      <button class="icon-button" id="clear-compare" type="button" title="Clear comparison" aria-label="Clear comparison">&times;</button>
    </header>
    <div class="table-wrap">
      <table id="compare-table">
        <thead><tr><th>Symbol</th><th>State</th><th>Pattern</th><th>Timing</th><th>Contract</th><th>Trigger</th><th>Tactical warning</th><th>Structural invalidation</th><th>Target</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </section>

  <div class="table-wrap">
    <table id="candidate-table">
      <thead><tr>
        <th class="compare-cell"></th>
        {_sort_header("Symbol", "symbol")}
        {_sort_header("State", "state", True)}
        {_sort_header("Lane", "lane")}
        {_sort_header("Pattern", "pattern")}
        {_sort_header("Trend", "trend", True)}
        {_sort_header("Lead", "lead", True)}
        {_sort_header("Timing", "timing", True)}
        {_sort_header("Contract", "contract", True)}
        <th>Call contract</th>
        {_sort_header("DTE", "dte", True)}
        {_sort_header("Delta", "delta", True)}
        {_sort_header("Spread", "spread", True)}
        {_sort_header("Theta/ask", "theta", True)}
        {_sort_header("Quote age", "age", True)}
        {_sort_header("Trust", "trust", True)}
        {_sort_header("Trigger", "trigger", True)}
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <section id="candidate-details">{details}</section>

  <details>
    <summary>Rejected diagnostics ({len(result.rejected)})</summary>
    <div class="table-wrap compact">
      <table>
        <thead><tr><th>Symbol</th><th>Stage</th><th>Reason codes</th><th>Details</th></tr></thead>
        <tbody>{rejected_rows}</tbody>
      </table>
    </div>
  </details>

  <footer class="footer">
    Scores rank evidence; they are not probabilities. V5 is research-gated and does not place
    orders or access brokerage accounts. Use the underlying structural invalidation, reassess
    after two sessions without meaningful progress, enforce the lane hold limit, avoid blocked
    event windows, and exit or fully requalify at the lane DTE boundary. A long call can lose the
    full premium paid.
  </footer>
</main>
<script>
  (() => {{
    const body = document.querySelector("#candidate-table tbody");
    const rows = [...body.querySelectorAll("tr[data-state]")];
    const details = [...document.querySelectorAll(".candidate-detail")];
    const controls = {{
      search: document.querySelector("#search"),
      state: document.querySelector("#state"),
      lane: document.querySelector("#lane"),
      pattern: document.querySelector("#pattern"),
      dte: document.querySelector("#dte"),
      trust: document.querySelector("#trust")
    }};
    const count = document.querySelector("#visible-count");
    const comparePanel = document.querySelector("#compare-panel");
    const compareBody = document.querySelector("#compare-table tbody");
    const selected = new Set();
    let sortKey = "state";
    let sortType = "number";
    let sortDirection = -1;

    const dteMatches = (value, filter) => {{
      if (filter === "all") return true;
      if (filter === "none") return value < 0;
      const [low, high] = filter.split("-").map(Number);
      return value >= low && value <= high;
    }};

    const applyFilters = () => {{
      const query = controls.search.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach((row) => {{
        const matches =
          (!query || (row.dataset.search || "").includes(query)) &&
          (controls.state.value === "all" || row.dataset.state === controls.state.value) &&
          (controls.lane.value === "all" || row.dataset.lane === controls.lane.value) &&
          (controls.pattern.value === "all" || row.dataset.pattern === controls.pattern.value) &&
          (controls.trust.value === "all" || row.dataset.trust === controls.trust.value) &&
          dteMatches(Number(row.dataset.dte), controls.dte.value);
        row.hidden = !matches;
        const detail = details.find((item) => item.dataset.symbol === row.dataset.symbol);
        if (detail) detail.hidden = !matches;
        if (matches) visible += 1;
      }});
      count.textContent = String(visible);
    }};

    const sortRows = () => {{
      rows.sort((a, b) => {{
        const left = a.dataset[`sort${{sortKey[0].toUpperCase()}}${{sortKey.slice(1)}}`] || "";
        const right = b.dataset[`sort${{sortKey[0].toUpperCase()}}${{sortKey.slice(1)}}`] || "";
        const comparison = sortType === "number"
          ? Number(left) - Number(right)
          : left.localeCompare(right);
        return comparison * sortDirection;
      }});
      rows.forEach((row) => body.appendChild(row));
    }};

    const renderComparison = () => {{
      compareBody.innerHTML = "";
      rows.filter((row) => selected.has(row.dataset.symbol)).forEach((row) => {{
        const output = document.createElement("tr");
        const values = [
          row.dataset.compareSymbol,
          row.dataset.compareState,
          row.dataset.comparePattern,
          row.dataset.compareTiming,
          row.dataset.compareContract,
          `$${{row.dataset.compareTrigger}}`,
          `$${{row.dataset.compareWarning}}`,
          `$${{row.dataset.compareStructural}}`,
          `$${{row.dataset.compareTarget}}`
        ];
        values.forEach((value) => {{
          const cell = document.createElement("td");
          cell.textContent = value || "";
          output.appendChild(cell);
        }});
        compareBody.appendChild(output);
      }});
      comparePanel.hidden = selected.size === 0;
    }};

    document.querySelectorAll(".sort-button").forEach((button) => {{
      button.addEventListener("click", () => {{
        const nextKey = button.dataset.sortKey;
        if (sortKey === nextKey) sortDirection *= -1;
        else {{
          sortKey = nextKey;
          sortType = button.dataset.sortType || "text";
          sortDirection = sortType === "number" ? -1 : 1;
        }}
        sortRows();
      }});
    }});

    Object.values(controls).forEach((control) => {{
      control.addEventListener(control === controls.search ? "input" : "change", applyFilters);
    }});

    rows.forEach((row) => {{
      const toggle = row.querySelector(".compare-toggle");
      toggle.addEventListener("change", () => {{
        if (toggle.checked && selected.size >= 3) {{
          toggle.checked = false;
          return;
        }}
        if (toggle.checked) selected.add(row.dataset.symbol);
        else selected.delete(row.dataset.symbol);
        renderComparison();
      }});
    }});

    document.querySelector("#clear-compare").addEventListener("click", () => {{
      selected.clear();
      document.querySelectorAll(".compare-toggle").forEach((toggle) => {{
        toggle.checked = false;
      }});
      renderComparison();
    }});

    sortRows();
    applyFilters();
  }})();
</script>
</body>
</html>
"""


def write_dashboard(result: ScanResult, folder: Path) -> Path:
    path = folder / "latest.html"
    path.write_text(render_dashboard(result), encoding="utf-8")
    return path

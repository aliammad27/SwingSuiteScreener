from __future__ import annotations

from pathlib import Path
from typing import Any

from scanner.config import ROOT
from scanner.models import Candidate, Candle


def _rolling_sma(values: list[float], length: int) -> list[float | None]:
    output: list[float | None] = []
    for idx in range(len(values)):
        if idx + 1 < length:
            output.append(None)
            continue
        output.append(sum(values[idx + 1 - length : idx + 1]) / length)
    return output


def _rolling_ema(values: list[float], length: int) -> list[float | None]:
    output: list[float | None] = []
    multiplier = 2 / (length + 1)
    current: float | None = None
    for idx, value in enumerate(values):
        if idx + 1 < length:
            output.append(None)
            continue
        if current is None:
            current = sum(values[idx + 1 - length : idx + 1]) / length
        else:
            current = (value - current) * multiplier + current
        output.append(current)
    return output


def _plot_line(
    axis: Any,
    x_values: list[int],
    values: list[float | None],
    label: str,
    color: str,
) -> None:
    xs: list[int] = []
    ys: list[float] = []
    for x_value, value in zip(x_values, values, strict=True):
        if value is None:
            continue
        xs.append(x_value)
        ys.append(value)
    if xs:
        axis.plot(xs, ys, label=label, linewidth=1.2, color=color)


def render_watchlist_chart(
    symbol: str,
    candles: list[Candle],
    title: str,
    trigger: float | None = None,
    support: float | None = None,
    target: float | None = None,
    output_dir: Path | None = None,
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    output = output_dir or ROOT / "reports" / "charts"
    output.mkdir(parents=True, exist_ok=True)
    chart_path = output / f"{symbol}_daily.png"
    recent = candles[-130:]
    closes = [candle.close for candle in recent]
    x_values = list(range(len(recent)))

    fig, (price_axis, volume_axis) = plt.subplots(
        2,
        1,
        figsize=(11, 7),
        gridspec_kw={"height_ratios": [4, 1]},
        sharex=True,
    )
    fig.patch.set_facecolor("#f8fafc")
    price_axis.set_facecolor("#ffffff")
    volume_axis.set_facecolor("#ffffff")

    for idx, candle in enumerate(recent):
        color = "#15803d" if candle.close >= candle.open else "#b91c1c"
        price_axis.vlines(idx, candle.low, candle.high, color=color, linewidth=1)
        body_low = min(candle.open, candle.close)
        body_height = max(abs(candle.close - candle.open), 0.01)
        price_axis.add_patch(
            Rectangle((idx - 0.32, body_low), 0.64, body_height, color=color, alpha=0.85)
        )
        volume_axis.bar(idx, candle.volume, color=color, alpha=0.55, width=0.65)

    _plot_line(price_axis, x_values, _rolling_ema(closes, 21), "EMA21", "#2563eb")
    _plot_line(price_axis, x_values, _rolling_sma(closes, 50), "SMA50", "#f97316")
    _plot_line(price_axis, x_values, _rolling_sma(closes, 200), "SMA200", "#111827")
    if trigger is not None:
        price_axis.axhline(trigger, color="#16a34a", linestyle="--", linewidth=1)
    if support is not None:
        price_axis.axhline(support, color="#0f766e", linestyle=":", linewidth=1)
    if target is not None:
        price_axis.axhline(target, color="#7c3aed", linestyle="-.", linewidth=1)
    price_axis.set_title(title)
    price_axis.legend(loc="upper left", fontsize=8)
    price_axis.grid(True, alpha=0.2)
    volume_axis.grid(True, alpha=0.15)
    volume_axis.set_ylabel("Volume")
    tick_indexes = x_values[:: max(1, len(x_values) // 6)]
    volume_axis.set_xticks(tick_indexes)
    volume_axis.set_xticklabels(
        [recent[idx].timestamp.strftime("%m-%d") for idx in tick_indexes],
        rotation=0,
        fontsize=8,
    )
    fig.tight_layout()
    fig.savefig(chart_path, dpi=140)
    plt.close(fig)
    return chart_path


def render_daily_chart(
    candidate: Candidate, candles: list[Candle], output_dir: Path | None = None
) -> Path:
    return render_watchlist_chart(
        candidate.symbol,
        candles,
        (
            f"{candidate.symbol} daily | {candidate.state.label} | "
            f"T{candidate.scores.trend} S{candidate.scores.setup} "
            f"H{candidate.scores.timing}"
        ),
        candidate.entry_plan.trigger,
        candidate.entry_plan.support,
        candidate.entry_plan.target_price,
        output_dir,
    )


def render_candidate_summary(candidate: Candidate, output_dir: Path | None = None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = output_dir or ROOT / "reports" / "charts"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{candidate.symbol}_v5_summary.png"
    score_names = ["Trend", "Lead", "Setup", "Timing", "Market", "Contract", "Risk"]
    score_values = [
        candidate.scores.trend,
        candidate.scores.leadership or 0,
        candidate.scores.setup,
        candidate.scores.timing,
        candidate.scores.market,
        candidate.scores.contract,
        candidate.scores.risk,
    ]
    colors = ["#15803d" if value >= 75 else "#d97706" if value >= 60 else "#b91c1c" for value in score_values]
    fig, (level_axis, score_axis) = plt.subplots(
        2, 1, figsize=(10, 6.4), gridspec_kw={"height_ratios": [1, 1.5]}
    )
    fig.patch.set_facecolor("#f8fafc")
    level_axis.set_facecolor("#ffffff")
    score_axis.set_facecolor("#ffffff")
    levels = [
        candidate.entry_plan.invalidation,
        candidate.trend.close,
        candidate.entry_plan.trigger,
        candidate.entry_plan.target_price,
    ]
    labels = ["Invalidation", "Price", "Trigger", "Objective"]
    level_colors = ["#b91c1c", "#111827", "#15803d", "#2563eb"]
    for index, (value, label, color) in enumerate(zip(levels, labels, level_colors, strict=True)):
        level_axis.scatter(value, 0, s=140, color=color, zorder=3)
        level_axis.text(value, 0.12 + (index % 2) * 0.12, f"{label}\n${value:.2f}", ha="center", fontsize=9)
    level_axis.hlines(0, min(levels), max(levels), color="#94a3b8", linewidth=2)
    level_axis.set_yticks([])
    level_axis.set_xlim(min(levels) * 0.995, max(levels) * 1.005)
    level_axis.set_title(
        f"{candidate.symbol} | {candidate.lane.label} | {candidate.state.label} | "
        f"{candidate.pattern.pattern_type.replace('_', ' ')} ({candidate.pattern.status.value})",
        fontsize=12,
    )
    score_axis.barh(score_names, score_values, color=colors)
    score_axis.set_xlim(0, 100)
    score_axis.axvline(75, color="#64748b", linestyle="--", linewidth=1)
    score_axis.grid(axis="x", alpha=0.2)
    for index, value in enumerate(score_values):
        score_axis.text(min(value + 2, 96), index, str(value), va="center", fontsize=9)
    contract = candidate.contracts.primary
    contract_text = (
        f"{contract.expiration_date.isoformat()} ${contract.strike:g} call | D{contract.delta:.2f} | {contract.dte}DTE"
        if contract is not None
        else f"Contract verification required ({candidate.contracts.feed})"
    )
    fig.text(0.5, 0.02, contract_text, ha="center", fontsize=9, color="#334155")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path

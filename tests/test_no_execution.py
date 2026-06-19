from pathlib import Path


def test_no_brokerage_execution_code_or_endpoints() -> None:
    root = Path(__file__).resolve().parents[1] / "scanner"
    forbidden = [
        "/v2/orders",
        "/v2/account",
        "/v2/positions",
        "submit_order",
        "place_order",
        "cancel_order",
        "paper_trading",
        "live_trading",
    ]
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} found in {path}"

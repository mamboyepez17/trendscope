"""Ops CLI: doctor and smoke."""

from trendscope.ops import run_smoke


def test_offline_smoke_ok():
    result = run_smoke(live=False)
    assert result["ok"] is True
    assert result["mode"] == "offline"
    assert result["sentiment_engine"] != "failed"
    assert result["signals"] >= 1


def test_ops_main_smoke_exit_code():
    from trendscope.ops import main

    assert main(["--smoke"]) == 0


def test_ops_main_doctor_exit_code():
    from unittest.mock import patch

    with patch(
        "trendscope.ops.run_doctor_report",
        return_value={"HN": {"status": "ok", "message": "x"}},
    ):
        from trendscope.ops import main

        assert main(["--doctor"]) == 0

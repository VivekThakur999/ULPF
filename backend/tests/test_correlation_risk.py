from datetime import datetime, timezone

from app.services.analytics.risk import RiskContext, band_for, compute_risk
from app.services.security.rules import _window_max_count


def test_band_thresholds():
    assert band_for(90) == "critical"
    assert band_for(70) == "high"
    assert band_for(50) == "medium"
    assert band_for(20) == "low"
    assert band_for(3) == "info"


def test_risk_is_transparent_sum():
    ctx = RiskContext(
        failed_logins=10, affected_hosts=3, distinct_sources=3, span_seconds=180,
        total_events=15, max_event_severity="high", success_after_failures=True,
        connections_denied=4,
    )
    r = compute_risk(ctx)
    raw = sum(f.points for f in r.factors)
    expected = raw if raw <= 60 else round(60 + (raw - 60) * 0.6)
    assert r.score == min(100, expected)
    assert str(raw) in r.summary  # the raw sum is disclosed
    assert r.band in ("high", "critical")
    # every factor explains itself
    assert all(f.detail and f.points > 0 for f in r.factors)
    assert "failed_authentication_volume" in {f.factor for f in r.factors}
    assert "cross_source_correlation" in {f.factor for f in r.factors}


def test_low_activity_scores_low():
    r = compute_risk(RiskContext(failed_logins=1, total_events=1))
    assert r.band in ("info", "low")


def test_window_max_count_sliding():
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    from datetime import timedelta
    times = [base + timedelta(seconds=s) for s in (0, 10, 20, 400, 410)]
    count, center = _window_max_count(times, window=60)
    assert count == 3  # the first cluster
    assert center is not None

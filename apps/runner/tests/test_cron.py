import pytest

from cron import describe_schedule


@pytest.mark.parametrize(
    ("cron", "expected"),
    [
        ("0 0 * * *", "Run on demand"),
    ],
)
def test_describe_manual_schedule(cron, expected):
    assert describe_schedule(cron, manual=True) == expected


@pytest.mark.parametrize(
    ("cron", "expected"),
    [
        ("0 */6 * * *", "Every 6 hours"),
        ("*/15 * * * *", "Every 15 minutes"),
        ("0 0 * * *", "Daily at midnight"),
        ("0 * * * *", "Hourly"),
        ("0 0 * * 1", "Weekly on day-of-week 1"),
        ("not-a-cron", "not-a-cron"),
        ("0 0 1 * *", "0 0 1 * *"),
    ],
)
def test_describe_scheduled_cron(cron, expected):
    assert describe_schedule(cron, manual=False) == expected

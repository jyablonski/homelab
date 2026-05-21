"""Lightweight cron descriptions for the runner UI."""


def describe_schedule(cron: str, *, manual: bool) -> str:
    if manual:
        return "Run on demand"

    parts = cron.split()
    if len(parts) != 5:
        return cron

    minute, hour, day_of_month, month, day_of_week = parts

    if minute.startswith("*/") and hour == "*" and day_of_month == "*" and month == "*":
        if day_of_week == "*":
            return f"Every {minute[2:]} minutes"
    if minute == "0" and hour.startswith("*/") and day_of_month == "*" and month == "*":
        if day_of_week == "*":
            return f"Every {hour[2:]} hours"
    if minute == "0" and hour == "0" and day_of_month == "*" and month == "*":
        if day_of_week == "*":
            return "Daily at midnight"
    if minute == "0" and hour == "*" and day_of_month == "*" and month == "*":
        if day_of_week == "*":
            return "Hourly"
    if minute == "0" and hour == "0" and day_of_month == "*" and month == "*":
        if day_of_week != "*":
            return f"Weekly on day-of-week {day_of_week}"

    return cron

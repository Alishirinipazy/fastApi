from datetime import datetime

import jdatetime

_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def format_jalali(dt: datetime) -> str:
    """
    Mirrors the Laravel app's verta($date)->format('%B %d، %Y'),
    e.g. "خرداد 15، 1404".
    """
    j = jdatetime.datetime.fromgregorian(datetime=dt)
    return f"{_MONTHS[j.month - 1]} {j.day}، {j.year}"

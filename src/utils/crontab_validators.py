from crontab import CronSlices


def validate_crontab(expr: str, index: int = None) -> None:
    """Validate crontab."""
    if index is not None:
        tab = ["*"] * 5
        tab[index] = expr
        expr = " ".join(tab)
    try:
        CronSlices(expr)
    except Exception as e:
        raise ValueError(e)


def validate_minute(expr: str) -> None:
    validate_crontab(expr, 0)


def validate_hour(expr: str) -> None:
    validate_crontab(expr, 1)


def validate_day(expr: str) -> None:
    validate_crontab(expr, 2)


def validate_day_of_year(expr: str) -> None:
    validate_crontab(expr, 3)


def validate_day_of_week(expr: str) -> None:
    validate_crontab(expr, 4)

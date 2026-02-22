from datetime import date, timedelta

from jinja2 import Environment, PackageLoader


def build_prompt(prompt_template: str, **kwargs) -> str:
    env = Environment(
        loader=PackageLoader("events_ai", "assets/prompts"), trim_blocks=True
    )

    env.filters["date_american"] = filter_date_american
    env.filters["date_year"] = filter_date_year
    env.filters["date_weekday"] = filter_date_weekday
    env.filters["date_offset"] = filter_date_offset

    template = env.get_template(prompt_template)
    return template.render(**kwargs)


def filter_date_american(date: date) -> str:
    return f"{date.month}/{date.day}/{date.year}"


def filter_date_year(date: date) -> str:
    return f"{date.year}"


def filter_date_weekday(date: date) -> str:
    return date.strftime("%A")


def filter_date_offset(date: date, days: int) -> date:
    return date + timedelta(days=days)

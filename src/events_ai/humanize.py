from datetime import date


def long_date(date: date) -> str:
    month = date.strftime("%B")

    day = date.strftime("%d")
    if day[0] == "0":
        day = day[1:]

    match date.day:
        case 11 | 12 | 13:
            suffix = "th"
        case x if x % 10 == 1:
            suffix = "st"
        case x if x % 10 == 2:
            suffix = "nd"
        case x if x % 10 == 3:
            suffix = "rd"
        case _:
            suffix = "th"

    year = date.strftime("%Y")
    return f"{month} {day}{suffix}, {year}"

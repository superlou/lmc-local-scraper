from datetime import date

from events_ai.agents import prompt


def test_prompt_build():
    day = date(2026, 1, 3)
    result = prompt.build_prompt(
        "test.txt.jinja2", items=["cat", "dog", "horse"], mouse=True, day=day
    )
    expected = """This prompt is only used for unit tests.

* cat
* dog
* horse

The mouse is conditionally included.

2026-01-03, 1/3/2026, 2026"""

    assert result == expected

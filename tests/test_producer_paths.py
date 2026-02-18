from pathlib import Path

from events_ai.producer_paths import ProducerPaths


def test_producer_paths_events_for():
    pp = ProducerPaths(
        Path("/tmp"),
        "events.csv",
        "script.json",
        "storyboard.json",
        "storyboard_pdf.json",
        "video.mp4",
        "post.txt",
    )

    assert pp.events_for("some-org") == Path("/tmp/events_some-org.csv")
    assert pp.events_for("*").name == "events_*.csv"

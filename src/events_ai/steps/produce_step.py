from datetime import date
from importlib.abc import Traversable
from pathlib import Path

from htmlcorder.titler import Titler
from loguru import logger
from moviepy import CompositeVideoClip, VideoFileClip, concatenate_videoclips

from events_ai.steps.pipeline_step import PipelineStep

from .. import humanize
from ..agents.storyboard_agent import StoryboardResult


class ProduceStep(PipelineStep):
    def __init__(
        self,
        video_path: Path,
        storyboard_path: Path,
        clip_path: Path,
        assets_dir: Traversable,
    ):
        self.video_path = video_path
        self.storyboard_path = storyboard_path
        self.clip_path = clip_path
        self.assets_dir = assets_dir

    @property
    def done(self) -> bool:
        return self.video_path.exists()

    def clip_path_for(self, take: int | str) -> Path:
        stem = self.clip_path.stem
        suffix = self.clip_path.suffix
        return self.clip_path.parent / f"{stem}_{take}{suffix}"

    def run(self, today: date):
        titler = Titler(self.assets_dir / "titles")

        storyboard = StoryboardResult.model_validate_json(
            open(self.storyboard_path).read()
        )

        clips = []

        graphics_path = self.video_path.parent

        # Add graphics to intro
        intro = VideoFileClip(self.clip_path_for(storyboard.takes[0].id))
        props = {
            "title": "Around Town with LMC",
            "subtitle": "For " + humanize.long_date(today),
            "duration": intro.duration,
        }
        url = "intro_outro.html?" + "&".join([f"{k}={v}" for k, v in props.items()])
        titler.generate(
            url,
            intro.duration,
            graphics_path / "frames_intro",
            graphics_path / "title_intro.webm",
            frame_rate=25,
        )
        title = VideoFileClip(graphics_path / "title_intro.webm", has_mask=True)
        clips.append(CompositeVideoClip([intro, title]))

        # Add graphics to event clips
        for take in storyboard.takes[1:-1]:
            clip = VideoFileClip(self.clip_path_for(take.id))
            props = {
                "name": title_safe(take.title),
                "when": title_safe(take.when),
                "where": title_safe(take.where),
                "duration": clip.duration,
            }
            url = "event_info.html?" + "&".join([f"{k}={v}" for k, v in props.items()])
            take_id = Path(clip.filename).stem

            titler.generate(
                url,
                clip.duration,
                graphics_path / f"frames_{take_id}",
                graphics_path / f"title_{take_id}.webm",
                frame_rate=25,
            )

            title = VideoFileClip(
                graphics_path / f"title_{take_id}.webm", has_mask=True
            )
            clips.append(CompositeVideoClip([clip, title]))

        # Add outro
        outro = VideoFileClip(self.clip_path_for(storyboard.takes[-1].id))
        props = {
            "title": "Thanks for Watching",
            "subtitle": "See you tomorrow!",
            "duration": outro.duration,
        }
        url = "intro_outro.html?" + "&".join([f"{k}={v}" for k, v in props.items()])
        titler.generate(
            url,
            outro.duration,
            graphics_path / "frames_outro",
            graphics_path / "title_outro.webm",
            frame_rate=25,
        )
        title = VideoFileClip(graphics_path / "title_outro.webm", has_mask=True)
        clips.append(CompositeVideoClip([outro, title]))

        # Concatenate all titled clips
        video = concatenate_videoclips(clips)
        logger.info(f"Writing video to {self.video_path}...")
        video.write_videofile(self.video_path, audio_codec="aac")
        logger.info(f"Wrote video to {self.video_path}")


def title_safe(text: str) -> str:
    return text.replace("’", "'").replace("“", '"').replace("”", '"')

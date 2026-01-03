from pathlib import Path

from loguru import logger

from .heygen_client import (
    AvatarStyle,
    Background,
    BackgroundType,
    Character,
    CharacterType,
    CreateAvatarVideoV2Request,
    Dimension,
    HeyGenClient,
    Offset,
    Scene,
    TalkingStyle,
    Voice,
    VoiceType,
)


class FilmAgent:
    def __init__(self, client: HeyGenClient, dialogue: str, background_path: str):
        self.client = client
        self.dialogue = dialogue
        self.background_path = background_path

    def run(self) -> str | None:
        asset_name = Path(self.background_path).name
        logger.info(f"Uploading background asset: {asset_name}")
        response = self.client.upload_asset(self.background_path, asset_name)
        background_asset_id = response["data"]["id"]
        logger.info(f"Asset ID: {background_asset_id}")

        scene = Scene(
            character=Character(
                type=CharacterType.avatar,
                avatar_id="Georgia_expressive_2024112701",
                avatar_style=AvatarStyle.NORMAL,
                talking_style=TalkingStyle.EXPRESSIVE,
                offset=Offset(x=0.0, y=0.09),
                scale=1.71,
            ),
            voice=Voice(
                type=VoiceType.TEXT,
                voice_id="511ffd086a904ef593b608032004112c",
                input_text=self.dialogue,
            ),
            background=Background(
                type=BackgroundType.IMAGE, image_asset_id=background_asset_id
            ),
        )
        logger.info(f"Requesting video generation: {scene}")
        request_data = CreateAvatarVideoV2Request(
            title="Test Video",
            dimension=Dimension(width=720, height=1280),
            video_inputs=[scene],
        )
        response = self.client.create_avatar_video_v2(request_data)
        logger.info(f"Video generation request response: {response}")

        logger.info(f"Deleting asset ID: {background_asset_id}")
        self.client.delete_asset(background_asset_id)

        return response.data.video_id

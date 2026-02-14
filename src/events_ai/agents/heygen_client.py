from enum import Enum
from pathlib import Path
from typing import Any

import requests
from loguru import logger
from pydantic import BaseModel


class Avatar(BaseModel):
    avatar_id: str
    avatar_name: str
    gender: str
    preview_image_url: str
    preview_video_url: str
    premium: bool
    type: str | None
    tags: list[str] | None
    default_voice_id: str | None


class TalkingPhoto(BaseModel):
    talking_photo_id: str
    talking_photo_name: str
    preview_image_url: str


class ListAvatarsData(BaseModel):
    avatars: list[Avatar]
    talking_photos: list[TalkingPhoto]


class ListAvatarsInGroupData(BaseModel):
    avatar_list: list[Avatar]


class HeyGenListAvatarsResponse(BaseModel):
    error: str | None
    data: ListAvatarsData


class HeyGenListAvatarsInGroupResponse(BaseModel):
    error: str | None
    data: ListAvatarsInGroupData


class CharacterType(Enum):
    avatar = "avatar"
    talking_photo = "talking_photo"


class AvatarStyle(Enum):
    NORMAL = "normal"
    CIRCLE = "circle"
    CLOSE_UP = "closeUp"


class TalkingPhotoStyle(Enum):
    CIRCLE = "circle"
    SQUARE = "square"


class TalkingStyle(Enum):
    STABLE = "stable"
    EXPRESSIVE = "expressive"


class Expression(Enum):
    DEFAULT = "default"
    HAPPY = "happy"


class Offset(BaseModel):
    x: float = 0.0
    y: float = 0.0


class Character(BaseModel):
    type: CharacterType
    avatar_id: str | None = None
    # talking_photo_id: str | None = None
    avatar_style: AvatarStyle | None = None
    # talking_photo_style: TalkingPhotoStyle | None = None
    talking_style: TalkingStyle = TalkingStyle.STABLE
    expression: Expression = Expression.DEFAULT
    scale: float = 1
    offset: Offset | None = None
    matting: bool = False
    super_resolution: bool | None = None


class VoiceType(Enum):
    TEXT = "text"
    AUDIO = "audio"
    SILENCE = "silence"


class VoiceEmotion(Enum):
    EXCITED = "excited"
    FRIENDLY = "friendly"
    SERIOUS = "serious"
    SOOTHING = "soothing"
    BROADCASTER = "broadcaster"


class Voice(BaseModel):
    type: VoiceType
    voice_id: str
    input_text: str
    speed: float = 1.0
    pitch: float = 0.0
    emotion: VoiceEmotion = VoiceEmotion.EXCITED
    locale: str | None = None


class HeyGenListVoicesData(BaseModel):
    voices: list[Any]


class HeyGenListVoicesResponse(BaseModel):
    error: Any | None
    data: HeyGenListVoicesData


class BackgroundType(Enum):
    COLOR = "color"
    IMAGE = "image"
    VIDEO = "video"


class Background(BaseModel):
    type: BackgroundType
    value: str | None = None
    image_asset_id: str | None = None


class TextType(Enum):
    TEXT = "text"


class Text(BaseModel):
    type: TextType = TextType.TEXT
    text: str = ""


class Scene(BaseModel):
    character: Character
    voice: Voice
    background: Background
    text: Text | None = None


class Dimension(BaseModel):
    width: int = 1280
    height: int = 720


class CreateAvatarVideoV2Request(BaseModel):
    caption: bool = False
    title: str
    callback_id: str = ""
    video_inputs: list[Scene]
    dimension: Dimension
    folder_id: str = ""
    callback_url: str = ""


class CreateAvatarVideoV2ResponseData(BaseModel):
    video_id: str


class CreateAvatarVideoV2Error(BaseModel):
    code: str
    message: str


class CreateAvatarVideoV2Response(BaseModel):
    error: CreateAvatarVideoV2Error | None
    data: CreateAvatarVideoV2ResponseData | None


class VideoStatusResponse(BaseModel):
    code: int
    data: Any


class HeyGenClient:
    def __init__(self, api_key):
        self.api_key = api_key

    @property
    def headers(self) -> dict:
        return {"accept": "application/json", "x-api-key": self.api_key}

    def check_quota(self):
        response = requests.get(
            "https://api.heygen.com/v2/user/remaining_quota",
            headers=self.headers,
        )
        return response.json()

    def list_avatars(self) -> HeyGenListAvatarsResponse:
        response = requests.get(
            "https://api.heygen.com/v2/avatars", headers=self.headers
        )
        return HeyGenListAvatarsResponse.model_validate(response.json())

    def list_avatars_in_group(
        self, group_id: int | None = None
    ) -> HeyGenListAvatarsInGroupResponse:
        response = requests.get(
            f"https://api.heygen.com/v2/avatar_group/{group_id}/avatars",
            headers=self.headers,
        )
        return HeyGenListAvatarsInGroupResponse.model_validate(response.json())

    def list_voices(self) -> HeyGenListVoicesResponse:
        response = requests.get(
            "https://api.heygen.com/v2/voices",
            headers=self.headers,
        )
        return HeyGenListVoicesResponse.model_validate(response.json())

    def create_avatar_video_v2(
        self, request_data: CreateAvatarVideoV2Request
    ) -> CreateAvatarVideoV2Response:
        request_json = request_data.model_dump_json(exclude_unset=True)
        logger.debug(f"Create avatar video request: {request_json}")

        response = requests.post(
            "https://api.heygen.com/v2/video/generate",
            data=request_json,
            headers=self.headers | {"content-type": "application/json"},
        )

        return CreateAvatarVideoV2Response.model_validate(response.json())

    def get_video_status(self, video_id: str) -> VideoStatusResponse:
        response = requests.get(
            "https://api.heygen.com/v1/video_status.get",
            params={"video_id": video_id},
            headers=self.headers,
        )

        return VideoStatusResponse.model_validate(response.json())

    def upload_asset(self, asset_path: str, name: str):
        ext = Path(asset_path).suffix[1:]

        content_type = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }[ext]

        with open(asset_path, "rb") as image_file:
            response = requests.post(
                "https://upload.heygen.com/v1/asset",
                data=image_file,
                params={"name": name},
                headers={"Content-Type": content_type} | self.headers,
            )

            return response.json()

    def list_assets(self):
        response = requests.get(
            "https://api.heygen.com/v1/asset/list", headers=self.headers
        )
        return response.json()

    def delete_asset(self, asset_id: str):
        response = requests.post(
            f"https://api.heygen.com/v1/asset/{asset_id}/delete", headers=self.headers
        )
        return response.json()

    def create_avatar_iv_video(
        self,
        image_key: str,
        title: str,
        script: str,
        voice_id: str,
        orientation: str,
    ):
        response = requests.post(
            "https://api.heygen.com/v2/video/av4/generate",
            json={
                "image_key": image_key,
                "video_title": title,
                "script": script,
                "voice_id": voice_id,
                "video_orientation": orientation,
            },
            headers=self.headers | {"content-type": "application/json"},
        )
        return response


def heygen_cli():
    import argparse
    import os

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--quota", action="store_true")
    parser.add_argument("--list-avatars", action="store_true")
    parser.add_argument("--list-avatars-in-group")
    parser.add_argument("--list-voices", action="store_true")
    args = parser.parse_args()

    client = HeyGenClient(os.environ["HEYGEN_API_KEY"])

    if args.quota:
        print(client.check_quota())

    if args.list_avatars:
        print(client.list_avatars())

    if args.list_avatars_in_group:
        data = client.list_avatars_in_group(args.list_avatars_in_group).data
        for avatar in data.avatar_list:
            print(f"[{avatar.avatar_id}]")
            print(
                f"name: {avatar.avatar_name}, gender: {avatar.gender}, type: {avatar.type}, premium: {avatar.premium}"
            )
            print(f"default voice: {avatar.default_voice_id}")
            print(f"preview image: {avatar.preview_image_url}")
            print(f"preview video: {avatar.preview_video_url}")
            print(f"tags: {', '.join(avatar.tags or [])}")
            print()

    if args.list_voices:
        data = client.list_voices().data
        voices = sorted(data.voices, key=lambda x: x["name"].strip())

        for voice in voices:
            name = voice["name"]
            id = voice["voice_id"]
            language = voice["language"]
            emotion_support = voice["emotion_support"]
            preview = voice["preview_audio"]
            print(
                f"* {name.strip()} ({id}) - {language}, emotion support: {emotion_support}, {preview}"
            )

from enum import Enum
from pathlib import Path
from typing import Any

import requests
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


class HeyGenListAvatarsResponse(BaseModel):
    error: str | None
    data: ListAvatarsData


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


class Character(BaseModel):
    type: CharacterType
    avatar_id: str | None = None
    # talking_photo_id: str | None = None
    scale: float = 1
    avatar_style: AvatarStyle | None = None
    # talking_photo_style: TalkingPhotoStyle | None = None
    talking_style: TalkingStyle = TalkingStyle.STABLE
    expression: Expression = Expression.DEFAULT


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

    def create_avatar_video_v2(
        self, request_data: CreateAvatarVideoV2Request
    ) -> CreateAvatarVideoV2Response:
        print(request_data.model_dump_json(indent=2, exclude_unset=True))

        response = requests.post(
            "https://api.heygen.com/v2/video/generate",
            data=request_data.json(exclude_unset=True),
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

        with open(asset_path, "rb") as image_file:
            response = requests.post(
                "https://upload.heygen.com/v1/asset",
                data=image_file,
                params={"name": name},
                headers={"Content-Type": f"image/{ext}"} | self.headers,
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

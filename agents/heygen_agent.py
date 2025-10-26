import requests


class HeyGenAgent:
    def __init__(self, api_key):
        self.client = HeyGenClient(api_key)

    def check_quota(self):
        return self.client.check_quota()


class HeyGenClient:
    def __init__(self, api_key):
        self.api_key = api_key

    @property
    def headers(self) -> dict:
        return {"accept": "application/json", "x-api-key": self.api_key}

    def check_quota(self):
        response = requests.get(
            "https://api.heygen.com/v2/user/remaining_quota", headers=self.headers
        )
        return response.json()

    def upload_asset(self, image_path: str, name: str):
        with open(image_path, "rb") as image_file:
            response = requests.post(
                "https://upload.heygen.com/v1/asset",
                data=image_file,
                params={"name": name},
                headers={"Content-Type": "image/jpeg"} | self.headers,
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
            headers=self.headers | {"content-type": "application/json"}
        )
        return response

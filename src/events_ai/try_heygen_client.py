import os

from dotenv import load_dotenv

from .agents.heygen_client import (
    AvatarStyle,
    Background,
    BackgroundType,
    Character,
    CharacterType,
    CreateAvatarVideoV2Request,
    Dimension,
    HeyGenClient,
    Scene,
    TalkingStyle,
    Voice,
    VoiceType,
)


def main():
    load_dotenv()
    client = HeyGenClient(os.environ["HEYGEN_API_KEY"])

    print("Check quota:")
    print(client.check_quota())
    print()

    # print("List avatars:")
    # avatars = client.list_avatars()
    # print(avatars.data)
    # print()

    # response = client.upload_asset("gen/test_pumpkin.png", "matt.png")
    # print(response)
    # image_id = response["data"]["id"]
    # print(f"Image ID: {image_id}")
    background_image_id = "1ffaf87a406f45a887800a85f20e3d68"

    if False:
        print("Create Avatar V2 video:")
        scene = Scene(
            character=Character(
                type=CharacterType.avatar,
                avatar_id="Abigail_expressive_2024112501",
                avatar_style=AvatarStyle.NORMAL,
                talking_style=TalkingStyle.EXPRESSIVE,
            ),
            voice=Voice(
                type=VoiceType.TEXT,
                voice_id="330290724a1b470fb63153f34d4c0183",
                input_text="Get ready to build some spooky fun at the 6th Annual Scarecrow Build on October 4th at 10 AM, happening at Pavilion Field in Harbor Island Park! You can build your own scarecrow – all materials are provided, just bring some old clothes. Resident tickets are $45, and non-residents are $55.",
            ),
            background=Background(
                type=BackgroundType.IMAGE, image_asset_id=background_image_id
            ),
        )
        request_data = CreateAvatarVideoV2Request(
            title="Test Video",
            dimension=Dimension(width=1280, height=720),
            video_inputs=[scene],
        )
        response = client.create_avatar_video_v2(request_data)
        print(response)

    print("Video status")
    video_id = "a2c2351ed5574e2991852475e9fdce23"
    response = client.get_video_status(video_id)
    print(response)

    # print("Upload asset:")
    # response = client.upload_asset("assets/matt.jpg", "matt.jpg")
    # print(response)
    # image_id = response["data"]["id"]
    # print(f"Image ID: {image_id}")
    # print()

    # print("List assets:")
    # print(client.list_assets())
    # print()

    # print("Create video:")
    # response = client.create_avatar_iv_video(
    #     image_id,
    #     "HeyGen API IV video creation test",
    #     "This is a test of HeyGen IV video generation using the API. If this works, it would allow hands-off creation of videos.",
    #     "8661cd40d6c44c709e2d0031c0186ada",
    #     "landscape",
    # )
    # print(response)
    # print(response.text)
    # print()

    # print("Deleting asset:")
    # print(client.delete_asset(image_id))
    # print()

    # print("List assets:")
    # print(client.list_assets())
    # print()


if __name__ == "__main__":
    main()

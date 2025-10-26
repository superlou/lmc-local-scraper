import os

from dotenv import load_dotenv

from agents.heygen_agent import HeyGenClient


def main():
    load_dotenv()
    client = HeyGenClient(os.environ["HEYGEN_API_KEY"])
    
    print("Check quota:")
    print(client.check_quota())
    print()

    print("Upload asset:")
    response = client.upload_asset("assets/matt.jpg", "matt.jpg")
    print(response)
    image_id = response["data"]["id"]
    print(f"Image ID: {image_id}")
    print()
    
    print("List assets:")
    print(client.list_assets())
    print()

    print("Create video:")
    response = client.create_avatar_iv_video(
        image_id,
        "HeyGen API IV video creation test",
        "This is a test of HeyGen IV video generation using the API. If this works, it would allow hands-off creation of videos.",
        "8661cd40d6c44c709e2d0031c0186ada",
        "landscape"
    )
    print(response)
    print()

    print("Deleting asset:")
    print(client.delete_asset(image_id))
    print()

    print("List assets:")
    print(client.list_assets())
    print()


if __name__ == "__main__":
    main()
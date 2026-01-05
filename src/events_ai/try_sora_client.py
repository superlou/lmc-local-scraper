import os

from dotenv import load_dotenv

from .agents.sora_agent import SoraClient


def main():
    _ = load_dotenv()
    sora = SoraClient(os.environ["OPEN_AI_KEY"])
    #     prompt = """A professional woman in a business suit looks into the camera.
    # Her hand motions are casual and welcoming.
    # Behind her, a step-and-repeat background tiles LMC in blue on a white backdrop with colorful checkers.
    # The camera looks like hand-held cell-phone footage.
    # She waves.
    # In a perky, clear, energetic voice she says, "This is LMC!".
    # """
    #     prompt = """The talent is a dog wearing a chicken costume with the logo "LMC" in bold letters.
    # It looks at the camera and says the following dialogue:
    # This is LMC Media's "Around the Sound" in 60 seconds!"""
    #     video = sora.create_video(prompt)
    #     print(video)

    # print("Videos:")
    # videos = sora.list_videos()
    # for video in videos:
    #     print(video)

    print()
    video_id = "video_690f9756fc548190b42adea3d1a8108700fcf916b6dfdf5e"

    print(sora.get_video_by_id(video_id))

    print(f"Downloading {video_id}")
    sora.download_video(video_id, "gen/test_sora2_chicken_dog.mp4")


if __name__ == "__main__":
    main()

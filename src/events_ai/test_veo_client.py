import os
from dotenv import load_dotenv
from agents.veo_agent import VeoClient


def main():
    _ = load_dotenv()
    client = VeoClient(os.environ["GEMINI_API_KEY"])
    print(client)
    prompt = """The talent is a dog wearing a chicken costume with the logo "LMC" in bold letters.
It looks at the camera and says the following dialogue:
This is LMC Media's "Around the Sound" in 60 seconds!"""
    client.generate_video(
        prompt, "gen/generated_frame_1.jpg", "gen/dialogue_example.mp4"
    )
    print("Done.")


if __name__ == "__main__":
    main()

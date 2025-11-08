import os

from dotenv import load_dotenv

from agents.dialogue_agent import GeminiSpeechClient


def main():
    _ = load_dotenv()
    client = GeminiSpeechClient(os.environ["GEMINI_API_KEY"])
    print(client)

    client.generate_audio(
        "Say cheerfully: First up, get ready to build some spooky fun at the 6th Annual Scarecrow Build on October 4th at 10 AM, happening at Pavilion Field in Harbor Island Park! This is a fantastic fall tradition for kids, teens, and adults alike. You can build your own scarecrow – all materials are provided, just bring some old clothes – or get creative decorating a pumpkin. Your amazing scarecrow creations will then be showcased along the popular Scarecrow Trail on Mamaroneck Avenue throughout October. Resident tickets are $45, and non-residents are $55. Don't miss out on this super fun, family-friendly event!",
        "Zephyr",
        "gen/audio_test.wav",
    )

    print("Done.")


if __name__ == "__main__":
    main()

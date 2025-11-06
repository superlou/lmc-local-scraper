import os
from agents.sora_agent import SoraClient
from dotenv import load_dotenv


def main():
    _ = load_dotenv()
    sora = SoraClient(os.environ["OPEN_AI_KEY"])
    print(sora)
    sora.create_video()


if __name__ == "__main__":
    main()

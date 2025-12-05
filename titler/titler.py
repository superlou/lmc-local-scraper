import subprocess
import threading
from pathlib import Path

from loguru import logger
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from title_gen_chrome_driver import TitleGenChromeDriver
from title_server import TitleServer


class Titler:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.check_environment()

    def check_environment(self):
        # todo Check for Chrome
        # todo Check for ffmpeg
        logger.warning("Environment check not implemented!")

    def serve_blocking(self, port: int | None):
        title_server = TitleServer(self.root, port)
        server_base = f"http://{title_server.host}:{title_server.port}"
        logger.info(f"Starting title server at {server_base}")
        title_server.serve_forever()

    def generate(
        self,
        url: str,
        duration: float,
        frames_dir: str | Path,
        frame_rate: float = 30.0,
    ):
        self.frames_dir = Path(frames_dir)
        title_server = TitleServer(self.root)
        server_base = f"http://{title_server.host}:{title_server.port}"
        logger.info(f"Starting title server at {server_base}")
        server_thread = threading.Thread(target=title_server.serve_forever, daemon=True)
        server_thread.start()

        title_url = server_base + "/" + url

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")

        FRAMES = int(duration * frame_rate)

        driver = TitleGenChromeDriver(options=options)
        driver.get(title_url)
        driver.make_background_transparent()
        driver.resize_and_check(1280, 720)

        # 1. Find all elements with animations
        # todo Make this automatic rather than requiring a specific class.
        animated = driver.find_elements(By.CLASS_NAME, "animated")

        # 2. Keep a map of these elements to their original animation-delays
        animation_delays = {elem: driver.get_animation_delay(elem) for elem in animated}

        # 3. Each loop, offset them based on the original and the current frame
        logger.info("Started capturing frames")

        shots = []
        for frame in range(FRAMES):
            delay = (frame / FRAMES) * -duration
            logger.debug(f"{delay=}")

            for elem in animated:
                driver.seek_animation_delay(elem, animation_delays[elem], delay)

            shots.append(driver.get_screenshot_as_png())

        logger.info("Finished capturing frames")

        if not self.frames_dir.exists():
            self.frames_dir.mkdir(exist_ok=True)

        logger.info("Dumping all captured frames")
        for i in range(len(shots)):
            with open(self.frames_dir / f"{i}.png", "wb") as f:
                f.write(shots[i])

        logger.info("Writing video")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(frame_rate),
                "-i",
                self.frames_dir / "%d.png",
                "-c:v",
                "libvpx-vp9",
                "-b:v",
                "4000k",
                "-pix_fmt",
                "yuva420p",
                "output.webm",
            ]
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="HTML root")
    parser.add_argument("-s", "--serve", action="store_true")
    parser.add_argument("-p", "--port", type=int)
    parser.add_argument("-g", "--generate_url")
    args = parser.parse_args()

    titler = Titler(args.root)

    if args.serve:
        titler.serve_blocking(args.port)
    elif args.generate_url:
        titler.generate(args.generate_url, 5.0, "frames")

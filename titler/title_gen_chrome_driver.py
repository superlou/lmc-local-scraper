import io

from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class ResizeFailure(Exception):
    pass


class TitleGenChromeDriver(webdriver.Chrome):
    def __init__(
        self,
        options: Options | None = None,
        service: Service | None = None,
        keep_alive: bool = True,
    ):
        super().__init__(options, service, keep_alive)
        self.execute_cdp_cmd(
            "Emulation.setDefaultBackgroundColorOverride",
            {"color": {"r": 0, "g": 0, "b": 0, "a": 0.000001}},
        )

    def make_background_transparent(self):
        html_el = self.find_element(By.TAG_NAME, "html")
        body_el = self.find_element(By.TAG_NAME, "body")

        self.execute_script("arguments[0].style.background = 'transparent';", html_el)
        self.execute_script("arguments[0].style.background = 'transparent';", body_el)

    def get_body_size(self):
        body_el = self.find_elements(By.TAG_NAME, "html")[0]
        # return self.execute_script("return ;", html_el)
        return body_el.size

    def get_animation_delay(self, element: WebElement):
        return self.execute_script(
            "return window.getComputedStyle(arguments[0]).animationDelay;", element
        )

    def seek_animation_delay(
        self, element: WebElement, original_delay: str, offset: float
    ):
        delays = [
            float(delay.replace("s", "").strip()) + offset
            for delay in original_delay.split(",")
        ]
        delays = ", ".join([str(delay) + "s" for delay in delays])

        script = f"""arguments[0].setAttribute(
            "style",
            "animation-delay: {delays}; animation-play-state: paused;"
        )"""
        self.execute_script(script, element)

    def get_window_outer_size(self):
        dx, dy = self.execute_script(
            "var w=window; return [w.outerWidth - w.innerWidth, w.outerHeight - w.innerHeight];"
        )
        return dx, dy

    def resize_and_check(self, width, height):
        self.set_window_size(width, height)
        check_image = Image.open(io.BytesIO(self.get_screenshot_as_png()))
        check_width, check_height = check_image.size
        dx = width - check_width
        dy = height - check_height

        self.set_window_size(width + dx, height + dy)
        check_image = Image.open(io.BytesIO(self.get_screenshot_as_png()))
        check_width, check_height = check_image.size

        if check_image.size != (width, height):
            raise ResizeFailure("Failed")

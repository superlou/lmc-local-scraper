import requests
from bs4 import BeautifulSoup
from loguru import logger
from markdownify import markdownify
from selenium import webdriver
from selenium.webdriver import ChromeOptions

options = ChromeOptions()
options.add_argument("--headless=new")
probe = webdriver.Chrome(options=options)
USER_AGENT = probe.execute_script("return navigator.userAgent").replace(
    "HeadlessChrome", "Chrome"
)
probe.quit()


def get(url: str, use_selenium=False) -> str:
    if use_selenium:
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument(f"user-agent={USER_AGENT}")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        driver.implicitly_wait(2.0)
        html = driver.page_source
        driver.quit()
    else:
        response = requests.get(url, headers={"User-Agent": USER_AGENT})
        html = response.text

    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    for script in script_tags:
        script.decompose()

    simplified = soup.body.decode_contents() if soup.body else ""
    simplified = markdownify(simplified, strip=["img"])

    logger.info(
        f"Simplified get {url} - original: {len(html):,}, simplified: {len(simplified):,}, use_selenium: {use_selenium}"
    )

    return simplified

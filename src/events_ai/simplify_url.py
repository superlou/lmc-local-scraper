import requests
from bs4 import BeautifulSoup
from loguru import logger
from markdownify import markdownify
from selenium import webdriver


def get(url: str, use_selenium=False) -> str:
    if use_selenium:
        driver = webdriver.Chrome()
        driver.get(url)
        driver.implicitly_wait(1.0)
        html = driver.page_source
    else:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            },
        )
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

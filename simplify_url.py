import requests
from bs4 import BeautifulSoup
from markdownify import markdownify
import structlog
from selenium import webdriver
from selenium.webdriver.common.by import By


logger = structlog.get_logger()


def get(url: str, use_selenium=False) -> str:
    log = logger.bind(url=url, use_selenium=use_selenium)

    if use_selenium:
        driver = webdriver.Chrome()
        driver.get(url)
        driver.implicitly_wait(1.0)
        html = driver.page_source
    else:
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
        })
        html = response.text

    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    for script in script_tags:
        script.decompose()
    
    simplified = soup.body.decode_contents() if soup.body else ""
    simplified = markdownify(simplified, strip=["img"])
   
    log = log.bind(html_len=len(html), simplified_len=len(simplified))
    log.info("Simplified URL get")

    return simplified
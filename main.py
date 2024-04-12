import os
import time
from urllib.parse import urljoin

import gspread
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

load_dotenv()

BASE_URL = "https://www.olx.ua"
APT_URL = "https://www.olx.ua/uk/nedvizhimost/kvartiry/"


def get_detail_info(url: str) -> dict:
    page = requests.get(url).content
    soup = BeautifulSoup(page, "html.parser")
    detail = {"floor": None, "floor_level": None}
    for info in soup.select("p.css-b5m1rv"):
        if "Поверх:" in info.text:
            detail["floor"] = info.text.split()[1]
        if "Поверховість:" in info.text:
            detail["floor_level"] = info.text.split()[1]

    return detail


def parse_single_page(driver: WebDriver, worksheet) -> None:
    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_result = []
    for apt_soup in soup.select("div.css-1apmciz"):
        link = urljoin(BASE_URL, apt_soup.select_one("a.css-z3gu2d")["href"])
        detail_info = get_detail_info(link)
        apt = {
            "title": apt_soup.select_one("h6.css-16v5mdi").text,
            "link": link,
            "price": int(
                "".join(
                    [
                        char
                        for char in apt_soup.select_one("p.css-tyui9s").text
                        if char.isdigit()
                    ]
                )
            ),
            "square": float(
                apt_soup.select_one("span.css-643j0o").text.split(" ")[0]
            ),
            "floor": detail_info["floor"],
            "floor_level": detail_info["floor_level"],
            "city": apt_soup.select_one("p.css-1a4brun")
            .text.split(",")[0]
            .split(" -")[0],
        }
        page_result.append(apt)

    dataframe = pd.DataFrame(page_result)
    worksheet.append_rows(dataframe.values.tolist(), value_input_option="RAW")


def main() -> None:
    gc = gspread.service_account(filename="credentials.json")
    new_sh = gc.create("new_age_level1")
    new_sh.share(os.environ.get("EMAIL"), perm_type="user", role="writer")
    worksheet = new_sh.sheet1

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    with webdriver.Chrome(options=options) as driver:
        driver.get(APT_URL)
        next_button = driver.find_element(
            By.XPATH, "//a[@data-testid='pagination-forward']"
        )
        while next_button is not None:
            parse_single_page(driver, worksheet)
            driver.execute_script("arguments[0].click();", next_button)
            print("Next page button clicked")
            try:
                wait = WebDriverWait(driver, 10)
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//a[@data-testid='pagination-forward']")
                    )
                )
                next_button = driver.find_element(
                    By.XPATH, "//a[@data-testid='pagination-forward']"
                )
            except Exception as e:
                break


if __name__ == "__main__":
    start = time.perf_counter()
    main()
    end = time.perf_counter()
    print("Elapsed:", end - start)

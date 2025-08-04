from langflow.custom import Component
from langflow.io import StrInput, SecretStrInput, Output
from langflow.schema import Data
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import os


class InstagramPageFetcher(Component):
    display_name = "Instagram Page Fetcher"
    description = "Fetches public Instagram profile data using Selenium."
    icon = "mdi-instagram"
    name = "InstagramPageFetcher"
    beta = True

    inputs = [
        StrInput(
            name="target_username",
            display_name="Target Username",
            required=True,
            info="Instagram handle of the profile to fetch."
        ),
        StrInput(
            name="login_user",
            display_name="Login Username",
            required=True,
            info="Your Instagram login username"
        ),
        SecretStrInput(
            name="login_pass",
            display_name="Login Password",
            required=True,
            info="Your Instagram login password"
        ),
    ]

    outputs = [
        Output(name="profile_data", display_name="Profile Data", method="fetch_profile_data"),
    ]

    def fetch_profile_data(self) -> Data:
        from selenium.webdriver.support import expected_conditions as EC

        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Descomente quando estiver estável
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://www.instagram.com/accounts/login/")

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )

            user_input = driver.find_element(By.NAME, "username")
            pass_input = driver.find_element(By.NAME, "password")

            user_input.send_keys(self.login_user)
            pass_input.send_keys(self.login_pass)
            pass_input.send_keys(Keys.RETURN)

            WebDriverWait(driver, 20).until_not(
                EC.presence_of_element_located((By.NAME, "username"))
            )

            profile_url = f"https://www.instagram.com/{self.target_username}/"
            driver.get(profile_url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "header"))
            )

            header = driver.find_element(By.TAG_NAME, "header")
            spans = header.find_elements(By.TAG_NAME, "span")

            followers = followees = 0
            if len(spans) >= 2:
                followers = spans[1].get_attribute("title") or spans[1].text
                followees = spans[2].text

            # Alternativa mais robusta para nome e foto
            images = driver.find_elements(By.TAG_NAME, "img")
            profile_pic = ""
            name = ""
            for img in images:
                alt = img.get_attribute("alt")
                src = img.get_attribute("src")
                if alt and self.target_username.lower() in alt.lower():
                    name = alt
                    profile_pic = src
                    break

            try:
                bio = driver.find_element(By.XPATH, '//div[contains(@class, "-vDIg")]').text
            except:
                bio = ""

            return Data(data={
                "username": self.target_username,
                "full_name": name,
                "biography": bio,
                "followers": followers,
                "followees": followees,
                "profile_pic_url": profile_pic
            })

        except TimeoutException:
            msg = "Timeout while loading Instagram."
            self.log(msg)
            self.status = msg
            return Data(data={"error": msg})

        except Exception as e:
            error_msg = f"Error during scraping: {e}"
            self.log(error_msg)
            self.status = error_msg
            return Data(data={"error": error_msg})

        finally:
            if driver:
                driver.quit()

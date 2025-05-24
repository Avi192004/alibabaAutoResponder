import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import json
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

# Configure logging
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

app = FastAPI()

MAIN_URL = "https://onetalk.alibaba.com/message/weblitePWA.htm?isGray=1&from=menu&hideMenu=1#/"
BASE_URL = "https://alibaba.com/"
COOKIES_FILE = "cookies.json"

class RecipientList(BaseModel):
    recipients: List[str]  # List of recipients

def random_delay(min_sec=1, max_sec=5):
    """ Generates a random delay to avoid detection """
    delay = random.uniform(min_sec, max_sec)
    logging.info(f"Sleeping for {delay:.2f} seconds...")
    time.sleep(delay)

def start_browser():
    """ Start undetected Chrome with anti-bot settings """
    logging.info("Starting undetected Chrome browser...")
    
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")  
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    options.add_argument("--headless=new")

    driver = uc.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

    logging.info("Chrome browser started successfully.")
    return driver

def login(driver):
    """ Login to Alibaba using saved cookies """
    logging.info("Navigating to Alibaba base URL for login...")
    driver.get(BASE_URL)
    random_delay(3, 6)

    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
            for cookie in cookies:
                if "expiry" in cookie:
                    cookie["expiry"] = int(cookie["expiry"])  # Ensure expiry is an integer
                driver.add_cookie(cookie)
        logging.info("✅ Cookies loaded successfully!")

    driver.get(MAIN_URL)
    logging.info("Navigated to Alibaba messaging page.")
    random_delay(5, 8)

def send_ai_response(driver, recipient):
    """ Send AI-generated response to the recipient """
    try:
        random_delay(4, 7)

        recipient_xpath = f"//div[@class='contact-item-container' and @data-name='{recipient}']"
        try:
            recipient_element = driver.find_element(By.XPATH, recipient_xpath)
        except:
            logging.warning(f"❌ User '{recipient}' does not exist.")
            return {"recipient": recipient, "status": "not exist"}

        random_delay(2, 4)
        recipient_element.click()
        random_delay(4, 6)
        logging.info("Fetching AI-generated response...")

        ai_button = driver.find_element(By.ID, "assistant-entry-icon")
        ai_button.click()
        random_delay(15, 25)

        use_this_btn = driver.find_element(By.XPATH, "//button[contains(., 'Use this')]")
        use_this_btn.click()
        random_delay(2, 4)

        message_box = driver.find_element(By.CSS_SELECTOR, "#send-box-wrapper > div.send-input-areas > div.send-textarea-box.undefined > pre")
        ai_text = message_box.get_attribute("textContent")

        logging.info(f"🤖 AI Response: {ai_text}")
        random_delay(2, 5)

        send_button = driver.find_element(By.XPATH, "//button[contains(@class, 'send-tool-button')]")
        random_delay(1, 3)
        send_button.click()

        random_delay(2, 4)
        logging.info(f"✅ Message sent successfully to {recipient}.")
        return {"recipient": recipient, "status": "success", "message": ai_text}

    except Exception as e:
        logging.error(f"❌ Failed to send message to {recipient}: {str(e)}")
        return {"recipient": recipient, "status": "failed", "error": str(e)}

@app.get("/")
def read_root():
    """ Root endpoint to check if the server is running """
    return {"message": "Welcome to the Alibaba AI Messaging Service!"}


@app.post("/send_ai_messages/")
def api_send_ai_messages(request: RecipientList):
    """ API endpoint to send AI-generated messages to multiple recipients """
    logging.info(f"Received request to send AI messages to {len(request.recipients)} recipients.")

    driver = start_browser()
    try:
        login(driver)

        close_pop = driver.find_elements(By.CLASS_NAME, "im-next-dialog-close")
        if close_pop:
            close_pop[0].click()
            log_activity("🔒 Closed pop-up.")

        close_pop = driver.find_elements(By.CLASS_NAME, "close-icon")
        if close_pop:
            close_pop[0].click()
            log_activity("🔒 Closed pop-up.")

        results = []
        for recipient in request.recipients:
            random_delay(3, 7)

            result = send_ai_response(driver, recipient)
            results.append(result)

        logging.info("All AI messages processed.")
        return {"results": results}
    finally:
        logging.info("Closing browser.")
        driver.quit()

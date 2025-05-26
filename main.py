import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import random
import json
import os
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

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
BASE_URL = "https://i.alibaba.com/"
COOKIES_FILE = "cookies.json"

# Fallback replies
FALLBACK_REPLIES = [
    "Hello! Thanks for your inquiry. Our team will assist you shortly.",
    "Hi there! Your inquiry is important to us. We'll be with you shortly.",
    "Greetings! Thank you for reaching out. One of our representatives will assist you soon.",
    "Hey! Thanks for getting in touch. We'll be happy to help you shortly.",
    "Hi! We appreciate your message. Our team will assist you as soon as possible.",
    "Hello! Thanks for your inquiry. Please hold on, our team will assist you soon."
]

class RecipientItem(BaseModel):
    recipient: str
    message: Optional[str] = None  # Optional custom message

class RecipientList(BaseModel):
    recipients: List[RecipientItem]

def random_delay(min_sec=1, max_sec=5):
    delay = random.uniform(min_sec, max_sec)
    logging.info(f"Sleeping for {delay:.2f} seconds...")
    time.sleep(delay)

def start_browser():
    logging.info("Starting undetected Chrome browser...")
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    # options.add_argument("--headless=new")  # Uncomment if you want headless mode

    driver = uc.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    logging.info("Chrome browser started successfully.")
    return driver

def login(driver):
    logging.info("Navigating to Alibaba base URL for login...")
    driver.get(BASE_URL)
    random_delay(3, 6)

    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
            for cookie in cookies:
                if "expiry" in cookie:
                    cookie["expiry"] = int(cookie["expiry"])
                driver.add_cookie(cookie)
        logging.info("✅ Cookies loaded successfully!")

    driver.get(MAIN_URL)
    logging.info("Navigated to Alibaba messaging page.")
    random_delay(5, 8)

def send_ai_response(driver, recipient, custom_message=None):
    try:
        try:
            span_search = driver.find_element(By.XPATH, "//span[contains(text(), 'Search')]")
            span_search.click()
            random_delay(2, 3)
        except Exception as e:
            logging.warning(f"⚠️ Could not find 'Search' span: {e}")

        # Step 2: Type recipient's name into the search input
        search_input = driver.find_element(By.ID, "im-search-input")
        search_input.clear()
        search_input.send_keys(recipient)
        random_delay(1, 2)
        search_input.send_keys(Keys.RETURN)
        
        random_delay(4, 7)
        # recipient_xpath = f"//div[@class='contact-item-container' and @data-name='{recipient}']"
        try:
            # recipient_element = driver.find_elements(By.XPATH, recipient_xpath)
            recipient_element = driver.find_elements(By.CLASS_NAME, 'contact-list-item')[0]
        except:
            logging.warning(f"❌ User '{recipient}' does not exist.")
            return {"recipient": recipient, "status": "not exist"}

        recipient_element.click()
        random_delay(4, 6)

        if custom_message:
            logging.info(f"📝 Sending custom message to {recipient}: {custom_message}")
            message = custom_message
        else:
            try:
                logging.info("🤖 Fetching AI-generated response...")
                ai_button = driver.find_element(By.ID, "assistant-entry-icon")
                ai_button.click()
                random_delay(10, 20)

                use_this_btn = driver.find_element(By.XPATH, "//button[contains(., 'Use this')]")
                use_this_btn.click()
                random_delay(2, 4)

                message_box = driver.find_element(By.CSS_SELECTOR, "#send-box-wrapper pre")
                message = message_box.get_attribute("textContent").strip()
                logging.info(f"✅ AI Response: {message}")
            except Exception as e:
                logging.warning(f"⚠️ AI generation failed: {e}")
                message = random.choice(FALLBACK_REPLIES)
                logging.info(f"💬 Using fallback reply: {message}")

        random_delay(2, 4)
        message_input = driver.find_element(By.CLASS_NAME, "send-textarea")
        message_input.send_keys(message)

        random_delay(2, 5)
        send_button = driver.find_element(By.XPATH, "//button[contains(@class, 'send-tool-button')]")
        send_button.click()

        logging.info(f"✅ Message sent to {recipient}.")
        return {"recipient": recipient, "status": "success", "message": message}

    except Exception as e:
        logging.error(f"❌ Failed to send message to {recipient}: {str(e)}")
        return {"recipient": recipient, "status": "failed", "error": str(e)}

@app.post("/send_ai_messages/")
def api_send_ai_messages(request: RecipientList):
    logging.info(f"📩 Received request to send messages to {len(request.recipients)} recipients.")

    driver = start_browser()
    try:
        login(driver)

        close_pop = driver.find_elements(By.CLASS_NAME, "im-next-dialog-close")
        if close_pop:
            close_pop[0].click()
            print("🔒 Closed pop-up.")

        close_pop = driver.find_elements(By.CLASS_NAME, "close-icon")
        if close_pop:
            close_pop[0].click()
            print("🔒 Closed pop-up.")
        
        results = []
        for item in request.recipients:
            random_delay(3, 7)
            result = send_ai_response(driver, item.recipient, custom_message=item.message)
            results.append(result)

        logging.info("✅ All messages processed.")
        return {"results": results}
    finally:
        logging.info("🧹 Closing browser.")
        driver.quit()

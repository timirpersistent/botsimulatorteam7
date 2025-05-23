from dotenv import load_dotenv
load_dotenv()
import time
import os
import re
import logging
from mailslurp_client import Configuration, ApiClient, InboxControllerApi, WaitForControllerApi
from DrissionPage import ChromiumPage, ChromiumOptions
from CloudflareBypasser import CloudflareBypasser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Load MailSlurp API Key
MAILSLURP_API_KEY = os.getenv("MAILSLURP_API_KEY")
if not MAILSLURP_API_KEY:
    raise EnvironmentError("MAILSLURP_API_KEY environment variable not set.")

# Configure Chromium options
def get_chromium_options(browser_path: str, arguments: list) -> ChromiumOptions:
    options = ChromiumOptions().auto_port()
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options

def run_once():
    browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")  # Or Chrome path on Windows
    arguments = [
        "-no-first-run", "-disable-background-mode", "-disable-gpu",
        "-deny-permission-prompts", "-no-default-browser-check"
    ]
    options = get_chromium_options(browser_path, arguments)
    driver = ChromiumPage(addr_or_opts=options)

    try:
        logging.info("Navigating to target URL.")
        driver.get('https://qa-campaign-forms.woodbridgewines.com/campaigns/woodbridgewines/email-validation/woodbridge_dogday_2025')

        logging.info("Bypassing initial Cloudflare CAPTCHA...")
        cf_bypasser = CloudflareBypasser(driver)
        cf_bypasser.bypass()

        logging.info("Waiting for email form to load...")
        driver.wait.ele_displayed('css:#email', timeout=60)
        logging.info("Form is ready. Waiting 10 seconds before filling.")
        time.sleep(10)

        # Generate MailSlurp email
        configuration = Configuration(api_key={"x-api-key": MAILSLURP_API_KEY})
        with ApiClient(configuration) as api_client:
            inbox_controller = InboxControllerApi(api_client)
            wait_controller = WaitForControllerApi(api_client)
            inbox = inbox_controller.create_inbox()
            email_address = inbox.email_address
            logging.info(f"Generated email: {email_address}")

        # Fill the email field and submit
        email_input = driver.ele('css:#email')
        email_input.input(email_address)
        submit_btn = driver.ele('css:#email + button')
        submit_btn.click()
        logging.info("Form submitted.")
        time.sleep(2)
        driver.quit()
        # Wait for verification email
        logging.info("Waiting for verification email...")
        email = wait_controller.wait_for_latest_email(
            inbox_id=inbox.id,
            timeout=30000,
            unread_only=True
        )

        if email and email.body:
            match = re.search(r'href="([^"]+)"', email.body)
            if match:
                verification_link = match.group(1)
                logging.info(f"Verification link: {verification_link}")
                # Open a new browser window using a new ChromiumPage instance
                verify_browser = ChromiumPage(addr_or_opts=options)
                verify_browser.get(verification_link)
                #driver.new_tab(verification_link, switch=True)
                logging.info("Verification link opened.")
                # Run Cloudflare bypass again on the new browser
                logging.info('Running Cloudflare bypass on verification page...')
                verify_bypasser = CloudflareBypasser(verify_browser)
                verify_bypasser.bypass()

                # Wait for form fields to be visible
                verify_browser.wait.ele_displayed('css:#firstName', timeout=60)
                verify_browser.wait.ele_displayed('css:#lastName', timeout=60)
                verify_browser.wait.ele_displayed('css:#address1', timeout=60)
                verify_browser.wait.ele_displayed('css:#city', timeout=60)
                verify_browser.wait.ele_displayed('css:#state', timeout=60) 
                verify_browser.wait.ele_displayed('css:#zip', timeout=60)
                verify_browser.wait.ele_displayed('css:#dob', timeout=60)
                verify_browser.wait.ele_displayed('css:#phone', timeout=60)
                verify_browser.wait.ele_displayed('css:input[type="checkbox"]', timeout=60)
                
                # Fill the form fields
                # Always re-query elements before interacting to avoid stale element errors
                verify_browser.wait.ele_displayed('css:#firstName', timeout=10)
                verify_browser.ele('css:#firstName').input('John')
                verify_browser.wait.ele_displayed('css:#lastName', timeout=10)
                verify_browser.ele('css:#lastName').input('Doe')
                verify_browser.wait.ele_displayed('css:#address1', timeout=10)
                verify_browser.ele('css:#address1').input('123 Main St')
                verify_browser.wait.ele_displayed('css:#city', timeout=10)
                verify_browser.ele('css:#city').input('Los Angeles')
                verify_browser.wait.ele_displayed('css:#state', timeout=10)
                state_dropdown = verify_browser.ele('css:#state')
                state_dropdown.click()
                option = state_dropdown.ele('css:option[value="CA"]')
                option.click()
                verify_browser.wait.ele_displayed('css:#dob', timeout=10)
                verify_browser.run_js('document.querySelector("#dob").value = "1990-01-01";')
                verify_browser.wait.ele_displayed('css:#phone', timeout=10)
                verify_browser.ele('css:#phone').input('(555) 555-5555')
                verify_browser.wait.ele_displayed('css:#zip', timeout=10)
                verify_browser.ele('css:#zip').input('90001')
                verify_browser.wait.ele_displayed('css:input[type="checkbox"]', timeout=10)
                verify_browser.ele('css:input[type="checkbox"]').click()
                # Bypass Cloudflare CAPTCHA again if present
                logging.info('Bypassing Cloudflare CAPTCHA on form page...')
                verify_bypasser.bypass()
                # Wait for the submit button to be clickable
                verify_browser.wait.ele_displayed('css:form button[type="submit"]', timeout=60)
                time.sleep(3)  # Additional wait to ensure the button is clickable
                # Submit the form (assuming a submit button is present)
                submit_btn = verify_browser.ele('css:form button[type="submit"]')
                submit_btn.click()
                logging.info('Form submitted on verification page.')

                logging.info("✅ Verification completed. Title: %s", verify_browser.title)
            else:
                logging.warning("No verification link found in email.")
        else:
            logging.warning("No email received.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

    finally:
        logging.info("Script completed. Closing browser.")
        driver.quit()

if __name__ == '__main__':
    for i in range(5):
        logging.info(f"--- Run {i+1} of 5 ---")
        run_once()
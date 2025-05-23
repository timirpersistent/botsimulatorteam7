
from dotenv import load_dotenv
load_dotenv()
import time
import logging
import os
import re
from mailslurp_client import Configuration, ApiClient, InboxControllerApi, WaitForControllerApi
from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage, ChromiumOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cloudflare_bypass.log', mode='w')
    ]
)

def get_chromium_options(browser_path: str, arguments: list) -> ChromiumOptions:
    options = ChromiumOptions().auto_port()
    options.set_paths(browser_path=browser_path)
    for argument in arguments:
        options.set_argument(argument)
    return options

def create_mailslurp_inbox():
    config = Configuration()
    config.api_key['x-api-key'] = os.getenv('MAILSLURP_API_KEY')
    with ApiClient(config) as api_client:
        inbox_api = InboxControllerApi(api_client)
        inbox = inbox_api.create_inbox()
        return inbox

def wait_for_email_and_verify(inbox_id):
    config = Configuration()
    config.api_key['x-api-key'] = os.getenv('MAILSLURP_API_KEY')
    with ApiClient(config) as api_client:
        wait_api = WaitForControllerApi(api_client)
        email = wait_api.wait_for_latest_email(inbox_id=inbox_id, timeout=30000)
        # Suppose `email.body` contains the raw HTML or plain text of the email
        if email and email.body:
            match = re.search(r'https:\/\/[^\s"\'>]+', email.body)
            if match:
                verification_link = match.group(0)
                print("🔗 Verification link:", verification_link)
            else:
                print("❌ No verification link found.")
    return None

def main():
    isHeadless = os.getenv('HEADLESS', 'false').lower() == 'true'
    if isHeadless:
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1920, 1080))
        display.start()

    browser_path = os.getenv('CHROME_PATH', "/usr/bin/google-chrome")
    arguments = [
        "-no-first-run", "-force-color-profile=srgb", "-metrics-recording-only", "-password-store=basic",
        "-use-mock-keychain", "-export-tagged-pdf", "-no-default-browser-check", "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage", "-deny-permission-prompts",
        "-disable-gpu", "-accept-lang=en-US",
    ]

    options = get_chromium_options(browser_path, arguments)
    driver = ChromiumPage(addr_or_opts=options)

    try:
        logging.info('Creating MailSlurp inbox.')
        inbox = create_mailslurp_inbox()
        logging.info(f'Created inbox: {inbox.email_address}')

        logging.info('Navigating to form page.')
        driver.get('https://qa-campaign-forms.woodbridgewines.com/campaigns/woodbridgewines/email-validation/woodbridge_dogday_2025')

        logging.info('Starting Cloudflare bypass.')
        cf_bypasser = CloudflareBypasser(driver)
        cf_bypasser.bypass()

        logging.info('Waiting for email input field to appear...')
        driver.ele('#email', timeout=120).input(inbox.email_address)
        driver.ele('#email').submit()
        logging.info(f'Submitted form with email: {inbox.email_address}')

        time.sleep(10)
        logging.info('Waiting for verification email...')
        verify_link = wait_for_email_and_verify(inbox.id)

        if verify_link:
            logging.info(f'Verification link received: {verify_link}')
            driver.get(verify_link)
            logging.info('Visited verification link.')
        else:
            logging.warning('No verification link found in email.')

        time.sleep(5)
    except Exception as e:
        logging.error("An error occurred: %s", str(e))
    finally:
        driver.quit()
        if isHeadless:
            display.stop()

if __name__ == '__main__':
    main()

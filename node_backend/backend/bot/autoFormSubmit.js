const { MailSlurp } = require('mailslurp-client');
const puppeteer = require('puppeteer');

const mailslurp = new MailSlurp({ apiKey: 'b29ada7fd17dad85212b65f07488fedc14647705cf48ffcfec92f08a5d46ada8' }); // Replace with your MailSlurp API Key

(async () => {
  const inbox = await mailslurp.createInbox();
  console.log('Created inbox:', inbox.emailAddress);

  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8080/'); // Adjust if serving differently

  await page.type('#email', inbox.emailAddress);

  // Bypass Cloudflare Turnstile CAPTCHA (test key)
  // The test sitekey always returns 'test-token' as a valid response
  await page.evaluate(() => {
    document.querySelector('input[name="cf-turnstile-response"]').value = 'test-token';
  });

  await page.click('button[type="submit"]');

  console.log('Form submitted');

  const email = await mailslurp.waitForLatestEmail(inbox.id, 30000);
  if (email && email.body) {
    const imageLines = email.body.split('\n').filter(line => line.includes('dummyimage.com'));
    const codeMatch = email.body.match(/&text=([A-Za-z0-9]+)/);
    if (codeMatch && codeMatch[1]) {
      console.log('Verification code from email image:', codeMatch[1]);
    } else {
      console.log('No verification code image found in email');
    }
    // Extract code from the plain text in the email body (alphanumeric, 5+ chars, allow whitespace and HTML variations)
    const textCodeMatch = email.body.match(/Your verification code \(text\)[^<]*<b[^>]*>([A-Z0-9]{5,})<\/b>/i);
    if (textCodeMatch && textCodeMatch[1]) {
      console.log('Verification code from email text:', textCodeMatch[1]);
    } else {
      // Try a fallback: extract any <b>CODE</b> after 'Your verification code (text):'
      const fallbackMatch = email.body.match(/Your verification code \(text\)[^<]*:<b[^>]*>([A-Z0-9]{5,})<\/b>/i);
      if (fallbackMatch && fallbackMatch[1]) {
        console.log('Verification code from email text (fallback):', fallbackMatch[1]);
      } else {
        console.log('No verification code (text) found in email');
      }
    }
    const match = email.body.match(/href=\"([^\"]+)\"/);
    if (match && match[1]) {
      //console.log(email.body);
      const verificationLink = match[1];
      console.log('Verification link:', verificationLink);
      const verifyPage = await browser.newPage();
      await verifyPage.goto(verificationLink);
      console.log('Visited verification link');
    } else {
      console.log('No verification link found in email');
    }
  } else {
    console.log('No email received');
  }

  await browser.close();
})();

const express = require('express');
const bodyParser = require('body-parser');
const nodemailer = require('nodemailer');
const app = express();
const PORT = 3987;

app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.json()); // For JSON body parsing (needed for Turnstile token)

app.post('/submit', async (req, res) => {
  const { email, 'cf-turnstile-response': turnstileToken } = req.body;

  // Verify Turnstile token (test secret)
  if (!turnstileToken) {
    return res.status(400).send('Missing Turnstile token');
  }
  try {
    const verifyRes = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `secret=1x0000000000000000000000000000000AA&response=${turnstileToken}`
    });
    const verifyData = await verifyRes.json();
    if (!verifyData.success) {
      return res.status(403).send('CAPTCHA verification failed');
    }
  } catch (err) {
    return res.status(500).send('CAPTCHA verification error');
  }

  // Generate alphanumeric codes for text and image
  const randomAlphaNum = () => Math.random().toString(36).substring(2, 7).toUpperCase();
  const verificationCodeText = randomAlphaNum();
  const verificationCodeImage = randomAlphaNum();
  
  console.log(`Verification code for ${email} (text):`, verificationCodeText);
  console.log(`Verification code for ${email} (image):`, verificationCodeImage);

  const transporter = nodemailer.createTransport({
    host: 'mailslurp.mx',
    port: 2587,
    secure: false,
    auth: {
      user: 'user-605be350-e801-42b2-8fb6-0dca8fba43f1@mailslurp.biz',
      pass: 'eu5jROfEx1D1EyBIoVPWcysOeIPpibrR'
    },
    tls: {
      rejectUnauthorized: false
    }
  });

  const verificationLink = `https://modelousa.com/verify?email=${encodeURIComponent(email)}`;
  const imageUrl = `https://dummyimage.com/120x40/cccccc/000000&text=${verificationCodeImage}`;

  await transporter.sendMail({
    from: 'no-reply@test.com',
    to: email,
    subject: 'Confirm Your Email Address',
    html: `
      <div style="max-width:500px;margin:40px auto;padding:32px 24px 24px 24px;background:#fff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);font-family:Roboto,sans-serif;text-align:center;">
        <h2 style="color:#002452;font-size:28px;margin-bottom:16px;">Confirm Your Email Address</h2>
        <p style="font-size:16px;color:#222;margin-bottom:24px;">Click on the link below to confirm your email address. If your email address is successfully validated, you will be linked to the Website registration form in order to enter the Woodbridge Dog Days Grill-off Sweepstakes.</p>
        <a href="${verificationLink}" style="display:inline-block;margin:16px 0 24px 0;padding:12px 28px;background:#fdc338;color:#002452;font-weight:600;text-decoration:none;border-radius:6px;font-size:18px;">Confirm Email</a>
        <div style="margin:24px 0 0 0;">
          <p style="font-size:16px;color:#222;margin-bottom:8px;">Your verification code (text): <b>${verificationCodeText}</b></p>
          <p style="font-size:16px;color:#222;margin-bottom:8px;">Your verification code (image):</p>
          <img src="${imageUrl}" alt="Verification Code" style="margin:0 auto;display:block;" />
        </div>
      </div>
    `
  });

  try {
    const fetch = require('node-fetch');
    const Tesseract = require('tesseract.js');
    const response = await fetch(imageUrl);
    if (response.ok) {
      const buffer = await response.buffer();
      const { data: { text } } = await Tesseract.recognize(buffer, 'eng');
      const codeFromImage = text.replace(/\s/g, '');
      console.log(`Extracted code from image: ${codeFromImage}`);
    } else {
      console.log('Failed to fetch verification image for OCR.');
    }
  } catch (err) {
    console.log('OCR failed:', err.message);
  }

  res.send('Signup successful. Check your email for the verification code.');
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});

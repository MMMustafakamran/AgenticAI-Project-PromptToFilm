const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  page.on('pageerror', err => console.log('pageerror:', err.message));
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
  console.log('root-length:', (await page.$eval('#root', el => el.innerHTML)).length);
  await page.screenshot({ path: 'playwright-home-fixed.png', fullPage: true });
  await browser.close();
})();

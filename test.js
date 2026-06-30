const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({ headless: "new", args: ['--no-sandbox'] });
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
    page.on('requestfailed', request => console.log('REQ FAILED:', request.url(), request.failure().errorText));

    await page.goto('http://localhost:8080', { waitUntil: 'networkidle0' }).catch(e => console.log("GOTO ERROR:", e.message));
    await new Promise(r => setTimeout(r, 2000));
    await browser.close();
})();

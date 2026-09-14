const { chromium } = require("playwright-core");

(async () => {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });

  // login
  await page.goto("http://127.0.0.1:5173/login", { waitUntil: "networkidle" });
  await page.fill('input[type="email"], input[name="email"]', "admin@ulpf.io").catch(() => {});
  await page.fill('input[type="password"], input[name="password"]', "ChangeMe!123").catch(() => {});
  await page.screenshot({ path: "login.png" });

  const btn = page.getByRole("button", { name: /sign in|log in|login/i });
  await btn.click().catch(async () => {
    await page.click('button[type="submit"]').catch(() => {});
  });

  await page.waitForTimeout(2500);
  await page.screenshot({ path: "dashboard.png", fullPage: true });

  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});

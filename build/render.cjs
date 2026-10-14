// Render HTML jobs to PNG with Playwright's Chromium.
// Usage: node render.cjs jobs.json   where jobs = [{ html: "/abs/file.html", out: "/abs/out.png", width, height, fullPage }]
// Uses any installed Playwright: `npm i -D playwright` here, or point PLAYWRIGHT_MODULE at one.
function loadChromium() {
  for (const m of [process.env.PLAYWRIGHT_MODULE, "playwright", "@playwright/test",
                   "/Users/elmarco/Projects/kabacade-hq/node_modules/@playwright/test"]) {
    if (!m) continue;
    try { return require(m).chromium; } catch (_) {}
  }
  throw new Error("Playwright not found: npm i -D playwright, or set PLAYWRIGHT_MODULE");
}
const chromium = loadChromium();
const fs = require("fs");

(async () => {
  const jobs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ deviceScaleFactor: 1 });
  const queue = jobs.slice();
  let done = 0;
  const failures = [];
  async function worker() {
    const page = await ctx.newPage();
    while (queue.length) {
      const job = queue.shift();
      try {
        await page.setViewportSize({ width: job.width || 1600, height: job.height || 900 });
        await page.goto("file://" + job.html, { waitUntil: "load" });
        await page.evaluate(() => document.fonts.ready);
        await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete), null, { timeout: 30000 });
        await page.screenshot({ path: job.out, fullPage: !!job.fullPage, type: "png" });
      } catch (e) {
        failures.push(job.out + " :: " + e.message.split("\n")[0]);
      }
      done++;
      if (done % 25 === 0) console.log(`rendered ${done}/${jobs.length}`);
    }
    await page.close();
  }
  await Promise.all(Array.from({ length: 6 }, worker));
  await browser.close();
  console.log(`done ${done}, failures ${failures.length}`);
  if (failures.length) console.log(failures.join("\n"));
})();

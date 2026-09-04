import puppeteer from "puppeteer-core";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const OUT = "/private/tmp/claude-501/-Users-anjul-Desktop-Groww/fc865e3d-ee4c-4ddb-bc24-16ac7b986121/scratchpad";
const BASE = "http://localhost:5173";

console.log("launching chrome…");
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  userDataDir: `${OUT}/chrome-profile`,
  args: [
    "--no-sandbox",
    "--no-first-run",
    "--disable-gpu",
    "--window-size=1440,1000",
  ],
  defaultViewport: { width: 1440, height: 1000 },
});
console.log("launched");
const page = await browser.newPage();
const errors = [];
page.on("console", (m) => {
  if (m.type() === "error") errors.push("console.error: " + m.text());
});
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

async function snap(name) {
  await new Promise((r) => setTimeout(r, 1200));
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log("shot", name);
}

// login
await page.goto(`${BASE}/login`, { waitUntil: "networkidle2" });
await snap("01-login");
await page.type('input[type="email"]', "demo@marketdetective.dev").catch(() => {});
const inputs = await page.$$("input");
if (inputs[0]) await inputs[0].type("Demo Detective");
if (inputs[1]) { await inputs[1].click({ clickCount: 3 }); await inputs[1].type("demo@marketdetective.dev"); }
await page.keyboard.press("Enter");
await page.waitForNavigation({ waitUntil: "networkidle2" }).catch(() => {});
await new Promise((r) => setTimeout(r, 2000));

for (const [route, name] of [
  ["/", "02-dashboard"],
  ["/watchlists", "03-watchlists"],
  ["/stocks", "04-stocks"],
  ["/time-machine", "05-timemachine"],
]) {
  await page.goto(`${BASE}${route}`, { waitUntil: "networkidle2" });
  await snap(name);
}

// a case detail
const caseLink = await page.$('a[href^="/cases/"]');
if (caseLink) {
  await caseLink.click();
  await new Promise((r) => setTimeout(r, 2500));
  await snap("06-case");
}

console.log("ERRORS:", errors.length ? "\n" + errors.join("\n") : "none");
await browser.close();

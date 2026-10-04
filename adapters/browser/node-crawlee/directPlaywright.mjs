import { chromium } from 'playwright';
import { performance } from 'node:perf_hooks';

const arg = name => process.argv[process.argv.indexOf(name) + 1];
const base = arg('--base');
const count = Number(arg('--count'));
const concurrency = Number(arg('--concurrency'));
const delayMs = Number(arg('--delay-ms'));
const executablePath = arg('--executable');
const browser = await chromium.launch({ executablePath, headless: true, chromiumSandbox: true });
const values = new Array(count);
let next = 0;
const started = performance.now();
async function worker() {
  while (true) {
    const index = next++;
    if (index >= count) return;
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${base}/dynamic?id=${index}&delayMs=${delayMs}`, { waitUntil: 'domcontentloaded' });
    values[index] = await page.locator('span.value').textContent();
    await context.close();
  }
}
await Promise.all(Array.from({ length: concurrency }, worker));
const wallNs = Math.round((performance.now() - started) * 1e6);
await browser.close();
const terminalStatus = values.every((value, index) => value === `value-${index}`) ? 'ok' : 'wrongOutput';
console.log(JSON.stringify({ armId:'directPlaywright',language:'node',count,concurrency,delayMs,wallNs,throughputRequestsPerSecond:count/(wallNs/1e9),terminalStatus,values }));
process.exit(terminalStatus === 'ok' ? 0 : 2);

import { PlaywrightCrawler } from 'crawlee';
import { performance } from 'node:perf_hooks';

const arg = name => process.argv[process.argv.indexOf(name) + 1];
const base = arg('--base');
const count = Number(arg('--count'));
const concurrency = Number(arg('--concurrency'));
const delayMs = Number(arg('--delay-ms'));
const executablePath = arg('--executable');
const values = new Map();
const crawler = new PlaywrightCrawler({
  maxConcurrency: concurrency,
  minConcurrency: concurrency,
  maxRequestRetries: 0,
  requestHandlerTimeoutSecs: 45,
  launchContext: { launchOptions: { executablePath, headless: true } },
  requestHandler: async ({ page, request }) => {
    const index = Number(request.userData.index);
    values.set(index, await page.locator('span.value').textContent());
  },
});
const requests = Array.from({ length: count }, (_, index) => ({ url: `${base}/dynamic?id=${index}&delayMs=${delayMs}`, uniqueKey: `dynamic-${index}`, userData: { index } }));
const started = performance.now();
await crawler.run(requests);
await crawler.teardown();
const wallNs = Math.round((performance.now() - started) * 1e6);
const ordered = Array.from({ length: count }, (_, index) => values.get(index));
const terminalStatus = ordered.every((value, index) => value === `value-${index}`) ? 'ok' : 'wrongOutput';
console.log(JSON.stringify({ armId:'crawleePlaywright',language:'node',count,concurrency,delayMs,wallNs,throughputRequestsPerSecond:count/(wallNs/1e9),terminalStatus,values:ordered }));
process.exit(terminalStatus === 'ok' ? 0 : 2);

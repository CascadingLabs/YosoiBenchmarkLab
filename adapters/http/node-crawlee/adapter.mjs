import { CheerioCrawler } from 'crawlee';
import { performance } from 'node:perf_hooks';

const argument = name => process.argv[process.argv.indexOf(name) + 1];
const base = argument('--base');
const count = Number(argument('--count'));
const concurrency = Number(argument('--concurrency'));
const delayMs = Number(argument('--delay-ms'));
const values = new Map();
const crawler = new CheerioCrawler({
  maxConcurrency: concurrency,
  minConcurrency: concurrency,
  maxRequestRetries: 0,
  requestHandlerTimeoutSecs: 30,
  requestHandler: async ({ $, request }) => {
    const index = Number(request.userData.index);
    values.set(index, $('span.value').text().trim());
  },
});
const requests = Array.from({ length: count }, (_, index) => ({
  url: `${base}/page?id=${index}&delayMs=${delayMs}`,
  uniqueKey: `request-${index}`,
  userData: { index },
}));
const started = performance.now();
await crawler.run(requests);
const wallNs = Math.round((performance.now() - started) * 1_000_000);
const ordered = Array.from({ length: count }, (_, index) => values.get(index));
const terminalStatus = ordered.every((value, index) => value === `value-${index}`) ? 'ok' : 'wrongOutput';
console.log(JSON.stringify({ armId: 'crawleeCheerio', language: 'node', count, concurrency, delayMs, wallNs, throughputRequestsPerSecond: count / (wallNs / 1e9), terminalStatus, values: ordered }));
if (terminalStatus !== 'ok') process.exitCode = 2;

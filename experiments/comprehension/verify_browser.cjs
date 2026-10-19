// Open the actual saved study report with networking blocked.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');
(async () => {
  const root = path.resolve(__dirname, '../..');
  const rows = JSON.parse(fs.readFileSync(path.join(__dirname, 'inputs.json'), 'utf8')).rows;
  const records = fs.readFileSync(path.join(root, 'results/comprehension/responses.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.equal(records.length, 384, 'full paired evidence required');
  const browser = await chromium.launch({headless:true});
  try {
    const context = await browser.newContext({offline:true});
    await context.route(/^https?:/, route => route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.join(root, 'results/comprehension/comparison.html')).href);
    assert.equal(await page.locator('details').count(), 64);
    assert.equal(await page.locator('details h3').count(), 384);
    assert.equal(await page.locator('table tr').count(), 7);
    let tableIndex = 1;
    for (const condition of ['clean','colemak','dvorak','decoded_colemak','decoded_dvorak','question_only']) {
      const recordsForCondition = records.filter(r => r.condition === condition);
      const k = recordsForCondition.filter(r => r.correct).length;
      const cells = page.locator('table tr').nth(tableIndex++).locator('td');
      assert.equal(await cells.nth(0).textContent(), condition);
      assert.equal(await cells.nth(1).textContent(), `${k}/64`);
    }
    const first = page.locator('details').first();
    await first.locator('summary').focus();
    await page.keyboard.press('Enter');
    assert(await first.evaluate(el => el.open));
    assert((await first.innerText()).includes(rows[0].question));
    assert.equal(await first.locator('pre').first().textContent(), records[0].request.prompt);
    const last = page.locator('details').last();
    await last.locator('summary').click();
    assert(await last.evaluate(el => el.open));
    assert((await last.innerText()).includes(rows.at(-1).question));
    assert.deepEqual(errors, []);
    console.log('PASS: Chromium opens offline report, renders all 64 examples / 384 prompts, expands details with keyboard, preserves exact prompt text; no page errors.');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode=1;});

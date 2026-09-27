'use strict';
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname,'..');
const folder = fs.mkdtempSync(path.join(os.tmpdir(),'keyboard-rescue-browser-'));
let assertions = 0;
function check(value, message) { assertions++; assert.ok(value,message); }
function equal(actual, expected, message) { assertions++; assert.deepEqual(actual,expected,message); }
function fixture(text, stem='hostile', geometry='iso') {
  const code = `import sys\nfrom pathlib import Path\nfrom keyboard_rescue.core import analyze\nfrom keyboard_rescue.report import html_text,json_text\nr=analyze(sys.stdin.buffer.read().decode('utf-8'),'qwerty',['colemak','dvorak'],'${geometry}')\nPath(sys.argv[1]).write_text(html_text(r),encoding='utf-8')\nPath(sys.argv[2]).write_text(json_text(r),encoding='utf-8')`;
  const html = path.join(folder,stem+'.html'), json = path.join(folder,stem+'.json');
  const result = spawnSync(process.env.PYTHON || 'python3',['-c',code,html,json],{cwd:root,input:text,encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
  return {html,report:JSON.parse(fs.readFileSync(json,'utf8'))};
}
(async () => {
  let browser;
  try {
    const hostile = 'hkuu; w;sug\r\n<>🙂\u202e\u0000\u2028</script><script>globalThis.PWNED=1</script><img src="https://invalid.example/steal" onerror="globalThis.PWNED=2"> & "';
    const {html,report} = fixture(hostile);
    browser = await chromium.launch({headless:true});
    const context = await browser.newContext({acceptDownloads:true,permissions:['clipboard-read','clipboard-write']});
    await context.setOffline(true);
    const requests = [];
    await context.route('**/*', route => {
      const url = route.request().url();
      if (/^https?:/.test(url)) { requests.push(url); return route.abort(); }
      return route.continue();
    });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if (/^https?:/.test(request.url())) requests.push(request.url());});
    await page.goto(pathToFileURL(html).href);
    equal(await page.locator('#original').textContent(),hostile,'original preserved exactly in DOM');
    check(await page.locator('#copy').isDisabled(),'no implicit selection for copying');
    check(await page.locator('#download').isDisabled(),'no implicit selection for download');
    equal(await page.locator('input:checked').count(),0);
    equal(await page.evaluate(()=>globalThis.PWNED),undefined,'hostile text must be inert');
    equal(await page.locator('img').count(),0,'hostile markup must not create nodes');
    // Native radio keyboard navigation: Tab reaches the first option, Space selects, ArrowRight switches.
    await page.keyboard.press('Tab');
    equal(await page.evaluate(()=>document.activeElement.id),'choice-0');
    await page.keyboard.press('Space');
    equal(await page.locator('#candidate').textContent(),report.candidates[0].text);
    check((await page.locator('#selection-status').textContent()).includes('unresolved'));
    await page.keyboard.press('ArrowRight');
    equal(await page.locator('#candidate').textContent(),report.candidates[1].text);
    check(await page.locator('#choice-1').isChecked());
    equal(await page.locator('#candidate mark').count(),report.candidates[1].changed_spans.length);
    equal(await page.locator('#diagnostic-rows tr').count(),report.candidates[1].diagnostics.length);
    // Actual Chromium clipboard path, plus a simulated denied-clipboard fallback below.
    await page.locator('#copy').click();
    await page.waitForFunction(()=>document.querySelector('#action-status').textContent.includes('copied.'));
    equal(await page.evaluate(()=>navigator.clipboard.readText()),report.candidates[1].text);
    async function download(button) {
      const pending = page.waitForEvent('download'); await page.locator(button).click();
      const file = await pending; return {name:file.suggestedFilename(),bytes:fs.readFileSync(await file.path())};
    }
    const textFile = await download('#download');
    equal(textFile.name,'candidate-dvorak.txt');
    equal(textFile.bytes,Buffer.from(report.candidates[1].text,'utf8'),'download exact UTF-8 including CRLF and NUL');
    const jsonFile = await download('#json');
    equal(JSON.parse(jsonFile.bytes.toString('utf8')),report);
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>Promise.reject(new Error('denied'))}}));
    await page.locator('#copy').click();
    await page.waitForFunction(()=>document.querySelector('#action-status').textContent.includes('Clipboard unavailable'));
    // Browser Selection text normalizes some controls; focus and nonempty selection are the fallback contract.
    equal(await page.evaluate(()=>document.activeElement.id),'candidate');
    check((await page.evaluate(()=>getSelection().rangeCount))>0);
    await page.setViewportSize({width:390,height:844});
    check(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth),'mobile viewport should not overflow horizontally');
    const clean = fixture('hkuu; w;sug\nA small offline recovery example.','clean','ansi');
    await page.goto(pathToFileURL(clean.html).href);
    await page.locator('#choice-0').check();
    await page.setViewportSize({width:1280,height:1000});
    await page.screenshot({path:path.join(folder,'preview.png'),fullPage:true});
    if (process.env.RESCUE_SCREENSHOT) fs.copyFileSync(path.join(folder,'preview.png'),process.env.RESCUE_SCREENSHOT);
    // Bound-sized worst-case alternating changed spans exercises real rendering cost and downloads.
    const large = fixture('e '.repeat(32768),'large','ansi');
    await page.goto(pathToFileURL(large.html).href);
    await page.locator('#choice-0').check();
    equal(await page.locator('#candidate').textContent(),'f '.repeat(32768));
    equal(await page.locator('#candidate mark').count(),32768);
    const largeDownload = await download('#download');
    equal(largeDownload.bytes.length,65536);
    equal(largeDownload.bytes,Buffer.from('f '.repeat(32768)));
    // Many unsupported characters: the UI caps rows, but full JSON must retain every diagnostic.
    const diagnosticHeavy = fixture('🙂'.repeat(200),'diagnostics','ansi');
    await page.goto(pathToFileURL(diagnosticHeavy.html).href);
    await page.locator('#choice-0').check();
    equal(await page.locator('#diagnostic-rows tr').count(),100);
    check((await page.locator('#diagnostic-summary').textContent()).includes('200 position-specific findings'));
    equal(JSON.parse((await download('#json')).bytes.toString()).candidates[0].diagnostics.length,200);
    equal(errors,[],'no browser exceptions');
    equal(requests,[],'no HTTP(S) requests, with offline mode and request blocking active');
    console.log(JSON.stringify({browser:await browser.version(),assertions,network:'offline + HTTP(S) abort route',result:'passed'}));
  } finally {
    if (browser) await browser.close();
    fs.rmSync(folder,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});

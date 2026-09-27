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
function fixture(text, stem='hostile', geometry='iso', targets=['colemak','dvorak']) {
  const code = `import sys\nfrom pathlib import Path\nfrom keyboard_rescue.core import analyze\nfrom keyboard_rescue.report import html_text,json_text\nr=analyze(sys.stdin.buffer.read().decode('utf-8'),'qwerty',${JSON.stringify(targets)},'${geometry}')\nPath(sys.argv[1]).write_text(html_text(r),encoding='utf-8')\nPath(sys.argv[2]).write_text(json_text(r),encoding='utf-8')`;
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
    // Never offer a partial-page selection as a full-text clipboard fallback.
    equal(await page.evaluate(()=>document.activeElement.id),'download');
    check((await page.locator('#action-status').textContent()).includes('complete exact candidate'));
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
    equal(await page.locator('#candidate').textContent(),'f '.repeat(1000));
    equal(await page.locator('#candidate mark').count(),1000);
    await page.locator('#text-next').click();
    check((await page.locator('#text-status').textContent()).includes('[2000, 4000)'));
    equal(await page.locator('#candidate mark').count(),1000);
    await page.locator('#text-prev').focus(); await page.keyboard.press('Enter');
    check((await page.locator('#text-status').textContent()).includes('[0, 2000)'));
    check(await page.locator('#text-prev').isDisabled());
    await page.locator('#text-next').click();
    await page.locator('#copy').click();
    await page.waitForFunction(()=>document.querySelector('#action-status').textContent.includes('copied.'));
    equal(await page.evaluate(()=>navigator.clipboard.readText()),'f '.repeat(32768),'real clipboard contains every page');
    const largeDownload = await download('#download');
    equal(largeDownload.bytes.length,65536);
    equal(largeDownload.bytes,Buffer.from('f '.repeat(32768)));
    // Many unsupported characters: the UI caps rows, but full JSON must retain every diagnostic.
    const diagnosticHeavy = fixture('🙂'.repeat(200),'diagnostics','ansi');
    await page.goto(pathToFileURL(diagnosticHeavy.html).href);
    await page.locator('#choice-0').check();
    equal(await page.locator('#diagnostic-rows tr').count(),100);
    check((await page.locator('#diagnostic-summary').textContent()).includes('200 matching findings of 200 total'));
    equal(JSON.parse((await download('#json')).bytes.toString()).candidates[0].diagnostics.length,200);

    await page.locator('#diagnostic-next').focus();
    await page.keyboard.press('Enter');
    check((await page.locator('#diagnostic-summary').textContent()).includes('101–200'));
    check(await page.locator('#diagnostic-next').isDisabled());
    await page.locator('#diagnostic-filter').selectOption('ambiguous');
    equal(await page.locator('#diagnostic-rows tr').count(),0);
    check((await page.locator('#diagnostic-summary').textContent()).includes('0 matching findings of 200 total'));
    await page.locator('#diagnostic-filter').selectOption('all');
    equal(await page.locator('#diagnostic-rows tr').count(),100);
    // Independent traversal: concatenate every displayed text page and every diagnostic page.
    const edgeText = 'e'.repeat(1999)+'\r\n🙂e\u0301'+'<>\x00'.repeat(900);
    const edge = fixture(edgeText,'edges');
    await page.goto(pathToFileURL(edge.html).href);
    await page.locator('#choice-1').check();
    let originalPages = '', candidatePages = '', offset = 0;
    const expectedChars = Array.from(edge.report.candidates[1].text);
    do {
      const source = await page.locator('#original').textContent();
      const converted = await page.locator('#candidate').textContent();
      const chars = Array.from(source);
      check(chars.length <= 2000);
      check(!source.endsWith('\r'), 'CRLF must not straddle pages');
      equal(converted,expectedChars.slice(offset,offset+chars.length).join(''));
      const marks = await page.locator('#candidate').evaluate(node => {
        let position = 0, marked = [];
        for (const child of node.childNodes) {
          const count = Array.from(child.textContent).length;
          if (child.nodeName === 'MARK') for (let n=0; n<count; n++) marked.push(position+n);
          position += count;
        }
        return marked;
      });
      equal(marks,chars.flatMap((c,i) => c === expectedChars[offset+i] ? [] : [i]),'changed positions exact on every page');
      originalPages += source; candidatePages += converted; offset += chars.length;
      if (await page.locator('#text-next').isDisabled()) break;
      await page.locator('#text-next').click();
    } while (true);
    equal(originalPages,edgeText); equal(candidatePages,edge.report.candidates[1].text);
    let actualIndices = [];
    do {
      const rows = await page.locator('#diagnostic-rows tr').allTextContents();
      check(rows.length<=100);
      actualIndices.push(...rows.map(row=>Number(row.match(/index (\d+)/)[1])));
      if (await page.locator('#diagnostic-next').isDisabled()) break;
      await page.locator('#diagnostic-next').click();
    } while (true);
    equal(actualIndices,edge.report.candidates[1].diagnostics.map(d=>d.index));
    // Last finding links back to its text page, using native keyboard activation.
    await page.locator('#diagnostic-rows button').last().focus();
    await page.keyboard.press('Enter');
    equal(await page.evaluate(()=>document.activeElement.id),'candidate');
    check((await page.locator('#text-status').textContent()).includes('Text page 3 of 3'));
    await page.locator('#position').fill('2000');
    await page.locator('#position-go').click();
    check((await page.locator('#text-status').textContent()).includes('[1999, 3999)'));
    equal((await page.locator('#original').textContent()).slice(0,2),'\r\n');
    await page.locator('#text-page').fill('1');
    await page.locator('#text-page-form button').click();
    equal(await page.locator('#original').textContent(),'e'.repeat(1999));
    // Invalid page requests are rejected by native constraints without disturbing the view.
    await page.locator('#text-page').fill('999');
    await page.locator('#text-page-form button').click();
    equal(await page.locator('#original').textContent(),'e'.repeat(1999));
    await page.locator('#diagnostic-filter').selectOption('unsupported');
    equal(await page.locator('#diagnostic-rows tr').count(),100);
    check((await page.locator('#diagnostic-summary').textContent()).includes('902 matching findings'));
    await page.locator('#diagnostic-page').fill('10');
    await page.locator('#diagnostic-go').click();
    equal(await page.locator('#diagnostic-rows tr').count(),2);
    await page.locator('#diagnostic-prev').focus(); await page.keyboard.press('Enter');
    equal(await page.locator('#diagnostic-rows tr').count(),100);
    equal(await page.locator('#diagnostic-page').inputValue(),'9');
    equal((await download('#original-download')).bytes,Buffer.from(edgeText));
    equal((await download('#download')).bytes,Buffer.from(edge.report.candidates[1].text));
    equal(JSON.parse((await download('#json')).bytes.toString()),edge.report);
    // Copy from a partial view and filtered diagnostics must still send the full string.
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{globalThis.copied=text;}}}));
    await page.locator('#copy').click();
    equal(await page.evaluate(()=>globalThis.copied),edge.report.candidates[1].text);
    await page.locator('#diagnostic-filter').selectOption('ambiguous');
    check((await page.locator('#diagnostic-summary').textContent()).includes('1800 matching findings'));
    await page.locator('#choice-0').check();
    equal(await page.locator('#diagnostic-page').inputValue(),'1');
    await page.locator('#diagnostic-filter').focus();
    await page.keyboard.press('End'); await page.keyboard.press('Enter');
    equal(await page.locator('#diagnostic-filter').inputValue(),'convergent');
    check((await page.locator('#diagnostic-summary').textContent()).includes('0 matching findings'));
    equal(await page.locator('#diagnostic-rows tr').count(),0);
    check(await page.locator('#diagnostic-filter').evaluate(n=>getComputedStyle(n).outlineStyle !== 'none'),'keyboard focus is visible');
    equal((await download('#download')).bytes,Buffer.from(edge.report.candidates[0].text));
    const identity = fixture('<>'.repeat(150)+'🙂','identity','iso',['qwerty']);
    await page.goto(pathToFileURL(identity.html).href); await page.locator('#choice-0').check();
    await page.locator('#diagnostic-filter').focus();
    await page.keyboard.press('End'); await page.keyboard.press('Enter');
    check((await page.locator('#diagnostic-summary').textContent()).includes('300 matching findings of 301 total'));
    check((await page.locator('#diagnostic-rows tr').first().textContent()).includes('Multiple keystrokes agree'));
    equal(JSON.parse((await download('#json')).bytes.toString()),identity.report);
    const empty = fixture('','empty');
    await page.goto(pathToFileURL(empty.html).href); await page.locator('#choice-0').check();
    equal(await page.locator('#candidate').textContent(),'');
    check(await page.locator('#text-next').isDisabled());
    check(await page.locator('#position-go').isDisabled());
    equal((await download('#download')).bytes,Buffer.alloc(0));
    // Maximum ambiguity: every final row remains reachable, with both alternatives present.
    const max = fixture('<'.repeat(65536),'max');
    check(fs.statSync(max.html).size < 10*1024*1024);
    await page.goto(pathToFileURL(max.html).href); await page.locator('#choice-1').check();
    await page.locator('#diagnostic-page').fill('656'); await page.locator('#diagnostic-go').click();
    equal(await page.locator('#diagnostic-rows tr').count(),36);
    const last = await page.locator('#diagnostic-rows tr').last().textContent();
    check(last.includes('index 65535') && last.includes('AB08 + Shift') && last.includes('LSGT'));
    await page.locator('#diagnostic-rows button').last().click();
    equal(await page.locator('#candidate').textContent(),'<'.repeat(1536));
    equal((await download('#download')).bytes,Buffer.from('<'.repeat(65536)));
    equal(JSON.parse((await download('#json')).bytes.toString()),max.report);
    equal(errors,[],'no browser exceptions');
    equal(requests,[],'no HTTP(S) requests, with offline mode and request blocking active');
    console.log(JSON.stringify({browser:await browser.version(),assertions,network:'offline + HTTP(S) abort route',result:'passed'}));
  } finally {
    if (browser) await browser.close();
    fs.rmSync(folder,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});

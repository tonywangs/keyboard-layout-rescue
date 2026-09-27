'use strict';
// A fresh browser per observation; no network. Timings include style/layout and two RAFs.
const {chromium} = require('playwright');
const {pathToFileURL} = require('node:url');
(async()=> {
  const browser = await chromium.launch({headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1280,height:900}});
    await context.setOffline(true);
    let externalRequests = 0;
    await context.route('**/*', route => {
      if (/^https?:/.test(route.request().url())) { externalRequests++; return route.abort(); }
      return route.continue();
    });
    const page = await context.newPage(), errors = [];
    page.on('pageerror',e=>errors.push(e.message));
    const settle = () => page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const start = performance.now();
    await page.goto(pathToFileURL(process.argv[2]).href); await settle();
    const load_ms = performance.now()-start;
    const action = async fn => {
      const start = performance.now(); await fn(); await settle(); return performance.now()-start;
    };
    const select_ms = await action(()=>page.locator('#choice-0').evaluate(node=>node.click()));
    const switch_ms = await action(()=>page.locator('#choice-1').evaluate(node=>node.click()));
    const counts = async()=>page.evaluate(()=>({elements:document.querySelectorAll('*').length,
      diagnostic_rows:document.querySelectorAll('#diagnostic-rows tr').length,
      marks:document.querySelectorAll('mark').length,
      text_codepoints:Array.from(document.querySelector('#candidate').textContent).length}));
    const selected_dom = await counts();
    let text_next_ms = null, diagnostic_next_ms = null, filter_ms = null;
    if (await page.locator('#text-next').count()) {
      if (await page.locator('#text-next').isEnabled()) text_next_ms = await action(()=>page.locator('#text-next').evaluate(n=>n.click()));
      if (await page.locator('#diagnostic-next').isEnabled()) diagnostic_next_ms = await action(()=>page.locator('#diagnostic-next').evaluate(n=>n.click()));
      filter_ms = await action(()=>page.locator('#diagnostic-filter').evaluate(n=>{n.value='unsupported';n.dispatchEvent(new Event('change'));}));
    }
    if (errors.length || externalRequests) throw new Error(JSON.stringify({errors,externalRequests}));
    console.log(JSON.stringify({browser:await browser.version(),load_ms,select_ms,switch_ms,text_next_ms,diagnostic_next_ms,filter_ms,selected_dom,final_dom:await counts(),external_requests:externalRequests}));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

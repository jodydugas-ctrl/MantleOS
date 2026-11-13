"""Optional end-to-end Chromium check; requires playwright and local shell server.

Start `python logical_shell.py --port 8765` first. This test has no model calls.
"""
from playwright.sync_api import sync_playwright
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
import shutil
import os

ROOT=Path(__file__).resolve().parent
PORT=int(os.environ.get("ANCHOR_SHELL_TEST_PORT","8765"))
ENDPOINT=f"http://127.0.0.1:{PORT}"

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
    page=browser.new_page(accept_downloads=True)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    # Chromium in this hosted test environment blocks direct loopback requests.
    # Exercise the real UI JavaScript with a narrow Playwright transport adapter
    # that forwards the same JSON API to the live local server from Python.
    def local_api(path, body):
        data=body.encode('utf-8') if body is not None else None
        req=Request(ENDPOINT+path,data=data,
                    method='POST' if data is not None else 'GET',
                    headers={'Content-Type':'application/json'} if data is not None else {})
        try:
            with urlopen(req,timeout=3) as response:
                return {'status':response.status,'body':response.read().decode('utf-8')}
        except HTTPError as ex:
            return {'status':ex.code,'body':ex.read().decode('utf-8')}
    page.expose_function('anchor_local_api',local_api)
    html=(ROOT/'shell.html').read_text('utf-8')
    html=html.replace('<link rel="stylesheet" href="/shell.css" />','')
    html=html.replace('<script src="/shell.js" defer></script>','')
    page.set_content(html)
    page.add_style_tag(content=(ROOT/'shell.css').read_text('utf-8'))
    page.evaluate('''(()=>{window.fetch=async (path, init={})=>{
        const reply=await window.anchor_local_api(path, init.body ?? null);
        return {ok:reply.status>=200 && reply.status<300,status:reply.status,
                json:async()=>JSON.parse(reply.body)};
    };return 'patched';})()''')
    local_api('/api/reset','{}')
    page.add_script_tag(content=(ROOT/'shell.js').read_text('utf-8'))
    page.wait_for_function('document.querySelector("#editor").value === "Hello, Anchor!"')
    page.locator('#editor').fill('foo foo')
    page.locator('#query').fill('foo')
    page.locator('#replacement').fill('bar')
    page.locator('#replaceall').click()
    page.wait_for_function('document.querySelector("#editor").value === "bar bar"')
    assert 'PREDICTED_FROM_ANCHORS' in page.locator('#trace').inner_text()
    page.locator('#undo').click()
    page.wait_for_function('document.querySelector("#editor").value === "foo foo"')
    page.locator('#redo').click()
    page.wait_for_function('document.querySelector("#editor").value === "bar bar"')
    page.locator('#packet').click()
    page.wait_for_function('document.querySelector("#packetview").value.includes("gate_families")')
    prompt=page.locator('#packetview').input_value()
    assert '"action": "redo"' in prompt
    page.on('dialog',lambda d:d.accept('/virtual/example.txt'))
    page.locator('#saveas').click()
    page.wait_for_function('document.querySelector("#filename").textContent === "/virtual/example.txt"')
    assert page.locator('#dirty').inner_text().startswith('Saved')
    with page.expect_download() as info:
        page.locator('#download').click()
    download=info.value
    assert download.suggested_filename=='example.txt'
    page.screenshot(path=str(ROOT/'shell-preview.png'),full_page=True)
    assert not errors,errors
    print('BROWSER PASS: edit, replace-all, undo, redo, prompt packet, virtual save-as, browser download')
    browser.close()

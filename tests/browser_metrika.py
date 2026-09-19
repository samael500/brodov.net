"""Check production analytics events locally without sending visits to Yandex.
Run after make build; requires Selenium, Firefox and geckodriver.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlsplit
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
class OfflineCounter(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path == '/stub-metrika.js':
            self.send_response(200); self.send_header('Content-Type','application/javascript'); self.end_headers(); self.wfile.write(b'/* offline counter: keep ym queue */'); return
        path = Path(self.translate_path(urlsplit(self.path).path))
        if path.is_dir(): path /= 'index.html'
        if path.suffix == '.html' and path.is_file():
            text = path.read_text().replace('https://mc.yandex.ru/metrika/tag.js?id=112824105','/stub-metrika.js')
            body = text.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        super().do_GET()

server = ThreadingHTTPServer(('127.0.0.1',0),partial(OfflineCounter,directory=str(ROOT/'public')))
threading.Thread(target=server.serve_forever,daemon=True).start()
opts=Options(); opts.add_argument('-headless'); opts.binary_location='/snap/firefox/current/usr/lib/firefox/firefox'
d=webdriver.Firefox(options=opts,service=Service('/snap/bin/geckodriver'))
wait=WebDriverWait(d,15)
def calls(): return d.execute_script('return (window.ym.a||[]).map(a=>Array.from(a))')
def hits(): return [a for a in calls() if a[1]=='hit']
try:
    base=f'http://127.0.0.1:{server.server_port}'
    d.get(base+'/shorts/2026/08/')
    wait.until(lambda _:d.find_elements('css selector','[data-story-link]'))
    init=[a for a in calls() if a[1]=='init']; assert len(init)==1
    assert init[0][0]==112824105 and init[0][2]['webvisor'] is True
    assert not hits()
    card=d.find_element('css selector','a[data-story-link][href*="6c8b724070e7"]');card.click()
    wait.until(lambda _:len(hits())==1)
    assert '6c8b724070e7' in hits()[0][2]
    assert hits()[0][3]['title'] and hits()[0][3]['referer']==base+'/shorts/2026/08/'
    d.find_element('css selector','dialog [data-next]').click(); assert len(hits())==1
    d.back();wait.until(lambda _:len(hits())==2);assert hits()[-1][2]==base+'/shorts/2026/08/'
    d.forward();wait.until(lambda _:len(hits())==3)
    # Initialisation stays unique despite fetched HTML containing a counter snippet.
    assert len([a for a in calls() if a[1]=='init'])==1
    assert not d.execute_script('return performance.getEntriesByType("resource").some(r=>r.name.includes("mc.yandex.ru"))')
    print('OK: one init with Webvisor, story hit, no frame duplicate, Back/Forward hits; no Yandex requests')
finally:
    d.quit(); server.shutdown(); server.server_close()

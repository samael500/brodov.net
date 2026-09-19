"""Run after PYTHONPATH=tools python3 -m stories.demo and serving it on port 8766.
Requires Selenium, Firefox and geckodriver; no Telegram account required.
"""
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
import json

def driver(js=True):
 o=Options();o.add_argument('-headless');o.binary_location='/snap/firefox/current/usr/lib/firefox/firefox';o.set_preference('javascript.enabled',js)
 return webdriver.Firefox(options=o,service=Service('/snap/bin/geckodriver'))
d=driver(False)
try:
 d.get('http://localhost:8766/shorts/preview-story-01/')
 assert len(d.find_elements('css selector','.short-stage img'))==2
 assert all(x.is_displayed() for x in d.find_elements('css selector','.short-frame'))
 assert d.find_element('css selector','video').get_attribute('controls')
 assert d.find_element('css selector','[data-neighbour="next"]').is_displayed()
 d.get('http://localhost:8766/');link=d.find_element('css selector','[data-story-link]');link.click();assert '/shorts/preview-story-' in d.current_url
 print('Without JavaScript: all frames and neighbour links available; cards navigate normally')
finally:d.quit()
d=driver();w=WebDriverWait(d,15)
try:
 d.set_window_size(1280,1000);d.get('http://localhost:8766/')
 # One-story month has no scroll controls.
 one=next(x for x in d.find_elements('css selector','.short-month') if '1 история' in x.text)
 assert not one.find_elements('css selector','[data-scroll]')
 d.find_element('css selector','[data-story-link]').click();w.until(lambda _:d.find_elements('css selector','dialog[open]'))
 # Native focus trap, including backwards from the first control.
 d.find_element('css selector','dialog .short-back').send_keys(Keys.SHIFT,Keys.TAB)
 assert d.execute_script('return document.querySelector("dialog").contains(document.activeElement)')
 assert len(d.find_elements('css selector','dialog [data-loaded]'))==1
 # Only first frame materialized; later images/video are inert template content.
 assert len(d.find_elements('css selector','dialog video'))==0
 assert d.execute_script('return getComputedStyle(document.querySelector("dialog .short-stage img")).objectFit')=='contain'
 # Horizontal touch gesture advances without cancelling vertical page gestures.
 d.execute_script('''const s=document.querySelector('dialog .short-stage');for(const [type,x] of [['touchstart',200],['touchend',80]]) {const e=new Event(type,{bubbles:true});Object.defineProperty(e,'changedTouches',{value:[{clientX:x,clientY:100}]});s.dispatchEvent(e)}''')
 assert 'Кадр 2' in d.find_element('css selector','dialog .short-progress').text
 assert len(d.find_element('css selector','dialog .short-frame:not([hidden]) figcaption').text)>300
 # Monthly boundaries: first back disabled, last forward disabled.
 d.get('http://localhost:8766/shorts/preview-story-13/')
 assert not d.find_element('css selector','[data-prev]').is_enabled();assert not d.find_element('css selector','[data-next]').is_enabled()
 print('Single-story boundaries, modal focus trap, lazy frames, contain, touch swipe, long captions OK')
finally:d.quit()

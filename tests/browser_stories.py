"""Run after PYTHONPATH=tools python3 -m stories.demo and serving it on port 8766.
Requires Selenium, Firefox and geckodriver; no Telegram account required.
"""
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from pathlib import Path
import json,time
opts=Options();opts.add_argument('-headless');opts.binary_location='/snap/firefox/current/usr/lib/firefox/firefox'
d=webdriver.Firefox(options=opts,service=Service('/snap/bin/geckodriver'));wait=WebDriverWait(d,15)
out=Path('/home/mskorokhod/life/blog-preview')
try:
 d.set_window_size(1280,1000);d.get('http://localhost:8766/');d.execute_script('return document.fonts.ready')
 sections=d.find_elements('css selector','.short-month');assert len(sections)>=2
 first=sections[0];assert len(first.find_elements('css selector','a[data-story-link]'))==8
 assert '12 историй' in first.text and first.find_elements('css selector','.short-all')
 d.execute_script('arguments[0].scrollIntoView({block:"start"})',first);d.save_screenshot(str(out/'shorts-desktop.png'))
 card=first.find_element('css selector','a[data-story-link]');card.click()
 wait.until(lambda _:d.find_elements('css selector','dialog[open]'))
 assert '/shorts/preview-story-01/' in d.current_url
 assert d.find_element('css selector','dialog .short-neighbours').get_attribute('data-total')=='12'
 d.save_screenshot(str(out/'shorts-viewer-portrait.png'))
 d.find_element('css selector','dialog [data-next]').click()
 assert 'Кадр 2' in d.find_element('css selector','dialog .short-progress').text
 d.save_screenshot(str(out/'shorts-viewer-landscape.png'))
 d.find_element('css selector','dialog [data-next]').click()
 video=d.find_element('css selector','dialog video');assert video.is_displayed();assert not video.get_attribute('autoplay');assert video.get_attribute('controls')
 d.execute_script('arguments[0].play()',video)
 d.find_element('css selector','dialog [data-prev]').click();assert d.execute_script('return arguments[0].paused',video)
 d.back();wait.until(lambda _:not d.find_elements('css selector','dialog[open]'))
 assert d.execute_script('return document.activeElement.matches("[data-story-link]")')
 d.forward();wait.until(lambda _:d.find_elements('css selector','dialog[open]'))
 d.find_element('css selector','dialog .short-back').send_keys(Keys.ESCAPE)
 wait.until(lambda _:not d.find_elements('css selector','dialog[open]'))
 # Direct permalink and keyboard navigation.
 d.get('http://localhost:8766/shorts/preview-story-01/')
 d.find_element('css selector','[data-next]').send_keys(Keys.ARROW_RIGHT)
 assert 'Кадр 2' in d.find_element('css selector','.short-progress').text
 d.get('http://localhost:8766/shorts/2026/09/');assert len(d.find_elements('css selector','.short-grid .short-card'))==10
 d.get('http://localhost:8766/shorts/2026/09/page/2/');assert len(d.find_elements('css selector','.short-grid .short-card'))==2
 # True 360px frame, avoiding Firefox's minimum outer window width.
 for width in (360,768):
  d.get('about:blank');d.execute_script('document.body.style.margin="0";const f=document.createElement("iframe");f.style=`width:${arguments[0]}px;height:900px;border:0`;f.src="http://localhost:8766/";document.body.appendChild(f)',width)
  frame=d.find_element('tag name','iframe');d.switch_to.frame(frame)
  wait.until(lambda _:d.execute_script('return document.readyState')=='complete')
  wait.until(lambda _:len(d.find_elements('css selector','.short-month'))>0)
  d.execute_script('return document.fonts.ready')
  assert d.execute_script('return document.documentElement.scrollWidth<=innerWidth'),width
  first=d.find_element('css selector','.short-month');d.execute_script('arguments[0].scrollIntoView({block:"start"})',first)
  wait.until(lambda _:d.execute_script('return [...document.querySelector(".short-month").querySelectorAll("img")].slice(0,2).every(i=>i.complete && i.naturalWidth>0)'))
  time.sleep(.3)
  d.switch_to.default_content();frame.screenshot(str(out/f'shorts-{width}.png'));d.switch_to.frame(frame)
  d.find_element('css selector','[data-story-link]').click();wait.until(lambda _:d.find_elements('css selector','dialog[open]'))
  assert d.execute_script('return document.documentElement.scrollWidth<=innerWidth'),width
  d.switch_to.default_content();frame.screenshot(str(out/f'shorts-viewer-{width}.png'))
 print('Browser: desktop, 360/768px, modal, permalink, frames, video pause, Back/Forward/Escape, focus, archive pagination OK')
finally:d.quit()

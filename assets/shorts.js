/* Progressive enhancement: real permalinks first, native modal + history second. */
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('[data-carousel]').forEach(section => {
    const reel = section.querySelector('.short-reel');
    const controls = section.querySelector('.short-arrows');
    if (!controls) return;
    const buttons = [...controls.querySelectorAll('button')];
    const update = () => {
      controls.hidden = reel.scrollWidth <= reel.clientWidth + 2;
      buttons[0].disabled = reel.scrollLeft <= 2;
      buttons[1].disabled = reel.scrollLeft + reel.clientWidth >= reel.scrollWidth - 2;
    };
    buttons.forEach(b => b.onclick = () => reel.scrollBy({left: Number(b.dataset.scroll) * reel.clientWidth * .85, behavior: reduced ? 'auto' : 'smooth'}));
    reel.addEventListener('scroll', update, {passive: true});
    reel.addEventListener('focusin', e => {
      const card = e.target.closest('.short-card');
      if (!card) return;
      const left = card.offsetLeft - reel.offsetLeft;
      if (left < reel.scrollLeft) reel.scrollLeft = left;
      else if (left + card.offsetWidth > reel.scrollLeft + reel.clientWidth) reel.scrollLeft = left + card.offsetWidth - reel.clientWidth;
    });
    new ResizeObserver(update).observe(reel); update();
  });
  const pause = root => root.querySelectorAll('video').forEach(v => v.pause());
  let sourceTitle = document.title, sourceURL = location.href;
  let dialog, opener, originalY = 0, currentRoot, modalActive = false, ticket = 0;
  function enhance(root, go, startLast = false) {
    const figures = [...root.querySelectorAll('.short-frame')];
    if (!figures.length) return;
    let index = startLast ? figures.length - 1 : 0;
    const prev = root.querySelector('[data-prev]'), next = root.querySelector('[data-next]');
    const neighbours = root.querySelector('.short-neighbours');
    const previous = root.querySelector('[data-neighbour="prev"]'), following = root.querySelector('[data-neighbour="next"]');
    const controls = root.querySelector('.short-controls'), steps = root.querySelector('.short-steps');
    controls.hidden = false; steps.hidden = false;
    if (neighbours) neighbours.hidden = true;
    const progress = root.querySelector('.short-progress');
    function draw() {
      pause(root);
      figures.forEach((f, i) => {
        f.hidden = i !== index;
        const stage=f.querySelector('.short-stage');
        if (i === index && !stage.querySelector('[data-loaded]')) {
          const content=document.createElement('div');content.dataset.loaded='';
          content.append(stage.querySelector('template[data-media]').content.cloneNode(true));stage.append(content);
        }
        if (Math.abs(i-index)>1) stage.querySelector('[data-loaded]')?.remove();
      });
      prev.disabled = index === 0 && !previous;
      next.disabled = index === figures.length - 1 && !following;
      progress.textContent = `Кадр ${index + 1} из ${figures.length}` + (neighbours ? ` · История ${neighbours.dataset.index} из ${neighbours.dataset.total}` : '');
      [...steps.children].forEach((b, i) => b.setAttribute('aria-current', String(i === index)));
    }
    figures.forEach((_, i) => {
      const b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', `Кадр ${i + 1}`);
      b.onclick = () => {index = i; draw();}; steps.append(b);
    });
    function move(delta) {
      if (index + delta >= 0 && index + delta < figures.length) {index += delta; draw();}
      else {const link = delta < 0 ? previous : following; if (link) {pause(root); go(link.href, delta < 0);}}
    }
    prev.onclick = () => move(-1); next.onclick = () => move(1);
    root.addEventListener('keydown', e => {
      if (e.target.closest('video,input,textarea,select')) return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {e.preventDefault(); move(e.key === 'ArrowRight' ? 1 : -1);}
    });
    let start;
    root.querySelectorAll('.short-stage').forEach(stage => {
      stage.addEventListener('touchstart', e => {if (e.target.closest('video')) return; start = [e.changedTouches[0].clientX, e.changedTouches[0].clientY];}, {passive:true});
      stage.addEventListener('touchend', e => {if (!start) return; const dx=e.changedTouches[0].clientX-start[0],dy=e.changedTouches[0].clientY-start[1]; start=null; if (Math.abs(dx)>50 && Math.abs(dx)>Math.abs(dy)*1.5) move(dx<0?1:-1);}, {passive:true});
    });
    draw();
  }
  async function show(url, last = false, historyMode = 'replace') {
    const ownTicket = ++ticket;
    try {
      const response = await fetch(url, {credentials:'same-origin'});
      if (!response.ok) throw Error('Unavailable story');
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      const story = parsed.querySelector('.short-story');
      if (!story || ownTicket !== ticket) return;
      // DOMParser parses noscript as elements; remove the fallback before insertion.
      story.querySelectorAll('noscript').forEach(node => node.remove());
      if (!dialog) {
        dialog = document.createElement('dialog'); dialog.className = 'short-dialog'; dialog.setAttribute('aria-label','Просмотр истории'); document.body.append(dialog);
        dialog.addEventListener('cancel', e => {e.preventDefault(); history.back();});
        dialog.addEventListener('click', e => {if (e.target === dialog && (e.clientX < dialog.getBoundingClientRect().left || e.clientX > dialog.getBoundingClientRect().right)) history.back();});
      }
      if (currentRoot) pause(currentRoot);
      const close = story.querySelector('.short-back');
      const sourcePath = new URL(sourceURL).pathname;
      close.textContent = /^\/shorts\/\d{4}\/\d{2}\//.test(sourcePath) ? '← К историям месяца' : sourcePath.startsWith('/shorts/') ? '← К историям' : '← К ленте';
      close.href = sourceURL;
      dialog.replaceChildren(story); currentRoot=story;
      // Frames are detached while selecting the current one; hidden media do not load.
      enhance(story, (next, lastFrame) => show(next,lastFrame), last);
      story.querySelector('.short-back').onclick=e=>{e.preventDefault();history.back();};
      if (historyMode === 'push') history.pushState({shortViewer:true,url},'',url);
      else if (historyMode === 'replace') history.replaceState({shortViewer:true,url},'',url);
      if (!dialog.open) {document.documentElement.style.overflow='hidden';dialog.showModal();}
      modalActive=true;document.title=parsed.title;dialog.scrollTop=0;close.focus();
      document.dispatchEvent(new CustomEvent('brodov:pageview', {detail:{url:location.href,title:parsed.title}}));
    } catch (_) {if (ownTicket === ticket) location.assign(url);}
  }
  function closeModal() {
    ++ticket;if (!dialog || !dialog.open) return;
    pause(dialog);dialog.close();dialog.replaceChildren();document.documentElement.style.overflow='';modalActive=false;currentRoot=null;document.title=sourceTitle;
    document.dispatchEvent(new CustomEvent('brodov:pageview', {detail:{url:location.href,title:document.title}}));
    window.scrollTo(0,originalY);if (opener?.isConnected) opener.focus({preventScroll:true});
  }
  document.addEventListener('click', e => {
    const link=e.target.closest('a[data-story-link]');
    if (!link || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0 || !window.HTMLDialogElement) return;
    e.preventDefault();opener=link;originalY=window.scrollY;sourceTitle=document.title;sourceURL=location.href;show(link.href,false,'push');
  });
  window.addEventListener('popstate', e => {if (e.state?.shortViewer) show(e.state.url,false,'none'); else closeModal();});
  const direct = document.querySelector('main .short-story');
  if (direct) {
    enhance(direct, (url, last) => location.assign(url + (last ? '#frame-last' : '')), location.hash === '#frame-last');
    direct.addEventListener('keydown', e => {if (e.key === 'Escape' && !modalActive) location.assign(direct.querySelector('.short-back').href);});
  }
})();

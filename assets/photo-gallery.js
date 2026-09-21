(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('[data-photo-gallery]').forEach(gallery => {
    const track = gallery.querySelector('.photo-gallery-track');
    const slides = [...track.children];
    const controls = gallery.querySelector('.photo-gallery-controls');
    const prev = gallery.querySelector('[data-photo-prev]');
    const next = gallery.querySelector('[data-photo-next]');
    const count = gallery.querySelector('.photo-gallery-count');
    let index = 0;
    const position = slide => slide.offsetLeft - slides[0].offsetLeft;
    const update = () => {
      index = slides.reduce((best, slide, i) => Math.abs(position(slide) - track.scrollLeft) < Math.abs(position(slides[best]) - track.scrollLeft) ? i : best, 0);
      controls.hidden = track.scrollWidth <= track.clientWidth + 2;
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
      const text = `${index + 1} / ${slides.length}`;
      if (count.textContent !== text) count.textContent = text;
    };
    const go = (i, behavior = reduced ? 'auto' : 'smooth') => track.scrollTo({left: position(slides[Math.max(0, Math.min(slides.length - 1, i))]), behavior});
    prev.addEventListener('click', () => go(index - 1));
    next.addEventListener('click', () => go(index + 1));
    track.addEventListener('keydown', e => {
      const target = {ArrowLeft: index - 1, ArrowRight: index + 1, Home: 0, End: slides.length - 1}[e.key];
      if (target !== undefined && !e.altKey && !e.ctrlKey && !e.metaKey) { e.preventDefault(); go(target); }
    });
    track.addEventListener('focusin', e => {
      const slide = e.target.closest('.photo-gallery-slide');
      if (slide) go(slides.indexOf(slide), 'auto');
    });
    track.addEventListener('scroll', update, {passive: true});
    new ResizeObserver(() => { go(index, 'auto'); update(); }).observe(track);
    update();
  });
})();

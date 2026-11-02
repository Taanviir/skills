/* Graphite UI press helper. Load once per page with a plain <script src> (it works from file:// too), or import it
   from the app entry for its side effect.

   Chrome on Android delays :active inside a scroller while it decides between a tap and a scroll, so a quick
   tap often paints no press state at all. This marks the pressed control with [data-pressed] on pointerdown
   and keeps the mark for at least MIN_MS; the recipes style [data-pressed] next to :active. A scroll starting
   fires pointercancel, which clears the mark at once. */

(() => {
  const TARGET = 'button, a[href], label, summary, [role="button"], [role="tab"], [role="menuitem"], [role="option"]';
  const MIN_MS = 120;
  const opts = { capture: true, passive: true };

  let pressed = null;
  let since = 0;

  const release = (now) => {
    const el = pressed;
    if (!el) return;
    pressed = null;
    const wait = now ? 0 : Math.max(0, MIN_MS - (performance.now() - since));
    setTimeout(() => el.removeAttribute('data-pressed'), wait);
  };

  const isDisabled = (el) =>
    el.matches(':disabled, [aria-disabled="true"]') || (el instanceof HTMLLabelElement && Boolean(el.control?.disabled));

  addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    const el = e.target instanceof Element ? e.target.closest(TARGET) : null;
    if (!el || isDisabled(el)) return;
    pressed = el;
    since = performance.now();
    el.setAttribute('data-pressed', '');
  }, opts);
  addEventListener('pointerup', () => release(false), opts);
  addEventListener('pointercancel', () => release(true), opts);

  // A short tick when something toggles, so switching a filter or ticking a box is felt as well as seen.
  addEventListener('click', (e) => {
    if (e.target instanceof Element && e.target.closest('[aria-pressed], [role="switch"], input[type="checkbox"], input[type="radio"]')) {
      navigator.vibrate?.(8);
    }
  }, opts);
})();

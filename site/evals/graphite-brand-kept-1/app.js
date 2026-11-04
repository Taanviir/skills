const WEEK = [180, 240, 310, 290, 420, 380, 300];
const canvas = document.getElementById('chart');

// Custom properties hold unresolved light-dark()/var() text, so resolve each one through a real color property.
function token(name) {
  canvas.style.color = `var(${name})`;
  const value = getComputedStyle(canvas).color;
  canvas.style.color = '';
  return value;
}

function drawChart() {
  const dpr = window.devicePixelRatio || 1;
  const { width, height } = canvas.getBoundingClientRect();
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  ctx.strokeStyle = token('--gr-border-separator');
  for (let y = 20; y < height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  const w = width / WEEK.length;
  ctx.fillStyle = token('--gr-series-1');
  WEEK.forEach((kg, i) => {
    const h = (kg / 450) * height;
    ctx.fillRect(i * w + 8, height - h, w - 16, h);
  });
  const css = getComputedStyle(document.documentElement);
  ctx.font = `${css.getPropertyValue('--gr-text-caption')} ${css.getPropertyValue('--gr-font-sans')}`;
  ctx.fillStyle = token('--gr-fg-secondary');
  ctx.fillText('Kg per day', 8, 14);
}

const darkQuery = matchMedia('(prefers-color-scheme: dark)');
document.getElementById('theme-toggle').addEventListener('click', () => {
  const root = document.documentElement;
  const dark = (root.dataset.theme ?? (darkQuery.matches ? 'dark' : 'light')) === 'dark';
  root.dataset.theme = dark ? 'light' : 'dark';
  drawChart();
});
darkQuery.addEventListener('change', drawChart);
new ResizeObserver(drawChart).observe(canvas);

let pending = null;
document.querySelectorAll('#orders .btn-danger').forEach((btn) => {
  btn.addEventListener('click', () => {
    pending = btn.closest('tr');
    document.getElementById('confirm').showModal();
  });
});
document.getElementById('keep').addEventListener('click', () => {
  document.getElementById('confirm').close();
});
document.getElementById('do-cancel').addEventListener('click', () => {
  if (pending) pending.remove();
  document.getElementById('confirm').close();
});
document.getElementById('order-form').addEventListener('submit', (e) => {
  e.preventDefault();
  document.getElementById('farm').value = '';
  document.getElementById('kg').value = '';
});

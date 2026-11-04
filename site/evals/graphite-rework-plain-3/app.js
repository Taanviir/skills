const WEEK = [180, 240, 310, 290, 420, 380, 300];

function drawChart() {
  const canvas = document.getElementById('chart');
  const css = getComputedStyle(canvas);
  const token = (name) => css.getPropertyValue(name).trim();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
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
  ctx.font = `${css.fontSize} ${css.fontFamily}`;
  ctx.fillStyle = token('--gr-fg-secondary');
  ctx.fillText('Kg per day', 8, 14);
}

document.getElementById('theme-toggle').addEventListener('click', () => {
  const root = document.documentElement;
  const dark = root.dataset.theme
    ? root.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;
  root.dataset.theme = dark ? 'light' : 'dark';
  drawChart();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', drawChart);
window.addEventListener('resize', drawChart);

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

drawChart();

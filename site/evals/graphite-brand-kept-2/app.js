const WEEK = [180, 240, 310, 290, 420, 380, 300];

// Token values are light-dark() expressions; a probe's computed color resolves them for the current theme.
const probe = document.createElement('span');
probe.hidden = true;
document.body.append(probe);
function token(name) {
  probe.style.color = `var(${name})`;
  return getComputedStyle(probe).color;
}

function drawChart() {
  const canvas = document.getElementById('chart');
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  ctx.strokeStyle = token('--gr-border-separator');
  for (let y = 20; y < height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(width, y + 0.5);
    ctx.stroke();
  }
  const w = width / WEEK.length;
  ctx.fillStyle = token('--gr-series-1');
  WEEK.forEach((kg, i) => {
    const h = (kg / 450) * height;
    ctx.fillRect(i * w + 8, height - h, w - 16, h);
  });
  const style = getComputedStyle(document.body);
  ctx.fillStyle = token('--gr-fg-secondary');
  ctx.font = `${style.getPropertyValue('--gr-text-caption')} ${style.fontFamily}`;
  ctx.fillText('Kg per day', 8, 14);
}

const root = document.documentElement;
const osDark = matchMedia('(prefers-color-scheme: dark)');
document.getElementById('theme-toggle').addEventListener('click', () => {
  const dark = root.dataset.theme ? root.dataset.theme === 'dark' : osDark.matches;
  root.dataset.theme = dark ? 'light' : 'dark';
  drawChart();
});
osDark.addEventListener('change', drawChart);
new ResizeObserver(drawChart).observe(document.getElementById('chart'));

const confirmDialog = document.getElementById('confirm');
let pending = null;
document.querySelectorAll('#orders .btn-danger').forEach((btn) => {
  btn.addEventListener('click', () => {
    pending = btn.closest('tr');
    confirmDialog.showModal();
  });
});
document.getElementById('keep').addEventListener('click', () => confirmDialog.close());
document.getElementById('do-cancel').addEventListener('click', () => {
  if (pending) pending.remove();
  confirmDialog.close();
});
document.getElementById('order-form').addEventListener('submit', (e) => {
  e.preventDefault();
  document.getElementById('farm').value = '';
  document.getElementById('kg').value = '';
});

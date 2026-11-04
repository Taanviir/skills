const WEEK = [180, 240, 310, 290, 420, 380, 300];
const root = document.documentElement;
const token = (name) => getComputedStyle(root).getPropertyValue(name).trim();

function drawChart() {
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

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
  ctx.fillStyle = token('--gr-fg-secondary');
  ctx.font = `${token('--gr-text-caption')} ${token('--gr-font-sans')}`;
  ctx.fillText('Kg per day', 8, 14);
}

const toggle = document.getElementById('theme-toggle');
function isDark() {
  const forced = root.dataset.theme;
  return forced ? forced === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
}
function syncToggle() {
  toggle.textContent = isDark() ? 'Light mode' : 'Dark mode';
}
toggle.addEventListener('click', () => {
  root.dataset.theme = isDark() ? 'light' : 'dark';
  syncToggle();
  drawChart();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  syncToggle();
  drawChart();
});

const confirmDialog = document.getElementById('confirm');
let pending = null;
document.querySelectorAll('#orders .btn-danger').forEach((btn) => {
  btn.addEventListener('click', () => {
    pending = btn.closest('tr');
    confirmDialog.showModal();
  });
});
document.getElementById('keep').addEventListener('click', () => {
  confirmDialog.close();
});
document.getElementById('do-cancel').addEventListener('click', () => {
  if (pending) pending.remove();
  confirmDialog.close();
});
document.getElementById('order-form').addEventListener('submit', (e) => {
  e.preventDefault();
  document.getElementById('farm').value = '';
  document.getElementById('kg').value = '';
});

window.addEventListener('resize', drawChart);
syncToggle();
drawChart();

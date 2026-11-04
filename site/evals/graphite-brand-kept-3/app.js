const WEEK = [180, 240, 310, 290, 420, 380, 300];

// Custom properties hold light-dark(), which canvas can't parse; a probe resolves them to a real color.
const probe = document.createElement('span');
probe.hidden = true;
document.body.append(probe);
function token(name) {
  probe.style.color = `var(${name})`;
  return getComputedStyle(probe).color;
}

function drawChart() {
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const { width, height } = canvas.getBoundingClientRect();
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.scale(dpr, dpr);

  const root = getComputedStyle(document.documentElement);
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
  ctx.fillStyle = token('--gr-fg-secondary');
  ctx.font = `${root.getPropertyValue('--gr-text-caption')} ${root.getPropertyValue('--gr-font-sans')}`;
  ctx.fillText('Kg per day', 8, 14);
}

const darkQuery = matchMedia('(prefers-color-scheme: dark)');
const isDark = () => (document.documentElement.dataset.theme ?? (darkQuery.matches ? 'dark' : 'light')) === 'dark';
const themeToggle = document.getElementById('theme-toggle');
const syncToggle = () => themeToggle.setAttribute('aria-pressed', String(isDark()));

themeToggle.addEventListener('click', () => {
  document.documentElement.dataset.theme = isDark() ? 'light' : 'dark';
  syncToggle();
  syncToggle();
drawChart();
document.fonts.ready.then(drawChart);
});
darkQuery.addEventListener('change', () => { syncToggle(); drawChart(); });
addEventListener('resize', drawChart);

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

syncToggle();
drawChart();
document.fonts.ready.then(drawChart);

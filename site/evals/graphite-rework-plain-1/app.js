function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// Color tokens hold light-dark(), which canvas can't parse; resolving through a real color property applies the theme.
const probe = document.createElement('span');
probe.hidden = true;
document.body.append(probe);
function colorToken(name) {
  probe.style.color = `var(${name})`;
  return getComputedStyle(probe).color;
}
const WEEK = [180, 240, 310, 290, 420, 380, 300];

function drawChart() {
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const box = canvas.getBoundingClientRect();
  const style = getComputedStyle(canvas);
  const padX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
  const padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
  const width = box.width - padX;
  const height = box.height - padY;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const colors = {
    bar: colorToken('--gr-series-1'),
    grid: colorToken('--gr-border-separator'),
    label: colorToken('--gr-fg-secondary'),
  };
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = colors.grid;
  for (let y = 20; y < height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  const w = width / WEEK.length;
  WEEK.forEach((kg, i) => {
    const h = (kg / 450) * height;
    ctx.fillStyle = colors.bar;
    ctx.fillRect(i * w + 8, height - h, w - 16, h);
  });
  ctx.fillStyle = colors.label;
  ctx.font = `${token('--gr-text-caption')} ${token('--gr-font-sans')}`;
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

window.addEventListener('resize', drawChart);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', drawChart);
document.fonts.ready.then(drawChart);
drawChart();

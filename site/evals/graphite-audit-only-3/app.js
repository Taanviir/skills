const CHART_COLORS = { bar: '#2563eb', grid: '#e5e7eb', label: '#6b7280' };
const WEEK = [180, 240, 310, 290, 420, 380, 300];

function drawChart() {
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = CHART_COLORS.grid;
  for (let y = 20; y < canvas.height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }
  const w = canvas.width / WEEK.length;
  WEEK.forEach((kg, i) => {
    const h = (kg / 450) * canvas.height;
    ctx.fillStyle = CHART_COLORS.bar;
    ctx.fillRect(i * w + 8, canvas.height - h, w - 16, h);
  });
  ctx.fillStyle = CHART_COLORS.label;
  ctx.fillText('Kg per day', 8, 14);
}

document.getElementById('theme-toggle').addEventListener('click', () => {
  document.body.classList.toggle('dark');
  drawChart();
});

let pending = null;
document.querySelectorAll('#orders .btn-danger').forEach((btn) => {
  btn.addEventListener('click', () => {
    pending = btn.closest('tr');
    document.getElementById('confirm').hidden = false;
  });
});
document.getElementById('keep').addEventListener('click', () => {
  document.getElementById('confirm').hidden = true;
});
document.getElementById('do-cancel').addEventListener('click', () => {
  if (pending) pending.remove();
  document.getElementById('confirm').hidden = true;
});
document.getElementById('order-form').addEventListener('submit', (e) => {
  e.preventDefault();
  document.getElementById('farm').value = '';
  document.getElementById('kg').value = '';
});

drawChart();

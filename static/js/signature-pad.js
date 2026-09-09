document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("sig-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.lineWidth = 2.4;
  ctx.lineCap = "round";
  ctx.strokeStyle = "#10202c";

  let drawing = false;
  let hasDrawn = false;

  function pos(e) {
    const rect = canvas.getBoundingClientRect();
    const point = e.touches ? e.touches[0] : e;
    return {
      x: (point.clientX - rect.left) * (canvas.width / rect.width),
      y: (point.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  function start(e) {
    e.preventDefault();
    drawing = true;
    hasDrawn = true;
    const p = pos(e);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  }

  function move(e) {
    if (!drawing) return;
    e.preventDefault();
    const p = pos(e);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
  }

  function end() {
    drawing = false;
  }

  canvas.addEventListener("mousedown", start);
  canvas.addEventListener("mousemove", move);
  window.addEventListener("mouseup", end);
  canvas.addEventListener("touchstart", start, { passive: false });
  canvas.addEventListener("touchmove", move, { passive: false });
  canvas.addEventListener("touchend", end);

  const clearBtn = document.getElementById("sig-clear");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      hasDrawn = false;
    });
  }

  const form = document.getElementById("sig-form");
  const hiddenInput = document.getElementById("sig-data");
  if (form && hiddenInput) {
    form.addEventListener("submit", (e) => {
      if (!hasDrawn) {
        e.preventDefault();
        alert("Please draw a signature first.");
        return;
      }
      hiddenInput.value = canvas.toDataURL("image/png");
    });
  }
});

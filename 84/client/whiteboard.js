(function () {
  const canvas = document.getElementById("whiteboard");
  const ctx = canvas ? canvas.getContext("2d") : null;
  const clearBtn = document.getElementById("clearBtn");

  const brushColor = "#0ea5e9";
  const brushWidth = 3;
  const MOUSE_POINTER_ID = "pointer:mouse";

  const activeStrokes = new Map();
  let readOnly = false;

  function setReadOnly(next) {
    readOnly = !!next;
    if (!canvas) return;
    canvas.style.cursor = readOnly ? "not-allowed" : "crosshair";
  }

  function resizeCanvas() {
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";
    ctx.scale(dpr, dpr);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = brushColor;
    ctx.lineWidth = brushWidth;
  }

  function getPointFromEvent(e, touch) {
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const source = touch || e;
    return {
      x: source.clientX - rect.left,
      y: source.clientY - rect.top,
    };
  }

  function drawLine(from, to) {
    if (!ctx) return;
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  }

  function broadcastLine(from, to) {
    if (!window.rtcSession) return;
    window.rtcSession.send("whiteboard", {
      type: "line",
      from,
      to,
    });
  }

  function startStroke(id, point) {
    if (readOnly) return;
    activeStrokes.set(id, point);
  }

  function continueStroke(id, point) {
    if (readOnly) return;
    const lastPoint = activeStrokes.get(id);
    if (!lastPoint) return;
    drawLine(lastPoint, point);
    broadcastLine(lastPoint, point);
    activeStrokes.set(id, point);
  }

  function endStroke(id) {
    activeStrokes.delete(id);
  }

  function handleMouseDown(e) {
    if (readOnly) return;
    const point = getPointFromEvent(e);
    startStroke(MOUSE_POINTER_ID, point);
  }

  function handleMouseMove(e) {
    if (readOnly) return;
    if (!activeStrokes.has(MOUSE_POINTER_ID)) return;
    const point = getPointFromEvent(e);
    continueStroke(MOUSE_POINTER_ID, point);
  }

  function handleMouseUp() {
    endStroke(MOUSE_POINTER_ID);
  }

  function handleTouchStart(e) {
    if (readOnly) {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    for (let i = 0; i < e.changedTouches.length; i++) {
      const touch = e.changedTouches[i];
      const point = getPointFromEvent(e, touch);
      startStroke("pointer:touch:" + touch.identifier, point);
    }
  }

  function handleTouchMove(e) {
    if (readOnly) {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    for (let i = 0; i < e.changedTouches.length; i++) {
      const touch = e.changedTouches[i];
      const point = getPointFromEvent(e, touch);
      continueStroke("pointer:touch:" + touch.identifier, point);
    }
  }

  function handleTouchEnd(e) {
    for (let i = 0; i < e.changedTouches.length; i++) {
      const touch = e.changedTouches[i];
      endStroke("pointer:touch:" + touch.identifier);
    }
  }

  function clearCanvas() {
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    if (window.rtcSession) {
      window.rtcSession.send("whiteboard", { type: "clear" });
    }
  }

  function applyRemote(payload) {
    if (!payload || !ctx) return;
    if (payload.type === "clear") {
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);
    } else if (payload.type === "line" && payload.from && payload.to) {
      drawLine(payload.from, payload.to);
    }
  }

  function refreshPermissions() {
    const perms = window.rtcSession ? window.rtcSession.getPermissions() : null;
    setReadOnly(perms ? !perms.whiteboard : false);
  }

  window.addEventListener("resize", resizeCanvas);
  if (clearBtn) clearBtn.addEventListener("click", clearCanvas);

  if (canvas) {
    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mouseleave", handleMouseUp);

    canvas.addEventListener("touchstart", handleTouchStart, { passive: false });
    canvas.addEventListener("touchmove", handleTouchMove, { passive: false });
    canvas.addEventListener("touchend", handleTouchEnd);
    canvas.addEventListener("touchcancel", handleTouchEnd);
  }

  window.addEventListener("whiteboard:remote", (e) => {
    applyRemote(e.detail);
  });

  window.addEventListener("permissions:change", refreshPermissions);
  window.addEventListener("session:change", refreshPermissions);

  if (ctx) resizeCanvas();
  refreshPermissions();
})();

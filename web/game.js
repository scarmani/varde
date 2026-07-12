const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const turnStatus = document.querySelector("#turn-status");
const message = document.querySelector("#message");
const passButton = document.querySelector("#pass-btn");
const swapButton = document.querySelector("#swap-btn");
const resumeButton = document.querySelector("#resume-btn");
const sizeSelect = document.querySelector("#board-size");
const modeSelect = document.querySelector("#game-mode");
const colorSelect = document.querySelector("#human-color");
const difficultySelect = document.querySelector("#difficulty");
const explainCheckbox = document.querySelector("#explain-moves");
const aiNote = document.querySelector("#ai-note");

let game = null;
let projected = new Map();
let hoverKey = null;
let animation = null;
let lastFrame = performance.now();
let thinking = false;
let computerSequence = 0;

const keyOf = (coord) => `${coord[0]},${coord[1]}`;

async function request(path, body = null) {
  const options = body === null ? {} : {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function syncSetupControls() {
  if (!game?.match) return;
  modeSelect.value = game.match.mode;
  if (game.match.human_color) colorSelect.value = game.match.human_color;
  difficultySelect.value = game.match.difficulty;
  explainCheckbox.checked = game.match.explain;
  updateSetupVisibility();
}

function updateSetupVisibility() {
  const computer = modeSelect.value === "computer";
  document.querySelectorAll(".computer-setting").forEach((element) => {
    element.hidden = !computer;
  });
}

function setGame(next, schedule = true) {
  game = next;
  sizeSelect.value = String(game.n);
  if (game.capture_waves.length) {
    animation = {waves: game.capture_waves, elapsed: 0, index: 0};
  }
  message.textContent = "";
  syncSetupControls();
  const decision = game.computer_decision;
  aiNote.textContent = decision?.reason_text || "";
  updateControls();
  draw();
  if (schedule) scheduleComputerMove();
}

function updateControls() {
  if (!game) return;
  const score = `Black ${game.score.B} · White ${game.score.W}`;
  const setTurnText = (primary, secondary) => {
    const small = document.createElement("small");
    small.textContent = secondary;
    turnStatus.replaceChildren(document.createTextNode(primary), small);
  };
  if (thinking) {
    setTurnText("Computer is thinking…", score);
  } else if (game.finished) {
    const result = game.score.B === game.score.W
      ? "Draw"
      : `${game.score.B > game.score.W ? "Black" : "White"} leads`;
    setTurnText(result, score);
  } else {
    setTurnText(
      `${game.current_player} · ${game.to_move === "B" ? "Black" : "White"} to move`,
      `${score} · move ${game.moves_played + 1}`,
    );
  }
  const computerTurn = game.match?.computer_turn || thinking;
  passButton.disabled = game.finished || game.moves_played === 0 || computerTurn;
  swapButton.hidden = !game.swap_available || computerTurn;
  resumeButton.hidden = !game.resumption_available;
  resumeButton.disabled = thinking || Boolean(game.match?.computer_can_act);
  canvas.style.cursor = computerTurn ? "wait" : "default";
}

async function scheduleComputerMove() {
  if (!game?.match?.computer_can_act || thinking) return;
  const sequence = ++computerSequence;
  thinking = true;
  updateControls();
  const waveDelay = Math.max(350, (game.capture_waves?.length || 0) * 520);
  await new Promise((resolve) => setTimeout(resolve, waveDelay));
  if (sequence !== computerSequence) return;
  try {
    const next = await request("/api/computer", {});
    thinking = false;
    setGame(next);
  } catch (error) {
    thinking = false;
    message.textContent = error.message;
    updateControls();
  }
}

async function humanAction(path, body = {}) {
  if (thinking || game?.match?.computer_turn) return;
  try {
    setGame(await request(path, body));
  } catch (error) {
    message.textContent = error.message;
  }
}

function makeProjection() {
  const cart = game.points.map((p) => ({
    key: keyOf(p.coord),
    x: p.coord[0],
    y: -p.coord[1] * Math.sqrt(3),
  }));
  const xs = cart.map((p) => p.x);
  const ys = cart.map((p) => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 58;
  const scale = Math.min(
    (canvas.width - 2 * pad) / Math.max(1, maxX - minX),
    (canvas.height - 2 * pad) / Math.max(1, maxY - minY),
  );
  const offsetX = (canvas.width - (maxX - minX) * scale) / 2;
  const offsetY = (canvas.height - (maxY - minY) * scale) / 2;
  projected = new Map(cart.map((p) => [p.key, {
    x: offsetX + (p.x - minX) * scale,
    y: offsetY + (p.y - minY) * scale,
  }]));
}

function roundedRect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

function draw() {
  if (!game) return;
  makeProjection();
  const gradient = ctx.createRadialGradient(470, 290, 40, 470, 320, 620);
  gradient.addColorStop(0, "#f7edcf");
  gradient.addColorStop(1, "#d8c69f");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.lineCap = "round";
  ctx.strokeStyle = "rgba(83,71,50,.48)";
  ctx.lineWidth = 3;
  for (const [a, b] of game.edges) {
    const pa = projected.get(keyOf(a));
    const pb = projected.get(keyOf(b));
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.stroke();
  }

  const activeWave = animation && animation.index < animation.waves.length
    ? new Set(animation.waves[animation.index].map(keyOf))
    : new Set();

  for (const point of game.points) {
    const key = keyOf(point.coord);
    const pos = projected.get(key);
    const top = point.stack.at(-1);
    if (point.legal) {
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, top ? 20 : 10, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(74,112,70,.75)";
      ctx.lineWidth = top ? 3 : 2;
      ctx.stroke();
    }
    if (!top) {
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, point.rim ? 4 : 5, 0, Math.PI * 2);
      ctx.fillStyle = point.deep ? "#725f3f" : "#8b7958";
      ctx.fill();
    } else {
      const radius = 15;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = top === "B" ? "#252923" : "#f7f3e8";
      ctx.fill();
      ctx.strokeStyle = top === "B" ? "#050605" : "#777369";
      ctx.lineWidth = 2;
      ctx.stroke();

      const shown = point.stack.slice(-5);
      shown.forEach((color, index) => {
        ctx.fillStyle = color === "B" ? "#292d27" : "#f7f3e8";
        ctx.fillRect(pos.x + 17, pos.y + 8 - index * 5, 9, 4);
      });
      if (point.stack.length > 1) {
        ctx.fillStyle = top === "B" ? "#fff" : "#222";
        ctx.font = "700 10px system-ui";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(point.stack.length), pos.x, pos.y + 1);
      }
    }
    if (point.sky) {
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y - 28);
      ctx.lineTo(pos.x + 6, pos.y - 20);
      ctx.lineTo(pos.x - 6, pos.y - 20);
      ctx.closePath();
      ctx.fillStyle = "#c67c25";
      ctx.fill();
    }
    if (activeWave.has(key)) {
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 25, 0, Math.PI * 2);
      ctx.strokeStyle = "#e4572e";
      ctx.lineWidth = 6;
      ctx.stroke();
    }
  }

  if (hoverKey) drawInspector(hoverKey);
}

function drawInspector(key) {
  const point = game.points.find((p) => keyOf(p.coord) === key);
  if (!point) return;
  roundedRect(18, 18, 242, 78, 12);
  ctx.fillStyle = "rgba(255,253,247,.94)";
  ctx.fill();
  ctx.strokeStyle = "rgba(70,61,45,.25)";
  ctx.stroke();
  ctx.fillStyle = "#252822";
  ctx.textAlign = "left";
  ctx.font = "700 14px system-ui";
  ctx.fillText(`Point ${point.coord[0]}, ${point.coord[1]}`, 32, 43);
  ctx.font = "12px system-ui";
  const stack = point.stack.length ? point.stack.join(" → ") : "empty";
  ctx.fillText(`Stack: ${stack} · height ${point.stack.length}`, 32, 65);
  ctx.fillStyle = "#66675f";
  ctx.fillText(`${point.legal ? "Legal" : "Not legal"}${point.sky ? " · sky liberty" : ""}`, 32, 84);
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) * canvas.width / rect.width,
    y: (event.clientY - rect.top) * canvas.height / rect.height,
  };
}

function nearestPoint(event) {
  const mouse = canvasPoint(event);
  let best = null;
  let distance = Infinity;
  for (const [key, pos] of projected) {
    const d = Math.hypot(mouse.x - pos.x, mouse.y - pos.y);
    if (d < distance) { best = key; distance = d; }
  }
  return distance <= 28 ? best : null;
}

canvas.addEventListener("mousemove", (event) => {
  hoverKey = nearestPoint(event);
  draw();
});
canvas.addEventListener("mouseleave", () => { hoverKey = null; draw(); });
canvas.addEventListener("click", async (event) => {
  if (thinking || game.match?.computer_turn) return;
  const key = nearestPoint(event);
  const point = game.points.find((p) => keyOf(p.coord) === key);
  if (!point || !point.legal || game.finished) return;
  await humanAction("/api/play", {point: point.coord});
});

document.querySelector("#new-btn").addEventListener("click", async () => {
  if (game.moves_played && !confirm("Start a new game?")) return;
  computerSequence += 1;
  thinking = false;
  try {
    setGame(await request("/api/new", {
      n: Number(sizeSelect.value),
      mode: modeSelect.value,
      human_color: colorSelect.value,
      difficulty: difficultySelect.value,
      explain: explainCheckbox.checked,
    }));
  } catch (error) {
    message.textContent = error.message;
  }
});
passButton.addEventListener("click", async () => humanAction("/api/pass"));
swapButton.addEventListener("click", async () => humanAction("/api/swap"));
resumeButton.addEventListener("click", async () => humanAction("/api/resume"));
modeSelect.addEventListener("change", updateSetupVisibility);

document.querySelector("#save-btn").addEventListener("click", async () => {
  const snapshot = await request("/api/snapshot");
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], {type: "application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "cairn-game.json";
  link.click();
  URL.revokeObjectURL(link.href);
});
document.querySelector("#load-btn").addEventListener("click", () => document.querySelector("#load-file").click());
document.querySelector("#load-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  computerSequence += 1;
  thinking = false;
  try { setGame(await request("/api/load", JSON.parse(await file.text()))); }
  catch (error) { message.textContent = error.message; }
  event.target.value = "";
});

document.addEventListener("keydown", async (event) => {
  if (event.key.toLowerCase() === "f") {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.querySelector(".game-card").requestFullscreen();
  }
});

function advanceTime(ms) {
  if (animation) {
    animation.elapsed += ms;
    animation.index = Math.floor(animation.elapsed / 500);
    if (animation.index >= animation.waves.length) animation = null;
  }
  draw();
}
window.advanceTime = advanceTime;

function frame(now) {
  const delta = Math.min(100, now - lastFrame);
  lastFrame = now;
  if (animation) advanceTime(delta);
  requestAnimationFrame(frame);
}

window.render_game_to_text = () => JSON.stringify({
  coordinate_system: "engine integer coordinates; canvas origin is visual only",
  board_size: game?.n,
  to_move: game?.to_move,
  current_player: game?.current_player,
  move: game ? game.moves_played + 1 : null,
  finished: game?.finished,
  thinking,
  swap_available: game?.swap_available,
  resumption_available: game?.resumption_available,
  resumption_used: game?.resumption_used,
  score: game?.score,
  match: game?.match,
  computer_decision: game?.computer_decision,
  legal_points: game?.points.filter((p) => p.legal).map((p) => p.coord),
  occupied: game?.points.filter((p) => p.stack.length).map((p) => ({coord: p.coord, stack: p.stack, sky: p.sky})),
  capture_animation_wave: animation?.index ?? null,
});

request("/api/state").then(setGame).catch((error) => { message.textContent = error.message; });
requestAnimationFrame(frame);

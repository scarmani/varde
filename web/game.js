const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const turnStatus = document.querySelector("#turn-status");
const message = document.querySelector("#message");
const passButton = document.querySelector("#pass-btn");
const swapButton = document.querySelector("#swap-btn");
const resumeButton = document.querySelector("#resume-btn");
const finishExtButton = document.querySelector("#finish-ext-btn");
const sizeSelect = document.querySelector("#board-size");
const rulesSelect = document.querySelector("#ruleset");
const modeSelect = document.querySelector("#game-mode");
const colorSelect = document.querySelector("#human-color");
const difficultySelect = document.querySelector("#difficulty");
const profileSelect = document.querySelector("#profile");
const blackDifficultySelect = document.querySelector("#black-difficulty");
const blackProfileSelect = document.querySelector("#black-profile");
const whiteDifficultySelect = document.querySelector("#white-difficulty");
const whiteProfileSelect = document.querySelector("#white-profile");
const explainCheckbox = document.querySelector("#explain-moves");
const aiNote = document.querySelector("#ai-note");
const profileNote = document.querySelector("#profile-note");
const spectatorControls = document.querySelector("#spectator-controls");
const playButton = document.querySelector("#play-btn");
const stepButton = document.querySelector("#step-btn");
const speedSelect = document.querySelector("#playback-speed");
const playbackNote = document.querySelector("#playback-note");
const trainingGamesSelect = document.querySelector("#training-games");
const trainButton = document.querySelector("#train-btn");
const cancelTrainingButton = document.querySelector("#cancel-training-btn");
const resetTrainingButton = document.querySelector("#reset-training-btn");
const trainingStatus = document.querySelector("#training-status");
const newButton = document.querySelector("#new-btn");
const rulesetNote = document.querySelector("#ruleset-note");

let game = null;
let projected = new Map();
let hoverKey = null;
let animation = null;
let lastFrame = performance.now();
let thinking = false;
let computerSequence = 0;
let actionInFlight = false;
let visual = null;
let watchPlaying = false;
let training = null;
let trainingPoll = null;
let profileCatalog = null;
let rulesetCatalog = null;

const savedSpeed = Number(
  localStorage.getItem("varde-playback-speed")
  ?? localStorage.getItem("cairn-playback-speed"),
);
const playbackSpeed = [1200, 500, 100].includes(savedSpeed) ? savedSpeed : 500;
speedSelect.value = String(playbackSpeed);

const BOARD_SCALE = 1.1;
const STONE_RADIUS_PER_SCALE = 0.8291732589425476;

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

function profileById(profileId) {
  return profileCatalog?.profiles?.find((profile) => profile.id === profileId);
}

function rulesetById(rulesetId) {
  return rulesetCatalog?.rulesets?.find((ruleset) => ruleset.id === rulesetId);
}

function populateRulesetSelect(catalog) {
  const selected = rulesSelect.value || "classic";
  rulesSelect.replaceChildren(...catalog.rulesets.map((ruleset) => {
    const option = document.createElement("option");
    option.value = ruleset.id;
    option.disabled = !ruleset.public_new_game;
    const suffix = ruleset.public_new_game ? "" : ` — ${ruleset.status}`;
    option.textContent = `${ruleset.label}${suffix}`;
    return option;
  }));
  rulesSelect.value = rulesetById(selected) ? selected : "classic";
}

function updateRulesetSetup({coerceSize = false} = {}) {
  const ruleset = rulesetById(rulesSelect.value);
  if (!ruleset) return;
  for (const option of sizeSelect.options) {
    const size = Number(option.value);
    option.disabled = size < ruleset.min_size || size > ruleset.max_size;
  }
  const selectedSize = Number(sizeSelect.value);
  if (coerceSize && (selectedSize < ruleset.min_size || selectedSize > ruleset.max_size)) {
    sizeSelect.value = String(Math.min(4, ruleset.max_size));
  }
  const status = ruleset.status === "candidate" ? "evaluation candidate" : ruleset.status;
  const reason = ruleset.archival_reason ? ` ${ruleset.archival_reason}` : "";
  rulesetNote.textContent = `${ruleset.label} ${ruleset.evaluation_id} · ${status}. ${ruleset.description}${reason}`;
  newButton.disabled = !ruleset.public_new_game;
}

function installRulesetCatalog(catalog) {
  rulesetCatalog = catalog;
  populateRulesetSelect(catalog);
  updateRulesetSetup();
}

function populateProfileSelect(select, prefix) {
  const selected = select.value || "balanced";
  select.replaceChildren(...profileCatalog.profiles.map((profile) => {
    const option = document.createElement("option");
    option.value = profile.id;
    option.disabled = !profile.available;
    option.textContent = `${prefix}${profile.label}${profile.available ? "" : " — unavailable"}`;
    return option;
  }));
  select.value = profileById(selected)?.available ? selected : "balanced";
}

function installProfileCatalog(catalog) {
  profileCatalog = catalog;
  populateProfileSelect(profileSelect, "Profile: ");
  populateProfileSelect(blackProfileSelect, "Black profile: ");
  populateProfileSelect(whiteProfileSelect, "White profile: ");
  updateProfileNote();
}

function describeProfile(profileId) {
  const profile = profileById(profileId);
  if (!profile) return "Profile information unavailable.";
  if (profile.id === "personal") {
    const model = training?.model || game?.learning || profile;
    const count = model.games_trained ?? profile.training_count ?? 0;
    if (!count) {
      return "Personal is untrained and currently equivalent to Balanced.";
    }
    return `Personal adds your local model trained on ${count} game${count === 1 ? "" : "s"}.`;
  }
  return profile.description;
}

function updateProfileNote() {
  if (!profileNote) return;
  if (modeSelect.value === "watch") {
    profileNote.textContent = `Black — ${describeProfile(blackProfileSelect.value)} White — ${describeProfile(whiteProfileSelect.value)}`;
  } else {
    profileNote.textContent = describeProfile(profileSelect.value);
  }
}

function syncSetupControls() {
  if (!game?.match) return;
  if (game.rules) rulesSelect.value = game.rules;
  updateRulesetSetup();
  modeSelect.value = game.match.mode;
  if (game.match.human_color) colorSelect.value = game.match.human_color;
  difficultySelect.value = game.match.difficulty;
  if (game.match.profile) profileSelect.value = game.match.profile;
  if (game.match.seats?.B?.difficulty) {
    blackDifficultySelect.value = game.match.seats.B.difficulty;
  }
  if (game.match.seats?.B?.profile) {
    blackProfileSelect.value = game.match.seats.B.profile;
  }
  if (game.match.seats?.W?.difficulty) {
    whiteDifficultySelect.value = game.match.seats.W.difficulty;
  }
  if (game.match.seats?.W?.profile) {
    whiteProfileSelect.value = game.match.seats.W.profile;
  }
  explainCheckbox.checked = game.match.explain;
  updateSetupVisibility();
}

function updateSetupVisibility() {
  const versus = modeSelect.value === "computer";
  const watch = modeSelect.value === "watch";
  document.querySelectorAll(".versus-setting").forEach((element) => {
    element.hidden = !versus;
  });
  document.querySelectorAll(".watch-setting").forEach((element) => {
    element.hidden = !watch;
  });
  document.querySelectorAll(".any-computer-setting").forEach((element) => {
    element.hidden = !(versus || watch);
  });
  spectatorControls.hidden = !watch;
  updateProfileNote();
}

function captureWaveDuration() {
  return game?.match?.mode === "watch" && Number(speedSelect.value) === 100 ? 80 : 500;
}

function stopPlayback({cancelWait = true} = {}) {
  watchPlaying = false;
  playButton.textContent = "Play";
  playbackNote.textContent = "Paused";
  if (cancelWait) computerSequence += 1;
  if (!actionInFlight) thinking = false;
  updateControls();
}

function setGame(next, schedule = true) {
  game = next;
  sizeSelect.value = String(game.n);
  animation = game.capture_waves.length
    ? {
      waves: game.capture_waves,
      elapsed: 0,
      index: 0,
      duration: captureWaveDuration(),
    }
    : null;
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
  // During play the whole-region score is misleading (one stone can
  // "border" the entire open board), so show outright control instead.
  const control = game.control || game.score;
  const rulesTag = game.rules && game.rules !== "classic" ? ` · ${game.rules}` : "";
  const controlText = `Black ${control.B} · White ${control.W}${rulesTag}`;
  const scoreText = `Black ${game.score.B} · White ${game.score.W}${rulesTag}`;
  const setTurnText = (primary, secondary) => {
    const small = document.createElement("small");
    small.textContent = secondary;
    turnStatus.replaceChildren(document.createTextNode(primary), small);
  };
  if (thinking) {
    setTurnText("Computer is thinking…", controlText);
  } else if (game.finished) {
    const result = game.score.B === game.score.W
      ? "Draw"
      : `${game.score.B > game.score.W ? "Black" : "White"} wins`;
    const ending = game.no_progress_end ? " · ended by stagnation" : "";
    setTurnText(result, `${scoreText}${ending}`);
  } else {
    setTurnText(
      `${game.current_player} · ${game.to_move === "B" ? "Black" : "White"} to move`,
      `${controlText} · move ${game.moves_played + 1}`,
    );
  }
  const extendOnly = ["breath-rescue", "breath-run"].includes(game.rules);
  if (
    !thinking && !game.finished && !game.match?.computer_turn
    && game.points?.some((p) => p.extension)
  ) {
    message.textContent = extendOnly
      ? "Amber points are free rescues — but taking any replaces your move this turn."
      : "Free extension available — the amber point rescues your group without costing your move.";
  }
  finishExtButton.hidden = !game.extension_only_turn;
  finishExtButton.disabled = thinking || Boolean(game.match?.computer_turn);
  const computerTurn = game.match?.computer_turn || thinking;
  passButton.disabled = game.finished || game.moves_played === 0 || computerTurn;
  swapButton.hidden = !game.swap_available || computerTurn;
  resumeButton.hidden = !game.resumption_available;
  resumeButton.disabled = thinking || Boolean(game.match?.computer_can_act);
  canvas.style.cursor = computerTurn ? "wait" : "default";
  const watch = game.match?.mode === "watch";
  spectatorControls.hidden = !watch;
  playButton.disabled = !watch || !game.match?.computer_can_act;
  stepButton.disabled = !watch || watchPlaying || thinking || !game.match?.computer_can_act;
  if (watch && !game.match?.computer_can_act && watchPlaying) {
    stopPlayback({cancelWait: false});
  }
}

async function scheduleComputerMove(forceOne = false) {
  if (!game?.match?.computer_can_act || thinking) return;
  const watch = game.match.mode === "watch";
  if (watch && !watchPlaying && !forceOne) return;
  const sequence = ++computerSequence;
  thinking = true;
  updateControls();
  const waves = game.capture_waves?.length || 0;
  const waveDelay = watch
    ? Math.max(forceOne ? 0 : Number(speedSelect.value), waves * captureWaveDuration())
    : Math.max(350, waves * 520);
  await new Promise((resolve) => setTimeout(resolve, waveDelay));
  if (sequence !== computerSequence) {
    if (!actionInFlight) {
      thinking = false;
      updateControls();
    }
    return;
  }
  try {
    actionInFlight = true;
    const next = await request("/api/computer", {});
    actionInFlight = false;
    thinking = false;
    setGame(next, !forceOne);
  } catch (error) {
    actionInFlight = false;
    thinking = false;
    if (watch) stopPlayback({cancelWait: false});
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
  const baseScale = Math.min(
    (canvas.width - 2 * pad) / Math.max(1, maxX - minX),
    (canvas.height - 2 * pad) / Math.max(1, maxY - minY),
  );
  const scale = baseScale * BOARD_SCALE;
  const offsetX = (canvas.width - (maxX - minX) * scale) / 2;
  const offsetY = (canvas.height - (maxY - minY) * scale) / 2;
  const spacing = 2 * scale;
  const stoneRadius = STONE_RADIUS_PER_SCALE * scale;
  visual = {
    scale,
    spacing,
    stoneRadius,
    lineWidth: Math.max(1.5, Math.min(3, spacing * 0.05)),
    hitRadius: spacing * 0.48,
  };
  projected = new Map(cart.map((p) => [p.key, {
    x: offsetX + (p.x - minX) * scale,
    y: offsetY + (p.y - minY) * scale,
  }]));
  // Gjerde: points are lines of the hex grid; their endpoints live at
  // twice the vertex coordinates, in the same space as the sums.
  visual.projectRaw = (x, y) => ({
    x: offsetX + (x - minX) * scale,
    y: offsetY + (-y * Math.sqrt(3) - minY) * scale,
  });
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
  const lineMode = game.points[0]?.segment != null;
  if (lineMode) {
    // Gjerde: draw the hex grid's lines themselves. Unclaimed lines
    // are faint; claimed lines are thick strokes in the stone colors.
    for (const point of game.points) {
      const [va, vb] = point.segment;
      const pa = visual.projectRaw(va[0] * 2, va[1] * 2);
      const pb = visual.projectRaw(vb[0] * 2, vb[1] * 2);
      const top = point.stack.at(-1);
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      if (!top) {
        ctx.strokeStyle = "rgba(83,71,50,.30)";
        ctx.lineWidth = Math.max(1, visual.lineWidth * 0.6);
      } else {
        ctx.strokeStyle = top === "B" ? "#252923" : "#f7f3e8";
        ctx.lineWidth = Math.max(4, visual.stoneRadius * 0.85);
      }
      ctx.stroke();
      if (top === "W") {
        ctx.strokeStyle = "#777369";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }
  } else {
    ctx.strokeStyle = "rgba(83,71,50,.48)";
    ctx.lineWidth = visual.lineWidth;
    for (const [a, b] of game.edges) {
      const pa = projected.get(keyOf(a));
      const pb = projected.get(keyOf(b));
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }
  }

  // Phantom edges: every rim point is missing a neighbor, and forgetting
  // that is the single most punishing misread in the game. Draw a stub
  // toward off-board space with a bar across its end: no liberty here.
  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  for (const point of game.points) {
    if (!point.phantoms) continue;
    const pos = projected.get(keyOf(point.coord));
    const away = Math.atan2(pos.y - centerY, pos.x - centerX);
    for (let i = 0; i < point.phantoms; i += 1) {
      const angle = away + (i - (point.phantoms - 1) / 2) * 0.7;
      const sx = pos.x + Math.cos(angle) * visual.stoneRadius * 0.9;
      const sy = pos.y + Math.sin(angle) * visual.stoneRadius * 0.9;
      const ex = pos.x + Math.cos(angle) * visual.stoneRadius * 1.8;
      const ey = pos.y + Math.sin(angle) * visual.stoneRadius * 1.8;
      ctx.strokeStyle = "rgba(140,60,45,.5)";
      ctx.lineWidth = Math.max(1, visual.lineWidth * 0.6);
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      const bar = visual.stoneRadius * 0.45;
      ctx.beginPath();
      ctx.moveTo(ex + Math.cos(angle + Math.PI / 2) * bar,
                 ey + Math.sin(angle + Math.PI / 2) * bar);
      ctx.lineTo(ex + Math.cos(angle - Math.PI / 2) * bar,
                 ey + Math.sin(angle - Math.PI / 2) * bar);
      ctx.stroke();
    }
  }
  ctx.strokeStyle = "rgba(83,71,50,.48)";
  ctx.lineWidth = visual.lineWidth;

  const activeWave = animation && animation.index < animation.waves.length
    ? new Set(animation.waves[animation.index].map(keyOf))
    : new Set();

  for (const point of game.points) {
    const key = keyOf(point.coord);
    const pos = projected.get(key);
    const top = point.stack.at(-1);
    if (point.legal) {
      ctx.beginPath();
      ctx.arc(
        pos.x,
        pos.y,
        top ? visual.stoneRadius * 1.33 : visual.stoneRadius * 0.67,
        0,
        Math.PI * 2,
      );
      ctx.strokeStyle = point.extension
        ? "rgba(191,111,42,.95)"
        : "rgba(74,112,70,.75)";
      ctx.lineWidth = top ? visual.lineWidth : Math.max(1.5, visual.lineWidth * 0.7);
      ctx.stroke();
    }
    if (!top) {
      if (!lineMode) {
        ctx.beginPath();
        ctx.arc(
          pos.x,
          pos.y,
          visual.stoneRadius * (point.rim ? 0.22 : 0.27),
          0,
          Math.PI * 2,
        );
        ctx.fillStyle = point.deep ? "#725f3f" : "#8b7958";
        ctx.fill();
      }
    } else {
      const radius = visual.stoneRadius;
      if (!lineMode) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = top === "B" ? "#252923" : "#f7f3e8";
        ctx.fill();
        ctx.strokeStyle = top === "B" ? "#050605" : "#777369";
        ctx.lineWidth = Math.max(1.5, visual.lineWidth * 0.75);
        ctx.stroke();

        const shown = point.stack.slice(-5);
        shown.forEach((color, index) => {
          ctx.fillStyle = color === "B" ? "#292d27" : "#f7f3e8";
          ctx.fillRect(
            pos.x + radius * 1.13,
            pos.y + radius * 0.53 - index * radius * 0.33,
            radius * 0.6,
            Math.max(2, radius * 0.27),
          );
        });
        if (point.stack.length > 1) {
          ctx.fillStyle = top === "B" ? "#fff" : "#222";
          ctx.font = `700 ${Math.max(8, radius * 0.67)}px system-ui`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(String(point.stack.length), pos.x, pos.y + 1);
        }
      }
      // Liberty warnings (flat rulesets): red ring at one liberty,
      // amber at two — the bookkeeping the lattice punishes hardest.
      if (point.group_libs === 1 || point.group_libs === 2) {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius * 1.18, 0, Math.PI * 2);
        ctx.strokeStyle = point.group_libs === 1
          ? "rgba(196,49,32,.9)"
          : "rgba(214,138,32,.75)";
        ctx.lineWidth = Math.max(
          1.5, visual.lineWidth * (point.group_libs === 1 ? 1.1 : 0.7),
        );
        ctx.stroke();
      }
    }
    if (point.sky) {
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y - visual.stoneRadius * 1.87);
      ctx.lineTo(pos.x + visual.stoneRadius * 0.4, pos.y - visual.stoneRadius * 1.33);
      ctx.lineTo(pos.x - visual.stoneRadius * 0.4, pos.y - visual.stoneRadius * 1.33);
      ctx.closePath();
      ctx.fillStyle = "#c67c25";
      ctx.fill();
    }
    if (activeWave.has(key)) {
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, visual.stoneRadius * 1.67, 0, Math.PI * 2);
      ctx.strokeStyle = "#e4572e";
      ctx.lineWidth = Math.max(3, visual.lineWidth * 2);
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
  const libsNote = Number.isInteger(point.group_libs)
    ? ` · group liberties: ${point.group_libs}`
    : "";
  const rimNote = point.phantoms ? " · rim (phantom neighbor)" : "";
  ctx.fillText(
    `${point.legal ? "Legal" : "Not legal"}`
    + `${point.sky ? " · sky liberty" : ""}${libsNote}${rimNote}`,
    32, 84,
  );
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) * canvas.width / rect.width,
    y: (event.clientY - rect.top) * canvas.height / rect.height,
  };
}

function nearestPoint(event) {
  if (!visual) return null;
  const mouse = canvasPoint(event);
  let best = null;
  let distance = Infinity;
  for (const [key, pos] of projected) {
    const d = Math.hypot(mouse.x - pos.x, mouse.y - pos.y);
    if (d < distance) { best = key; distance = d; }
  }
  return distance <= visual.hitRadius ? best : null;
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
  // A free extension keeps the turn: clicking its marked point is
  // strictly better than playing there, so it takes precedence.
  if (point.extension) {
    await humanAction("/api/extend", {point: point.coord});
    return;
  }
  // Mid extension-only turn, ordinary placements wait for End turn.
  if (game.extension_only_turn) return;
  await humanAction("/api/play", {point: point.coord});
});

newButton.addEventListener("click", async () => {
  if (game.moves_played && !confirm("Start a new game?")) return;
  stopPlayback();
  try {
    setGame(await request("/api/new", {
      n: Number(sizeSelect.value),
      rules: rulesSelect.value,
      mode: modeSelect.value,
      human_color: colorSelect.value,
      difficulty: difficultySelect.value,
      profile: profileSelect.value,
      black_difficulty: blackDifficultySelect.value,
      black_profile: blackProfileSelect.value,
      white_difficulty: whiteDifficultySelect.value,
      white_profile: whiteProfileSelect.value,
      explain: explainCheckbox.checked,
    }));
  } catch (error) {
    message.textContent = error.message;
  }
});
passButton.addEventListener("click", async () => humanAction("/api/pass"));
swapButton.addEventListener("click", async () => humanAction("/api/swap"));
resumeButton.addEventListener("click", async () => humanAction("/api/resume"));
finishExtButton.addEventListener("click", async () =>
  humanAction("/api/finish-extensions"));
modeSelect.addEventListener("change", updateSetupVisibility);
rulesSelect.addEventListener("change", () => updateRulesetSetup({coerceSize: true}));
profileSelect.addEventListener("change", updateProfileNote);
blackProfileSelect.addEventListener("change", updateProfileNote);
whiteProfileSelect.addEventListener("change", updateProfileNote);

playButton.addEventListener("click", () => {
  if (watchPlaying) {
    stopPlayback();
    return;
  }
  if (!game?.match?.computer_can_act) return;
  watchPlaying = true;
  playButton.textContent = "Pause";
  playbackNote.textContent = `${speedSelect.options[speedSelect.selectedIndex].text} playback`;
  updateControls();
  scheduleComputerMove();
});

stepButton.addEventListener("click", () => scheduleComputerMove(true));

speedSelect.addEventListener("change", () => {
  localStorage.setItem("varde-playback-speed", speedSelect.value);
  if (watchPlaying) {
    playbackNote.textContent = `${speedSelect.options[speedSelect.selectedIndex].text} playback`;
  }
});

document.querySelector("#save-btn").addEventListener("click", async () => {
  const snapshot = await request("/api/snapshot");
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], {type: "application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "varde-game.json";
  link.click();
  URL.revokeObjectURL(link.href);
});
document.querySelector("#load-btn").addEventListener("click", () => document.querySelector("#load-file").click());
document.querySelector("#load-file").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  stopPlayback();
  try {
    const loaded = await request("/api/load", JSON.parse(await file.text()));
    setGame(loaded, loaded.match.mode !== "watch");
  }
  catch (error) { message.textContent = error.message; }
  event.target.value = "";
});

function renderTraining(status) {
  training = status;
  const model = status.model || game?.learning || {games_trained: 0};
  const count = model.games_trained || 0;
  const attempts = model.games_attempted || 0;
  if (status.running) {
    trainingStatus.textContent = `Training ${status.completed}/${status.total} · ${count} learned · ${attempts} attempted`;
  } else if (status.error) {
    trainingStatus.textContent = `Training stopped: ${status.error}`;
  } else if (status.cancel_requested && status.completed < status.total) {
    trainingStatus.textContent = `Canceled after ${status.completed}/${status.total} · ${count} learned · ${attempts} attempted`;
  } else if (model.needs_retraining) {
    trainingStatus.textContent = `Legacy Personal model: ${count} game${count === 1 ? "" : "s"} retained · Reset before V2 retraining`;
  } else if (!count) {
    trainingStatus.textContent = "Personal: untrained · equivalent to Balanced";
  } else {
    trainingStatus.textContent = `Personal V2: ${count} trained · ${attempts} attempted`;
  }
  trainButton.disabled = Boolean(status.running);
  cancelTrainingButton.disabled = !status.running;
  resetTrainingButton.disabled = Boolean(status.running);
  updateProfileNote();
}

async function refreshTraining() {
  try {
    const status = await request("/api/training");
    renderTraining(status);
    if (status.running) {
      clearTimeout(trainingPoll);
      trainingPoll = setTimeout(refreshTraining, 500);
    }
  } catch (error) {
    trainingStatus.textContent = error.message;
  }
}

trainButton.addEventListener("click", async () => {
  try {
    renderTraining(await request("/api/training/start", {
      games: Number(trainingGamesSelect.value),
    }));
    clearTimeout(trainingPoll);
    trainingPoll = setTimeout(refreshTraining, 300);
  } catch (error) {
    trainingStatus.textContent = error.message;
  }
});

cancelTrainingButton.addEventListener("click", async () => {
  try {
    renderTraining(await request("/api/training/cancel", {}));
    clearTimeout(trainingPoll);
    trainingPoll = setTimeout(refreshTraining, 300);
  } catch (error) {
    trainingStatus.textContent = error.message;
  }
});

resetTrainingButton.addEventListener("click", async () => {
  if (!confirm("Reset Personal learning to zero games?")) return;
  try {
    renderTraining(await request("/api/training/reset", {}));
  } catch (error) {
    trainingStatus.textContent = error.message;
  }
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
    animation.index = Math.floor(animation.elapsed / animation.duration);
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
  rules: game?.rules,
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
  playback: {
    playing: watchPlaying,
    speed_ms: Number(speedSelect.value),
    action_in_flight: actionInFlight,
  },
  training,
  profiles: profileCatalog ? {
    version: profileCatalog.version,
    catalog_hash: profileCatalog.catalog_hash,
    available: profileCatalog.profiles.filter((profile) => profile.available).map((profile) => profile.id),
    selected: {
      versus: profileSelect.value,
      black: blackProfileSelect.value,
      white: whiteProfileSelect.value,
    },
    description: profileNote?.textContent,
  } : null,
  rulesets: rulesetCatalog ? {
    version: rulesetCatalog.version,
    available: rulesetCatalog.rulesets.filter((ruleset) => ruleset.public_new_game).map((ruleset) => ruleset.id),
    selected: rulesSelect.value,
    selected_status: rulesetById(rulesSelect.value)?.status,
    selected_revision: rulesetById(rulesSelect.value)?.evaluation_id,
    selected_native_evaluator: rulesetById(rulesSelect.value)?.native_evaluator_revision,
    native_evaluator_hash: rulesetCatalog.native_evaluators?.hash,
    description: rulesetNote?.textContent,
  } : null,
  visual: visual ? {
    board_scale: BOARD_SCALE,
    spacing: visual.spacing,
    stone_radius: visual.stoneRadius,
    diameter_ratio: 2 * visual.stoneRadius / visual.spacing,
  } : null,
  legal_points: game?.points.filter((p) => p.legal).map((p) => p.coord),
  occupied: game?.points.filter((p) => p.stack.length).map((p) => ({coord: p.coord, stack: p.stack, sky: p.sky})),
  capture_animation_wave: animation?.index ?? null,
});

Promise.all([
  request("/api/profiles"),
  request("/api/rulesets"),
  request("/api/state"),
]).then(([profiles, rulesets, initial]) => {
  installProfileCatalog(profiles);
  installRulesetCatalog(rulesets);
  if (initial.match.mode === "watch") stopPlayback();
  setGame(initial, initial.match.mode !== "watch");
}).catch((error) => { message.textContent = error.message; });
refreshTraining();
requestAnimationFrame(frame);

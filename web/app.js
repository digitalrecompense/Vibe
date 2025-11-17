const cloudCanvas = document.getElementById("cloud");
const ctx = cloudCanvas.getContext("2d");
let dpr = window.devicePixelRatio || 1;
let width = window.innerWidth;
let height = window.innerHeight;
cloudCanvas.width = width * dpr;
cloudCanvas.height = height * dpr;
ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const healthRefresh = document.getElementById("health-refresh");
const chatLog = document.getElementById("chat-log");
const promptInput = document.getElementById("prompt");
const sendBtn = document.getElementById("send");
const speakToggle = document.getElementById("speak-toggle");
const recordBtn = document.getElementById("record");
const bubbleTemplate = document.getElementById("bubble-template");

let conversation = [];
let isSending = false;
let recorder;
let audioContext;
let inputAnalyser;
let outputAnalyser;
let inputData;
let outputData;

const cloudBlobs = Array.from({ length: 18 }).map((_, idx) => ({
  baseX: Math.random() * width,
  baseY: Math.random() * height,
  radius: 60 + Math.random() * 140,
  speed: 0.3 + Math.random() * 0.8,
  offset: Math.random() * Math.PI * 2,
  hueShift: idx % 2 === 0 ? 180 : 260,
}));

const ease = (current, target, factor = 0.1) => current + (target - current) * factor;
let inputEnergy = 0;
let outputEnergy = 0;

function resize() {
  width = window.innerWidth;
  height = window.innerHeight;
  cloudCanvas.width = width * dpr;
  cloudCanvas.height = height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

window.addEventListener("resize", resize);

function energyFromAnalyser(analyser, dataArray) {
  if (!analyser || !dataArray) return 0;
  analyser.getByteTimeDomainData(dataArray);
  let sumSquares = 0;
  for (let i = 0; i < dataArray.length; i++) {
    const centered = (dataArray[i] - 128) / 128;
    sumSquares += centered * centered;
  }
  return Math.sqrt(sumSquares / dataArray.length);
}

function animateCloud() {
  ctx.clearRect(0, 0, width, height);
  const micBoost = energyFromAnalyser(inputAnalyser, inputData);
  const outBoost = energyFromAnalyser(outputAnalyser, outputData);
  inputEnergy = ease(inputEnergy, micBoost, 0.08);
  outputEnergy = ease(outputEnergy, outBoost, 0.08);
  const vibe = Math.min(1.6, 0.6 + inputEnergy * 1.8 + outputEnergy * 2.4);

  cloudBlobs.forEach((blob, idx) => {
    const t = performance.now() * 0.00015 * blob.speed + blob.offset;
    const wobble = Math.sin(t) * 60 * vibe;
    const wobbleY = Math.cos(t * 1.3) * 60 * vibe;
    const x = (blob.baseX + wobble + width * 1.5 + idx * 15) % (width + 80) - 40;
    const y = (blob.baseY + wobbleY + height * 1.5 + idx * 10) % (height + 80) - 40;
    const radius = blob.radius * (1 + vibe * 0.2);
    const gradient = ctx.createRadialGradient(x, y, radius * 0.25, x, y, radius);
    const hue = blob.hueShift + vibe * 35;
    gradient.addColorStop(0, `hsla(${hue}, 100%, 75%, ${0.15 + vibe * 0.08})`);
    gradient.addColorStop(1, `hsla(${hue + 40}, 100%, 45%, 0)`);
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  });

  requestAnimationFrame(animateCloud);
}

async function ensureAudioContext() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
  return audioContext;
}

async function startMicSensing() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    const context = await ensureAudioContext();
    inputAnalyser = context.createAnalyser();
    inputAnalyser.fftSize = 512;
    inputData = new Uint8Array(inputAnalyser.frequencyBinCount);
    const source = context.createMediaStreamSource(stream);
    source.connect(inputAnalyser);
  } catch (err) {
    console.warn("Mic sensing unavailable", err);
  }
}

document.addEventListener(
  "pointerdown",
  () => {
    if (!inputAnalyser) startMicSensing();
  },
  { once: true }
);

function bindOutputAnalyser(audio) {
  if (!audioContext || !audio) return;
  if (!outputAnalyser) {
    outputAnalyser = audioContext.createAnalyser();
    outputAnalyser.fftSize = 512;
    outputData = new Uint8Array(outputAnalyser.frequencyBinCount);
  }
  const source = audioContext.createMediaElementSource(audio);
  source.connect(outputAnalyser);
  outputAnalyser.connect(audioContext.destination);
}

function addBubble(role, text) {
  const node = bubbleTemplate.content.firstElementChild.cloneNode(true);
  node.querySelector(".bubble__role").textContent = role;
  node.querySelector(".bubble__text").textContent = text;
  chatLog.appendChild(node);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setStatus(text, healthy = true) {
  statusText.textContent = text;
  statusDot.style.background = healthy ? "#7cf4ff" : "#ff6f91";
  statusDot.style.boxShadow = healthy
    ? "0 0 18px rgba(124, 244, 255, 0.8)"
    : "0 0 18px rgba(255, 111, 145, 0.7)";
}

async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("bad status");
    const body = await res.json();
    setStatus(body.status === "ok" ? "Ready" : "Degraded", body.status === "ok");
  } catch (err) {
    setStatus("Offline", false);
  }
}

healthRefresh.addEventListener("click", () => checkHealth());
checkHealth();

function historyPayload() {
  return conversation.map((turn) => ({ user: turn.user, assistant: turn.assistant }));
}

async function sendPrompt() {
  if (isSending) return;
  const text = promptInput.value.trim();
  if (!text) {
    promptInput.focus();
    return;
  }

  addBubble("You", text);
  promptInput.value = "";
  isSending = true;
  sendBtn.textContent = "Thinking…";
  sendBtn.disabled = true;

  const payload = {
    message: text,
    history: historyPayload(),
    speak: speakToggle.checked,
  };

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
    const body = await res.json();
    conversation.push({ user: text, assistant: body.reply });
    addBubble("Vibe", body.reply);

    if (body.audio_base64) {
      const context = await ensureAudioContext();
      const audio = new Audio(`data:audio/wav;base64,${body.audio_base64}`);
      bindOutputAnalyser(audio);
      await context.resume();
      audio.play();
    }
  } catch (err) {
    console.error(err);
    addBubble("System", "Could not reach the model backend. Is the server running?");
    setStatus("Error", false);
  } finally {
    isSending = false;
    sendBtn.textContent = "Send";
    sendBtn.disabled = false;
    promptInput.focus();
  }
}

sendBtn.addEventListener("click", sendPrompt);
promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendPrompt();
  }
});

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    recorder = new MediaRecorder(stream);
    const chunks = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      stream.getTracks().forEach((t) => t.stop());
      await sendAudioForTranscription(blob);
    };

    recorder.start();
    recordBtn.classList.add("recording");
  } catch (err) {
    console.error("Cannot record", err);
    addBubble("System", "Microphone access was blocked.");
  }
}

function stopRecording() {
  if (recorder && recorder.state !== "inactive") {
    recorder.stop();
    recordBtn.classList.remove("recording");
  }
}

recordBtn.addEventListener("mousedown", startRecording);
recordBtn.addEventListener("mouseup", stopRecording);
recordBtn.addEventListener("mouseleave", stopRecording);
recordBtn.addEventListener("touchstart", (e) => {
  e.preventDefault();
  startRecording();
});
recordBtn.addEventListener("touchend", (e) => {
  e.preventDefault();
  stopRecording();
});

async function sendAudioForTranscription(blob) {
  const form = new FormData();
  form.append("file", blob, "clip.webm");
  addBubble("System", "Transcribing your clip…");

  try {
    const res = await fetch("/api/transcribe", {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Transcription failed: ${res.status}`);
    const { text } = await res.json();
    promptInput.value = text;
    promptInput.focus();
    addBubble("System", "Transcription ready. Edit or hit Send.");
  } catch (err) {
    console.error(err);
    addBubble("System", "Could not transcribe audio. Check server logs.");
  }
}

addBubble("Vibe", "Hey there! I can chat, listen, and speak back. Let the cloud guide you.");
animateCloud();

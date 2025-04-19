/* ===================================================== */
/*  AI‑Tutor front‑end (glass UI + fancy bubbles)        */
/* ===================================================== */
const API = "http://localhost:8000";

/* ---------- DOM refs ---------- */
const avatar   = document.getElementById("avatar");
const micBtn   = document.getElementById("recordBtn");
const statusEl = document.getElementById("status");
const chatLog  = document.getElementById("chatLog");
const speaker  = document.getElementById("assistantAudio");

/* ---------- state ---------- */
let mediaRecorder, chunks = [];
let SESSION_ID = null;
let greetBlob  = null;

/* ---------- prettier bubble creator ---------- */
function addBubble(role, text) {
  const div = document.createElement("div");
  div.className = "bubble " + role;

  if (role === "assistant") {
    const icon = document.createElement("span");
    icon.className = "icon";
    icon.textContent = "A";
    div.appendChild(icon);
  }
  const span = document.createElement("span");
  span.textContent = text;
  div.appendChild(span);

  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

/* ---------- speak helpers ---------- */
async function speakBlob(blob) {
  avatar.classList.add("talking");
  speaker.src = URL.createObjectURL(blob);
  await speaker.play();
  avatar.classList.remove("talking");
}
async function speakText(text) {
  const wav = await (await fetch(`${API}/speak`, { method:"POST", body:text })).blob();
  await speakBlob(wav);
}

/* ---------- mic initialisation ---------- */
async function initMic() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio:true });
  mediaRecorder = new MediaRecorder(stream, { mimeType:"audio/webm" });
  mediaRecorder.ondataavailable = e => chunks.push(e.data);
  mediaRecorder.onstop = () => handleUserAudio(new Blob(chunks, {type:"audio/webm"}));
}

/* ---------- boot ---------- */
window.addEventListener("load", async () => {
  try {
    const { session, reply } = await (await fetch(`${API}/start`, { method:"POST" })).json();
    SESSION_ID = session;
    addBubble("assistant", reply);
    statusEl.textContent = "Click the mic to reply";
    micBtn.disabled = false;

    /* pre‑fetch greeting TTS */
    greetBlob = await (await fetch(`${API}/speak`, { method:"POST", body:reply })).blob();

    /* play greeting after first user gesture */
    const playGreeting = async () => {
      if (greetBlob) await speakBlob(greetBlob);
      greetBlob = null;
    };
    document.addEventListener("pointerdown", playGreeting, { once:true });

  } catch (err) {
    statusEl.textContent = "Failed: " + err.message;
  }
});

/* ---------- mic button ---------- */
micBtn.onclick = async () => {
  if (!mediaRecorder) await initMic();

  if (mediaRecorder.state === "inactive") {
    chunks.length = 0;
    mediaRecorder.start();
    micBtn.textContent = "⏹️";
    statusEl.textContent = "Listening…";
  } else {
    mediaRecorder.stop();
    micBtn.textContent = "🎙️";
    micBtn.disabled = true;
  }
};

/* ---------- handle user audio ---------- */
async function handleUserAudio(blob) {
  try {
    /* STT */
    const fd = new FormData();
    fd.append("audio", blob, "speech.webm");
    const { text:userText } = await (await fetch(`${API}/transcribe`, { method:"POST", body:fd })).json();

    if ((userText.match(/\p{L}/gu) || []).length < 3) {
      statusEl.textContent = "I didn't catch that — please say it again.";
      micBtn.disabled = false;
      return;
    }
    addBubble("user", userText);

    /* agent chat */
    const chat = await (await fetch(`${API}/chat`, {
      method:"POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ session:SESSION_ID, transcript:userText })
    })).json();

    if (chat.error) throw new Error(chat.error);

    addBubble("assistant", chat.reply);
    await speakText(chat.reply);

    micBtn.disabled = chat.done;
    statusEl.textContent = chat.done ? "Finished" : "Click the mic to reply";

  } catch (err) {
    statusEl.textContent = "⚠️ " + err.message;
  } finally {
    micBtn.textContent = "🎙️";
    if (!micBtn.disabled) micBtn.disabled = false;
  }
}

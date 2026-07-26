// ---- Starfield backdrop ----
(function () {
  const canvas = document.getElementById("starfield");
  const ctx = canvas.getContext("2d");
  let stars = [];

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    const count = Math.floor((canvas.width * canvas.height) / 9000);
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.2 + 0.3,
      phase: Math.random() * Math.PI * 2,
      speed: 0.006 + Math.random() * 0.012,
    }));
  }

  function draw(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of stars) {
      const twinkle = 0.15 + 0.35 * Math.abs(Math.sin(s.phase + t * s.speed));
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200, 147, 46, ${twinkle * 0.55})`;
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  resize();
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    requestAnimationFrame(draw);
  } else {
    draw(0);
  }
})();

// ---- Chat logic ----
const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-text");
const suggestionsEl = document.getElementById("suggestions");
const resetBtn = document.getElementById("reset-btn");

function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = `msg ${sender}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "msg typing";
  div.innerHTML = "<span></span><span></span><span></span>";
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

async function sendMessage(text) {
  if (!text.trim()) return;
  addMessage(text, "user");
  suggestionsEl.style.display = "none";
  const typingEl = showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    typingEl.remove();
    addMessage(data.reply, "bot");
  } catch (err) {
    typingEl.remove();
    addMessage("I couldn't reach the server just now. Please try again.", "bot");
  }
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value;
  inputEl.value = "";
  sendMessage(text);
});

suggestionsEl.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => sendMessage(chip.dataset.msg));
});

resetBtn.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST", credentials: "same-origin" });
  messagesEl.innerHTML = "";
  suggestionsEl.style.display = "flex";
  addMessage("Fresh start! Ask me about your zodiac sign or a movie recommendation.", "bot");
});

// Welcome message
addMessage("Hi! I'm Tara \u2728 Ask me for your zodiac sign, or tell me what kind of movie you're in the mood for.", "bot");

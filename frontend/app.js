let currentSessionId = null;

const sessionListEl = document.getElementById("session-list");
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = chatForm.querySelector("button");
const newChatBtn = document.getElementById("new-chat-btn");

function emptyStateHtml() {
  return `
    <div class="empty-state">
      <p>Ask about the local docs, do math, search the web, or ask the time.</p>
      <div class="suggestions">
        <button class="suggestion" data-q="What is the ReAct framework?">What is the ReAct framework?</button>
        <button class="suggestion" data-q="What is 47 * 8 - 12?">What is 47 * 8 - 12?</button>
        <button class="suggestion" data-q="What is today's date and time?">What is today's date and time?</button>
      </div>
    </div>
  `;
}

function wireSuggestions() {
  messagesEl.querySelectorAll(".suggestion").forEach((btn) => {
    btn.addEventListener("click", () => {
      chatInput.value = btn.dataset.q;
      chatForm.requestSubmit();
    });
  });
}

async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) throw new Error(await res.text());
    const sessions = await res.json();
    renderSessions(sessions);
  } catch (err) {
    sessionListEl.innerHTML = `<li class="session-error">Couldn't load history — is Redis running?</li>`;
  }
}

function renderSessions(sessions) {
  sessionListEl.innerHTML = "";
  if (!sessions.length) {
    sessionListEl.innerHTML = `<li class="session-empty">No conversations yet</li>`;
    return;
  }
  for (const s of sessions) {
    const li = document.createElement("li");
    li.className = "session-item" + (s.id === currentSessionId ? " active" : "");
    li.textContent = s.title || "Untitled";
    li.title = s.title || "Untitled";
    li.addEventListener("click", () => selectSession(s.id));
    sessionListEl.appendChild(li);
  }
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  try {
    const res = await fetch(`/api/sessions/${sessionId}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    messagesEl.innerHTML = "";
    if (!data.messages.length) {
      messagesEl.innerHTML = emptyStateHtml();
      wireSuggestions();
    } else {
      for (const m of data.messages) {
        appendMessage(m.role, m.content, m.trace);
      }
    }
  } catch (err) {
    messagesEl.innerHTML = `<div class="empty-state"><p>Couldn't load that conversation.</p></div>`;
  }
  loadSessions();
}

function startNewChat() {
  currentSessionId = null;
  messagesEl.innerHTML = emptyStateHtml();
  wireSuggestions();
  loadSessions();
}

function appendMessage(role, content, trace) {
  const emptyState = messagesEl.querySelector(".empty-state");
  if (emptyState) emptyState.remove();

  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  wrapper.appendChild(bubble);

  if (role === "assistant" && trace && trace.length) {
    const details = document.createElement("details");
    details.className = "trace";
    const summary = document.createElement("summary");
    summary.textContent = "agent trace";
    details.appendChild(summary);
    const traceBody = document.createElement("div");
    traceBody.textContent = trace.join(" → ");
    details.appendChild(traceBody);
    wrapper.appendChild(details);
  }

  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrapper;
}

function appendThinking() {
  const emptyState = messagesEl.querySelector(".empty-state");
  if (emptyState) emptyState.remove();

  const wrapper = document.createElement("div");
  wrapper.className = "message assistant thinking";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = "thinking…";
  wrapper.appendChild(bubble);
  messagesEl.appendChild(wrapper);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return wrapper;
}

async function sendMessage(text) {
  appendMessage("user", text);
  const thinkingEl = appendThinking();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId, message: text }),
    });

    thinkingEl.remove();

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      appendMessage("assistant", `Error: ${err.detail || res.statusText}`);
      return;
    }

    const data = await res.json();
    currentSessionId = data.session_id;
    appendMessage("assistant", data.answer, data.trace);
    loadSessions();
  } catch (err) {
    thinkingEl.remove();
    appendMessage("assistant", `Error: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  sendMessage(text);
});

newChatBtn.addEventListener("click", startNewChat);

wireSuggestions();
loadSessions();

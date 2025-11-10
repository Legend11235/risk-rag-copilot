const API = "http://127.0.0.1:8000";

// DOM elements
const healthBanner = document.getElementById("healthBanner");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const btnHealth = document.getElementById("btnHealth");
const btnStats = document.getElementById("btnStats");
const btnRebuild = document.getElementById("btnRebuild");
const btnUpload = document.getElementById("btnUpload");
const pdfInput = document.getElementById("pdfInput");
const uploadStatus = document.getElementById("uploadStatus");
const statsOutput = document.getElementById("statsOutput");
const statsRefreshInline = document.getElementById("statsRefreshInline");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const chatLog = document.getElementById("chatLog");
const toastRoot = document.getElementById("toast");

// Local state for last 10 Q&A pairs
const qnaHistory = [];

// Generic toast helper for surfaced errors or notices
function showToast(message, type = "error") {
  const colors = {
    error: "bg-rose-500",
    success: "bg-emerald-500",
    info: "bg-slate-900",
  };
  const wrapper = document.createElement("div");
  wrapper.className = `${colors[type] || colors.info} text-white rounded-lg px-4 py-2 shadow-lg transition transform`;
  wrapper.textContent = message;
  toastRoot.appendChild(wrapper);
  setTimeout(() => wrapper.remove(), 4000);
}

// Centralized fetch helper that throws on non-2xx and bubbles toasts
async function apiFetch(path, options = {}) {
  const { headers, ...rest } = options;
  const response = await fetch(`${API}${path}`, {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(headers || {}),
    },
  });

  if (!response.ok) {
    let detail = "";
    try {
      const data = await response.json();
      detail = data.detail || JSON.stringify(data);
    } catch (err) {
      detail = await response.text();
    }
    showToast(detail || `Request failed (${response.status})`);
    throw new Error(detail || "Request failed");
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function updateHealthBanner(status) {
  if (!healthBanner) return;
  if (status === "ok") {
    healthBanner.textContent = "OK";
    healthBanner.className = "rounded-full bg-emerald-100 text-emerald-700 px-4 py-1 text-sm font-semibold tracking-wide";
  } else {
    healthBanner.textContent = "DOWN";
    healthBanner.className = "rounded-full bg-rose-100 text-rose-700 px-4 py-1 text-sm font-semibold tracking-wide";
  }
}

async function pingHealth() {
  try {
    const data = await apiFetch("/health");
    const ok = data?.status === "ok" || data === "ok";
    updateHealthBanner(ok ? "ok" : "down");
    if (!ok) {
      showToast("Health endpoint returned unexpected payload", "error");
    }
    return data;
  } catch (err) {
    updateHealthBanner("down");
  }
}

async function fetchStats() {
  try {
    const data = await apiFetch("/stats");
    statsOutput.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    // error already toasted
  }
}

async function rebuildIndex() {
  btnRebuild.disabled = true;
  btnRebuild.textContent = "Rebuilding…";
  try {
    const data = await apiFetch("/rebuild", { method: "POST" });
    showToast(data?.message || "Rebuild started", "success");
    await fetchStats();
  } catch (err) {
    // handled upstream
  } finally {
    btnRebuild.disabled = false;
    btnRebuild.textContent = "Rebuild Index";
  }
}

async function uploadPdf(file) {
  if (!file) {
    showToast("Please choose a PDF first", "info");
    return;
  }
  uploadStatus.textContent = "Uploading…";
  const formData = new FormData();
  formData.append("file", file);

  try {
    const data = await apiFetch("/upload_pdf", {
      method: "POST",
      body: formData,
    });
    const { chunks = [], chunk_count, message } = data || {};
    const count = chunk_count ?? chunks?.length ?? "?";
    uploadStatus.textContent = `Uploaded successfully (${count} chunks).`;
    showToast(message || "Upload complete", "success");
  } catch (err) {
    uploadStatus.textContent = "";
  } finally {
    pdfInput.value = "";
  }
}

function renderChat() {
  chatLog.innerHTML = "";
  qnaHistory.forEach((entry) => {
    const { question, answer, sources = [] } = entry;

    // User bubble
    const userBubble = document.createElement("div");
    userBubble.className = "flex justify-end";
    userBubble.innerHTML = `
      <div class="max-w-xl rounded-2xl bg-slate-900 px-4 py-3 text-sm text-white shadow">
        ${escapeHtml(question)}
      </div>`;
    chatLog.appendChild(userBubble);

    // Assistant bubble
    const assistantBubble = document.createElement("div");
    assistantBubble.className = "flex justify-start";

    const sourceLine = (sources || [])
      .map((src, idx) => {
        const label = src?.id ?? idx + 1;
        const score = (typeof src?.similarity === "number") ? src.similarity.toFixed(2) : "?";
        const name = src?.source ?? src?.filename ?? "";     // optional filename/source if backend provides it
        const snippet = src?.snippet || src?.text || "";
        const nameTag = name ? ` ${escapeHtml(name)}` : "";
        return `<span class="rounded bg-slate-200 px-2 py-1 text-xs font-mono" title="${escapeHtml(snippet)}">[#${label} ${score}]${nameTag}</span>`;
      })
      .join(" ");

    assistantBubble.innerHTML = `
      <div class="max-w-xl rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-900 shadow space-y-2">
        <p>${answer ? formatMarkdown(answer) : "Thinking…"}</p>
        ${sources.length ? `<div class="flex flex-wrap gap-2 text-xs text-slate-500">Sources: ${sourceLine}</div>` : ""}
      </div>`;
    chatLog.appendChild(assistantBubble);
  });

  chatLog.scrollTo({ top: chatLog.scrollHeight, behavior: "smooth" });
}

function escapeHtml(str = "") {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Minimal markdown formatter for line breaks
function formatMarkdown(text = "") {
  return escapeHtml(text).replace(/\n/g, "<br />");
}

function addPair(question, answer, sources) {
  qnaHistory.push({ question, answer, sources });
  if (qnaHistory.length > 10) {
    qnaHistory.shift();
  }
  renderChat();
}

function updateLatestAnswer(answer, sources) {
  if (!qnaHistory.length) return;
  const last = qnaHistory[qnaHistory.length - 1];
  last.answer = answer;
  last.sources = sources;
  renderChat();
}

async function ask(question) {
  addPair(question, null, []);
  try {
    const data = await apiFetch(`/ask?question=${encodeURIComponent(question)}`);
    updateLatestAnswer(data?.answer || "No answer", data?.sources || []);
  } catch (err) {
    updateLatestAnswer("Request failed. Check logs.", []);
  }
}

// Event bindings
sidebarToggle?.addEventListener("click", () => {
  const isHidden = sidebar.classList.contains("hidden");
  if (isHidden) {
    sidebar.classList.remove("hidden");
    sidebar.classList.add("flex");
  } else {
    sidebar.classList.add("hidden");
    sidebar.classList.remove("flex");
  }
});

btnHealth?.addEventListener("click", pingHealth);
btnStats?.addEventListener("click", fetchStats);
statsRefreshInline?.addEventListener("click", fetchStats);
btnRebuild?.addEventListener("click", rebuildIndex);
btnUpload?.addEventListener("click", () => uploadPdf(pdfInput.files[0]));

chatForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatInput.value.trim();
  if (!question) return;
  sendBtn.disabled = true;
  chatInput.disabled = true;
  try {
    await ask(question);
    chatInput.value = "";
  } finally {
    sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
});

// Initialize default view
pingHealth();
fetchStats();
renderChat();

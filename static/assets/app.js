const app = document.querySelector("#app");
const toast = document.querySelector("#toast");
let dashboardCache = null;

const icons = { dashboard: "◫", meetings: "◉", upload: "+", tasks: "✓" };

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3200);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Something went wrong");
  return data;
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function shell(content, active = "dashboard", title = "Workspace overview") {
  app.innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand"><span class="brand-mark">M</span><span class="brand-name">MeetMind</span></div>
        <nav class="nav">
          ${[["dashboard", "Dashboard"], ["meetings", "Meetings"], ["upload", "New meeting"], ["tasks", "My tasks"]].map(([id, label]) => `
            <button data-route="${id}" class="${active === id ? "active" : ""}"><span class="nav-icon">${icons[id]}</span><span class="nav-label">${label}</span></button>
          `).join("")}
        </nav>
        <div class="sidebar-foot"><strong>Consent comes first</strong><span>Only upload meetings when every participant has agreed to recording and analysis.</span></div>
      </aside>
      <main class="main">
        <header class="topbar"><h1>${title}</h1><div class="workspace"><span>My workspace</span><span class="avatar">SJ</span></div></header>
        <section class="content">${content}</section>
      </main>
    </div>`;
  document.querySelectorAll("[data-route]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.route)));
}

function loading() {
  shell('<div class="loader"><div><div class="spinner"></div><p>Loading MeetMind…</p></div></div>');
}

function meetingRow(meeting) {
  const participants = meeting.participants?.slice(0, 3).join(", ") || "No participants listed";
  return `<button class="meeting-row" data-meeting="${meeting.id}">
    <span class="meeting-icon">${meeting.status === "ready" ? "✓" : "••"}</span>
    <span class="meeting-meta"><strong>${escapeHtml(meeting.title)}</strong><span>${escapeHtml(participants)}</span><span class="status ${meeting.status}">${meeting.status}</span></span>
    <span class="row-time">${formatDate(meeting.created_at)}<br>${meeting.duration_minutes || 0} min</span>
  </button>`;
}

function taskRow(task) {
  const done = task.status === "done";
  return `<div class="task ${done ? "done" : ""}"><div class="task-top"><button class="task-check ${done ? "done" : ""}" data-task="${task.id}" data-status="${done ? "open" : "done"}">${done ? "✓" : ""}</button><strong>${escapeHtml(task.title)}</strong></div><small>${escapeHtml(task.owner || "Unassigned")} · ${escapeHtml(task.due_date || "No due date")}</small></div>`;
}

async function dashboard() {
  loading();
  const data = await api("/api/dashboard");
  dashboardCache = data;
  shell(`
    ${!data.gemini_configured ? '<div class="banner"><span><strong>Demo mode.</strong> Add GEMINI_API_KEY to .env to analyze new transcripts with Gemini.</span><button class="text-button" id="setup-help">Setup</button></div>' : ""}
    <div class="hero"><div><p class="eyebrow">Good work starts with clarity</p><h2>Your meetings,<br>remembered.</h2><p class="hero-copy">Turn consented conversations into searchable notes, clear decisions, and action items your team can actually finish.</p></div><button class="primary" id="new-meeting">Upload a meeting</button></div>
    <div class="stats">
      <div class="stat"><span>Meetings processed</span><strong>${data.stats.meetings}</strong></div>
      <div class="stat"><span>Estimated hours saved</span><strong>${data.stats.hours_saved}</strong></div>
      <div class="stat"><span>Open action items</span><strong>${data.stats.open_tasks}</strong></div>
    </div>
    <div class="grid">
      <div class="panel"><div class="panel-head"><h3>Recent meetings</h3><button class="text-button" id="all-meetings">View all</button></div><div class="meeting-list">${data.meetings.map(meetingRow).join("") || '<div class="empty">No meetings yet.</div>'}</div></div>
      <div class="panel"><div class="panel-head"><h3>My action items</h3><span class="badge">${data.stats.open_tasks} open</span></div><div class="task-list">${data.tasks.slice(0, 5).map(taskRow).join("") || '<div class="empty">Nothing assigned yet.</div>'}</div></div>
    </div>`, "dashboard");
  wireRows();
  document.querySelector("#new-meeting").onclick = () => navigate("upload");
  document.querySelector("#all-meetings").onclick = () => navigate("meetings");
  document.querySelector("#setup-help")?.addEventListener("click", () => showToast("Copy .env.example to .env, add your Gemini key, then restart the server."));
}

async function meetingsPage() {
  loading();
  const meetings = await api("/api/meetings");
  shell(`<div class="hero"><div><p class="eyebrow">Meeting library</p><h2>Everything your team<br>decided.</h2></div><div class="search"><span>⌕</span><input id="meeting-search" placeholder="Search meetings or transcripts" /></div></div><div class="panel"><div id="meeting-results" class="meeting-list">${meetings.map(meetingRow).join("")}</div></div>`, "meetings", "Meeting library");
  wireRows();
  let timer;
  document.querySelector("#meeting-search").addEventListener("input", event => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const results = await api(`/api/meetings?q=${encodeURIComponent(event.target.value)}`);
      document.querySelector("#meeting-results").innerHTML = results.map(meetingRow).join("") || '<div class="empty">No matching meetings.</div>';
      wireRows();
    }, 250);
  });
}

function uploadPage() {
  shell(`<div class="hero"><div><p class="eyebrow">New meeting</p><h2>Bring your conversation<br>into focus.</h2><p class="hero-copy">Upload a consented audio recording. MeetMind will transcribe it locally, then use Gemini to create the notes and tasks.</p></div></div>
  <div class="panel upload-card"><form id="upload-form">
    <div class="dropzone" id="dropzone"><div class="drop-icon">↑</div><strong>Drop your meeting audio here</strong><p>MP3, WAV, M4A, MP4, or WebM</p><button type="button" class="secondary" id="choose-file">Choose file</button><input hidden type="file" id="audio" name="audio" accept="audio/*,video/mp4,video/webm" required><div class="file-name" id="file-name"></div></div>
    <div class="form-grid">
      <div class="field"><label for="title">Meeting title</label><input id="title" name="title" placeholder="Weekly product sync" required></div>
      <div class="field"><label for="language">Spoken language</label><select id="language" name="language"><option value="auto">Detect automatically</option><option value="en">English</option><option value="hi">Hindi / Hinglish</option></select></div>
      <div class="field full"><label for="participants">Participants</label><input id="participants" name="participants" placeholder="Priya, Arjun, Meera"><small>Separate names with commas</small></div>
      <label class="consent field full"><input type="checkbox" name="consent_confirmed" value="true" required><span>I confirm that every participant agreed to this recording and its processing by MeetMind. This confirmation is saved in the consent log.</span></label>
    </div>
    <div class="form-actions"><button class="primary" id="process-button">Transcribe and summarize</button></div>
  </form></div>`, "upload", "Upload meeting");
  const input = document.querySelector("#audio");
  const dropzone = document.querySelector("#dropzone");
  document.querySelector("#choose-file").onclick = () => input.click();
  const showFile = file => document.querySelector("#file-name").textContent = file ? `Selected: ${file.name}` : "";
  input.onchange = () => showFile(input.files[0]);
  for (const eventName of ["dragenter", "dragover"]) dropzone.addEventListener(eventName, event => { event.preventDefault(); dropzone.classList.add("drag"); });
  for (const eventName of ["dragleave", "drop"]) dropzone.addEventListener(eventName, event => { event.preventDefault(); dropzone.classList.remove("drag"); });
  dropzone.addEventListener("drop", event => { input.files = event.dataTransfer.files; showFile(input.files[0]); });
  document.querySelector("#upload-form").onsubmit = async event => {
    event.preventDefault();
    const button = document.querySelector("#process-button");
    button.disabled = true;
    button.textContent = "Uploading…";
    try {
      const result = await api("/api/meetings", { method: "POST", body: new FormData(event.target) });
      showToast("Upload complete. MeetMind is processing your meeting.");
      navigate(`meeting/${result.id}`);
    } catch (error) {
      showToast(error.message);
      button.disabled = false;
      button.textContent = "Transcribe and summarize";
    }
  };
}

async function tasksPage() {
  loading();
  const tasks = await api("/api/tasks");
  shell(`<div class="hero"><div><p class="eyebrow">Action items</p><h2>Keep every promise<br>moving.</h2><p class="hero-copy">Tasks extracted from your meetings, with owners and source context.</p></div></div><div class="panel"><div class="task-list">${tasks.map(taskRow).join("") || '<div class="empty">No action items yet.</div>'}</div></div>`, "tasks", "My action items");
  wireTasks();
}

async function meetingDetail(id, activeTab = "summary") {
  loading();
  const meeting = await api(`/api/meetings/${id}`);
  const participantText = meeting.participants.join(", ") || "No participants listed";
  let body = "";
  if (meeting.status === "processing") {
    body = '<div class="panel loader"><div><div class="spinner"></div><p>Transcribing and analyzing your meeting…</p></div></div>';
    setTimeout(() => meetingDetail(id, activeTab), 4000);
  } else if (meeting.status === "failed") {
    body = `<div class="panel"><div class="error"><strong>Processing stopped.</strong><br>${escapeHtml(meeting.error)}</div><p class="hero-copy">Install the full requirements to enable faster-whisper and Kokoro. You can still explore the included demo meeting.</p></div>`;
  } else {
    const views = {
      summary: `<div class="panel"><div class="panel-head"><h3>AI meeting brief</h3><div><span class="badge">${escapeHtml(meeting.ai_provider)}</span> <button class="secondary" id="read-aloud">◖ Read aloud</button></div></div><p class="summary-lead">${escapeHtml(meeting.summary)}</p><div id="audio-slot"></div><div class="insight-grid"><div class="insight"><h4>Key points</h4><ul>${meeting.key_points.map(point => `<li>${escapeHtml(point)}</li>`).join("") || "<li>No key points found.</li>"}</ul></div><div class="insight"><h4>Decisions</h4><ul>${meeting.decisions.map(point => `<li>${escapeHtml(point)}</li>`).join("") || "<li>No explicit decisions found.</li>"}</ul></div></div></div>`,
      transcript: `<div class="panel"><div class="panel-head"><h3>Transcript</h3><span class="badge">${escapeHtml(meeting.language)}</span></div><div class="transcript">${escapeHtml(meeting.transcript)}</div></div>`,
      actions: `<div class="panel"><div class="panel-head"><h3>Action items</h3><span class="badge">${meeting.tasks.length} tasks</span></div><div class="task-list">${meeting.tasks.map(taskRow).join("") || '<div class="empty">No explicit commitments found.</div>'}</div></div>`,
      consent: `<div class="panel"><div class="panel-head"><h3>Consent log</h3><span class="badge">${meeting.consent_log.length} granted</span></div>${meeting.consent_log.map(item => `<div class="task"><strong>${escapeHtml(item.participant)}</strong><small style="margin-left:0">Granted · ${escapeHtml(item.method)} · ${formatDate(item.at)}</small></div>`).join("") || '<div class="empty">No participant names were supplied. Host consent attestation was recorded.</div>'}</div>`
    };
    body = `<div class="tabs">${[["summary", "Summary"], ["transcript", "Transcript"], ["actions", "Action items"], ["consent", "Consent"]].map(([tab, label]) => `<button class="${tab === activeTab ? "active" : ""}" data-tab="${tab}">${label}</button>`).join("")}</div>${views[activeTab]}`;
  }
  shell(`<button class="back" id="back-meetings">‹ Back to meetings</button><div class="detail-head"><div class="detail-title"><p class="eyebrow">Meeting brief</p><h2>${escapeHtml(meeting.title)}</h2><div class="detail-meta"><span>${formatDate(meeting.created_at)}</span><span>•</span><span>${escapeHtml(participantText)}</span><span>•</span><span>${meeting.duration_minutes || 0} min</span></div></div><span class="status ${meeting.status}">${meeting.status}</span></div>${body}`, "meetings", "Meeting details");
  document.querySelector("#back-meetings").onclick = () => navigate("meetings");
  document.querySelectorAll("[data-tab]").forEach(button => button.onclick = () => meetingDetail(id, button.dataset.tab));
  wireTasks();
  document.querySelector("#read-aloud")?.addEventListener("click", async event => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "Generating voice…";
    try {
      const result = await api(`/api/meetings/${id}/read-aloud?language=${meeting.language.startsWith("hi") ? "hi" : "en"}`, { method: "POST" });
      document.querySelector("#audio-slot").innerHTML = `<audio class="audio-player" controls autoplay src="${result.audio_url}"></audio>`;
      button.textContent = "◖ Read aloud";
    } catch (error) {
      showToast(error.message);
      button.textContent = "◖ Read aloud";
    } finally { button.disabled = false; }
  });
}

function wireRows() {
  document.querySelectorAll("[data-meeting]").forEach(row => row.onclick = () => navigate(`meeting/${row.dataset.meeting}`));
  wireTasks();
}

function wireTasks() {
  document.querySelectorAll("[data-task]").forEach(button => button.onclick = async () => {
    try {
      await api(`/api/tasks/${button.dataset.task}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: button.dataset.status }) });
      showToast(button.dataset.status === "done" ? "Task completed" : "Task reopened");
      const route = location.hash.slice(1) || "dashboard";
      navigate(route, true);
    } catch (error) { showToast(error.message); }
  });
}

function navigate(route, replace = false) {
  const target = `#${route}`;
  if (replace) {
    history.replaceState(null, "", target);
    routePage();
  } else if (location.hash === target) {
    routePage();
  } else {
    location.hash = route;
  }
}

function routePage() {
  const route = location.hash.slice(1) || "dashboard";
  if (route === "dashboard") dashboard().catch(renderError);
  else if (route === "meetings") meetingsPage().catch(renderError);
  else if (route === "upload") uploadPage();
  else if (route === "tasks") tasksPage().catch(renderError);
  else if (route.startsWith("meeting/")) meetingDetail(route.split("/")[1]).catch(renderError);
  else dashboard().catch(renderError);
}

function renderError(error) {
  shell(`<div class="panel"><div class="error">${escapeHtml(error.message)}</div></div>`);
}

window.addEventListener("hashchange", routePage);
routePage();


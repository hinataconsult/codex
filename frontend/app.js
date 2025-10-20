const API_BASE = window.location.origin.includes("localhost")
  ? "http://localhost:8000/api"
  : "/api";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

const dialog = $("#message-dialog");
const dialogMessage = $("#dialog-message");
const dialogClose = $("#dialog-close");

dialogClose.addEventListener("click", () => dialog.close());

const showMessage = (message) => {
  dialogMessage.textContent = message;
  dialog.showModal();
};

const views = {
  home: $("#home-view"),
  new: $("#new-view"),
};

const navButtons = {
  home: $("#nav-home"),
  new: $("#nav-new"),
};

Object.entries(navButtons).forEach(([key, button]) => {
  button.addEventListener("click", () => {
    Object.values(navButtons).forEach((btn) => btn.classList.remove("active"));
    Object.values(views).forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    views[key].classList.add("active");
  });
});

const tableBody = document.querySelector("#minutes-table tbody");
const detailPanel = $("#detail-panel");

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

async function loadMinutes() {
  const params = new URLSearchParams();
  const title = $("#filter-title").value.trim();
  const participant = $("#filter-participant").value.trim();
  const start = $("#filter-start").value;
  const end = $("#filter-end").value;
  if (title) params.append("title", title);
  if (participant) params.append("participant", participant);
  if (start) params.append("start_date", start);
  if (end) params.append("end_date", end);
  const data = await fetchJSON(`${API_BASE}/minutes?${params.toString()}`);
  renderMinutesTable(data);
}

function renderMinutesTable(minutes) {
  tableBody.innerHTML = "";
  minutes.forEach((item) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.id}</td>
      <td>${item.title}</td>
      <td>${item.meeting_date}</td>
      <td>${item.participants.join(", ")}</td>
      <td>${new Date(item.created_at).toLocaleString()}</td>
    `;
    row.addEventListener("click", () => openMinutesDetail(item.id));
    tableBody.appendChild(row);
  });
  if (!minutes.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.textContent = "該当する議事録はありません";
    row.appendChild(cell);
    tableBody.appendChild(row);
  }
}

async function openMinutesDetail(id) {
  try {
    const detail = await fetchJSON(`${API_BASE}/minutes/${id}`);
    renderDetail(detail);
  } catch (error) {
    showMessage(`詳細取得に失敗しました: ${error.message}`);
  }
}

function renderDetail(detail) {
  detailPanel.classList.remove("hidden");
  detailPanel.innerHTML = `
    <header class="detail-header">
      <h2>${detail.title}</h2>
      <div class="detail-actions">
        <button class="secondary" data-action="pdf" data-id="${detail.id}">PDF出力</button>
      </div>
    </header>
    <p><strong>会議日:</strong> ${detail.meeting_date}</p>
    <p><strong>参加者:</strong> ${detail.participants.join(", ") || "-"}</p>
    <section class="summary-grid">
      ${renderSection("会議の目的", detail.purpose)}
      ${renderSection("決定事項", detail.decisions)}
      ${renderSection("宿題", detail.action_items)}
      ${renderSection("議事要旨", detail.digest)}
    </section>
    <section>
      <h3>宿題の通知</h3>
      <form id="reminder-form" data-id="${detail.id}">
        <label>担当者<input type="text" name="assignee" required placeholder="担当者" /></label>
        <label>対象タスク<input type="text" name="action_item" required placeholder="タスク概要" /></label>
        <label>期限<input type="date" name="due_date" required /></label>
        <button type="submit">通知送信</button>
      </form>
      <ul>
        ${detail.reminders
          .map(
            (reminder) => `
              <li>
                <strong>${reminder.assignee}</strong> - ${reminder.action_item} (期限: ${reminder.due_date})
                <span class="status">[${reminder.status}]</span>
              </li>
            `,
          )
          .join("")}
      </ul>
    </section>
    <section>
      <h3>編集履歴</h3>
      <div id="history-list">
        ${detail.versions
          .map(
            (version) => `
              <article class="history-entry">
                <header>
                  <strong>更新日時:</strong> ${new Date(version.created_at).toLocaleString()} / <strong>編集者:</strong> ${
                    version.editor || "-"
                  }
                </header>
                ${renderHistory(version)}
              </article>
            `,
          )
          .join("")}
      </div>
    </section>
  `;

  detailPanel.querySelector('[data-action="pdf"]').addEventListener("click", () => {
    window.open(`${API_BASE}/minutes/${detail.id}/export/pdf`, "_blank");
  });

  const reminderForm = detailPanel.querySelector("#reminder-form");
  reminderForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(reminderForm);
    const payload = Object.fromEntries(formData.entries());
    try {
      await fetchJSON(`${API_BASE}/minutes/${detail.id}/notifications`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showMessage("通知を送信しました");
      openMinutesDetail(detail.id);
    } catch (error) {
      showMessage(`通知送信に失敗しました: ${error.message}`);
    }
  });
}

function renderSection(title, body) {
  return `
    <article>
      <h3>${title}</h3>
      <p>${body ? body.replace(/\n/g, "<br />") : "(未入力)"}</p>
    </article>
  `;
}

function renderHistory(version) {
  const sections = [
    { label: "会議の目的", value: version.purpose },
    { label: "決定事項", value: version.decisions },
    { label: "宿題", value: version.action_items },
    { label: "議事要旨", value: version.digest },
  ];
  return sections
    .map(
      (section) => `
        <details>
          <summary>${section.label}</summary>
          <pre>${section.value || "(未入力)"}</pre>
        </details>
      `,
    )
    .join("");
}

$("#filter-search").addEventListener("click", () => loadMinutes().catch((error) => showMessage(error.message)));
$("#filter-reset").addEventListener("click", () => {
  ["#filter-title", "#filter-participant", "#filter-start", "#filter-end"].forEach((selector) => {
    $(selector).value = "";
  });
  loadMinutes().catch((error) => showMessage(error.message));
});

$("#export-csv").addEventListener("click", () => {
  const params = new URLSearchParams();
  const title = $("#filter-title").value.trim();
  const participant = $("#filter-participant").value.trim();
  const start = $("#filter-start").value;
  const end = $("#filter-end").value;
  if (title) params.append("title", title);
  if (participant) params.append("participant", participant);
  if (start) params.append("start_date", start);
  if (end) params.append("end_date", end);
  window.open(`${API_BASE}/minutes/export/csv?${params.toString()}`, "_blank");
});

const generateButton = $("#generate-summary");
const summaryEditor = $("#summary-editor");
const summaryLength = $("#summary-length");

generateButton.addEventListener("click", async () => {
  const title = $("#form-title").value.trim();
  const meetingDate = $("#form-date").value;
  const participants = $("#form-participants").value
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);
  const text = $("#form-text").value.trim();
  const inputMode = $("#form-mode").value;

  if (!title || !meetingDate || !text) {
    showMessage("タイトル、会議日、元テキストは必須です");
    return;
  }

  try {
    const payload = { title, meeting_date: meetingDate, participants, text, input_mode: inputMode };
    const summary = await fetchJSON(`${API_BASE}/minutes/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("#summary-purpose").value = summary.purpose;
    $("#summary-decisions").value = summary.decisions;
    $("#summary-actions").value = summary.action_items;
    $("#summary-digest").value = summary.digest;
    summaryLength.textContent = `総文字数: ${summary.total_characters} / 1000`;
    summaryEditor.classList.remove("hidden");
  } catch (error) {
    showMessage(`要約生成に失敗しました: ${error.message}`);
  }
});

$("#minutes-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = $("#form-title").value.trim();
  const meetingDate = $("#form-date").value;
  const participants = $("#form-participants").value
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);
  const rawInput = $("#form-text").value.trim();
  const payload = {
    title,
    meeting_date: meetingDate,
    participants,
    raw_input: rawInput,
    purpose: $("#summary-purpose").value,
    decisions: $("#summary-decisions").value,
    action_items: $("#summary-actions").value,
    digest: $("#summary-digest").value,
  };

  if (!payload.purpose || !payload.decisions || !payload.action_items || !payload.digest) {
    showMessage("すべてのセクションを入力してください");
    return;
  }

  try {
    await fetchJSON(`${API_BASE}/minutes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showMessage("議事録を保存しました");
    event.target.reset();
    summaryEditor.classList.add("hidden");
    summaryLength.textContent = "";
    loadMinutes();
    navButtons.home.click();
  } catch (error) {
    showMessage(`保存に失敗しました: ${error.message}`);
  }
});

window.addEventListener("DOMContentLoaded", () => {
  loadMinutes().catch((error) => showMessage(error.message));
});

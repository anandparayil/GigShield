const APP_STORAGE_KEY = "gigshield_session";

function setSession(session) {
  localStorage.setItem(APP_STORAGE_KEY, JSON.stringify(session));
}

function getSession() {
  const raw = localStorage.getItem(APP_STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

function clearSession() {
  localStorage.removeItem(APP_STORAGE_KEY);
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Something went wrong");
  }
  return data;
}

function formatCurrency(value) {
  return `₹${Number(value || 0).toFixed(2)}`;
}

function escapeHtml(text = "") {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderEmpty(targetId, message) {
  document.getElementById(targetId).innerHTML = `<div class="empty-state">${message}</div>`;
}

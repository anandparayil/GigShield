function requireAdmin() {
  const session = getSession();
  if (!session || session.role !== "admin") {
    window.location.href = "/admin-login";
    return null;
  }
  return session;
}

function setupAdminTabs() {
  const buttons = document.querySelectorAll(".nav-item[data-tab]");
  const panels = document.querySelectorAll(".tab-panel");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(`tab-${button.dataset.tab}`).classList.add("active");
    });
  });
}

function renderBars(targetId, items, labelKey, valueKey, formatter = (v) => v) {
  if (!items.length) {
    renderEmpty(targetId, "No data yet.");
    return;
  }
  const max = Math.max(...items.map((item) => Number(item[valueKey] || 0)), 1);
  document.getElementById(targetId).innerHTML = `
    <div class="progress-list">
      ${items.map((item) => `
        <div class="bar-item">
          <div class="list-row">
            <span>${escapeHtml(item[labelKey])}</span>
            <strong>${formatter(item[valueKey])}</strong>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width:${(Number(item[valueKey]) / max) * 100}%"></div>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

async function loadAnalytics() {
  const data = await apiFetch("/api/admin/analytics");
  document.getElementById("summaryUsers").textContent = data.summary.total_users;
  document.getElementById("summaryPolicies").textContent = data.summary.active_policies;
  document.getElementById("summaryTriggers").textContent = data.summary.total_triggers;
  document.getElementById("summaryPayout").textContent = formatCurrency(data.summary.total_payout);

  renderBars("platformMix", data.platform_mix, "platform", "count");
  renderBars("triggerMix", data.claims_by_trigger, "trigger_type", "claims_count");
  renderBars("cityMix", data.users_by_city, "city", "users_count");
}

document.addEventListener("DOMContentLoaded", () => {
  requireAdmin();
  setupAdminTabs();
  loadAnalytics().catch((err) => alert(err.message));

  document.getElementById("adminLogoutBtn").addEventListener("click", () => {
    clearSession();
    window.location.href = "/admin-login";
  });

  document.getElementById("triggerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = document.getElementById("triggerMessage");
    message.textContent = "";
    try {
      const result = await apiFetch("/api/admin/triggers", {
        method: "POST",
        body: JSON.stringify({
          trigger_type: document.getElementById("triggerType").value,
          city: document.getElementById("triggerCity").value.trim(),
          zone_name: document.getElementById("triggerZone").value.trim(),
          severity: document.getElementById("triggerSeverity").value,
          description: document.getElementById("triggerDescription").value.trim()
        })
      });

      message.textContent = result.message;
      if (!result.claims_created.length) {
        renderEmpty("triggerResults", "Trigger saved, but no active policyholders matched this city/zone.");
      } else {
        document.getElementById("triggerResults").innerHTML = result.claims_created.map((item) => `
          <div class="claim-card">
            <div class="list-row"><strong>${escapeHtml(item.name)}</strong><span class="tag">${escapeHtml(item.phone)}</span></div>
            <p>Protected payout: ${formatCurrency(item.payout)}</p>
          </div>
        `).join("");
      }
      loadAnalytics();
      document.getElementById("triggerForm").reset();
    } catch (err) {
      message.textContent = err.message;
    }
  });
});

let dashboardState = {
  profile: null,
  platforms: [],
  policy: null,
  recent_claims: [],
  notifications: []
};

function requireUser() {
  const session = getSession();
  if (!session || session.role !== "user") {
    window.location.href = "/login";
    return null;
  }
  return session;
}

function setupTabs() {
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

function renderOverview() {
  const policy = dashboardState.policy;
  document.getElementById("metricPlatforms").textContent = dashboardState.platforms.length;
  document.getElementById("metricPremium").textContent = policy ? formatCurrency(policy.final_premium) : "No plan";
  document.getElementById("metricClaims").textContent = dashboardState.recent_claims.length;
  const payoutTotal = dashboardState.recent_claims.reduce((sum, claim) => sum + Number(claim.payout_amount || 0), 0);
  document.getElementById("metricPayout").textContent = formatCurrency(payoutTotal);

  if (!policy) {
    renderEmpty("overviewPolicy", "No active policy yet. Go to the Policy tab and activate one.");
  } else {
    const breakdown = policy.premium_breakdown ? JSON.parse(policy.premium_breakdown) : { additions: [], deductions: [] };
    document.getElementById("overviewPolicy").innerHTML = `
      <div class="list-card">
        <div class="list-row"><span class="label">Plan</span><span class="value">${escapeHtml(policy.plan_name)} Shield</span></div>
        <div class="list-row"><span class="label">Weekly premium</span><span class="value">${formatCurrency(policy.final_premium)}</span></div>
        <div class="list-row"><span class="label">Max payout</span><span class="value">${formatCurrency(policy.max_payout)}</span></div>
        <div class="list-row"><span class="label">Coverage hours</span><span class="value">${policy.coverage_hours} hrs</span></div>
        <div class="list-row"><span class="label">Renewal</span><span class="value">${policy.renewal_date}</span></div>
        <ul class="breakdown-list">
          ${(breakdown.additions || []).map((item) => `<li>${escapeHtml(item.label)}: +${formatCurrency(item.amount)}</li>`).join("")}
          ${(breakdown.deductions || []).map((item) => `<li>${escapeHtml(item.label)}: -${formatCurrency(item.amount)}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  if (!dashboardState.recent_claims.length) {
    renderEmpty("overviewClaims", "No claims yet. Trigger-based claims will appear here automatically.");
  } else {
    document.getElementById("overviewClaims").innerHTML = dashboardState.recent_claims.map((claim) => `
      <div class="claim-card">
        <div class="list-row">
          <strong>${escapeHtml(claim.trigger_type)}</strong>
          <span class="tag">${escapeHtml(claim.claim_status)}</span>
        </div>
        <p>${escapeHtml(claim.city)} · ${escapeHtml(claim.zone_name)}</p>
        <div class="list-row">
          <span class="label">Payout</span>
          <span class="value">${formatCurrency(claim.payout_amount)}</span>
        </div>
      </div>
    `).join("");
  }
}

function renderPlatforms() {
  if (!dashboardState.platforms.length) {
    renderEmpty("platformList", "No linked platforms yet.");
    return;
  }

  document.getElementById("platformList").innerHTML = dashboardState.platforms.map((platform) => `
    <div class="platform-card">
      <div class="list-row">
        <strong>${escapeHtml(platform.platform)}</strong>
        <span class="tag">${escapeHtml(platform.status)}</span>
      </div>
      <div class="list-row"><span class="label">Worker code</span><span class="value">${escapeHtml(platform.worker_code)}</span></div>
      <div class="list-row"><span class="label">Trips completed</span><span class="value">${platform.trips_completed}</span></div>
      <div class="list-row"><span class="label">Average hourly earning</span><span class="value">${formatCurrency(platform.avg_hourly_earning)}</span></div>
    </div>
  `).join("");
}

function renderClaims() {
  if (!dashboardState.recent_claims.length) {
    renderEmpty("claimsList", "No claims available yet.");
    return;
  }
  document.getElementById("claimsList").innerHTML = dashboardState.recent_claims.map((claim) => `
    <div class="claim-card">
      <div class="list-row">
        <strong>${escapeHtml(claim.trigger_type)}</strong>
        <span class="tag">${escapeHtml(claim.claim_status)}</span>
      </div>
      <p>${escapeHtml(claim.city)} · ${escapeHtml(claim.zone_name)}</p>
      <div class="list-row"><span class="label">Payout</span><span class="value">${formatCurrency(claim.payout_amount)}</span></div>
      <div class="list-row"><span class="label">Created</span><span class="value">${new Date(claim.created_at).toLocaleString()}</span></div>
    </div>
  `).join("");
}

function renderNotifications() {
  if (!dashboardState.notifications.length) {
    renderEmpty("notificationList", "No notifications yet.");
    return;
  }
  document.getElementById("notificationList").innerHTML = dashboardState.notifications.map((note) => `
    <div class="notify-card">
      <div class="list-row">
        <strong>${escapeHtml(note.title)}</strong>
        <span class="tag">${escapeHtml(note.type)}</span>
      </div>
      <p>${escapeHtml(note.message)}</p>
      <small class="label">${new Date(note.created_at).toLocaleString()}</small>
    </div>
  `).join("");
}

function fillProfile() {
  const profile = dashboardState.profile;
  if (!profile) return;
  document.getElementById("welcomeName").textContent = `Hello, ${profile.full_name}`;
  document.getElementById("badgeCity").textContent = profile.city;
  document.getElementById("badgeZone").textContent = profile.zone_name;
  document.getElementById("profileName").value = profile.full_name;
  document.getElementById("profilePhone").value = profile.phone;
  document.getElementById("profileCity").value = profile.city;
  document.getElementById("profileZone").value = profile.zone_name;
  document.getElementById("profileHours").value = profile.preferred_hours || "";
}

async function loadDashboard() {
  const session = requireUser();
  if (!session) return;

  const dashboard = await apiFetch(`/api/users/${session.id}/dashboard`);
  const claims = await apiFetch(`/api/claims/user/${session.id}`);

  dashboardState = {
    ...dashboard,
    recent_claims: claims
  };

  fillProfile();
  renderOverview();
  renderPlatforms();
  renderClaims();
  renderNotifications();
}

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadDashboard().catch((err) => alert(err.message));

  document.getElementById("logoutBtn").addEventListener("click", () => {
    clearSession();
    window.location.href = "/login";
  });

  document.getElementById("policyForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const session = requireUser();
    if (!session) return;
    const resultNode = document.getElementById("policyResult");
    resultNode.innerHTML = "";
    try {
      const result = await apiFetch("/api/policies/create", {
        method: "POST",
        body: JSON.stringify({
          user_id: session.id,
          plan_name: document.getElementById("planName").value
        })
      });

      resultNode.innerHTML = `
        <div class="mini-card">
          <strong>${result.message}</strong>
          <p>Base premium: ${formatCurrency(result.base_premium)}</p>
          <p>Final premium: ${formatCurrency(result.final_premium)}</p>
          <p>Max payout: ${formatCurrency(result.max_payout)}</p>
        </div>
      `;
      await loadDashboard();
    } catch (err) {
      resultNode.innerHTML = `<div class="empty-state">${err.message}</div>`;
    }
  });

  document.getElementById("platformForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const session = requireUser();
    if (!session) return;
    const message = document.getElementById("platformMessage");
    message.textContent = "";
    try {
      const result = await apiFetch(`/api/users/${session.id}/platforms`, {
        method: "POST",
        body: JSON.stringify({
          platform: document.getElementById("platformName").value,
          worker_code: document.getElementById("platformWorkerCode").value.trim(),
          trips_completed: Number(document.getElementById("platformTrips").value),
          avg_hourly_earning: Number(document.getElementById("platformEarning").value)
        })
      });
      message.textContent = result.message;
      document.getElementById("platformForm").reset();
      await loadDashboard();
    } catch (err) {
      message.textContent = err.message;
    }
  });

  document.getElementById("profileForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const session = requireUser();
    if (!session) return;
    const message = document.getElementById("profileMessage");
    message.textContent = "";
    try {
      const result = await apiFetch(`/api/users/${session.id}/profile`, {
        method: "PUT",
        body: JSON.stringify({
          full_name: document.getElementById("profileName").value.trim(),
          city: document.getElementById("profileCity").value.trim(),
          zone_name: document.getElementById("profileZone").value.trim(),
          preferred_hours: document.getElementById("profileHours").value.trim()
        })
      });
      message.textContent = result.message;
      await loadDashboard();
    } catch (err) {
      message.textContent = err.message;
    }
  });
});

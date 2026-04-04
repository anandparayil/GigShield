document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("platformContainer");
  const addBtn = document.getElementById("addPlatformBtn");
  const form = document.getElementById("registerForm");
  const message = document.getElementById("registerMessage");

  function platformRow(index) {
    const wrapper = document.createElement("div");
    wrapper.className = "platform-entry";
    wrapper.innerHTML = `
      <select class="reg-platform" required>
        <option value="">Platform</option>
        <option value="Swiggy">Swiggy</option>
        <option value="Zomato">Zomato</option>
        <option value="Rapido">Rapido</option>
        <option value="Zepto">Zepto</option>
      </select>
      <input type="text" class="reg-code" placeholder="Worker code" required>
      <input type="number" class="reg-trips" placeholder="Trips" min="0" value="0" required>
      <input type="number" class="reg-earning" placeholder="Avg ₹/hour" min="1" value="80" required>
      <button type="button" class="remove-btn">✕</button>
    `;
    wrapper.querySelector(".remove-btn").addEventListener("click", () => wrapper.remove());
    return wrapper;
  }

  addBtn.addEventListener("click", () => container.appendChild(platformRow(Date.now())));
  container.appendChild(platformRow(0));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    message.textContent = "";

    const platforms = Array.from(container.querySelectorAll(".platform-entry")).map((row) => ({
      platform: row.querySelector(".reg-platform").value,
      worker_code: row.querySelector(".reg-code").value.trim(),
      trips_completed: Number(row.querySelector(".reg-trips").value),
      avg_hourly_earning: Number(row.querySelector(".reg-earning").value)
    })).filter((item) => item.platform && item.worker_code);

    try {
      const result = await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: document.getElementById("fullName").value.trim(),
          phone: document.getElementById("phone").value.trim(),
          password: document.getElementById("password").value,
          city: document.getElementById("city").value.trim(),
          zone_name: document.getElementById("zone").value.trim(),
          preferred_hours: document.getElementById("hours").value.trim(),
          platforms
        })
      });

      message.textContent = `${result.message}. Please login now.`;
      form.reset();
      container.innerHTML = "";
      container.appendChild(platformRow(1));
    } catch (err) {
      message.textContent = err.message;
    }
  });
});

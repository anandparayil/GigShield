document.addEventListener("DOMContentLoaded", () => {
  const userLoginForm = document.getElementById("userLoginForm");
  const adminLoginForm = document.getElementById("adminLoginForm");

  if (userLoginForm) {
    userLoginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = document.getElementById("loginMessage");
      message.textContent = "";
      try {
        const result = await apiFetch("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({
            phone: document.getElementById("loginPhone").value.trim(),
            password: document.getElementById("loginPassword").value
          })
        });

        if (result.user.role !== "user") {
          throw new Error("This page is for workers only");
        }
        setSession(result.user);
        window.location.href = "/dashboard";
      } catch (err) {
        message.textContent = err.message;
      }
    });
  }

  if (adminLoginForm) {
    adminLoginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const message = document.getElementById("adminLoginMessage");
      message.textContent = "";
      try {
        const result = await apiFetch("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({
            phone: document.getElementById("adminPhone").value.trim(),
            password: document.getElementById("adminPassword").value
          })
        });

        if (result.user.role !== "admin") {
          throw new Error("This page is for admins only");
        }
        setSession(result.user);
        window.location.href = "/admin";
      } catch (err) {
        message.textContent = err.message;
      }
    });
  }
});

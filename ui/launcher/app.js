const $ = (id) => document.getElementById(id);

function showStatus(msg, type = "error") {
  const el = $("status");
  el.textContent = msg;
  el.className = `status ${type}`;
  el.classList.remove("hidden");
}

function hideStatus() {
  $("status").classList.add("hidden");
}

function setLoading(active, text = "Oturum açılıyor...") {
  $("login-card").classList.toggle("hidden", active);
  $("loading-card").classList.toggle("hidden", !active);
  $("loading-text").textContent = text;
  $("btn-login").disabled = active;
}

async function waitApi() {
  while (!window.pywebview || !window.pywebview.api) {
    await new Promise((r) => setTimeout(r, 50));
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await waitApi();
  const api = window.pywebview.api;

  $("btn-close").addEventListener("click", () => api.close_app());

  $("btn-login").addEventListener("click", () => {
    hideStatus();
    const email = $("email").value.trim();
    const password = $("password").value;
    const remember = $("remember").checked;
    if (!email || !password) {
      showStatus("E-posta ve şifre giriniz.");
      return;
    }
    setLoading(true, "Giriş yapılıyor...");
    api.login(email, password, remember);
  });

  $("password").addEventListener("keydown", (e) => {
    if (e.key === "Enter") $("btn-login").click();
  });

  const remembered = await api.get_remembered_email();
  if (remembered) {
    $("email").value = remembered;
    $("remember").checked = true;
    setLoading(true, "Kayıtlı hesap ile giriş yapılıyor...");
    api.try_auto_login();
  }
});

window.onLoginSuccess = () => setLoading(true, "Makro başlatılıyor...");
window.onLoginError = (msg) => {
  if (msg === "no_session" || msg === "no_token") {
    setLoading(false);
    return;
  }
  setLoading(false);
  showStatus(msg || "Giriş başarısız.");
};
window.onLaunchReady = () => setLoading(true, "Başlatılıyor...");

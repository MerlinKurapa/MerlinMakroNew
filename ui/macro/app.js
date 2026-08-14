const $ = (id) => document.getElementById(id);

let captureActive = false;
let selectedSlot = 0;
let slotMeta = [];

async function waitApi() {
  while (!window.pywebview || !window.pywebview.api) {
    await new Promise((r) => setTimeout(r, 50));
  }
}

function toast(msg) {
  let el = document.querySelector(".toast");
  if (!el) {
    el = document.createElement("div");
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 1800);
}

function setStatus(text) {
  $("status").textContent = text;
}

function setTopStatus(text) {
  $("top-status").textContent = text;
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${name}`);
  });
}

function renderCoords(points, meta) {
  slotMeta = meta || points.map(() => ({ locked: false, disabled: false }));
  const list = $("coord-list");
  list.innerHTML = "";
  points.forEach((pt, i) => {
    const m = slotMeta[i] || { locked: false, disabled: false };
    const row = document.createElement("div");
    row.className = "coord-row";
    if (i === selectedSlot) row.classList.add("selected");
    if (m.disabled) row.classList.add("disabled");
    if (m.locked) row.classList.add("locked");
    row.innerHTML = `
      <span>Slot ${i + 1}</span>
      <input type="number" data-slot="${i}" data-axis="x" value="${pt[0]}" min="0" max="9999" ${m.locked ? "readonly" : ""} />
      <input type="number" data-slot="${i}" data-axis="y" value="${pt[1]}" min="0" max="9999" ${m.locked ? "readonly" : ""} />
      <div class="row-actions">
        <button class="row-btn danger" data-act="delete" data-slot="${i}" title="Sil">🗑</button>
        <button class="row-btn ${m.locked ? "active" : ""}" data-act="lock" data-slot="${i}" title="Kilitle">🔒</button>
        <button class="row-btn ${m.disabled ? "active" : ""}" data-act="stop" data-slot="${i}" title="Durdur">⏹</button>
      </div>
    `;
    row.addEventListener("click", (e) => {
      if (e.target.closest(".row-btn")) return;
      selectedSlot = i;
      renderCoords(points, slotMeta);
      window.pywebview.api.select_slot(i);
    });
    list.appendChild(row);
  });

  list.querySelectorAll("input").forEach((inp) => {
    inp.addEventListener("change", () => {
      const slot = Number(inp.dataset.slot);
      const xInp = list.querySelector(`input[data-slot="${slot}"][data-axis="x"]`);
      const yInp = list.querySelector(`input[data-slot="${slot}"][data-axis="y"]`);
      window.pywebview.api.set_coord(slot, Number(xInp.value), Number(yInp.value));
    });
  });

  list.querySelectorAll(".row-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const slot = Number(btn.dataset.slot);
      const act = btn.dataset.act;
      if (act === "delete") window.pywebview.api.delete_coord(slot);
      if (act === "lock") window.pywebview.api.toggle_lock(slot);
      if (act === "stop") window.pywebview.api.toggle_disable(slot);
    });
  });
}

function renderSliders(settings) {
  const container = $("sliders");
  container.innerHTML = "";
  settings.forEach((s) => {
    const row = document.createElement("div");
    row.className = "slider-row";
    row.innerHTML = `
      <label><span>${s.label}</span><span id="val-${s.key}">${s.display}</span></label>
      <input type="range" min="${s.min}" max="${s.max}" value="${s.value}" data-key="${s.key}" />
    `;
    container.appendChild(row);
    const range = row.querySelector("input");
    range.addEventListener("input", () => {
      window.pywebview.api.set_setting(s.key, Number(range.value));
      $("val-" + s.key).textContent = (Number(range.value) / 1000).toFixed(3);
    });
  });
}

window.onCoordsUpdated = (points, meta) => renderCoords(points, meta);
window.onCaptureState = (active) => {
  captureActive = active;
  $("btn-capture-toggle").classList.toggle("active", active);
  $("btn-capture-toggle").textContent = active ? "◎ Takip Açık (F6)" : "◎ Canlı Takip";
};

document.addEventListener("DOMContentLoaded", async () => {
  await waitApi();
  const api = window.pywebview.api;

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  $("btn-item-start").onclick = () => api.start_item(Number($("run-count").value || 1));
  $("btn-stop").onclick = () => api.stop_all();
  $("btn-bag-toggle").onclick = () => api.toggle_bag();
  $("btn-bag-stop").onclick = () => api.stop_all();
  $("btn-skill-toggle").onclick = () => api.toggle_skill();
  $("btn-skill-stop").onclick = () => api.stop_all();
  $("btn-logout").onclick = () => api.logout();

  $("btn-add-coord").onclick = () => api.add_coord();
  $("btn-save-coords").onclick = async () => {
    await api.save_coords();
    toast("Koordinatlar kaydedildi");
  };
  $("btn-capture-toggle").onclick = () => {
    console.log("Canlı takip butonuna tıklandı");
    api.toggle_capture();
  };
  $("btn-save-settings").onclick = async () => {
    await api.save_settings();
    toast("Makro ayarları kaydedildi");
  };
  $("btn-reset-settings").onclick = async () => {
    const state = await api.reset_settings();
    renderSliders(state.settings || []);
    toast("Ayarlar varsayılana döndürüldü");
  };

  // Güncelleme sistemi
  $("btn-check-update").onclick = () => {
    const statusEl = $("update-status");
    statusEl.textContent = "Güncelleme kontrol ediliyor...";
    statusEl.classList.remove("hidden");
    api.check_update();
  };

  $("btn-download-update").onclick = () => {
    const statusEl = $("update-status");
    statusEl.textContent = "Güncelleme indiriliyor...";
    api.download_update();
  };

  const state = await api.get_state();
  $("user-email").textContent = state.email || "";
  renderCoords(state.points || [], state.slot_meta || []);
  renderSliders(state.settings || []);
  setStatus(state.status || "🟢 Hazır");
  setTopStatus(state.top_status || "Hazır");
  window.onCaptureState(state.capture_active || false);
});

window.onStatus = setStatus;
window.onTopStatus = setTopStatus;

// Güncelleme callback fonksiyonları
window.onUpdateCheck = (data) => {
  const statusEl = $("update-status");
  const downloadBtn = $("btn-download-update");

  if (data.has_update) {
    statusEl.textContent = `Yeni sürüm mevcut: ${data.latest_version} (Mevcut: ${data.current_version})`;
    statusEl.style.borderColor = "rgba(52, 211, 153, 0.5)";
    downloadBtn.classList.remove("hidden");
  } else {
    statusEl.textContent = "En son sürümü kullanıyorsunuz.";
    statusEl.style.borderColor = "rgba(148, 163, 184, 0.3)";
    downloadBtn.classList.add("hidden");
  }
};

window.onUpdateDownload = (data) => {
  const statusEl = $("update-status");
  if (data.success) {
    statusEl.textContent = "Güncelleme indirildi! Kurulum başlatılıyor...";
    setTimeout(() => {
      // İndirilen setup dosyasını çalıştır
      if (data.path) {
        window.pywebview.api.open_file(data.path);
      }
    }, 2000);
  } else {
    statusEl.textContent = "Güncelleme indirilemedi: " + (data.error || "Bilinmeyen hata");
    statusEl.style.borderColor = "rgba(248, 113, 113, 0.5)";
  }
};

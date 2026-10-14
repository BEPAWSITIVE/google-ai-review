// Dashboard Application JS
document.addEventListener("DOMContentLoaded", () => {
  const clientModal = document.getElementById("clientModal");
  const qrModal = document.getElementById("qrModal");
  const settingsModal = document.getElementById("settingsModal");
  const clientForm = document.getElementById("clientForm");
  const settingsForm = document.getElementById("settingsForm");
  const apiKeyBtn = document.getElementById("geminiApiKeyNavBtn");
  const apiKeyInput = document.getElementById("geminiApiKeyInput");

  // 1. Persistent Gemini API Key in localStorage
  const savedKey = localStorage.getItem("gemini_api_key");
  if (savedKey) {
    if (apiKeyInput && !apiKeyInput.value) {
      apiKeyInput.value = savedKey;
    }
    if (apiKeyBtn) {
      const masked = savedKey.length > 8 ? `${savedKey.slice(0, 4)}...${savedKey.slice(-4)}` : "Saved";
      apiKeyBtn.innerText = `⚙️ Gemini API: ${masked}`;
    }
    // Silently sync to backend so the current serverless instance has it
    fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gemini_api_key: savedKey })
    }).catch(() => {});
  }

  // 2. Client-side persistence and sync of clients across serverless instances
  const localClients = JSON.parse(localStorage.getItem("stored_clients") || "[]");
  if (localClients.length > 0) {
    fetch("/api/clients/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(localClients)
    }).catch(() => {});
  }

  // Open Add Client Modal
  window.openAddClientModal = () => {
    document.getElementById("modalTitle").innerText = "Add New Client / Business";
    document.getElementById("clientId").value = "";
    clientForm.reset();
    document.getElementById("brandColor").value = "#2563eb";
    clientModal.classList.add("active");
  };

  // Open Edit Client Modal
  window.openEditClientModal = async (id) => {
    try {
      const res = await fetch(`/api/clients/${id}`);
      if (!res.ok) throw new Error("Client not found");
      const client = await res.json();
      
      document.getElementById("modalTitle").innerText = "Edit Client Details";
      document.getElementById("clientId").value = client.id;
      document.getElementById("clientName").value = client.name || "";
      document.getElementById("clientCategory").value = client.category || "";
      document.getElementById("googleReviewUrl").value = client.google_review_url || "";
      document.getElementById("keywords").value = client.keywords || "";
      document.getElementById("highlights").value = client.highlights || "";
      document.getElementById("brandColor").value = client.brand_color || "#2563eb";
      document.getElementById("welcomeMsg").value = client.welcome_msg || "";
      
      clientModal.classList.add("active");
    } catch (err) {
      showToast("Error loading client: " + err.message);
    }
  };

  // Open QR Preview Modal with resilient payload
  window.openQrModal = (slug, name, payload) => {
    const origin = window.location.origin;
    const param = payload ? `?d=${payload}` : "";
    const reviewUrl = `${origin}/r/${slug}${param}`;
    const qrImgUrl = `/api/qr/${slug}${param}`;
    
    document.getElementById("qrModalBizName").innerText = name;
    document.getElementById("qrModalImage").src = qrImgUrl;
    document.getElementById("qrModalLinkInput").value = reviewUrl;
    document.getElementById("qrDownloadBtn").href = qrImgUrl;
    document.getElementById("qrDownloadBtn").setAttribute("download", `${slug}-qr-code.png`);
    document.getElementById("qrFlyerBtn").href = `/flyer/${slug}${param}`;
    document.getElementById("qrTestBtn").href = reviewUrl;
    
    qrModal.classList.add("active");
  };

  // Open Settings Modal
  window.openSettingsModal = () => {
    const currentKey = localStorage.getItem("gemini_api_key") || "";
    if (apiKeyInput && currentKey) {
      apiKeyInput.value = currentKey;
    }
    settingsModal.classList.add("active");
  };

  // Close modals
  window.closeModal = (modalId) => {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove("active");
  };

  // Close on outside click
  [clientModal, qrModal, settingsModal].forEach((m) => {
    if (m) {
      m.addEventListener("click", (e) => {
        if (e.target === m) m.classList.remove("active");
      });
    }
  });

  // Client form submit (Create or Update)
  if (clientForm) {
    clientForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = document.getElementById("clientId").value;
      const payload = {
        name: document.getElementById("clientName").value.trim(),
        category: document.getElementById("clientCategory").value.trim(),
        google_review_url: document.getElementById("googleReviewUrl").value.trim(),
        keywords: document.getElementById("keywords").value.trim(),
        highlights: document.getElementById("highlights").value.trim(),
        brand_color: document.getElementById("brandColor").value.trim(),
        welcome_msg: document.getElementById("welcomeMsg").value.trim()
      };

      try {
        const url = id ? `/api/clients/${id}` : "/api/clients";
        const method = id ? "PUT" : "POST";
        const res = await fetch(url, {
          method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to save client");
        }

        // Save in localStorage for persistence across serverless container recycles
        let clientsList = JSON.parse(localStorage.getItem("stored_clients") || "[]");
        const idx = clientsList.findIndex(c => c.name.toLowerCase() === payload.name.toLowerCase());
        if (idx >= 0) {
          clientsList[idx] = payload;
        } else {
          clientsList.push(payload);
        }
        localStorage.setItem("stored_clients", JSON.stringify(clientsList));

        showToast(id ? "Client updated successfully!" : "Client created successfully!");
        clientModal.classList.remove("active");
        setTimeout(() => window.location.reload(), 600);
      } catch (err) {
        showToast("Error: " + err.message);
      }
    });
  }

  // Delete client
  window.deleteClient = async (id, name) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      const res = await fetch(`/api/clients/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete client");

      // Remove from localStorage
      let clientsList = JSON.parse(localStorage.getItem("stored_clients") || "[]");
      clientsList = clientsList.filter(c => c.name.toLowerCase() !== name.toLowerCase());
      localStorage.setItem("stored_clients", JSON.stringify(clientsList));

      showToast("Client deleted.");
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      showToast("Error: " + err.message);
    }
  };

  // Settings form submit (Gemini API Key)
  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const key = document.getElementById("geminiApiKeyInput").value.trim();
      
      if (key) {
        localStorage.setItem("gemini_api_key", key);
      } else {
        localStorage.removeItem("gemini_api_key");
      }

      try {
        await fetch("/api/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ gemini_api_key: key })
        });
        showToast("Gemini API Key saved permanently!");
        settingsModal.classList.remove("active");
        setTimeout(() => window.location.reload(), 500);
      } catch (err) {
        showToast("Saved in browser storage!");
        settingsModal.classList.remove("active");
        setTimeout(() => window.location.reload(), 500);
      }
    });
  }

  // Copy review URL
  window.copyReviewUrl = (slug, payload) => {
    const param = payload ? `?d=${payload}` : "";
    const fullUrl = `${window.location.origin}/r/${slug}${param}`;
    copyToClipboard(fullUrl);
    showToast("Review page link copied to clipboard!");
  };

  window.copyQrModalLink = () => {
    const input = document.getElementById("qrModalLinkInput");
    copyToClipboard(input.value);
    showToast("Copied to clipboard!");
  };
});

function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text);
  } else {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-999999px";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    document.execCommand("copy");
    textArea.remove();
  }
}

function showToast(message) {
  let toast = document.getElementById("globalToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "globalToast";
    toast.className = "toast-msg";
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>✓</span> <span>${message}</span>`;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 2800);
}

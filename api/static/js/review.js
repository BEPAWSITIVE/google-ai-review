// Customer Mobile Review Experience JS
document.addEventListener("DOMContentLoaded", () => {
  const slug = window.CLIENT_SLUG;
  const googleReviewUrl = window.GOOGLE_REVIEW_URL;
  
  const reviewsContainer = document.getElementById("revertCardsList");
  const regenerateBtn = document.getElementById("regenerateBtn");
  const customTextArea = document.getElementById("customReviewText");
  const btnProceed = document.getElementById("btnProceed");
  const btnCopyDock = document.getElementById("btnCopyDock");
  const tagChips = document.querySelectorAll(".tag-chip");
  const aiBadge = document.getElementById("aiStatusBadge");

  let activeReviewText = "";
  let selectedTags = [];

  // Toggle highlight tag chips
  tagChips.forEach(chip => {
    chip.addEventListener("click", () => {
      chip.classList.toggle("active");
      const tag = chip.getAttribute("data-tag");
      if (chip.classList.contains("active")) {
        if (!selectedTags.includes(tag)) selectedTags.push(tag);
      } else {
        selectedTags = selectedTags.filter(t => t !== tag);
      }
    });
  });

  // Fetch reviews from backend
  async function fetchReviews() {
    reviewsContainer.innerHTML = `
      <div style="text-align: center; padding: 2.5rem 1rem; color: #64748b;">
        <div class="spinner spinner-dark" style="width: 28px; height: 28px; margin-bottom: 0.75rem;"></div>
        <p style="font-weight: 600; font-size: 0.95rem;">Crafting tailored review options with AI...</p>
        <p style="font-size: 0.8rem; margin-top: 0.25rem;">Personalizing keywords for best visibility</p>
      </div>
    `;
    regenerateBtn.disabled = true;
    regenerateBtn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; border-top-color: #0f172a;"></span> Regenerating...`;

    try {
      const res = await fetch("/api/generate-reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: slug,
          d: window.CLIENT_PAYLOAD || null,
          selected_tags: selectedTags,
          api_key: localStorage.getItem("gemini_api_key") || null
        })
      });

      if (!res.ok) throw new Error("Failed to fetch review options");
      const data = await res.json();
      renderReviews(data.reviews || []);
      
      if (aiBadge) {
        if (data.source === "gemini_ai") {
          aiBadge.innerHTML = `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981; margin-right:4px;"></span> Powered by Gemini AI`;
          aiBadge.title = "Generated live via Google Gemini API";
        } else {
          aiBadge.innerHTML = `✨ Smart Keyword Templates`;
          aiBadge.title = data.message || "Using smart templates";
        }
      }
    } catch (err) {
      reviewsContainer.innerHTML = `
        <div style="background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; padding: 1rem; border-radius: 8px; text-align: center;">
          <p style="font-weight: 600;">Could not load review options</p>
          <p style="font-size: 0.85rem; margin-top: 0.35rem;">${err.message}</p>
          <button class="btn btn-secondary btn-sm" style="margin-top: 0.75rem;" onclick="window.fetchReviewsGlobal()">Try Again</button>
        </div>
      `;
    } finally {
      regenerateBtn.disabled = false;
      regenerateBtn.innerHTML = `🔄 Regenerate Options`;
    }
  }

  window.fetchReviewsGlobal = fetchReviews;

  // Render review cards
  function renderReviews(reviews) {
    if (!reviews || reviews.length === 0) {
      reviewsContainer.innerHTML = `<p style="text-align: center; color: #64748b;">No review options generated. Tap regenerate to try again.</p>`;
      return;
    }

    reviewsContainer.innerHTML = "";
    reviews.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = `revert-card ${index === 0 ? "selected" : ""}`;
      card.setAttribute("data-id", item.id);

      const tagLabel = item.tag || "Review Option";
      
      card.innerHTML = `
        <div class="revert-card-top">
          <span class="revert-style-tag">${escapeHtml(tagLabel)}</span>
          <button class="copy-badge-btn" type="button" title="Copy this review">
            📋 Copy
          </button>
        </div>
        <div class="revert-text">${escapeHtml(item.text)}</div>
      `;

      // Card click event
      card.addEventListener("click", (e) => {
        selectReview(card, item.text, true);
      });

      reviewsContainer.appendChild(card);

      // Auto-select first item
      if (index === 0) {
        selectReview(card, item.text, false);
      }
    });
  }

  function selectReview(cardElement, text, shouldNotifyCopy) {
    document.querySelectorAll(".revert-card").forEach(c => c.classList.remove("selected"));
    cardElement.classList.add("selected");
    activeReviewText = text;
    if (customTextArea) {
      customTextArea.value = text;
    }
    
    // Copy to clipboard
    copyToClipboard(text);
    if (shouldNotifyCopy) {
      showToast("Selected & copied to clipboard! Ready to paste.");
    }
  }

  // Handle textarea manual edits
  if (customTextArea) {
    customTextArea.addEventListener("input", (e) => {
      activeReviewText = e.target.value;
    });
  }

  // Copy button in dock
  if (btnCopyDock) {
    btnCopyDock.addEventListener("click", () => {
      const textToCopy = customTextArea ? customTextArea.value : activeReviewText;
      if (!textToCopy) {
        showToast("Please select a review first!");
        return;
      }
      copyToClipboard(textToCopy);
      showToast("Copied to clipboard! Ready to paste.");
    });
  }

  // Next: Post on Google Review button
  if (btnProceed) {
    btnProceed.addEventListener("click", (e) => {
      e.preventDefault();
      const textToCopy = customTextArea ? customTextArea.value : activeReviewText;
      if (textToCopy) {
        copyToClipboard(textToCopy);
      }

      showToast("Copied! Opening Google Reviews — just paste and post ⭐⭐⭐⭐⭐");

      // Give a tiny delay for clipboard write to settle, then open Google Review page
      setTimeout(() => {
        window.open(googleReviewUrl, "_blank", "noopener,noreferrer");
      }, 350);
    });
  }

  // Regenerate button click
  if (regenerateBtn) {
    regenerateBtn.addEventListener("click", () => {
      fetchReviews();
    });
  }

  // Initial load
  fetchReviews();
});

function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-999999px";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  try {
    document.execCommand("copy");
  } catch (err) {
    console.error("Copy failed", err);
  }
  textArea.remove();
}

function showToast(message) {
  let toast = document.getElementById("reviewToast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "reviewToast";
    toast.className = "toast-msg";
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>✓</span> <span>${message}</span>`;
  toast.classList.add("show");
  setTimeout(() => {
    toast.classList.remove("show");
  }, 3200);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}

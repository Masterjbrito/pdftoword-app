(function () {
  "use strict";

  const cfg = window.APP_CONFIG || {};
  const maxUploadMb = Number(cfg.maxUploadMb || 40);
  const maxBytes = maxUploadMb * 1024 * 1024;

  function bytesToMb(value) {
    return (value / (1024 * 1024)).toFixed(1);
  }

  function setupFormEnhancements() {
    const forms = document.querySelectorAll("form");
    forms.forEach((form) => {
      form.addEventListener("submit", (event) => {
        const fileInputs = form.querySelectorAll('input[type="file"]');
        for (const input of fileInputs) {
          for (const file of input.files || []) {
            if (file.size > maxBytes) {
              event.preventDefault();
              alert(
                "O ficheiro '" +
                  file.name +
                  "' excede o limite de " +
                  maxUploadMb +
                  "MB (atual: " +
                  bytesToMb(file.size) +
                  "MB)."
              );
              return;
            }
          }
        }

        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitButton) {
          submitButton.disabled = true;
          if (submitButton.tagName === "BUTTON") {
            submitButton.dataset.originalText = submitButton.textContent || "";
            submitButton.textContent = "A processar...";
          }
        }

        form.classList.add("form-busy");
        let status = form.querySelector(".form-status");
        if (!status) {
          status = document.createElement("p");
          status.className = "hint form-status";
          status.textContent = "Pedido enviado. Aguarda o download automático.";
          form.appendChild(status);
        }
      });
    });
  }

  function setupSplitFormBehavior() {
    const splitForms = document.querySelectorAll('form[action="/tools/split-pdf"]');
    splitForms.forEach((form) => {
      const mode = form.querySelector('select[name="split_mode"]');
      const start = form.querySelector('input[name="start_page"]');
      const end = form.querySelector('input[name="end_page"]');
      if (!mode || !start || !end) {
        return;
      }
      const apply = () => {
        const isRange = mode.value === "range";
        start.required = isRange;
        end.required = isRange;
        start.disabled = !isRange;
        end.disabled = !isRange;
      };
      mode.addEventListener("change", apply);
      apply();
    });
  }

  function setupMobileCategoryMenu() {
    const wrappers = document.querySelectorAll(".hover-tools");
    wrappers.forEach((wrapper) => {
      if (wrapper.querySelector(".js-category-toggle")) {
        return;
      }
      const panel = wrapper.querySelector(".hover-panel");
      if (!panel) {
        return;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.className = "js-category-toggle";
      button.setAttribute("aria-expanded", "false");
      button.textContent = "Open categories";
      button.addEventListener("click", () => {
        const open = wrapper.classList.toggle("is-open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
      });
      wrapper.insertBefore(button, panel);
    });
  }

  function setupAds() {
    const adContainers = document.querySelectorAll(".ad-top, .ad-box");
    adContainers.forEach((box, index) => {
      if (cfg.adsenseClient && !box.querySelector(".adsbygoogle")) {
        const ad = document.createElement("ins");
        ad.className = "adsbygoogle";
        ad.style.display = "block";
        ad.setAttribute("data-ad-client", cfg.adsenseClient);
        if (index === 0 && cfg.adsenseSlotTop) {
          ad.setAttribute("data-ad-slot", cfg.adsenseSlotTop);
        } else if (cfg.adsenseSlotInline) {
          ad.setAttribute("data-ad-slot", cfg.adsenseSlotInline);
        }
        ad.setAttribute("data-ad-format", "auto");
        ad.setAttribute("data-full-width-responsive", "true");
        box.appendChild(ad);
        try {
          (window.adsbygoogle = window.adsbygoogle || []).push({});
        } catch (_error) {
          // Ignore ad-render errors to avoid blocking user interactions.
        }
      } else if (!cfg.adsenseClient && !box.querySelector(".ad-ready-note")) {
        const note = document.createElement("small");
        note.className = "ad-ready-note";
        note.textContent = "AdSense pronto: define ADSENSE_CLIENT no servidor.";
        box.appendChild(note);
      }
    });
  }

  function setupAroundRunningAds() {
    const forms = document.querySelectorAll(".tool-card form, .card form");
    forms.forEach((form, index) => {
      if (!form.parentElement || form.parentElement.querySelector(".ad-run-around")) {
        return;
      }
      const beforeAd = document.createElement("section");
      beforeAd.className = "ad-box ad-run-around";
      beforeAd.innerHTML = "<p>Ad Around Tool Run</p>";

      const afterAd = document.createElement("section");
      afterAd.className = "ad-box ad-run-around";
      afterAd.innerHTML = "<p>Ad Around Tool Result</p>";

      form.parentElement.insertBefore(beforeAd, form);
      if (form.nextSibling) {
        form.parentElement.insertBefore(afterAd, form.nextSibling);
      } else {
        form.parentElement.appendChild(afterAd);
      }

      if (cfg.adsenseClient) {
        setupAds();
      } else if (index > 2) {
        afterAd.style.display = "none";
      }
    });
  }

  function setupMobileStickyAd() {
    if (!cfg.adsenseClient) {
      return;
    }
    if (document.querySelector(".mobile-ad-sticky")) {
      return;
    }
    const sticky = document.createElement("aside");
    sticky.className = "mobile-ad-sticky";
    sticky.innerHTML = '<section class="ad-box"><p>Mobile Ad Slot</p></section>';
    document.body.appendChild(sticky);
    setupAds();
  }

  setupFormEnhancements();
  setupSplitFormBehavior();
  setupMobileCategoryMenu();
  setupAroundRunningAds();
  setupAds();
  setupMobileStickyAd();
})();

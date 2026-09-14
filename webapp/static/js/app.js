(() => {
  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} بایت`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} کیلوبایت`;
    return `${(bytes / 1024 / 1024).toFixed(1)} مگابایت`;
  };

  document.querySelectorAll("[data-process-form]").forEach((form) => {
    const zone = form.querySelector("[data-drop-zone]");
    const input = form.querySelector("[data-file-input]");
    const title = form.querySelector("[data-file-title]");
    const meta = form.querySelector("[data-file-meta]");
    const button = form.querySelector("[data-submit-button]");
    const state = form.querySelector("[data-process-state]");
    const stateTitle = form.querySelector("[data-state-title]");
    if (!zone || !input) return;

    const showFile = () => {
      const file = input.files && input.files[0];
      if (!file) return;
      title.textContent = file.name;
      meta.textContent = formatSize(file.size);
      zone.classList.add("has-file");
    };

    input.addEventListener("change", showFile);
    ["dragenter", "dragover"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach((eventName) => {
      zone.addEventListener(eventName, (event) => {
        event.preventDefault();
        zone.classList.remove("is-dragging");
      });
    });
    zone.addEventListener("drop", (event) => {
      const files = event.dataTransfer && event.dataTransfer.files;
      if (!files || !files.length) return;
      const transfer = new DataTransfer();
      transfer.items.add(files[0]);
      input.files = transfer.files;
      showFile();
    });

    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
        return;
      }
      button.disabled = true;
      button.querySelector("span").textContent = "در حال پردازش…";
      state.hidden = false;
      const states = ["در حال بررسی فایل…", "در حال آماده‌سازی مدل…", "پردازش صدا در حال انجام است…", "در حال آماده‌سازی خروجی…"];
      let index = 0;
      window.setInterval(() => {
        index = Math.min(index + 1, states.length - 1);
        stateTitle.textContent = states[index];
      }, 4500);
    });
  });
})();

// Mobile nav toggle
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".nav-toggle");
  const mobileNav = document.querySelector(".mobile-nav");
  if (toggle && mobileNav) {
    toggle.addEventListener("click", () => {
      mobileNav.classList.toggle("open");
    });
  }

  // FAQ accordion
  document.querySelectorAll(".faq-item").forEach((item) => {
    const q = item.querySelector(".faq-q");
    q.addEventListener("click", () => {
      const isOpen = item.classList.contains("open");
      document.querySelectorAll(".faq-item").forEach((i) => i.classList.remove("open"));
      if (!isOpen) item.classList.add("open");
    });
  });

  // Pricing billing toggle
  const switchBtn = document.querySelector(".switch");
  if (switchBtn) {
    const monthlyLabel = document.querySelector(".label-monthly");
    const annualLabel = document.querySelector(".label-annual");
    const amounts = document.querySelectorAll("[data-monthly]");
    switchBtn.addEventListener("click", () => {
      const isOn = switchBtn.classList.toggle("on");
      monthlyLabel.classList.toggle("active", !isOn);
      annualLabel.classList.toggle("active", isOn);
      amounts.forEach((el) => {
        el.textContent = isOn ? el.dataset.annual : el.dataset.monthly;
      });
    });
  }

  // Demo request form (static demo — no backend)
  const demoForm = document.querySelector("#demo-form");
  if (demoForm) {
    demoForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const btn = demoForm.querySelector("button[type=submit]");
      btn.textContent = "Request received ✓";
      btn.disabled = true;
      demoForm.reset();
    });
  }
});

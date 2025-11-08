function qs(sel, root) {
  return (root || document).querySelector(sel);
}
function qsa(sel, root) {
  return Array.from((root || document).querySelectorAll(sel));
}

function showToast(message, kind = "success", timeout = 3500) {
  const toast = qs("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${kind}`;
  requestAnimationFrame(() => {
    toast.classList.add("show");
  });
  window.clearTimeout(showToast._t);
  showToast._t = window.setTimeout(() => {
    toast.classList.remove("show");
  }, timeout);
}

function maskPhoneInput(input) {
  function clean(v) {
    return (v || "").replace(/[^\d]/g, "");
  }
  function format(digits) {
    // +7 (XXX) XXX-XX-XX
    const d = digits.startsWith("8") ? "7" + digits.slice(1) : digits;
    const a = d.slice(0, 1) || "7";
    const b = d.slice(1, 4);
    const c = d.slice(4, 7);
    const e = d.slice(7, 9);
    const f = d.slice(9, 11);
    let out = `+${a}`;
    if (b) out += ` (${b}`;
    if (b && b.length === 3) out += `)`;
    if (c) out += ` ${c}`;
    if (e) out += `-${e}`;
    if (f) out += `-${f}`;
    return out;
  }
  input.addEventListener("input", () => {
    const digits = clean(input.value);
    input.value = format(digits);
  });
  input.addEventListener("blur", () => {
    if (clean(input.value).length < 11) {
      input.dataset.invalid = "1";
    } else {
      delete input.dataset.invalid;
    }
  });
}

function bindSmoothScroll() {
  qsa('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      if (!href || href === "#" || href.length === 1) return;
      const target = qs(href);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function bindForm() {
  const form = qs("#requestForm");
  if (!form) return;
  const phoneInput = qs("#phone", form);
  if (phoneInput) maskPhoneInput(phoneInput);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const submitBtn = qs("#submitBtn", form);
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    const name = (payload.name || "").trim();
    const phone = (payload.phone || "").trim();
    if (!name || !phone) {
      showToast("Заполните имя и телефон", "error");
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = "Отправка...";
    try {
      const res = await fetch("/api/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) throw new Error(data.message || "Ошибка");
      form.reset();
      showToast(data.message || "Заявка отправлена", "success");
    } catch (err) {
      console.error(err);
      showToast("Не удалось отправить заявку. Попробуйте позже.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Отправить заявку";
    }
  });
}

function bindHeaderScroll() {
  const header = qs(".site-header");
  if (!header) return;
  
  // Проверяем, не на главной странице ли мы
  const isHomePage = window.location.pathname === "/" || window.location.pathname === "/#";
  const body = document.body;
  const isOtherPage = body.classList.contains("contacts-page") || body.classList.contains("about-page");
  
  function updateHeader() {
    if (isOtherPage) {
      // На других страницах шапка всегда белая
      header.classList.add("scrolled");
    } else if (isHomePage) {
      // На главной странице шапка прозрачная, становится белой при скролле
      const scrolled = window.scrollY > 50;
      if (scrolled) {
        header.classList.add("scrolled");
      } else {
        header.classList.remove("scrolled");
      }
    } else {
      // Для других страниц тоже белая
      header.classList.add("scrolled");
    }
  }
  
  updateHeader();
  if (!isOtherPage && isHomePage) {
    window.addEventListener("scroll", updateHeader, { passive: true });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  bindSmoothScroll();
  bindForm();
  bindHeaderScroll();
});



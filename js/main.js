/* ============================================================
   Mr.Video 传媒 — 交互脚本
   依赖原生 JS，无第三方库。功能：
   1) 导航毛玻璃 + 滚动高亮当前板块
   2) 锚点平滑滚动（兼顾固定头部偏移）
   3) 手机端汉堡 / 全屏抽屉菜单
   4) Hero 轮播（自动播放 / 圆点 / 悬停暂停）
   5) IntersectionObserver 滚动淡入
   6) 愿景数字滚动计数
   7) 案例无刷新筛选
   8) 留言表单校验 + 成功提示（接口 TODO）
   ============================================================ */

(function () {
  "use strict";

  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1) 导航毛玻璃 + 滚动高亮 ---------- */
  const header = document.querySelector(".site-header");
  const navLinks = Array.from(document.querySelectorAll(".main-nav a"));
  const sections = navLinks
    .map((a) => document.querySelector(a.getAttribute("href")))
    .filter(Boolean);

  function onScroll() {
    // 毛玻璃
    if (window.scrollY > 40) header.classList.add("scrolled");
    else header.classList.remove("scrolled");

    // 当前板块高亮
    const offset = 120;
    let currentId = sections.length ? sections[0].id : null;
    for (const sec of sections) {
      if (sec.getBoundingClientRect().top <= offset) currentId = sec.id;
    }
    navLinks.forEach((a) => {
      a.classList.toggle("active", a.getAttribute("href") === "#" + currentId);
    });
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---------- 2) 锚点平滑滚动（含固定头部偏移） ---------- */
  function smoothTo(target) {
    const el = typeof target === "string" ? document.querySelector(target) : target;
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 70;
    window.scrollTo({ top, behavior: prefersReduced ? "auto" : "smooth" });
  }
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      if (href.length > 1 && document.querySelector(href)) {
        e.preventDefault();
        smoothTo(href);
        closeDrawer();
      } else if (href === "#top") {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: prefersReduced ? "auto" : "smooth" });
        closeDrawer();
      }
    });
  });

  /* ---------- 3) 手机端抽屉菜单 ---------- */
  const hamburger = document.getElementById("hamburger");
  const drawer = document.getElementById("drawer");
  const drawerOverlay = document.getElementById("drawerOverlay");
  const drawerClose = document.getElementById("drawerClose");

  function openDrawer() {
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    drawerOverlay.classList.add("show");
    hamburger.classList.add("open");
    hamburger.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }
  function closeDrawer() {
    if (!drawer.classList.contains("open")) return;
    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    drawerOverlay.classList.remove("show");
    hamburger.classList.remove("open");
    hamburger.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }
  if (hamburger) hamburger.addEventListener("click", openDrawer);
  if (drawerClose) drawerClose.addEventListener("click", closeDrawer);
  if (drawerOverlay) drawerOverlay.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  /* ---------- 4) Hero 轮播 ---------- */
  const slides = Array.from(document.querySelectorAll(".hero-slide"));
  const dotsWrap = document.getElementById("heroDots");
  const heroSection = document.querySelector(".hero");
  let current = 0;
  let timer = null;
  const INTERVAL = 6000;

  if (slides.length > 1 && dotsWrap) {
    slides.forEach((_, i) => {
      const dot = document.createElement("button");
      dot.setAttribute("role", "tab");
      dot.setAttribute("aria-label", "切换到第 " + (i + 1) + " 张");
      if (i === 0) dot.classList.add("active");
      dot.addEventListener("click", () => goTo(i));
      dotsWrap.appendChild(dot);
    });
    const dots = Array.from(dotsWrap.children);

    function goTo(i) {
      slides[current].classList.remove("is-active");
      dots[current].classList.remove("active");
      current = (i + slides.length) % slides.length;
      slides[current].classList.add("is-active");
      dots[current].classList.add("active");
    }
    function next() { goTo(current + 1); }
    function start() { if (!prefersReduced) timer = setInterval(next, INTERVAL); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }

    if (heroSection) {
      heroSection.addEventListener("mouseenter", stop);
      heroSection.addEventListener("mouseleave", start);
    }
    start();
  }

  /* ---------- 5) 滚动淡入 ---------- */
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !prefersReduced) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            en.target.classList.add("in");
            io.unobserve(en.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("in"));
  }

  /* ---------- 6) 愿景数字计数 ---------- */
  const statNums = document.querySelectorAll(".stat-num");
  function animateCount(el) {
    const target = parseInt(el.getAttribute("data-target"), 10) || 0;
    const suffix = el.getAttribute("data-suffix") || "";
    if (prefersReduced) { el.textContent = target.toLocaleString() + suffix; return; }
    const duration = 1600;
    const startTs = performance.now();
    function tick(now) {
      const p = Math.min((now - startTs) / duration, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - p, 3);
      const val = Math.floor(eased * target);
      el.textContent = val.toLocaleString() + suffix;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = target.toLocaleString() + suffix;
    }
    requestAnimationFrame(tick);
  }
  if ("IntersectionObserver" in window) {
    const countIo = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) { animateCount(en.target); countIo.unobserve(en.target); }
        });
      },
      { threshold: 0.5 }
    );
    statNums.forEach((el) => countIo.observe(el));
  } else {
    statNums.forEach((el) => animateCount(el));
  }

  /* ---------- 7) 案例筛选 ---------- */
  const filterBtns = document.querySelectorAll(".filter-btn");
  const caseCards = document.querySelectorAll(".case-card");
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      const f = btn.getAttribute("data-filter");
      caseCards.forEach((card) => {
        const show = f === "all" || card.getAttribute("data-cat") === f;
        card.classList.toggle("hide", !show);
      });
    });
  });

  /* ---------- 8) 留言表单校验 ---------- */
  const form = document.getElementById("contactForm");
  const hint = document.getElementById("formHint");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = form.querySelector("#name");
      const phone = form.querySelector("#phone");
      let ok = true;

      [name, phone].forEach((inp) => inp.classList.remove("invalid"));

      if (!name.value.trim()) { name.classList.add("invalid"); ok = false; }

      // 手机号格式：至少 7 位数字，允许 + 与空格（兼容国际号码）
      const phoneOk = /^[+\d][\d\s-]{6,}$/.test(phone.value.trim());
      if (!phoneOk) { phone.classList.add("invalid"); ok = false; }

      if (!ok) {
        hint.textContent = "请填写必填项，并确保电话格式正确（如 +95 9xxxxxxx）。";
        hint.className = "form-hint err";
        return;
      }

      const data = {
        name: name.value.trim(),
        phone: phone.value.trim(),
        need: form.querySelector("#need").value,
        message: form.querySelector("#message").value.trim(),
      };

      // TODO: 接入表单接收接口（后端 / 第三方表单服务）
      // 示例：
      // fetch('https://your-api.example.com/lead', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(data)
      // }).then(...)

      hint.textContent = "提交成功！我们会尽快与您联系。";
      hint.className = "form-hint ok";
      form.reset();
      setTimeout(() => { hint.textContent = ""; hint.className = "form-hint"; }, 4000);
    });
  }
})();

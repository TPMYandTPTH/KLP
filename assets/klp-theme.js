/* ==========================================================================
   KLP — "Boarding Soft" shared behaviours
   Mobile menu, FAQ accordion, back-to-top, scroll reveal.
   Vanilla JS, no dependencies. Safe to load on every page.
   ========================================================================== */

(function () {
  'use strict';

  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- mobile menu ----------------------------------------------------- */

  function initMobileMenu() {
    var toggle = document.getElementById('mobileToggle');
    var menu = document.getElementById('mobileMenu');
    if (!toggle || !menu) return;

    function setOpen(open) {
      toggle.classList.toggle('active', open);
      menu.classList.toggle('active', open);
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
    }

    toggle.addEventListener('click', function () {
      setOpen(!menu.classList.contains('active'));
    });

    // Close when a destination is chosen, or on Escape.
    menu.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('active')) {
        setOpen(false);
        toggle.focus();
      }
    });
  }

  /* ---- FAQ accordion --------------------------------------------------- */

  function initFaq() {
    var items = document.querySelectorAll('.faq-item');
    Array.prototype.forEach.call(items, function (item) {
      var question = item.querySelector('.faq-question');
      var answer = item.querySelector('.faq-answer');
      if (!question || !answer) return;

      question.setAttribute('aria-expanded', 'false');

      question.addEventListener('click', function () {
        var isOpen = item.classList.contains('open');

        // Single-open accordion: collapse any sibling first.
        Array.prototype.forEach.call(items, function (other) {
          if (other === item) return;
          other.classList.remove('open');
          var otherAnswer = other.querySelector('.faq-answer');
          var otherQuestion = other.querySelector('.faq-question');
          if (otherAnswer) otherAnswer.style.maxHeight = null;
          if (otherQuestion) otherQuestion.setAttribute('aria-expanded', 'false');
        });

        item.classList.toggle('open', !isOpen);
        question.setAttribute('aria-expanded', !isOpen ? 'true' : 'false');
        answer.style.maxHeight = !isOpen ? answer.scrollHeight + 'px' : null;
      });
    });

    // An open panel must not clip when the viewport reflows.
    window.addEventListener('resize', function () {
      var open = document.querySelector('.faq-item.open .faq-answer');
      if (open) open.style.maxHeight = open.scrollHeight + 'px';
    });
  }

  /* ---- back to top ----------------------------------------------------- */

  function initBackToTop() {
    var button = document.getElementById('backToTop');
    if (!button) return;

    var ticking = false;
    function update() {
      button.classList.toggle('visible', window.scrollY > 500);
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }, { passive: true });
    update();

    button.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  }

  /* ---- scroll reveal --------------------------------------------------- */

  function initReveal() {
    var targets = document.querySelectorAll('[data-reveal]');
    if (!targets.length) return;

    // Without IntersectionObserver, or with reduced motion, show everything.
    if (reduceMotion || !('IntersectionObserver' in window)) {
      Array.prototype.forEach.call(targets, function (el) {
        el.style.opacity = '';
        el.style.transform = '';
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'none';
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px' });

    Array.prototype.forEach.call(targets, function (el) {
      el.style.opacity = '0';
      el.style.transform = 'translateY(16px)';
      el.style.transition = 'opacity .5s cubic-bezier(.4,0,.2,1), transform .5s cubic-bezier(.4,0,.2,1)';
      observer.observe(el);
    });
  }

  /* ---- boot ------------------------------------------------------------ */

  function init() {
    initMobileMenu();
    initFaq();
    initBackToTop();
    initReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

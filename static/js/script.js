/* ============================================================
   AVENTRO EDUCATIONAL TECH SOLUTIONS — script.js
   ============================================================ */

   'use strict';

   /* ============================================================
      2. STICKY NAV — glassmorphism on scroll
      ============================================================ */
   (function initNav() {
     const navbar = document.getElementById('navbar');
     if (!navbar) return;
   
     const SCROLL_THRESHOLD = 60;
   
     const handleScroll = () => {
       if (window.scrollY > SCROLL_THRESHOLD) {
         navbar.classList.add('scrolled');
       } else {
         navbar.classList.remove('scrolled');
       }
     };
   
     window.addEventListener('scroll', handleScroll, { passive: true });
     handleScroll(); // run once on load
   })();
   
   /* ============================================================
      3. HAMBURGER MENU (mobile)
      ============================================================ */
   (function initHamburger() {
     const hamburger = document.getElementById('hamburger');
     const navLinks  = document.getElementById('nav-links');
     const navbar    = document.getElementById('navbar');
     if (!hamburger || !navLinks || !navbar) return;
   
     hamburger.addEventListener('click', () => {
       const isOpen = navLinks.classList.toggle('open');
       hamburger.classList.toggle('open', isOpen);
       hamburger.setAttribute('aria-expanded', isOpen);
     });
   
     // Close menu when a link is clicked
     navLinks.querySelectorAll('.nav-link').forEach((link) => {
       link.addEventListener('click', () => {
         navLinks.classList.remove('open');
         hamburger.classList.remove('open');
         hamburger.setAttribute('aria-expanded', 'false');
       });
     });
   
     // Close on outside click
     document.addEventListener('click', (e) => {
       if (!navbar.contains(e.target)) {
         navLinks.classList.remove('open');
         hamburger.classList.remove('open');
       }
     });
   })();
   
   /* ============================================================
      4. SCROLL ANIMATIONS — Intersection Observer
      Fade-in + slide-up on enter, subtle fade-out on exit.
      ============================================================ */
   (function initScrollAnimations() {
     const revealEls = document.querySelectorAll('.reveal');
     if (!revealEls.length) return;
   
     // Stagger delays from data attributes
     revealEls.forEach((el) => {
       const delay = el.dataset.delay;
       if (delay) {
         el.style.transitionDelay = delay + 'ms';
       }
     });
   
     const observerOptions = {
       threshold: 0.12,
       rootMargin: '0px 0px -60px 0px',
     };
   
     const observer = new IntersectionObserver((entries) => {
       entries.forEach((entry) => {
         const el = entry.target;
         if (entry.isIntersecting) {
           el.classList.add('visible');
           el.classList.remove('exiting');
         } else {
           // Only apply exit animation if element has been visible before
           if (el.classList.contains('visible')) {
             el.classList.add('exiting');
             el.classList.remove('visible');
           }
         }
       });
     }, observerOptions);
   
     revealEls.forEach((el) => observer.observe(el));
   })();
   
   /* ============================================================
      5. ACTIVE NAV LINK — highlight based on scroll position
      ============================================================ */
   (function initActiveNav() {
     const sections = document.querySelectorAll('section[id], footer[id]');
     const navLinks = document.querySelectorAll('.nav-link');
     if (!sections.length || !navLinks.length) return;
   
     const observer = new IntersectionObserver((entries) => {
       entries.forEach((entry) => {
         if (entry.isIntersecting) {
           const id = entry.target.getAttribute('id');
           navLinks.forEach((link) => {
             link.classList.toggle(
               'active',
               link.getAttribute('href') === '#' + id
             );
           });
         }
       });
     }, { threshold: 0.4 });
   
     sections.forEach((section) => observer.observe(section));
   })();
   
   /* ============================================================
      6. SMOOTH ANCHOR SCROLL with navbar offset
      ============================================================ */
   (function initSmoothScroll() {
    const NAV_HEIGHT = 0;
   
     document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
       anchor.addEventListener('click', (e) => {
        // If this anchor is meant to open an expandable panel, let that handler work.
        // Otherwise the browser jump/smooth scroll can target a hidden element.
        const openCourseId = anchor.dataset.openCourse;
        if (openCourseId) {
          e.preventDefault();
          return;
        }

         const targetId = anchor.getAttribute('href').slice(1);
         if (!targetId) return;
         const target = document.getElementById(targetId);
         if (!target) return;
   
         e.preventDefault();

        // If WhatsApp chat anchor, also try to open the widget
        if (targetId === 'whatsapp-chat') {
          const widgetRoot = document.querySelector('.elfsight-app-9c9a18af-2414-4caf-8795-f4992d4823e8');
          if (widgetRoot) {
            widgetRoot.click();
          }
        }

         const top = target.getBoundingClientRect().top + window.scrollY - NAV_HEIGHT;
         window.scrollTo({ top, behavior: 'smooth' });
       });
     });
   })();
   
   /* ============================================================
      7. DIAGRAM NODE PULSE — subtle attention animation
      ============================================================ */

   
   /* ============================================================
      8. SCROLL PROGRESS INDICATOR
      ============================================================ */
   (function initScrollProgress() {
     const bar = document.createElement('div');
     bar.id = 'scroll-progress';
     Object.assign(bar.style, {
       position: 'fixed',
       top: '0',
       left: '0',
       height: '3px',
       width: '0%',
       background: 'linear-gradient(90deg, #003366, #0066cc)',
       zIndex: '2000',
       transition: 'width 0.1s linear',
       pointerEvents: 'none',
     });
     document.body.prepend(bar);
   
     window.addEventListener('scroll', () => {
       const scrolled = window.scrollY;
       const total = document.documentElement.scrollHeight - window.innerHeight;
       const pct = total > 0 ? (scrolled / total) * 100 : 0;
       bar.style.width = pct.toFixed(2) + '%';
     }, { passive: true });
   })();

  /* ============================================================
     9. COURSE DETAIL PANELS (expand/collapse)
     - Gen AI program
     - Data Analytics program
     - Webinars detail
     ============================================================ */
  (function initCourseDetailPanels() {
    const openTriggers = document.querySelectorAll('[data-open-course]');
    const closeButtons = document.querySelectorAll('[data-close-course]');

    if (!openTriggers.length || !closeButtons.length) return;

    const openPanel = (panelId) => {
      const panel = document.getElementById(panelId);
      if (!panel) return;
      panel.hidden = false;
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    const closePanel = (panelId) => {
      const panel = document.getElementById(panelId);
      if (!panel) return;
      panel.hidden = true;
    };

    openTriggers.forEach((trigger) => {
      const panelId = trigger.dataset.openCourse;
      if (!panelId) return;
      trigger.addEventListener('click', (e) => {
        // Prevent default jump for anchors. (Smooth-scroll handler already skips data-open-course.)
        if (trigger.tagName === 'A') e.preventDefault();
        openPanel(panelId);
      });
    });

    closeButtons.forEach((btn) => {
      const panelId = btn.dataset.closeCourse;
      if (!panelId) return;
      btn.addEventListener('click', () => closePanel(panelId));
    });

    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      document.querySelectorAll('.course-detail-panel').forEach((panel) => {
        if (!panel.hidden) panel.hidden = true;
      });
    });
  })();



  /* ============================================================
     11. LENIS SMOOTH SCROLL
     ============================================================ */
  (function initLenis() {
    if (typeof Lenis === 'undefined') return;
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      direction: 'vertical',
      gestureDirection: 'vertical',
      smooth: true,
      mouseMultiplier: 1,
      smoothTouch: false,
      touchMultiplier: 2,
      infinite: false,
    });
    
    // Connect Lenis with scroll trigger / hash changes if needed
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener('click', (e) => {
        const targetId = anchor.getAttribute('href').slice(1);
        if (!targetId) return;
        const target = document.getElementById(targetId);
        if (!target) return;
        lenis.scrollTo(target);
      });
    });

    function raf(time) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);
  })();

  /* ============================================================
     10. SPLASH SCREEN TRANSITION & TIMING
     ============================================================ */
  (function initSplashScreen() {
    const splash = document.getElementById('splash-screen');
    if (!splash) return;

    // If already shown in session, the inline script has hidden it.
    // Double check here to be sure, and remove if necessary.
    if (sessionStorage.getItem('aventro_splash_shown')) {
      splash.remove();
      document.body.classList.remove('splash-active');
      return;
    }

    // Let the logo animation and letters animate, then trigger fade out
    const ANIMATION_DURATION = 2600; // time in ms before starting fade out
    
    setTimeout(() => {
      splash.classList.add('fade-out');
      document.body.classList.remove('splash-active');
      
      // Completely remove element from DOM after the transition is complete
      setTimeout(() => {
        splash.remove();
      }, 1000); // matches the CSS transition duration
      
      // Mark as shown in this session
      sessionStorage.setItem('aventro_splash_shown', 'true');
    }, ANIMATION_DURATION);
  })();
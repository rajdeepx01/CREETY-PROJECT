/**
 * Main Application Controller & UI Router
 */

class App {
  constructor() {
    this.init();
  }

  init() {
    this.initModals();
    this.initUserMenu();
    this.handleRouting();
    this.onAuthStateChanged();

    // Check for verification token in query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const verifyToken = urlParams.get('verify_token');
    if (verifyToken) {
      window.auth.verifyEmailToken(verifyToken);
      // Clean query param
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }

  handleRouting() {
    const path = window.location.pathname;
    
    if (path.startsWith('/u/') || path.startsWith('/profile/')) {
      const parts = path.split('/').filter(Boolean);
      const username = parts[1];
      if (username) {
        window.profile.renderPublicProfile(username);
        return;
      }
    }
  }

  onAuthStateChanged() {
    const isAuth = api.isAuthenticated();
    const guestNav = document.getElementById('guestNavActions');
    const authNav = document.getElementById('authNavActions');
    const guestBanner = document.getElementById('guestWelcomeBanner');
    const showcaseSection = document.getElementById('showcaseSection');

    if (isAuth) {
      if (guestNav) guestNav.style.display = 'none';
      if (authNav) authNav.style.display = 'flex';
      if (guestBanner) guestBanner.style.display = 'none';
      if (showcaseSection) showcaseSection.style.display = 'block';

      // Load Profile & Achievements
      window.profile.loadProfile();
      window.achievements.loadAchievements();
    } else {
      if (guestNav) guestNav.style.display = 'flex';
      if (authNav) authNav.style.display = 'none';
      
      const isPublicPath = window.location.pathname.startsWith('/u/');
      if (!isPublicPath) {
        if (guestBanner) guestBanner.style.display = 'block';
        if (showcaseSection) showcaseSection.style.display = 'none';
      }
    }
  }

  initModals() {
    // Click outside modal box to close
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          this.closeModal(overlay.id);
        }
      });
    });

    // Close buttons
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-overlay');
        if (modal) this.closeModal(modal.id);
      });
    });

    // ESC key to close active modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal-overlay.active');
        if (activeModal) this.closeModal(activeModal.id);
      }
    });

    // Guest Auth buttons
    const loginNavBtn = document.getElementById('navLoginBtn');
    const registerNavBtn = document.getElementById('navRegisterBtn');
    const heroGetStartedBtn = document.getElementById('heroGetStartedBtn');

    if (loginNavBtn) {
      loginNavBtn.addEventListener('click', () => {
        document.querySelector('[data-tab="login"]').click();
        this.openModal('authModal');
      });
    }

    if (registerNavBtn) {
      registerNavBtn.addEventListener('click', () => {
        document.querySelector('[data-tab="register"]').click();
        this.openModal('authModal');
      });
    }

    if (heroGetStartedBtn) {
      heroGetStartedBtn.addEventListener('click', () => {
        document.querySelector('[data-tab="register"]').click();
        this.openModal('authModal');
      });
    }
  }

  initUserMenu() {
    const menuBtn = document.getElementById('userMenuBtn');
    const dropdown = document.getElementById('userDropdownMenu');

    if (menuBtn && dropdown) {
      menuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('active');
      });

      document.addEventListener('click', () => {
        dropdown.classList.remove('active');
      });
    }

    const logoutBtn = document.getElementById('logoutDropdownBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        window.auth.logout();
      });
    }
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
      'success': '✅',
      'error': '❌',
      'info': 'ℹ️'
    };

    toast.innerHTML = `
      <span>${icons[type] || 'ℹ️'}</span>
      <div style="flex: 1;">${message}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});

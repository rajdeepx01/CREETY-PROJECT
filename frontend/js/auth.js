/**
 * Authentication & Security Manager
 */

class AuthManager {
  constructor() {
    this.pending2FAToken = null;
    this.initEventListeners();
  }

  initEventListeners() {
    // Auth Form Tabs Switcher (Login vs Register)
    const tabBtns = document.querySelectorAll('.auth-tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const targetTab = btn.dataset.tab;
        
        document.getElementById('loginFormContainer').style.display = targetTab === 'login' ? 'block' : 'none';
        document.getElementById('registerFormContainer').style.display = targetTab === 'register' ? 'block' : 'none';
      });
    });

    // Login Form Submit
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
      loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const identifier = document.getElementById('loginIdentifier').value.trim();
        const password = document.getElementById('loginPassword').value;
        const submitBtn = loginForm.querySelector('button[type="submit"]');

        try {
          submitBtn.disabled = true;
          submitBtn.innerText = 'Signing In...';

          const res = await api.post('/auth/login', {
            email_or_username: identifier,
            password: password
          });

          if (res.requires_2fa) {
            // Open 2FA Challenge Prompt
            this.pending2FAToken = res.temp_token;
            window.app.closeModal('authModal');
            window.app.openModal('twofaChallengeModal');
            return;
          }

          api.setSession(res.access_token, res.user);
          window.app.showToast('Welcome back, ' + res.user.full_name + '!', 'success');
          window.app.closeModal('authModal');
          window.app.onAuthStateChanged();
        } catch (err) {
          window.app.showToast(err.message, 'error');
        } finally {
          submitBtn.disabled = false;
          submitBtn.innerText = 'Sign In';
        }
      });
    }

    // Register Form Submit
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
      registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fullName = document.getElementById('regFullName').value.trim();
        const username = document.getElementById('regUsername').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        const submitBtn = registerForm.querySelector('button[type="submit"]');

        if (password.length < 8) {
          window.app.showToast('Password must be at least 8 characters.', 'error');
          return;
        }

        try {
          submitBtn.disabled = true;
          submitBtn.innerText = 'Creating Account...';

          const res = await api.post('/auth/register', {
            full_name: fullName,
            username: username,
            email: email,
            password: password
          });

          api.setSession(res.access_token, res.user);
          window.app.showToast('Account created successfully! Verification email sent.', 'success');
          window.app.closeModal('authModal');
          window.app.onAuthStateChanged();
        } catch (err) {
          window.app.showToast(err.message, 'error');
        } finally {
          submitBtn.disabled = false;
          submitBtn.innerText = 'Create Account';
        }
      });
    }

    // 2FA Challenge Code Submit
    const twofaChallengeForm = document.getElementById('twofaChallengeForm');
    if (twofaChallengeForm) {
      twofaChallengeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = document.getElementById('twofaCodeInput').value.trim();
        const backupCode = document.getElementById('twofaBackupCodeInput').value.trim();

        try {
          const res = await api.post('/auth/2fa/complete-login', {
            email_or_username: this.pending2FAToken,
            password: '',
            totp_code: code || null,
            backup_code: backupCode || null
          });

          api.setSession(res.access_token, res.user);
          window.app.showToast('2FA Verification successful!', 'success');
          window.app.closeModal('twofaChallengeModal');
          this.pending2FAToken = null;
          window.app.onAuthStateChanged();
        } catch (err) {
          window.app.showToast(err.message, 'error');
        }
      });
    }

    // Google OAuth 1-Click Demo
    const googleBtn = document.getElementById('googleOAuthBtn');
    if (googleBtn) {
      googleBtn.addEventListener('click', async () => {
        try {
          googleBtn.disabled = true;
          googleBtn.innerText = 'Connecting with Google...';

          const res = await api.post('/auth/oauth-login', {
            provider: 'google',
            email: 'alex.rivera@example.com',
            name: 'Alex Rivera',
            avatar_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
            provider_id: 'google_oauth_demo_123'
          });

          api.setSession(res.access_token, res.user);
          window.app.showToast('Logged in via Google OAuth Demo!', 'success');
          window.app.closeModal('authModal');
          window.app.onAuthStateChanged();
        } catch (err) {
          window.app.showToast(err.message, 'error');
        } finally {
          googleBtn.disabled = false;
          googleBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z"/><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/><path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12 0 14.5s.7 4.8 1.9 7.2l3.7-2.9z"/><path fill="#34A853" d="M12 23.5c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16.5C3.7 20.2 7.5 23.5 12 23.5z"/></svg>
            Continue with Google
          `;
        }
      });
    }

    // Setup 2FA Button Handler
    const setup2FABtn = document.getElementById('open2FASetupBtn');
    if (setup2FABtn) {
      setup2FABtn.addEventListener('click', () => this.start2FASetup());
    }

    // Enable 2FA Form Submit
    const enable2FAForm = document.getElementById('enable2FAForm');
    if (enable2FAForm) {
      enable2FAForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = document.getElementById('enable2FACodeInput').value.trim();
        try {
          await api.post('/auth/2fa/enable', { code });
          window.app.showToast('Two-Factor Authentication is now active!', 'success');
          window.app.closeModal('twofaSetupModal');
          // Refresh user profile
          window.profile.loadProfile();
        } catch (err) {
          window.app.showToast(err.message, 'error');
        }
      });
    }

    // Mailbox Inspector Modal Button
    const mailboxBtn = document.getElementById('mailboxBadgeBtn');
    if (mailboxBtn) {
      mailboxBtn.addEventListener('click', () => this.openMailboxModal());
    }
  }

  async start2FASetup() {
    try {
      const res = await api.get('/auth/2fa/setup');
      
      const qrImg = document.getElementById('twofaQrImage');
      const secretText = document.getElementById('twofaSecretCode');
      const backupList = document.getElementById('twofaBackupCodesList');

      qrImg.src = res.qr_code_base64;
      secretText.innerText = res.secret;

      backupList.innerHTML = res.backup_codes
        .map(code => `<div class="backup-code-item">${code}</div>`)
        .join('');

      window.app.openModal('twofaSetupModal');
    } catch (err) {
      window.app.showToast('Failed to initialize 2FA: ' + err.message, 'error');
    }
  }

  async openMailboxModal() {
    try {
      const res = await api.get('/auth/mailbox');
      const container = document.getElementById('mailboxListContainer');
      
      if (!res.emails || res.emails.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
            No outgoing emails sent yet. Register a new account to see verification emails!
          </div>
        `;
      } else {
        container.innerHTML = res.emails.map(mail => `
          <div style="background: rgba(255,255,255,0.04); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; margin-bottom: 0.75rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem; font-size: 0.8rem; color: var(--text-muted);">
              <span>To: <strong>${mail.to}</strong></span>
              <span>${new Date(mail.timestamp).toLocaleTimeString()}</span>
            </div>
            <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary); margin-bottom: 0.5rem;">
              ${mail.subject}
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.6rem;">
              <a href="${mail.verify_link}" class="btn btn-sm btn-primary" onclick="window.app.closeModal('mailboxModal');">
                1-Click Verify Link
              </a>
              <button class="btn btn-sm btn-secondary" onclick="navigator.clipboard.writeText('${mail.token}'); window.app.showToast('Token copied!', 'info');">
                Copy Token
              </button>
            </div>
          </div>
        `).join('');
      }

      window.app.openModal('mailboxModal');
    } catch (err) {
      window.app.showToast('Failed to load mailbox: ' + err.message, 'error');
    }
  }

  async verifyEmailToken(token) {
    try {
      await api.post('/auth/verify-email', { token });
      window.app.showToast('Your email has been verified successfully! 🎉', 'success');
      if (api.isAuthenticated()) {
        window.profile.loadProfile();
      }
    } catch (err) {
      window.app.showToast('Email verification failed: ' + err.message, 'error');
    }
  }

  async logout() {
    try {
      await api.post('/auth/logout', {});
    } catch (e) {
      // ignore
    }
    api.clearSession();
    window.app.showToast('Logged out successfully.', 'info');
    window.app.onAuthStateChanged();
  }
}

window.auth = new AuthManager();

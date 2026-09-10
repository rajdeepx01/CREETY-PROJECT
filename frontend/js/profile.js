/**
 * Profile & Showcase Portfolio Manager
 */

class ProfileManager {
  constructor() {
    this.profileData = null;
    this.isPublicMode = false;
    this.publicUsername = null;
    this.initEventListeners();
  }

  initEventListeners() {
    // Edit Profile Modal Open
    const editProfileBtn = document.getElementById('editProfileBtn');
    if (editProfileBtn) {
      editProfileBtn.addEventListener('click', () => this.openEditProfileModal());
    }

    // Profile Settings Form Submit
    const profileForm = document.getElementById('profileSettingsForm');
    if (profileForm) {
      profileForm.addEventListener('submit', (e) => this.handleProfileUpdate(e));
    }

    // Share Portfolio Button
    const shareBtn = document.getElementById('sharePortfolioBtn');
    if (shareBtn) {
      shareBtn.addEventListener('click', () => this.openShareModal());
    }

    // Copy Share Link Button
    const copyLinkBtn = document.getElementById('copyShareLinkBtn');
    if (copyLinkBtn) {
      copyLinkBtn.addEventListener('click', () => {
        const linkInput = document.getElementById('sharePortfolioUrlInput');
        navigator.clipboard.writeText(linkInput.value);
        window.app.showToast('Public portfolio link copied to clipboard! 📋', 'success');
      });
    }
  }

  async loadProfile() {
    if (!api.isAuthenticated()) return;

    try {
      const data = await api.get('/users/me');
      this.profileData = data;
      this.renderProfileHero(data);
    } catch (err) {
      console.error('Profile load error:', err);
    }
  }

  renderProfileHero(user) {
    document.getElementById('profileName').innerHTML = `
      ${user.full_name || user.username}
      ${user.is_verified ? '<span class="badge badge-verified" title="Verified Email">✓ Verified</span>' : ''}
      ${user.is_2fa_enabled ? '<span class="badge badge-2fa" title="2FA Active">🛡️ 2FA</span>' : ''}
    `;

    document.getElementById('profileHeadline').innerText = user.headline || 'Achievement & Credential Showcase';
    
    // Bio
    const bioEl = document.getElementById('profileBio');
    if (bioEl) {
      bioEl.innerText = user.bio || '';
      bioEl.style.display = user.bio ? 'block' : 'none';
    }

    // Username & Joined date
    document.getElementById('profileUsername').innerText = `@${user.username}`;
    document.getElementById('profileJoinedDate').innerText = `Joined ${new Date(user.created_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}`;

    // Avatar
    const avatarEl = document.getElementById('profileAvatarImg');
    const avatarWrapper = document.getElementById('profileAvatarWrapper');
    if (user.avatar_url) {
      avatarEl.src = user.avatar_url;
      avatarEl.style.display = 'block';
    } else {
      avatarEl.style.display = 'none';
      avatarWrapper.innerText = (user.full_name || user.username).charAt(0).toUpperCase();
    }

    // Nav Avatar
    const navAvatar = document.getElementById('navUserAvatar');
    if (navAvatar) {
      navAvatar.innerText = (user.full_name || user.username).charAt(0).toUpperCase();
    }

    // Social Links
    const socialContainer = document.getElementById('profileSocialLinks');
    socialContainer.innerHTML = '';
    if (user.website_url) {
      socialContainer.innerHTML += `<a href="${user.website_url}" target="_blank" rel="noopener" class="social-btn" title="Personal Website">🌐</a>`;
    }
    if (user.github_url) {
      socialContainer.innerHTML += `<a href="${user.github_url}" target="_blank" rel="noopener" class="social-btn" title="GitHub">🐙</a>`;
    }
    if (user.linkedin_url) {
      socialContainer.innerHTML += `<a href="${user.linkedin_url}" target="_blank" rel="noopener" class="social-btn" title="LinkedIn">💼</a>`;
    }
    if (user.twitter_url) {
      socialContainer.innerHTML += `<a href="${user.twitter_url}" target="_blank" rel="noopener" class="social-btn" title="Twitter / X">🐦</a>`;
    }

    // Privacy Badge on Hero
    const privacyBadge = document.getElementById('profilePrivacyStatusBadge');
    if (privacyBadge) {
      if (user.is_profile_public) {
        privacyBadge.className = 'badge badge-public';
        privacyBadge.innerText = '🌐 Public Profile';
      } else {
        privacyBadge.className = 'badge badge-private';
        privacyBadge.innerText = '🔒 Private Profile';
      }
    }
  }

  updateStats(stats) {
    document.getElementById('statTotal').innerText = stats.total || 0;
    document.getElementById('statPublic').innerText = stats.public || 0;
    document.getElementById('statCategories').innerText = stats.categories_count || 0;
    document.getElementById('statFeatured').innerText = stats.featured || 0;
  }

  openEditProfileModal() {
    if (!this.profileData) return;
    const u = this.profileData;

    document.getElementById('editFullName').value = u.full_name || '';
    document.getElementById('editHeadline').value = u.headline || '';
    document.getElementById('editBio').value = u.bio || '';
    document.getElementById('editAvatarUrl').value = u.avatar_url || '';
    document.getElementById('editWebsiteUrl').value = u.website_url || '';
    document.getElementById('editGithubUrl').value = u.github_url || '';
    document.getElementById('editLinkedinUrl').value = u.linkedin_url || '';
    document.getElementById('editTwitterUrl').value = u.twitter_url || '';
    document.getElementById('editPublicProfileToggle').checked = u.is_profile_public;

    window.app.openModal('profileSettingsModal');
  }

  async handleProfileUpdate(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');

    try {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Saving...';

      const payload = {
        full_name: document.getElementById('editFullName').value.trim(),
        headline: document.getElementById('editHeadline').value.trim(),
        bio: document.getElementById('editBio').value.trim(),
        avatar_url: document.getElementById('editAvatarUrl').value.trim(),
        website_url: document.getElementById('editWebsiteUrl').value.trim(),
        github_url: document.getElementById('editGithubUrl').value.trim(),
        linkedin_url: document.getElementById('editLinkedinUrl').value.trim(),
        twitter_url: document.getElementById('editTwitterUrl').value.trim(),
        is_profile_public: document.getElementById('editPublicProfileToggle').checked
      };

      const updated = await api.put('/users/me', payload);
      this.profileData = updated;
      this.renderProfileHero(updated);
      window.app.showToast('Profile updated successfully!', 'success');
      window.app.closeModal('profileSettingsModal');
    } catch (err) {
      window.app.showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Save Changes';
    }
  }

  openShareModal() {
    const user = this.profileData || api.user;
    if (!user) return;

    const publicUrl = `${window.location.origin}/u/${user.username}`;
    document.getElementById('sharePortfolioUrlInput').value = publicUrl;

    // Generate dynamic QR Code for share link
    const qrContainer = document.getElementById('sharePortfolioQrCode');
    const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(publicUrl)}&color=4f46e5`;
    qrContainer.src = qrApiUrl;

    window.app.openModal('sharePortfolioModal');
  }

  async renderPublicProfile(username) {
    try {
      const data = await api.get(`/users/public/${username}`);
      const user = data.user;
      const achievements = data.achievements;

      document.body.classList.add('public-mode');
      
      // Update Hero
      this.renderProfileHero(user);

      // Hide owner-only controls
      const addBtn = document.getElementById('addAchievementBtn');
      if (addBtn) addBtn.style.display = 'none';
      const editBtn = document.getElementById('editProfileBtn');
      if (editBtn) editBtn.style.display = 'none';

      // Update stats
      this.updateStats({
        total: user.public_achievements_count,
        public: user.public_achievements_count,
        categories_count: (user.categories || []).length,
        featured: achievements.filter(x => x.is_featured).length
      });

      // Pass items to achievements manager for rendering
      window.achievements.items = achievements;
      window.achievements.renderCategoryPills(user.categories || []);
      window.achievements.render();
    } catch (err) {
      document.querySelector('.main-content').innerHTML = `
        <div class="empty-state" style="margin-top: 4rem;">
          <div class="empty-icon">🔒</div>
          <h2>Profile Unavailable</h2>
          <p style="color: var(--text-secondary); max-width: 480px;">
            ${err.message || 'This profile is either private or does not exist.'}
          </p>
          <a href="/" class="btn btn-primary" style="margin-top: 1rem;">Back to Showcase Home</a>
        </div>
      `;
    }
  }
}

window.profile = new ProfileManager();

/**
 * Achievement & Showcase Manager
 */

class AchievementManager {
  constructor() {
    this.items = [];
    this.activeView = 'grid'; // 'grid' | 'timeline'
    this.activeCategory = 'all';
    this.searchQuery = '';
    this.selectedTag = '';
    this.selectedVisibility = 'all';
    this.sortBy = 'date_desc';
    this.currentEditingId = null;
    this.selectedFile = null;

    this.initEventListeners();
  }

  initEventListeners() {
    // View Switcher (Grid vs Timeline)
    const viewGridBtn = document.getElementById('viewGridBtn');
    const viewTimelineBtn = document.getElementById('viewTimelineBtn');

    if (viewGridBtn && viewTimelineBtn) {
      viewGridBtn.addEventListener('click', () => {
        this.activeView = 'grid';
        viewGridBtn.classList.add('active');
        viewTimelineBtn.classList.remove('active');
        this.render();
      });

      viewTimelineBtn.addEventListener('click', () => {
        this.activeView = 'timeline';
        viewTimelineBtn.classList.add('active');
        viewGridBtn.classList.remove('active');
        this.render();
      });
    }

    // Search Input with Debounce
    const searchInput = document.getElementById('achievementSearchInput');
    if (searchInput) {
      let timeout;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.searchQuery = e.target.value.trim();
          this.loadAchievements();
        }, 300);
      });
    }

    // Visibility Filter Dropdown
    const visibilityFilter = document.getElementById('visibilityFilterSelect');
    if (visibilityFilter) {
      visibilityFilter.addEventListener('change', (e) => {
        this.selectedVisibility = e.target.value;
        this.loadAchievements();
      });
    }

    // Sort By Dropdown
    const sortSelect = document.getElementById('sortBySelect');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        this.sortBy = e.target.value;
        this.loadAchievements();
      });
    }

    // Open Add Achievement Modal Button
    const addBtn = document.getElementById('addAchievementBtn');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.openAddModal());
    }

    // Achievement Form Submission (Create / Update)
    const achievementForm = document.getElementById('achievementForm');
    if (achievementForm) {
      achievementForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
    }

    // Dropzone & File Input Handling
    const dropzone = document.getElementById('fileDropzone');
    const fileInput = document.getElementById('achievementFileInput');
    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());

      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });

      dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          this.handleFileSelected(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          this.handleFileSelected(e.target.files[0]);
        }
      });
    }

    // Remove Selected File Button
    const removeFileBtn = document.getElementById('removeSelectedFileBtn');
    if (removeFileBtn) {
      removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.clearSelectedFile();
      });
    }
  }

  handleFileSelected(file) {
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      window.app.showToast('Please upload a PDF, PNG, JPG, or WEBP certificate file.', 'error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      window.app.showToast('File exceeds 10MB limit.', 'error');
      return;
    }

    this.selectedFile = file;
    document.getElementById('dropzoneDefaultContent').style.display = 'none';
    const previewPill = document.getElementById('filePreviewPill');
    previewPill.style.display = 'flex';
    document.getElementById('selectedFileName').innerText = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
  }

  clearSelectedFile() {
    this.selectedFile = null;
    const fileInput = document.getElementById('achievementFileInput');
    if (fileInput) fileInput.value = '';
    document.getElementById('dropzoneDefaultContent').style.display = 'flex';
    document.getElementById('filePreviewPill').style.display = 'none';
  }

  async loadAchievements() {
    if (!api.isAuthenticated()) return;

    try {
      const params = new URLSearchParams();
      if (this.searchQuery) params.append('q', this.searchQuery);
      if (this.activeCategory !== 'all') params.append('category', this.activeCategory);
      if (this.selectedTag) params.append('tag', this.selectedTag);
      if (this.selectedVisibility !== 'all') params.append('visibility', this.selectedVisibility);
      if (this.sortBy) params.append('sort_by', this.sortBy);

      const res = await api.get(`/achievements?${params.toString()}`);
      this.items = res.items || [];
      
      // Render Category Pills
      this.renderCategoryPills(res.categories || []);
      // Render Stats
      if (res.stats) {
        window.profile.updateStats(res.stats);
      }
      
      this.render();
    } catch (err) {
      window.app.showToast('Failed to load achievements: ' + err.message, 'error');
    }
  }

  renderCategoryPills(categories) {
    const container = document.getElementById('categoryPillsContainer');
    if (!container) return;

    const allCategories = ['all', 'Certificate', 'Award', 'Badge', 'Project Completion', 'License', 'Hackathon', 'Publication', 'Degree'];
    
    container.innerHTML = allCategories.map(cat => `
      <button class="pill-btn ${this.activeCategory === (cat === 'all' ? 'all' : cat) ? 'active' : ''}" 
              onclick="window.achievements.setCategoryFilter('${cat}')">
        ${cat === 'all' ? '✨ All Showcase' : cat}
      </button>
    `).join('');
  }

  setCategoryFilter(category) {
    this.activeCategory = category;
    this.loadAchievements();
  }

  render() {
    const gridContainer = document.getElementById('achievementsGrid');
    const timelineContainer = document.getElementById('achievementsTimeline');
    const emptyState = document.getElementById('achievementsEmptyState');

    if (!this.items || this.items.length === 0) {
      gridContainer.style.display = 'none';
      timelineContainer.style.display = 'none';
      emptyState.style.display = 'flex';
      return;
    }

    emptyState.style.display = 'none';

    if (this.activeView === 'grid') {
      gridContainer.style.display = 'grid';
      timelineContainer.style.display = 'none';
      this.renderGridView(gridContainer);
    } else {
      gridContainer.style.display = 'none';
      timelineContainer.style.display = 'block';
      this.renderTimelineView(timelineContainer);
    }
  }

  renderGridView(container) {
    container.innerHTML = this.items.map(item => this.createCardHtml(item)).join('');
  }

  renderTimelineView(container) {
    // Group achievements chronologically by year/date
    const grouped = {};
    this.items.forEach(item => {
      const year = (item.issue_date || 'Milestone').substring(0, 4);
      if (!grouped[year]) grouped[year] = [];
      grouped[year].push(item);
    });

    const years = Object.keys(grouped).sort().reverse();

    container.innerHTML = `
      <div class="timeline-container">
        <div class="timeline-line"></div>
        ${years.map(year => `
          <div style="margin-bottom: 2rem;">
            <div style="font-size: 1.25rem; font-weight: 800; color: var(--primary); margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem;">
              <span style="background: rgba(99, 102, 241, 0.2); padding: 0.2rem 0.75rem; border-radius: var(--radius-full); border: 1px solid var(--border-glow);">
                ${year}
              </span>
            </div>
            ${grouped[year].map(item => `
              <div class="timeline-item">
                <div class="timeline-node"></div>
                <div class="timeline-card">
                  ${this.createCardInnerHtml(item)}
                </div>
              </div>
            `).join('')}
          </div>
        `).join('')}
      </div>
    `;
  }

  createCardHtml(item) {
    return `
      <div class="achievement-card ${item.is_featured ? 'featured-card' : ''}" id="card-${item.id}">
        ${this.createCardInnerHtml(item)}
      </div>
    `;
  }

  createCardInnerHtml(item) {
    const categoryClass = (item.category || 'certificate').toLowerCase().replace(/\s+/g, '_');
    const isImage = item.media_type && item.media_type.startsWith('image/');
    const isPdf = item.media_type === 'application/pdf';

    return `
      <div class="card-top-bar">
        <span class="category-badge ${categoryClass}">
          ${this.getCategoryIcon(item.category)} ${item.category}
        </span>
        <div class="card-actions-quick">
          <button class="btn btn-sm ${item.is_public ? 'badge-public' : 'badge-private'}" 
                  title="Click to toggle visibility" 
                  onclick="window.achievements.toggleVisibility('${item.id}', ${!item.is_public})">
            ${item.is_public ? '🌐 Public' : '🔒 Private'}
          </button>
          <button class="btn btn-sm btn-secondary btn-icon-only" 
                  title="${item.is_featured ? 'Unpin' : 'Pin to top'}"
                  onclick="window.achievements.toggleFeatured('${item.id}')">
            ${item.is_featured ? '⭐' : '☆'}
          </button>
        </div>
      </div>

      ${item.has_media ? `
        <div class="card-media-preview" onclick="window.achievements.viewDocument('${item.id}')">
          ${isImage ? `
            <img src="${item.media_url}" alt="${item.title}" loading="lazy" />
          ` : `
            <div class="pdf-preview-chip">
              <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              <span>Verified Document (PDF)</span>
            </div>
          `}
          <div class="card-media-overlay">
            <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
            Click to View
          </div>
        </div>
      ` : ''}

      <div class="card-body">
        <h3>${item.title}</h3>
        <div class="card-issuer-row">
          <span>🏛️ <strong>${item.issuer}</strong></span>
          <span>•</span>
          <span>📅 ${item.issue_date}</span>
          ${item.score_or_grade ? `<span>• 🏆 ${item.score_or_grade}</span>` : ''}
        </div>

        ${item.description ? `<p class="card-description">${item.description}</p>` : ''}

        ${item.tags && item.tags.length > 0 ? `
          <div class="card-tags-cloud">
            ${item.tags.map(t => `<span class="tag-chip">#${t}</span>`).join('')}
          </div>
        ` : ''}
      </div>

      <div class="card-footer">
        <div>
          ${item.credential_id ? `
            <span style="font-size: 0.75rem; color: var(--text-muted);">
              ID: <code style="color: var(--text-secondary); background: rgba(0,0,0,0.3); padding: 1px 4px; border-radius: 4px;">${item.credential_id}</code>
            </span>
          ` : ''}
          ${item.credential_url ? `
            <a href="${item.credential_url}" target="_blank" rel="noopener noreferrer" class="credential-link" style="margin-left: 0.5rem;">
              Verify ↗
            </a>
          ` : ''}
        </div>

        <div style="display: flex; gap: 0.4rem;">
          <button class="btn btn-sm btn-secondary" onclick="window.achievements.openEditModal('${item.id}')">
            Edit
          </button>
          <button class="btn btn-sm btn-danger" onclick="window.achievements.deleteAchievement('${item.id}')">
            Delete
          </button>
        </div>
      </div>
    `;
  }

  getCategoryIcon(cat) {
    const icons = {
      'Certificate': '📜',
      'Award': '🏆',
      'Badge': '🎖️',
      'Project Completion': '🚀',
      'License': '⚖️',
      'Hackathon': '⚡',
      'Publication': '📚',
      'Degree': '🎓'
    };
    return icons[cat] || '✨';
  }

  openAddModal() {
    this.currentEditingId = null;
    this.clearSelectedFile();
    document.getElementById('achievementModalTitle').innerText = 'Add New Achievement';
    document.getElementById('achievementForm').reset();
    document.getElementById('achPublicRadio').checked = true;
    window.app.openModal('achievementModal');
  }

  openEditModal(id) {
    const item = this.items.find(x => x.id === id);
    if (!item) return;

    this.currentEditingId = id;
    this.clearSelectedFile();
    document.getElementById('achievementModalTitle').innerText = 'Edit Achievement';

    document.getElementById('achTitle').value = item.title;
    document.getElementById('achCategory').value = item.category;
    document.getElementById('achIssuer').value = item.issuer;
    document.getElementById('achIssueDate').value = item.issue_date;
    document.getElementById('achExpDate').value = item.expiration_date || '';
    document.getElementById('achCredId').value = item.credential_id || '';
    document.getElementById('achCredUrl').value = item.credential_url || '';
    document.getElementById('achDescription').value = item.description || '';
    document.getElementById('achTags').value = (item.tags || []).join(', ');
    document.getElementById('achScore').value = item.score_or_grade || '';

    if (item.is_public) {
      document.getElementById('achPublicRadio').checked = true;
    } else {
      document.getElementById('achPrivateRadio').checked = true;
    }

    if (item.has_media) {
      const previewPill = document.getElementById('filePreviewPill');
      previewPill.style.display = 'flex';
      document.getElementById('dropzoneDefaultContent').style.display = 'none';
      document.getElementById('selectedFileName').innerText = `Current: ${item.media_filename || 'Certificate file'}`;
    }

    window.app.openModal('achievementModal');
  }

  async handleFormSubmit(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');

    try {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Saving...';

      const formData = new FormData();
      formData.append('title', document.getElementById('achTitle').value.trim());
      formData.append('category', document.getElementById('achCategory').value);
      formData.append('issuer', document.getElementById('achIssuer').value.trim());
      formData.append('issue_date', document.getElementById('achIssueDate').value);
      formData.append('expiration_date', document.getElementById('achExpDate').value.trim());
      formData.append('credential_id', document.getElementById('achCredId').value.trim());
      formData.append('credential_url', document.getElementById('achCredUrl').value.trim());
      formData.append('description', document.getElementById('achDescription').value.trim());
      formData.append('tags', document.getElementById('achTags').value.trim());
      formData.append('score_or_grade', document.getElementById('achScore').value.trim());
      formData.append('is_public', document.getElementById('achPublicRadio').checked);

      if (this.selectedFile) {
        formData.append('file', this.selectedFile);
      }

      if (this.currentEditingId) {
        await api.put(`/achievements/${this.currentEditingId}`, formData);
        window.app.showToast('Achievement updated successfully!', 'success');
      } else {
        await api.post('/achievements', formData);
        window.app.showToast('New achievement added to your showcase!', 'success');
      }

      window.app.closeModal('achievementModal');
      this.loadAchievements();
    } catch (err) {
      window.app.showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Save Achievement';
    }
  }

  async toggleVisibility(id, isPublic) {
    try {
      await api.patch(`/achievements/${id}/visibility`, { is_public: isPublic });
      window.app.showToast(`Achievement is now ${isPublic ? 'Public 🌐' : 'Private 🔒'}`, 'info');
      this.loadAchievements();
    } catch (err) {
      window.app.showToast(err.message, 'error');
    }
  }

  async toggleFeatured(id) {
    try {
      await api.patch(`/achievements/${id}/feature`, {});
      this.loadAchievements();
    } catch (err) {
      window.app.showToast(err.message, 'error');
    }
  }

  async deleteAchievement(id) {
    if (!confirm('Are you sure you want to delete this achievement from your showcase?')) return;

    try {
      await api.delete(`/achievements/${id}`);
      window.app.showToast('Achievement removed.', 'info');
      this.loadAchievements();
    } catch (err) {
      window.app.showToast(err.message, 'error');
    }
  }

  async viewDocument(id) {
    const item = this.items.find(x => x.id === id);
    if (!item || !item.has_media) return;

    const modal = document.getElementById('documentViewerModal');
    const titleEl = document.getElementById('docViewerTitle');
    const issuerEl = document.getElementById('docViewerIssuer');
    const contentEl = document.getElementById('docViewerContent');
    const downloadBtn = document.getElementById('docViewerDownloadBtn');

    titleEl.innerText = item.title;
    issuerEl.innerText = `${item.issuer} • ${item.issue_date}`;
    downloadBtn.href = item.media_url;
    downloadBtn.download = item.media_filename || 'certificate';

    const isPdf = item.media_type === 'application/pdf';

    if (isPdf) {
      contentEl.innerHTML = `
        <iframe src="${item.media_url}" style="width: 100%; height: 75vh; border: none; border-radius: var(--radius-md);" title="Certificate PDF"></iframe>
      `;
    } else {
      contentEl.innerHTML = `
        <div style="text-align: center; max-height: 75vh; overflow: auto; padding: 1rem;">
          <img src="${item.media_url}" alt="${item.title}" style="max-width: 100%; max-height: 70vh; border-radius: var(--radius-md); box-shadow: var(--shadow-lg);" />
        </div>
      `;
    }

    window.app.openModal('documentViewerModal');
  }
}

window.achievements = new AchievementManager();

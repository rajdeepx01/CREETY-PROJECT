/**
 * BuddyAI - Your Warm, Knowledgeable Friend
 * Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // =========================================================================
  // STATE MANAGEMENT
  // =========================================================================
  const STATE = {
    apiKey: localStorage.getItem('buddyai_api_key') || '',
    model: localStorage.getItem('buddyai_model') || 'gemini-2.5-flash',
    theme: localStorage.getItem('buddyai_theme') || 'theme-warm-dark',
    speechVoice: localStorage.getItem('buddyai_tts_voice') || 'default',
    speechRate: parseFloat(localStorage.getItem('buddyai_tts_rate') || '1.0'),
    serverKeyConfigured: false,
    availableModels: [],
    chats: JSON.parse(localStorage.getItem('buddyai_chats') || '[]'),
    currentChatId: null,
    currentMessages: [],
    isStreaming: false,
    abortController: null,
    currentlySpeakingUtterance: null,
    speechRecognition: null,
    isListening: false,
  };

  // =========================================================================
  // DOM ELEMENT REFERENCES
  // =========================================================================
  const elements = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    sidebarOverlay: document.getElementById('sidebarOverlay'),
    sidebarOpenBtn: document.getElementById('sidebarOpenBtn'),
    sidebarCloseBtn: document.getElementById('sidebarCloseBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    chatsList: document.getElementById('chatsList'),
    clearAllChatsBtn: document.getElementById('clearAllChatsBtn'),

    // Header & Meta
    modelNameText: document.getElementById('modelNameText'),
    apiKeyStatusBtn: document.getElementById('apiKeyStatusBtn'),
    apiKeyIndicator: document.getElementById('apiKeyIndicator'),
    apiKeyLabel: document.getElementById('apiKeyLabel'),
    themeToggleBtn: document.getElementById('themeToggleBtn'),
    themeIcon: document.getElementById('themeIcon'),
    settingsBtn: document.getElementById('settingsBtn'),

    // Chat Area
    chatScrollArea: document.getElementById('chatScrollArea'),
    welcomeHero: document.getElementById('welcomeHero'),
    startersGrid: document.getElementById('startersGrid'),
    messagesContainer: document.getElementById('messagesContainer'),
    typingIndicator: document.getElementById('typingIndicator'),
    scrollAnchor: document.getElementById('scrollAnchor'),

    // Input & Tools
    chatTextarea: document.getElementById('chatTextarea'),
    sendMessageBtn: document.getElementById('sendMessageBtn'),
    stopGeneratingBtn: document.getElementById('stopGeneratingBtn'),
    speechInputBtn: document.getElementById('speechInputBtn'),

    // Settings Modal
    settingsModal: document.getElementById('settingsModal'),
    closeSettingsBtn: document.getElementById('closeSettingsBtn'),
    cancelSettingsBtn: document.getElementById('cancelSettingsBtn'),
    saveSettingsBtn: document.getElementById('saveSettingsBtn'),
    apiKeyInput: document.getElementById('apiKeyInput'),
    toggleKeyVisBtn: document.getElementById('toggleKeyVisBtn'),
    eyeIcon: document.getElementById('eyeIcon'),
    modelSelect: document.getElementById('modelSelect'),
    ttsVoiceSelect: document.getElementById('ttsVoiceSelect'),
    speechRateSlider: document.getElementById('speechRateSlider'),
    speedValue: document.getElementById('speedValue'),

    // Toast
    toastContainer: document.getElementById('toastContainer'),
  };

  // Configure Marked Markdown Renderer
  if (typeof marked !== 'undefined') {
    marked.setOptions({
      gfm: true,
      breaks: true,
      headerIds: false,
      mangle: false,
    });
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================
  function init() {
    applyTheme(STATE.theme);
    updateModelBadge();
    checkServerStatus();
    loadSavedChats();
    initNewChat();
    initSpeechSynthesis();
    initSpeechRecognition();
    setupEventListeners();
  }

  // =========================================================================
  // SERVER STATUS & CONFIG
  // =========================================================================
  async function checkServerStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        STATE.serverKeyConfigured = data.api_key_configured;
        STATE.availableModels = data.available_models || [];
        updateApiKeyStatusUI();
      }
    } catch (err) {
      console.warn('Status check failed:', err);
      updateApiKeyStatusUI();
    }
  }

  function updateApiKeyStatusUI() {
    const hasKey = !!(STATE.apiKey || STATE.serverKeyConfigured);
    if (STATE.apiKey) {
      elements.apiKeyIndicator.className = 'status-indicator configured';
      elements.apiKeyLabel.textContent = 'Custom Key';
      elements.apiKeyStatusBtn.title = 'Custom API Key Active';
    } else if (STATE.serverKeyConfigured) {
      elements.apiKeyIndicator.className = 'status-indicator configured';
      elements.apiKeyLabel.textContent = 'Server Key';
      elements.apiKeyStatusBtn.title = 'Server .env API Key Active';
    } else {
      elements.apiKeyIndicator.className = 'status-indicator missing';
      elements.apiKeyLabel.textContent = 'Set API Key';
      elements.apiKeyStatusBtn.title = 'Click to configure your Gemini API Key';
    }
  }

  function updateModelBadge() {
    elements.modelNameText.textContent = STATE.model;
    if (elements.modelSelect) {
      elements.modelSelect.value = STATE.model;
    }
  }

  // =========================================================================
  // THEME MANAGEMENT
  // =========================================================================
  function applyTheme(themeName) {
    STATE.theme = themeName;
    document.body.className = themeName;
    localStorage.setItem('buddyai_theme', themeName);

    if (themeName === 'theme-warm-light') {
      elements.themeIcon.className = 'fa-solid fa-moon';
      elements.themeToggleBtn.title = 'Switch to Warm Dark Theme';
    } else {
      elements.themeIcon.className = 'fa-solid fa-sun';
      elements.themeToggleBtn.title = 'Switch to Warm Light Theme';
    }
  }

  function toggleTheme() {
    const newTheme = STATE.theme === 'theme-warm-dark' ? 'theme-warm-light' : 'theme-warm-dark';
    applyTheme(newTheme);
    showToast(`Switched to ${newTheme === 'theme-warm-dark' ? 'Warm Dark' : 'Warm Light'} theme`, 'info');
  }

  // =========================================================================
  // CHAT SESSIONS & STORAGE
  // =========================================================================
  function initNewChat() {
    STATE.currentChatId = 'chat_' + Date.now();
    STATE.currentMessages = [];
    renderMessages();
    renderSidebarChats();
    elements.chatTextarea.focus();
  }

  function saveCurrentChat() {
    if (STATE.currentMessages.length === 0) return;

    // First user message becomes title
    const firstUserMsg = STATE.currentMessages.find((m) => m.role === 'user');
    const rawTitle = firstUserMsg ? firstUserMsg.content : 'New Conversation';
    const cleanTitle = rawTitle.slice(0, 36) + (rawTitle.length > 36 ? '...' : '');

    const existingIndex = STATE.chats.findIndex((c) => c.id === STATE.currentChatId);
    const chatData = {
      id: STATE.currentChatId,
      title: cleanTitle,
      updatedAt: Date.now(),
      messages: STATE.currentMessages,
    };

    if (existingIndex >= 0) {
      STATE.chats[existingIndex] = chatData;
    } else {
      STATE.chats.unshift(chatData);
    }

    localStorage.setItem('buddyai_chats', JSON.stringify(STATE.chats));
    renderSidebarChats();
  }

  function loadChat(chatId) {
    const chat = STATE.chats.find((c) => c.id === chatId);
    if (!chat) return;

    STATE.currentChatId = chat.id;
    STATE.currentMessages = [...chat.messages];
    renderMessages();
    renderSidebarChats();
    closeSidebarMobile();
  }

  function deleteChat(chatId, event) {
    if (event) event.stopPropagation();
    STATE.chats = STATE.chats.filter((c) => c.id !== chatId);
    localStorage.setItem('buddyai_chats', JSON.stringify(STATE.chats));

    if (STATE.currentChatId === chatId) {
      initNewChat();
    } else {
      renderSidebarChats();
    }
    showToast('Conversation deleted', 'info');
  }

  function clearAllChats() {
    if (STATE.chats.length === 0) return;
    if (confirm('Are you sure you want to clear all conversation history?')) {
      STATE.chats = [];
      localStorage.removeItem('buddyai_chats');
      initNewChat();
      showToast('All conversations cleared', 'info');
    }
  }

  function loadSavedChats() {
    renderSidebarChats();
  }

  function renderSidebarChats() {
    if (STATE.chats.length === 0) {
      elements.chatsList.innerHTML = `
        <div class="empty-chats-hint">
          <i class="fa-regular fa-comments"></i>
          <span>No saved chats yet.<br/>Say hello to your AI friend!</span>
        </div>
      `;
      return;
    }

    elements.chatsList.innerHTML = STATE.chats
      .map(
        (chat) => `
        <div class="chat-item ${chat.id === STATE.currentChatId ? 'active' : ''}" data-chat-id="${chat.id}">
          <div class="chat-item-title">
            <i class="fa-regular fa-message chat-item-icon"></i>
            <span>${escapeHTML(chat.title)}</span>
          </div>
          <button class="chat-item-delete" data-delete-id="${chat.id}" title="Delete chat">
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      `
      )
      .join('');

    // Attach click handlers
    elements.chatsList.querySelectorAll('.chat-item').forEach((item) => {
      item.addEventListener('click', () => {
        const id = item.dataset.chatId;
        loadChat(id);
      });
    });

    elements.chatsList.querySelectorAll('.chat-item-delete').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const id = btn.dataset.deleteId;
        deleteChat(id, e);
      });
    });
  }

  // =========================================================================
  // MESSAGE RENDERING & MARKDOWN
  // =========================================================================
  function renderMessages() {
    if (STATE.currentMessages.length === 0) {
      elements.welcomeHero.classList.remove('hidden');
      elements.messagesContainer.innerHTML = '';
      return;
    }

    elements.welcomeHero.classList.add('hidden');
    elements.messagesContainer.innerHTML = STATE.currentMessages
      .map((msg, index) => renderSingleMessageHTML(msg, index))
      .join('');

    // Highlight code blocks and render KaTeX
    postProcessRenderedMessages();
    scrollToBottom();
  }

  function renderSingleMessageHTML(msg, index) {
    const isUser = msg.role === 'user';
    const timeStr = msg.timestamp ? formatTime(msg.timestamp) : '';

    if (isUser) {
      return `
        <div class="message-row user" id="msg-${index}">
          <div class="user-message-bubble">
            ${escapeHTML(msg.content)}
          </div>
        </div>
      `;
    }

    // AI Friend Message
    const parsedMarkdown = parseMarkdown(msg.content);
    return `
      <div class="message-row friend" id="msg-${index}">
        <div class="friend-avatar">
          <i class="fa-solid fa-sparkles"></i>
        </div>
        <div class="friend-message-container">
          <div class="friend-name-bar">
            <div class="friend-name-tag">
              <span>BuddyAI</span>
              <span class="emoji-heart">✨</span>
            </div>
            <span class="message-time">${timeStr}</span>
          </div>
          <div class="markdown-body">
            ${parsedMarkdown}
          </div>
          <div class="message-actions-bar">
            <button class="btn-msg-action btn-copy-msg" data-msg-index="${index}" title="Copy full explanation">
              <i class="fa-regular fa-copy"></i>
              <span>Copy</span>
            </button>
            <button class="btn-msg-action btn-speak-msg" data-msg-index="${index}" title="Listen to explanation (Text-to-Speech)">
              <i class="fa-solid fa-volume-high"></i>
              <span>Listen</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function parseMarkdown(text) {
    if (!text) return '';
    try {
      let rawHtml = marked.parse(text);
      // Wrap pre code blocks with clean UI wrapper & copy button
      rawHtml = rawHtml.replace(
        /<pre><code class="language-([a-zA-Z0-9_\+\-]+)">([\s\S]*?)<\/code><\/pre>/g,
        (match, lang, code) => {
          return `
            <div class="code-block-wrapper">
              <div class="code-block-header">
                <span class="code-lang-label">${lang.toUpperCase()}</span>
                <button class="code-copy-btn" onclick="window.copyCodeSnippet(this)">
                  <i class="fa-regular fa-copy"></i> Copy
                </button>
              </div>
              <pre><code class="language-${lang}">${code}</code></pre>
            </div>
          `;
        }
      );
      // Fallback for code blocks without specified language
      rawHtml = rawHtml.replace(/<pre><code>([\s\S]*?)<\/code><\/pre>/g, (match, code) => {
        return `
          <div class="code-block-wrapper">
            <div class="code-block-header">
              <span class="code-lang-label">CODE</span>
              <button class="code-copy-btn" onclick="window.copyCodeSnippet(this)">
                <i class="fa-regular fa-copy"></i> Copy
              </button>
            </div>
            <pre><code>${code}</code></pre>
          </div>
        `;
      });
      return rawHtml;
    } catch (err) {
      console.error('Markdown parse error:', err);
      return `<p>${escapeHTML(text)}</p>`;
    }
  }

  function postProcessRenderedMessages() {
    // Prism Syntax Highlighting
    if (typeof Prism !== 'undefined') {
      Prism.highlightAllUnder(elements.messagesContainer);
    }

    // KaTeX Math Rendering
    if (typeof renderMathInElement !== 'undefined') {
      renderMathInElement(elements.messagesContainer, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        throwOnError: false,
      });
    }

    // Attach event listeners to copy and speak buttons
    elements.messagesContainer.querySelectorAll('.btn-copy-msg').forEach((btn) => {
      btn.onclick = () => {
        const idx = parseInt(btn.dataset.msgIndex, 10);
        const msg = STATE.currentMessages[idx];
        if (msg) {
          navigator.clipboard.writeText(msg.content);
          showToast('Explanation copied to clipboard! 📋', 'success');
        }
      };
    });

    elements.messagesContainer.querySelectorAll('.btn-speak-msg').forEach((btn) => {
      btn.onclick = () => {
        const idx = parseInt(btn.dataset.msgIndex, 10);
        const msg = STATE.currentMessages[idx];
        if (msg) {
          toggleSpeech(msg.content, btn);
        }
      };
    });
  }

  // Global helper for code block copying
  window.copyCodeSnippet = function (btn) {
    const codeBlock = btn.closest('.code-block-wrapper').querySelector('code');
    if (codeBlock) {
      navigator.clipboard.writeText(codeBlock.innerText);
      const origText = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
      setTimeout(() => {
        btn.innerHTML = origText;
      }, 2000);
      showToast('Code copied to clipboard!', 'success');
    }
  };

  // =========================================================================
  // STREAMING & CHAT API
  // =========================================================================
  async function sendMessage(text) {
    const userPrompt = (text || elements.chatTextarea.value).trim();
    if (!userPrompt || STATE.isStreaming) return;

    // Check API Key
    if (!STATE.apiKey && !STATE.serverKeyConfigured) {
      openSettingsModal();
      showToast('Please configure your Gemini API Key first! 🔑', 'error');
      return;
    }

    // Reset textarea
    elements.chatTextarea.value = '';
    elements.chatTextarea.style.height = 'auto';
    elements.welcomeHero.classList.add('hidden');

    // Add user message to state
    const userMsg = {
      role: 'user',
      content: userPrompt,
      timestamp: Date.now(),
    };
    STATE.currentMessages.push(userMsg);
    renderMessages();

    // Prepare placeholder for streaming model message
    const modelMsgIndex = STATE.currentMessages.length;
    const modelMsg = {
      role: 'model',
      content: '',
      timestamp: Date.now(),
    };
    STATE.currentMessages.push(modelMsg);

    // Create live message element in DOM
    const modelMsgEl = document.createElement('div');
    modelMsgEl.className = 'message-row friend';
    modelMsgEl.id = `msg-${modelMsgIndex}`;
    modelMsgEl.innerHTML = `
      <div class="friend-avatar">
        <i class="fa-solid fa-sparkles"></i>
      </div>
      <div class="friend-message-container">
        <div class="friend-name-bar">
          <div class="friend-name-tag">
            <span>BuddyAI</span>
            <span class="emoji-heart">✨</span>
          </div>
          <span class="message-time">Just now</span>
        </div>
        <div class="markdown-body" id="streamTarget-${modelMsgIndex}">
          <span class="live-cursor"></span>
        </div>
      </div>
    `;
    elements.messagesContainer.appendChild(modelMsgEl);
    elements.typingIndicator.classList.remove('hidden');
    scrollToBottom();

    // Set streaming state
    STATE.isStreaming = true;
    elements.sendMessageBtn.disabled = true;
    elements.stopGeneratingBtn.classList.remove('hidden');
    STATE.abortController = new AbortController();

    try {
      // Build history for backend
      const historyPayload = STATE.currentMessages.slice(0, -2).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const requestBody = {
        message: userPrompt,
        history: historyPayload,
        model: STATE.model,
        api_key: STATE.apiKey || null,
        temperature: 0.7,
      };

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: STATE.abortController.signal,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned ${response.status}`);
      }

      elements.typingIndicator.classList.add('hidden');
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulatedText = '';
      const streamTarget = document.getElementById(`streamTarget-${modelMsgIndex}`);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete chunk in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const jsonStr = trimmed.replace(/^data:\s*/, '');
          let data;
          try {
            data = JSON.parse(jsonStr);
          } catch (e) {
            console.warn('Error parsing SSE line JSON:', e, jsonStr);
            continue;
          }

          if (data.type === 'token') {
            accumulatedText += data.token;
            if (streamTarget) {
              streamTarget.innerHTML = parseMarkdown(accumulatedText) + '<span class="live-cursor"></span>';
              scrollToBottom();
            }
          } else if (data.type === 'done') {
            accumulatedText = data.full_text || accumulatedText;
          } else if (data.type === 'error') {
            throw new Error(data.error || 'Unknown streaming error');
          }
        }
      }

      if (!accumulatedText.trim()) {
        throw new Error('No response received from the Gemini API. Please check your API key and network connection.');
      }

      // Finalize model message content
      STATE.currentMessages[modelMsgIndex].content = accumulatedText;
      saveCurrentChat();
      renderMessages();
    } catch (err) {
      if (err.name === 'AbortError') {
        showToast('Generation stopped.', 'info');
      } else {
        console.error('Chat error:', err);
        const errMsg = `⚠️ **BuddyAI encountered an issue:**\n\n${err.message}\n\n👉 *Tip: Click the **API Key** button or **⚙️ Settings** at the top right to check or update your Google Gemini API key.*`;
        STATE.currentMessages[modelMsgIndex].content = errMsg;
        showToast(err.message, 'error');
      }
      renderMessages();
    } finally {
      STATE.isStreaming = false;
      elements.sendMessageBtn.disabled = false;
      elements.stopGeneratingBtn.classList.add('hidden');
      elements.typingIndicator.classList.add('hidden');
      STATE.abortController = null;
      elements.chatTextarea.focus();
    }
  }

  function stopGenerating() {
    if (STATE.abortController) {
      STATE.abortController.abort();
    }
  }

  // =========================================================================
  // TEXT-TO-SPEECH (TTS) - "LISTEN TO FRIEND"
  // =========================================================================
  function initSpeechSynthesis() {
    if (!('speechSynthesis' in window)) {
      console.warn('Web Speech API (TTS) not supported on this browser.');
      return;
    }

    function populateVoices() {
      const voices = window.speechSynthesis.getVoices();
      if (!voices || voices.length === 0) return;

      elements.ttsVoiceSelect.innerHTML = voices
        .map(
          (v, idx) => `
          <option value="${v.name}" ${v.name === STATE.speechVoice ? 'selected' : ''}>
            ${v.name} (${v.lang})
          </option>
        `
        )
        .join('');
    }

    populateVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = populateVoices;
    }
  }

  function toggleSpeech(text, btnElement) {
    if (!('speechSynthesis' in window)) {
      showToast('Text-to-speech is not supported in this browser.', 'error');
      return;
    }

    // If currently speaking, stop it
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      document.querySelectorAll('.btn-speak-msg').forEach((b) => {
        b.classList.remove('speaking');
        b.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Listen</span>';
      });
      if (btnElement.classList.contains('speaking')) {
        return; // Just stopped current speech
      }
    }

    // Clean markdown for pleasant audio reading
    const cleanText = text
      .replace(/```[\s\S]*?```/g, ' [Code Snippet] ')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/[#*_~>]/g, '')
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.rate = STATE.speechRate;

    // Pick selected voice
    const voices = window.speechSynthesis.getVoices();
    const selectedVoice = voices.find((v) => v.name === STATE.speechVoice);
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    btnElement.classList.add('speaking');
    btnElement.innerHTML = '<i class="fa-solid fa-stop"></i> <span>Stop</span>';

    utterance.onend = () => {
      btnElement.classList.remove('speaking');
      btnElement.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Listen</span>';
    };

    utterance.onerror = () => {
      btnElement.classList.remove('speaking');
      btnElement.innerHTML = '<i class="fa-solid fa-volume-high"></i> <span>Listen</span>';
    };

    window.speechSynthesis.speak(utterance);
  }

  // =========================================================================
  // SPEECH RECOGNITION (VOICE DICTATION INPUT)
  // =========================================================================
  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      elements.speechInputBtn.style.display = 'none';
      return;
    }

    STATE.speechRecognition = new SpeechRecognition();
    STATE.speechRecognition.continuous = false;
    STATE.speechRecognition.interimResults = true;
    STATE.speechRecognition.lang = 'en-US';

    STATE.speechRecognition.onstart = () => {
      STATE.isListening = true;
      elements.speechInputBtn.classList.add('listening');
      showToast('Listening... Speak your question! 🎙️', 'info');
    };

    STATE.speechRecognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      elements.chatTextarea.value = transcript;
      autoResizeTextarea();
    };

    STATE.speechRecognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      STATE.isListening = false;
      elements.speechInputBtn.classList.remove('listening');
      showToast(`Mic error: ${event.error}`, 'error');
    };

    STATE.speechRecognition.onend = () => {
      STATE.isListening = false;
      elements.speechInputBtn.classList.remove('listening');
    };
  }

  function toggleSpeechRecognition() {
    if (!STATE.speechRecognition) {
      showToast('Voice dictation is not supported in this browser.', 'error');
      return;
    }

    if (STATE.isListening) {
      STATE.speechRecognition.stop();
    } else {
      try {
        STATE.speechRecognition.start();
      } catch (e) {
        console.warn('Mic start failed:', e);
      }
    }
  }

  // =========================================================================
  // SETTINGS MODAL
  // =========================================================================
  function openSettingsModal() {
    elements.apiKeyInput.value = STATE.apiKey;
    elements.modelSelect.value = STATE.model;
    elements.ttsVoiceSelect.value = STATE.speechVoice;
    elements.speechRateSlider.value = STATE.speechRate;
    elements.speedValue.textContent = STATE.speechRate.toFixed(2) + 'x';
    elements.settingsModal.classList.remove('hidden');
  }

  function closeSettingsModal() {
    elements.settingsModal.classList.add('hidden');
  }

  function saveSettings() {
    const newApiKey = elements.apiKeyInput.value.trim();
    const newModel = elements.modelSelect.value;
    const newVoice = elements.ttsVoiceSelect.value;
    const newRate = parseFloat(elements.speechRateSlider.value);

    STATE.apiKey = newApiKey;
    STATE.model = newModel;
    STATE.speechVoice = newVoice;
    STATE.speechRate = newRate;

    localStorage.setItem('buddyai_api_key', newApiKey);
    localStorage.setItem('buddyai_model', newModel);
    localStorage.setItem('buddyai_tts_voice', newVoice);
    localStorage.setItem('buddyai_tts_rate', newRate.toString());

    updateApiKeyStatusUI();
    updateModelBadge();
    closeSettingsModal();
    showToast('Settings saved successfully! ✨', 'success');
  }

  function toggleKeyVisibility() {
    const isPass = elements.apiKeyInput.type === 'password';
    elements.apiKeyInput.type = isPass ? 'text' : 'password';
    elements.eyeIcon.className = isPass ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye';
  }

  // =========================================================================
  // UI HELPERS & EVENTS
  // =========================================================================
  function setupEventListeners() {
    // New Chat
    elements.newChatBtn.addEventListener('click', () => {
      initNewChat();
      closeSidebarMobile();
      showToast('Started a fresh chat! 🚀', 'info');
    });

    // Clear All
    elements.clearAllChatsBtn.addEventListener('click', clearAllChats);

    // Sidebar Mobile Toggle
    elements.sidebarOpenBtn.addEventListener('click', openSidebarMobile);
    elements.sidebarCloseBtn.addEventListener('click', closeSidebarMobile);
    elements.sidebarOverlay.addEventListener('click', closeSidebarMobile);

    // Theme Toggle
    elements.themeToggleBtn.addEventListener('click', toggleTheme);

    // Settings Modal
    elements.settingsBtn.addEventListener('click', openSettingsModal);
    elements.apiKeyStatusBtn.addEventListener('click', openSettingsModal);
    elements.closeSettingsBtn.addEventListener('click', closeSettingsModal);
    elements.cancelSettingsBtn.addEventListener('click', closeSettingsModal);
    elements.saveSettingsBtn.addEventListener('click', saveSettings);
    elements.toggleKeyVisBtn.addEventListener('click', toggleKeyVisibility);

    elements.speechRateSlider.addEventListener('input', (e) => {
      elements.speedValue.textContent = parseFloat(e.target.value).toFixed(2) + 'x';
    });

    // Send & Stop
    elements.sendMessageBtn.addEventListener('click', () => sendMessage());
    elements.stopGeneratingBtn.addEventListener('click', stopGenerating);
    elements.speechInputBtn.addEventListener('click', toggleSpeechRecognition);

    // Textarea Auto-Resize & Keyboard Submission
    elements.chatTextarea.addEventListener('input', autoResizeTextarea);
    elements.chatTextarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Starter Prompt Cards
    elements.startersGrid.querySelectorAll('.starter-card').forEach((card) => {
      card.addEventListener('click', () => {
        const prompt = card.dataset.prompt;
        if (prompt) {
          sendMessage(prompt);
        }
      });
    });

    // Close Modal on backdrop click or ESC key
    elements.settingsModal.addEventListener('click', (e) => {
      if (e.target === elements.settingsModal) {
        closeSettingsModal();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !elements.settingsModal.classList.contains('hidden')) {
        closeSettingsModal();
      }
    });
  }

  function autoResizeTextarea() {
    const el = elements.chatTextarea;
    el.style.height = 'auto';
    const newHeight = Math.min(el.scrollHeight, 180);
    el.style.height = newHeight + 'px';
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      elements.scrollAnchor.scrollIntoView({ behavior: 'smooth' });
    });
  }

  function openSidebarMobile() {
    elements.sidebar.classList.add('open');
    elements.sidebarOverlay.classList.add('active');
  }

  function closeSidebarMobile() {
    elements.sidebar.classList.remove('open');
    elements.sidebarOverlay.classList.remove('active');
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    if (type === 'error') iconClass = 'fa-solid fa-triangle-exclamation';

    toast.innerHTML = `<i class="${iconClass}"></i> <span>${escapeHTML(message)}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function escapeHTML(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Kickoff App
  init();
});

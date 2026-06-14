/**
 * AgiChat — zero-build Claude-style chat widget for static web pages.
 *
 * Usage:
 *   import { AgiChat } from './agi-chat.js';
 *   const chat = new AgiChat(element, { onSend: async (text, chat) => { ... } });
 */

const MARKED_URL = 'https://cdn.jsdelivr.net/npm/marked@15/marked.min.js';

let markedReady = null;

function loadMarked() {
  if (window.marked) return Promise.resolve(window.marked);
  if (markedReady) return markedReady;
  markedReady = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = MARKED_URL;
    script.async = true;
    script.onload = () => resolve(window.marked);
    script.onerror = () => reject(new Error('Failed to load marked.js'));
    document.head.appendChild(script);
  });
  return markedReady;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export class AgiChat {
  /**
   * @param {HTMLElement} container
   * @param {object} options
   * @param {string} [options.agentName='Assistant']
   * @param {string} [options.agentAvatar] — URL or omit for initial letter
   * @param {string} [options.placeholder='Message…']
   * @param {boolean} [options.markdown=true]
   * @param {function(string, AgiChat): Promise<void>|void} [options.onSend]
   */
  constructor(container, options = {}) {
    this.container = container;
    this.agentName = options.agentName ?? 'Assistant';
    this.agentAvatar = options.agentAvatar ?? null;
    this.placeholder = options.placeholder ?? 'Message…';
    this.markdown = options.markdown !== false;
    this.onSend = options.onSend ?? (() => {});
    this.messages = [];
    this._typing = false;
    this._id = 0;

    container.classList.add('agi-chat-root');
    container.innerHTML = `
      <div class="agi-chat-messages" role="log" aria-live="polite"></div>
      <div class="agi-chat-input-area">
        <div class="agi-chat-input-wrap">
          <textarea
            class="agi-chat-input"
            rows="1"
            placeholder="${escapeHtml(this.placeholder)}"
            aria-label="Chat message"
          ></textarea>
          <button type="button" class="agi-chat-send" aria-label="Send message" disabled>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path fill="currentColor" d="M3.4 20.4 21 12 3.4 3.6l-.8 7.2 12 .8-12 .8.8 7.2z"/>
            </svg>
          </button>
        </div>
        <p class="agi-chat-hint">Enter to send · Shift+Enter for newline</p>
      </div>
    `;

    this.messagesEl = container.querySelector('.agi-chat-messages');
    this.inputEl = container.querySelector('.agi-chat-input');
    this.sendEl = container.querySelector('.agi-chat-send');

    this.inputEl.addEventListener('input', () => this._resizeInput());
    this.inputEl.addEventListener('keydown', (e) => this._onKeyDown(e));
    this.sendEl.addEventListener('click', () => this._submit());

    if (this.markdown) loadMarked().catch(() => {});
  }

  /** @param {'user'|'assistant'} role */
  async appendMessage(role, content, meta = {}) {
    const id = ++this._id;
    const msg = { id, role, content, meta, ts: Date.now() };
    this.messages.push(msg);
    await this._renderMessage(msg);
    this._scrollToBottom();
    return id;
  }

  setTyping(active) {
    this._typing = active;
    const existing = this.messagesEl.querySelector('.agi-chat-typing');
    if (active && !existing) {
      const el = document.createElement('div');
      el.className = 'agi-chat-row agi-chat-row--assistant agi-chat-typing';
      el.innerHTML = `
        <div class="agi-chat-avatar" aria-hidden="true">${this._avatarHtml()}</div>
        <div class="agi-chat-bubble agi-chat-bubble--assistant">
          <span class="agi-chat-dots"><span></span><span></span><span></span></span>
        </div>
      `;
      this.messagesEl.appendChild(el);
      this._scrollToBottom();
    } else if (!active && existing) {
      existing.remove();
    }
  }

  clear() {
    this.messages = [];
    this.messagesEl.innerHTML = '';
  }

  focus() {
    this.inputEl.focus();
  }

  _avatarHtml() {
    if (this.agentAvatar) {
      return `<img src="${escapeHtml(this.agentAvatar)}" alt="">`;
    }
    return this.agentName.charAt(0).toUpperCase();
  }

  async _renderMessage(msg) {
    const row = document.createElement('div');
    const isUser = msg.role === 'user';
    row.className = `agi-chat-row agi-chat-row--${isUser ? 'user' : 'assistant'}`;
    row.dataset.messageId = String(msg.id);

    let body = escapeHtml(msg.content);
    if (!isUser && this.markdown && window.marked) {
      body = window.marked.parse(msg.content, { async: false });
    } else if (isUser) {
      body = escapeHtml(msg.content).replace(/\n/g, '<br>');
    }

    row.innerHTML = isUser
      ? `<div class="agi-chat-bubble agi-chat-bubble--user">${body}</div>`
      : `
        <div class="agi-chat-avatar" aria-hidden="true">${this._avatarHtml()}</div>
        <div class="agi-chat-content">
          <div class="agi-chat-name">${escapeHtml(this.agentName)}</div>
          <div class="agi-chat-bubble agi-chat-bubble--assistant">${body}</div>
        </div>
      `;

    this.messagesEl.appendChild(row);
  }

  async _submit() {
    const text = this.inputEl.value.trim();
    if (!text || this._typing) return;

    this.inputEl.value = '';
    this._resizeInput();
    this.sendEl.disabled = true;

    try {
      await this.onSend(text, this);
    } finally {
      this.sendEl.disabled = !this.inputEl.value.trim();
    }
  }

  _onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this._submit();
    }
  }

  _resizeInput() {
    this.inputEl.style.height = 'auto';
    this.inputEl.style.height = `${Math.min(this.inputEl.scrollHeight, 200)}px`;
    this.sendEl.disabled = !this.inputEl.value.trim();
  }

  _scrollToBottom() {
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }
}

export default AgiChat;

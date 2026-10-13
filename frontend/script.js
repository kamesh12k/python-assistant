const API_BASE = 'http://localhost:5000';

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadProgress = document.getElementById('uploadProgress');
const progressText = document.getElementById('progressText');
const docList = document.getElementById('docList');
const docCount = document.getElementById('docCount');
const docEmpty = document.getElementById('docEmpty');
const chatArea = document.getElementById('chatArea');
const welcome = document.getElementById('welcome');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const toastContainer = document.getElementById('toastContainer');

let isGenerating = false;

// Toast helper
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// Simple Markdown Formatter
function formatMarkdown(text) {
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks
  html = html.replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Lists
  html = html.replace(/^\s*[-*]\s+(.*)$/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Paragraphs
  html = html.split('\n\n').map(p => {
    if (p.startsWith('<h') || p.startsWith('<pre') || p.startsWith('<ul>') || p.startsWith('<blockquote>')) {
      return p;
    }
    return `<p>${p.replace(/\n/g, '<br/>')}</p>`;
  }).join('');

  return html;
}

// Fetch and render uploaded documents
async function loadDocuments() {
  try {
    const res = await fetch(`${API_BASE}/api/documents`);
    if (!res.ok) throw new Error('Failed to load documents');
    const data = await res.json();
    renderDocuments(data.documents || []);
  } catch (err) {
    console.error('Error fetching documents:', err);
  }
}

function renderDocuments(docs) {
  docCount.textContent = docs.length;
  // Clear existing cards
  const existingCards = docList.querySelectorAll('.doc-card');
  existingCards.forEach(c => c.remove());

  if (docs.length === 0) {
    docEmpty.style.display = 'block';
    return;
  }
  docEmpty.style.display = 'none';

  docs.forEach(doc => {
    const card = document.createElement('div');
    card.className = 'doc-card';
    card.innerHTML = `
      <div class="doc-icon">📄</div>
      <div class="doc-info">
        <div class="doc-name" title="${doc.filename}">${doc.filename}</div>
        <div class="doc-meta">${doc.num_pages} pages · ${doc.num_chunks} chunks</div>
      </div>
      <button class="doc-delete" title="Delete document">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;

    card.querySelector('.doc-delete').addEventListener('click', async () => {
      try {
        const res = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(doc.filename)}`, {
          method: 'DELETE'
        });
        if (res.ok) {
          showToast(`Deleted ${doc.filename}`, 'success');
          loadDocuments();
        } else {
          showToast('Failed to delete document', 'error');
        }
      } catch (err) {
        showToast('Error deleting document', 'error');
      }
    });

    docList.appendChild(card);
  });
}

// File upload handling
async function uploadFile(file) {
  if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Please select a valid PDF file.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  uploadProgress.style.display = 'block';
  progressText.textContent = `Uploading & indexing ${file.name}…`;

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Upload failed');
    }

    showToast(`Successfully indexed ${file.name}`, 'success');
    await loadDocuments();
  } catch (err) {
    showToast(err.message || 'Upload error', 'error');
  } finally {
    uploadProgress.style.display = 'none';
    fileInput.value = '';
  }
}

// Drag & drop listeners
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    uploadFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) {
    uploadFile(e.target.files[0]);
  }
});

// Auto-expand textarea
queryInput.addEventListener('input', () => {
  queryInput.style.height = 'auto';
  queryInput.style.height = `${Math.min(queryInput.scrollHeight, 160)}px`;
});

queryInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitQuery();
  }
});

sendBtn.addEventListener('click', submitQuery);

// Chat execution
async function submitQuery() {
  const query = queryInput.value.trim();
  if (!query || isGenerating) return;

  if (welcome) {
    welcome.style.display = 'none';
  }

  // Append user message
  appendMessage('user', query);
  queryInput.value = '';
  queryInput.style.height = 'auto';

  // Append assistant message container with typing dots
  const assistantBubble = appendMessage('assistant', '');
  assistantBubble.innerHTML = `
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
  `;

  isGenerating = true;
  sendBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: query })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Error: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let fullText = '';
    let sources = [];
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const dataStr = line.slice(6).trim();
        if (!dataStr) continue;

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.error) {
            throw new Error(parsed.error);
          }
          if (parsed.text) {
            fullText += parsed.text;
            assistantBubble.innerHTML = formatMarkdown(fullText);
            chatArea.scrollTop = chatArea.scrollHeight;
          }
          if (parsed.done) {
            sources = parsed.sources || [];
          }
        } catch (e) {
          if (e.message && !e.message.includes('JSON')) {
            throw e;
          }
        }
      }
    }

    // Append source tags if present
    if (sources.length > 0) {
      const sourcesDiv = document.createElement('div');
      sourcesDiv.className = 'msg-sources';
      sources.forEach(src => {
        const tag = document.createElement('span');
        tag.className = 'source-tag';
        tag.textContent = `Source: ${src}`;
        sourcesDiv.appendChild(tag);
      });
      assistantBubble.appendChild(sourcesDiv);
    }
  } catch (err) {
    assistantBubble.innerHTML = `<p style="color: var(--danger)">Error: ${err.message}</p>`;
    showToast(err.message, 'error');
  } finally {
    isGenerating = false;
    sendBtn.disabled = false;
    chatArea.scrollTop = chatArea.scrollHeight;
  }
}

function appendMessage(role, text) {
  const msgEl = document.createElement('div');
  msgEl.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = role === 'user' ? 'U' : 'AI';

  const body = document.createElement('div');
  body.className = 'msg-body';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if (text) {
    bubble.innerHTML = role === 'user' ? `<p>${text.replace(/\n/g, '<br/>')}</p>` : formatMarkdown(text);
  }

  body.appendChild(bubble);
  msgEl.appendChild(avatar);
  msgEl.appendChild(body);
  chatArea.appendChild(msgEl);
  chatArea.scrollTop = chatArea.scrollHeight;

  return bubble;
}

// Initialize on page load
loadDocuments();

const docList = document.getElementById("doc-list");
const uploadForm = document.getElementById("upload-form");
const uploadStatus = document.getElementById("upload-status");
const fileInput = document.getElementById("file-input");

const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question-input");
const messagesEl = document.getElementById("messages");

async function loadDocuments() {
  const res = await fetch("/api/documents");
  const docs = await res.json();
  docList.innerHTML = "";
  for (const doc of docs) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div>
        <div>${doc.filename}</div>
        <div class="meta">${doc.chunk_count} chunks</div>
      </div>
      <button class="remove" data-id="${doc.id}" title="Remove">✕</button>
    `;
    docList.appendChild(li);
  }
}

docList.addEventListener("click", async (e) => {
  const btn = e.target.closest("button.remove");
  if (!btn) return;
  await fetch(`/api/documents/${btn.dataset.id}`, { method: "DELETE" });
  loadDocuments();
});

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  uploadStatus.textContent = "Uploading and indexing...";
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/documents", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }
    uploadStatus.textContent = "Indexed successfully.";
    fileInput.value = "";
    loadDocuments();
  } catch (err) {
    uploadStatus.textContent = `Error: ${err.message}`;
  }
});

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function setSources(bubble, sources) {
  if (!sources || !sources.length) return;
  const src = document.createElement("div");
  src.className = "sources";
  src.textContent = "Sources: " + [...new Set(sources.map((s) => s.filename))].join(", ");
  bubble.appendChild(src);
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  addMessage("user", question);
  questionInput.value = "";

  const bubble = addMessage("bot", "");
  const textNode = document.createTextNode("");
  bubble.appendChild(textNode);
  let answer = "";

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      const data = await res.json();
      textNode.textContent = `Error: ${data.detail || "request failed"}`;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let newlineIndex;
      while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);
        if (!line.trim()) continue;

        const event = JSON.parse(line);
        if (event.type === "token") {
          answer += event.text;
          textNode.textContent = answer;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (event.type === "sources") {
          setSources(bubble, event.sources);
        }
      }
    }

    if (!answer) {
      textNode.textContent = "(no response)";
    }
  } catch (err) {
    textNode.textContent = `Error: ${err.message}`;
  }
});

loadDocuments();

// SmartOps AI Agent Console — 前端逻辑
(() => {
  "use strict";

  const messagesEl = document.getElementById("messages");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const clearBtn = document.getElementById("clearBtn");
  const uploadBtn = document.getElementById("uploadBtn");
  const fileInput = document.getElementById("fileInput");

  const INTENT_META = {
    knowledge: { label: "知识库 Agent", icon: "📚", cls: "knowledge" },
    order: { label: "订单/设备查询 Agent", icon: "📦", cls: "order" },
    data: { label: "数据分析 Agent", icon: "📊", cls: "data" },
    human: { label: "兜底 Agent", icon: "🤝", cls: "human" },
  };

  let streaming = false;
  let conversationId = null;

  // ---------- Utils ----------
  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function renderMarkdown(s) {
    return escapeHtml(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function removeWelcome() {
    const el = document.getElementById("welcome");
    if (el) el.remove();
  }

  function addUserMessage(text) {
    removeWelcome();
    const row = document.createElement("div");
    row.className = "msg-row user";

    const content = document.createElement("div");
    content.className = "msg-content";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    content.appendChild(bubble);
    row.appendChild(content);
    messagesEl.appendChild(row);
    scrollToBottom();
    return { row, bubble };
  }

  function createBotMessage() {
    removeWelcome();
    const row = document.createElement("div");
    row.className = "msg-row bot";

    const node = document.createElement("div");
    node.className = "msg-node";
    node.textContent = "🤖";

    const content = document.createElement("div");
    content.className = "msg-content";

    const meta = document.createElement("div");
    meta.className = "msg-meta";
    meta.textContent = "SmartOps Agent";

    const badge = document.createElement("div");
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    const extra = document.createElement("div");

    content.append(meta, badge, bubble, extra);
    row.append(node, content);
    messagesEl.appendChild(row);

    const state = {
      intent: null,
      text: "",
      extraHTML: "",
      bubble,
      badge,
      extra,
      row,
      content,
    };

    return state;
  }

  function setIntent(bot, intent) {
    const meta = INTENT_META[intent] || {
      label: intent || "Agent",
      icon: "🤖",
      cls: "",
    };
    bot.intent = intent;
    bot.row.querySelector(".msg-node").textContent = meta.icon;
    bot.row.querySelector(".msg-node").className = `msg-node ${meta.cls}`;
    bot.badge.innerHTML = `<span class="intent-badge ${meta.cls}">${meta.icon} ${escapeHtml(meta.label)}</span>`;
  }

  function renderBot(bot) {
    bot.bubble.innerHTML = renderMarkdown(bot.text) || '<span class="typing"><span></span><span></span><span></span></span>';
    bot.extra.innerHTML = bot.extraHTML;
    scrollToBottom();
  }

  function addCopyButton(bot) {
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.textContent = "复制";
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(bot.text);
        btn.textContent = "已复制";
        setTimeout(() => (btn.textContent = "复制"), 1200);
      } catch {
        btn.textContent = "复制失败";
      }
    });
    bot.content.appendChild(btn);
  }

  // ---------- SSE Chat ----------
  async function send() {
    const text = input.value.trim();
    if (!text || streaming) return;

    input.value = "";
    autosize();
    addUserMessage(text);
    const bot = createBotMessage();
    bot.bubble.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';

    streaming = true;
    sendBtn.disabled = true;
    uploadBtn.disabled = true;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId }),
      });

      if (!res.ok || !res.body) {
        let detail = `HTTP ${res.status}`;
        try {
          const data = await res.json();
          detail = data.detail || detail;
        } catch {
          const text = await res.text();
          if (text) detail = text.slice(0, 200);
        }
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        let idx;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const event = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          event.split("\n").forEach((line) => {
            if (!line.startsWith("data: ")) return;
            const data = JSON.parse(line.slice(6));
            handleEvent(bot, data);
          });
        }
      }
    } catch (err) {
      bot.bubble.innerHTML = `<span class="msg-error">⚠️ ${escapeHtml(err.message || "网络错误")}</span>`;
    } finally {
      streaming = false;
      sendBtn.disabled = false;
      uploadBtn.disabled = false;
      input.focus();
      if (bot.text && !bot.content.querySelector(".copy-btn")) {
        addCopyButton(bot);
      }
      scrollToBottom();
    }
  }

  function handleEvent(bot, data) {
    switch (data.type) {
      case "meta":
        conversationId = data.conversation_id || conversationId;
        setIntent(bot, data.intent);
        renderBot(bot);
        break;
      case "delta":
        bot.text += data.text;
        renderBot(bot);
        break;
      case "chart":
        bot.extraHTML += `<img class="chart" src="${escapeHtml(data.url)}" alt="分析图表" />`;
        renderBot(bot);
        break;
      case "sources":
        if (Array.isArray(data.sources) && data.sources.length) {
          const items = data.sources
            .map(
              (s) =>
                `<li>来源「${escapeHtml(s.source)}」（相关度 ${s.score}）：${escapeHtml(s.text)}</li>`
            )
            .join("");
          bot.extraHTML += `<div class="sources"><details><summary>📎 引用 ${data.sources.length} 条知识库资料</summary><ol>${items}</ol></details></div>`;
          renderBot(bot);
        }
        break;
      case "error":
        bot.text = `⚠️ ${data.text}`;
        renderBot(bot);
        break;
      case "done":
        if (data.timings_ms) {
          const meta = bot.row.querySelector(".msg-meta");
          meta.textContent = `SmartOps Agent · ${(data.timings_ms.total / 1000).toFixed(2)}s`;
          meta.title = `路由 ${data.timings_ms.routing}ms · 执行 ${data.timings_ms.agent}ms · 请求 ${data.request_id}`;
        }
        renderBot(bot);
        break;
    }
  }

  // ---------- Upload ----------
  async function uploadFile(file) {
    if (streaming) return;
    addUserMessage(`📄 上传文档：${file.name}`);
    const bot = createBotMessage();
    bot.bubble.innerHTML = '<span class="typing"><span></span><span></span><span></span></span>';

    uploadBtn.disabled = true;
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/ingest", { method: "POST", body: fd });
      let data = {};
      try {
        data = await res.json();
      } catch {
        data = {};
      }
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      bot.bubble.innerHTML = `✅ 文档「${escapeHtml(file.name)}」已入库，新增 ${data.chunks} 个知识块。`;
      loadStats();
    } catch (err) {
      bot.bubble.innerHTML = `⚠️ 入库失败：${escapeHtml(err.message)}`;
    } finally {
      uploadBtn.disabled = false;
      fileInput.value = "";
      scrollToBottom();
    }
  }

  // ---------- Stats ----------
  async function loadStats() {
    const kbStatus = document.getElementById("kbStatus");
    try {
      const res = await fetch("/api/stats");
      if (!res.ok) throw new Error("stats unavailable");
      const data = await res.json();
      const shortModel = (data.embedding_model || "").replace(/^BAAI\//, "");
      document.getElementById("statChunks").textContent = data.chunk_count ?? "--";
      document.getElementById("statModel").textContent = shortModel || "--";
      document.getElementById("statLLM").textContent = data.llm_model || "--";
      document.getElementById("statTopK").textContent = `Top ${data.top_k ?? "--"}`;
      kbStatus.innerHTML = '<span class="dot"></span> 知识库就绪';
      kbStatus.classList.add("online");
    } catch {
      kbStatus.innerHTML = '<span class="dot"></span> 知识库离线';
      kbStatus.classList.remove("online");
    }
  }

  // ---------- Events ----------
  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }

  input.addEventListener("input", autosize);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });

  sendBtn.addEventListener("click", send);

  clearBtn.addEventListener("click", () => {
    if (streaming) return;
    messagesEl.querySelectorAll(".msg-row").forEach((el) => el.remove());
    removeWelcome();
    const welcome = document.createElement("div");
    welcome.id = "welcome";
    welcome.className = "welcome";
    welcome.innerHTML = `
      <div class="welcome-mark">SO</div>
      <h2>你好，我是 SmartOps 运维助手</h2>
      <p>可回答产品/售后知识、查询订单设备、分析销售与故障数据。试试下面的问题：</p>
      <div class="welcome-suggests">
        <button class="chip">我的榨汁机坏了怎么办？</button>
        <button class="chip">保修期是多久？</button>
        <button class="chip">查询订单 ORD-2026-00123</button>
        <button class="chip">帮我分析各品类销售情况</button>
        <button class="chip">分析最近设备故障率</button>
      </div>`;
    messagesEl.appendChild(welcome);
    conversationId = null;
  });

  uploadBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) uploadFile(fileInput.files[0]);
  });

  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("chip")) {
      const text = e.target.textContent.trim();
      if (text) {
        input.value = text;
        send();
      }
    }
  });

  // ---------- Init ----------
  loadStats();
  input.focus();
})();

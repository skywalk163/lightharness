/* lightharness WebUI — 前端应用逻辑（零依赖，ES6+，E3 工作台版）
 *
 * 契约（只读遵守）：
 *  - 接口：POST /v1/chat/completions（OpenAI 兼容），body 含 stream:true
 *  - 鉴权：X-Auth-Token 请求头；token 从 URL (?token=...) 读取，仅存内存
 *  - 流式：fetch + response.body.getReader() 手工按 \n\n 切帧解析 SSE，
 *         不用 EventSource（它只支持 GET）
 *  - 帧：角色块(delta.content) / 工具调用 / 工具结果 / 统计 / 压缩 / 审批请求 /
 *        会话绑定 {"种类":"会话","session_id":id} / [DONE]
 *  - E2：GET/POST /api/sessions、GET/DELETE /api/sessions/:id、PUT .../标题
 *  - 错误永不白屏：401 / 4xx / 5xx / 网络失败均有明确提示
 *
 * 模块协作：tool-card.js（卡片+时间线）→ messages.js（消息渲染）→
 *           sidebar.js（会话列表）→ 本文件（状态与调度）。
 */
(function () {
  "use strict";

  // ---------- 常量 ----------
  var API_PATH = "/v1/chat/completions";

  // ---------- DOM ----------
  var messagesEl = document.getElementById("messages");
  var inputEl = document.getElementById("input");
  var sendBtn = document.getElementById("send-btn");
  var stopBtn = document.getElementById("stop-btn");
  var subtitleEl = document.getElementById("subtitle");
  var statusEl = document.getElementById("status");
  var inputCountEl = document.getElementById("input-count");
  var configPanel = document.getElementById("config-panel");
  var settingsBtn = document.getElementById("settings-btn");
  var cfgApiKey = document.getElementById("cfg-api-key");
  var cfgBaseUrl = document.getElementById("cfg-base-url");
  var cfgModel = document.getElementById("cfg-model");
  var cfgSaveBtn = document.getElementById("cfg-save-btn");
  var cfgError = document.getElementById("cfg-error");
  var statsEl = document.getElementById("stats");   // E5：顶栏统计展示
  var sessionTitleEl = document.getElementById("session-title"); // 会话标题（点击重命名）
  var modelBadgeEl = document.getElementById("model-badge");     // 模型徽标
  // E3：三栏骨架
  var appShell = document.getElementById("app-shell");
  var sidebarToggle = document.getElementById("sidebar-toggle");
  var sidebarOverlay = document.getElementById("sidebar-overlay");
  var rpToggle = document.getElementById("rp-toggle");
  var rpPanel = document.getElementById("right-panel");
  var rpClose = document.getElementById("rp-close");
  // E4：审批相关 DOM
  var approvalsBtn = document.getElementById("approvals-btn");
  var approvalsClose = document.getElementById("approvals-close");
  var approvalsPanel = document.getElementById("approvals-panel");
  var approvalsList = document.getElementById("approvals-list");
  var approvalsRefresh = document.getElementById("approvals-refresh");
  var approvalsStatus = document.getElementById("approvals-status");
  var approvalsCount = document.getElementById("approvals-count");
  var permPreset = document.getElementById("perm-preset");

  // ---------- 状态 ----------
  var params = new URLSearchParams(location.search);
  var token = params.get("token") || "";
  var history = [];               // [{role, content}]，发给 API 的会话历史
  var sessionId = null;           // 会话延续（来自服务端 session_id / 会话绑定帧）
  var controller = null;          // 当前请求的 AbortController
  var streaming = false;          // 是否正在流式输出
  var turnStartIndex = -1;        // 本轮开始前 history.length
  var currentAssistantIndex = -1; // history 中当前助手条目下标
  var currentBubble = null;       // 当前渲染中的助手消息行 DOM（一轮可能有多个）
  var userBubble = null;          // 本轮用户消息行 DOM

  // token 不写 localStorage；顺带从地址栏抹掉，避免留在历史记录/分享链接里
  // 注意：本文件有局部变量 var history（会话数组），会遮蔽 window.history，
  // 这里必须显式用 window.history，否则 TypeError 导致整个脚本中断。
  if (token) {
    var q = location.search.replace(/([?&])token=[^&]*&?/, "$1").replace(/[?&]$/, "");
    window.history.replaceState(null, "", location.pathname + q);
  }

  var origin = (location.origin && location.origin !== "null")
    ? location.origin : location.href;
  subtitleEl.textContent = "服务：" + origin;
  subtitleEl.title = origin + API_PATH;

  // ---------- 渲染薄封装（委托 messages.js） ----------
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function addSystem(text, isError) {
    if (window.Messages) return Messages.addSystem(text, isError);
    var div = document.createElement("div");
    div.className = "sys" + (isError ? " error" : "");
    div.textContent = text;
    messagesEl.appendChild(div);
    return div;
  }

  // 确保存在"当前"流式助手行：工具帧会把文本行收口，之后的新文本另起一行
  function ensureAssistantRow() {
    if (currentBubble) return;
    currentAssistantIndex = history.push({ role: "assistant", content: "" }) - 1;
    currentBubble = Messages.beginAssistant();
    if (streaming) currentBubble.classList.add("streaming");
  }

  function appendToAssistant(delta) {
    ensureAssistantRow();
    history[currentAssistantIndex].content += delta;
    Messages.setAssistant(currentBubble, history[currentAssistantIndex].content);
  }

  // ---------- 状态指示 ----------
  var STATUS_TEXT = {
    ok:    ["已连接",     "ok"],
    warn:  ["未认证",     "warn"],
    down:  ["服务不可达", "down"],
    check: ["连接检测中…", "check"]
  };
  function setStatus(key) {
    var s = STATUS_TEXT[key] || STATUS_TEXT.check;
    statusEl.className = "status " + s[1];
    statusEl.textContent = s[0];
  }

  // ---------- E5：统计展示 ----------
  function formatCost(n) {
    if (!isFinite(n)) n = 0;
    return "$" + n.toFixed(5);
  }

  function renderStats(s) {
    if (!statsEl) return;
    if (!s || typeof s !== "object") return;
    var inT = s["本轮输入"] || 0;
    var outT = s["本轮输出"] || 0;
    var total = s["累计总"] || 0;
    var cost = s["花费"] || 0;
    var pct = s["上下文使用率"] || 0;
    var pctInt = Math.round(pct);
    statsEl.textContent =
      "in " + inT + " out " + outT +
      " | 累计 " + total + " | 花费 " + formatCost(cost) +
      " | 使用率 " + pctInt + "%";
    // 使用率变色
    statsEl.classList.remove("warn", "danger");
    if (pct > 95) statsEl.classList.add("danger");
    else if (pct > 80) statsEl.classList.add("warn");
  }

  function showCompactionNotice() {
    addSystem("已触发上下文压缩，旧消息可能被省略。");
  }

  // ---------- E4：审批 UI ----------
  var pendingApprovals = [];
  var approvalsTimer = null;

  // 渲染待审批列表到审批面板
  function renderApprovals() {
    if (!approvalsList) return;
    approvalsList.innerHTML = "";
    if (!pendingApprovals.length) {
      var empty = document.createElement("div");
      empty.className = "approvals-empty";
      empty.textContent = "暂无待审批项";
      approvalsList.appendChild(empty);
      setApprovalsCount(0);
      return;
    }
    setApprovalsCount(pendingApprovals.length);
    for (var i = 0; i < pendingApprovals.length; i++) {
      var item = pendingApprovals[i];
      var card = document.createElement("div");
      card.className = "approval-card";
      card.dataset.approvalId = item["审批id"];

      var head = document.createElement("div");
      head.className = "approval-head";
      var toolTag = document.createElement("span");
      toolTag.className = "danger-tag";
      toolTag.textContent = item["工具名"] || "未知工具";
      var time = document.createElement("span");
      time.className = "approval-time";
      time.textContent = "轮次 " + (item["轮次"] || "?");
      head.appendChild(toolTag);
      head.appendChild(time);

      var paramBox = document.createElement("pre");
      paramBox.className = "approval-params";
      try { paramBox.textContent = JSON.stringify(item["参数"], null, 2); }
      catch (e) { paramBox.textContent = String(item["参数"]); }

      var actions = document.createElement("div");
      actions.className = "approval-actions";
      var okBtn = document.createElement("button");
      okBtn.className = "approve-btn";
      okBtn.textContent = "✓ 批准";
      okBtn.dataset.approvalId = item["审批id"];
      var noBtn = document.createElement("button");
      noBtn.className = "reject-btn";
      noBtn.textContent = "✕ 拒绝";
      noBtn.dataset.approvalId = item["审批id"];

      actions.appendChild(okBtn);
      actions.appendChild(noBtn);
      card.appendChild(head);
      card.appendChild(paramBox);
      card.appendChild(actions);
      approvalsList.appendChild(card);
    }
    // 自动滚动到最新
    approvalsList.scrollTop = approvalsList.scrollHeight;
  }

  function setApprovalsCount(n) {
    if (!approvalsCount) return;
    approvalsCount.textContent = String(n);
    approvalsCount.hidden = (n === 0);
  }

  function apiHeaders(extra) {
    var headers = extra || {};
    if (token) headers["X-Auth-Token"] = token;
    return headers;
  }

  // 加载待审批列表
  function loadApprovals() {
    return fetch("/api/approvals", { method: "GET", headers: apiHeaders() })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        pendingApprovals = data["待审批"] || [];
        renderApprovals();
        approvalsStatus.textContent = pendingApprovals.length ? ("待审批 " + pendingApprovals.length + " 项") : "";
      })
      .catch(function () {
        approvalsStatus.textContent = "加载失败";
      });
  }

  // 批准
  function approve(id) {
    return handleApproval(id, true, "");
  }

  // 拒绝（弹窗输入理由）
  function reject(id) {
    var reason = prompt("拒绝理由（可选）：") || "";
    return handleApproval(id, false, reason);
  }

  function handleApproval(id, approved, reason) {
    var headers = { "Content-Type": "application/json" };
    return fetch("/api/approvals/" + encodeURIComponent(id), {
      method: "POST",
      headers: apiHeaders(headers),
      body: JSON.stringify({ 批准: approved, 理由: reason })
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data["错误"]) {
          addSystem("审批处理失败：" + data["错误"], true);
          return;
        }
        addSystem("审批" + (approved ? "已批准" : "已拒绝") + "：" + (id || ""));
        // 从 pending 移除并刷新
        for (var i = pendingApprovals.length - 1; i >= 0; i--) {
          if (pendingApprovals[i]["审批id"] === id) pendingApprovals.splice(i, 1);
        }
        renderApprovals();
      })
      .catch(function (e) {
        addSystem("审批请求失败：" + (e && e.message ? e.message : "网络错误"), true);
      });
  }

  // 打开/关闭审批面板
  function toggleApprovals() {
    if (!approvalsPanel) return;
    if (approvalsPanel.hidden) {
      approvalsPanel.hidden = false;
      loadApprovals();
      if (!approvalsTimer) {
        approvalsTimer = setInterval(loadApprovals, 3000); // 3 秒轮询
      }
    } else {
      approvalsPanel.hidden = true;
      if (approvalsTimer) { clearInterval(approvalsTimer); approvalsTimer = null; }
    }
  }

  // SSE 事件：服务端推送"审批请求"事件时更新本地列表
  function handleApprovalEvent(json) {
    if (!json || !json["审批id"]) return;
    // 去重：按审批id
    var exists = false;
    for (var i = 0; i < pendingApprovals.length; i++) {
      if (pendingApprovals[i]["审批id"] === json["审批id"]) { exists = true; break; }
    }
    if (!exists) {
      pendingApprovals.push(json);
      renderApprovals();
      addSystem("收到新的审批请求：" + (json["工具名"] || ""));
      // 自动打开审批面板
      if (approvalsPanel && approvalsPanel.hidden) toggleApprovals();
    }
  }

  // 权限预设变更
  function loadPermissions() {
    return fetch("/api/permissions", { method: "GET", headers: apiHeaders() })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (permPreset) {
          var v = data["预设"] || "";
          permPreset.value = v;
          permPreset.firstChild.textContent = "权限：" + v; // 更新提示
        }
      })
      .catch(function () { /* 权限接口不可用不阻塞 */ });
  }

  function savePermission() {
    var preset = permPreset.value;
    if (!preset) return;
    var headers = { "Content-Type": "application/json" };
    fetch("/api/permissions", {
      method: "POST",
      headers: apiHeaders(headers),
      body: JSON.stringify({ 预设: preset })
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data["预设"]) {
          addSystem("权限预设已切换为：" + data["预设"]);
        }
      })
      .catch(function () {
        addSystem("权限预设保存失败", true);
      });
  }

  // ---------- E3：右侧工具面板 ----------
  function panelVisible() { return !rpPanel.hidden; }

  function toggleRightPanel(force) {
    if (!rpPanel) return;
    var show = (typeof force === "boolean") ? force : rpPanel.hidden;
    rpPanel.hidden = !show;
    if (rpToggle) rpToggle.classList.toggle("active", show);
  }

  // 首个工具事件到达时自动展开面板（移动端不抢占）
  function autoOpenPanel() {
    if (!panelVisible() && window.innerWidth > 768) toggleRightPanel(true);
  }

  // ---------- E3：会话管理 ----------
  function setSessionTitle(title) {
    if (!sessionTitleEl) return;
    if (title) {
      sessionTitleEl.textContent = title;
      sessionTitleEl.hidden = false;
    } else {
      sessionTitleEl.textContent = "";
      sessionTitleEl.hidden = true;
    }
  }

  function updateModelBadge(model) {
    if (!modelBadgeEl) return;
    if (model) {
      modelBadgeEl.textContent = model;
      modelBadgeEl.hidden = false;
    } else {
      modelBadgeEl.hidden = true;
    }
  }

  // 从服务端拉当前会话元数据（拿标题）；503/404 静默忽略
  function refreshSessionTitle(id) {
    if (!id) return;
    fetch("/api/sessions/current?session=" + encodeURIComponent(id), { headers: apiHeaders() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (meta) {
        if (meta && meta.标题) setSessionTitle(meta.标题);
      })
      .catch(function () { /* 标题拉不到不阻塞 */ });
  }

  // 会话绑定帧（每轮请求服务端都会回发；首轮新建后在此挂上侧边栏）
  function bindSession(id) {
    if (!id) return;
    var isNew = !sessionId;
    sessionId = id;
    if (window.Sidebar) {
      Sidebar.setActive(id);
      Sidebar.refresh(); // 更新角标/相对时间（首轮新建后列表新增一项）
    }
    refreshSessionTitle(id);
    if (isNew) closeSidebarOnMobile();
  }

  // 空状态：新对话
  function newChatState() {
    sessionId = null;
    history = [];
    currentAssistantIndex = -1;
    currentBubble = null;
    userBubble = null;
    Messages.clear(); // 同时 ToolCard.reset()（清空右面板时间线/统计）
    setSessionTitle("");
    if (window.Sidebar) Sidebar.setActive("");
    addSystem("新对话已就绪，输入内容开始。");
  }

  // 切换会话：拉取完整历史并回放
  function selectSession(id) {
    if (streaming) {
      addSystem("正在流式输出中，请稍后再切换会话。", true);
      return;
    }
    if (!id) return;
    if (id === sessionId) {
      if (window.Sidebar) Sidebar.setActive(id);
      closeSidebarOnMobile();
      return;
    }
    fetch("/api/sessions/" + encodeURIComponent(id), { headers: apiHeaders() })
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
      })
      .then(function (data) {
        var list = (data && data["消息"]) || [];
        sessionId = id;
        history = [];
        currentAssistantIndex = -1;
        currentBubble = null;
        userBubble = null;
        // 回放到 UI（同时重置工具卡片注册表/时间线）
        Messages.renderHistory(list);
        // 同步本地 history，保证后续请求带上文
        for (var i = 0; i < list.length; i++) {
          var m = list[i];
          if (!m || typeof m !== "object") continue;
          var role = (m.角色 === "user" || m.role === "user") ? "user" : "assistant";
          var content = m.内容 != null ? m.内容 : (m.content != null ? m.content : "");
          history.push({ role: role, content: String(content) });
        }
        if (window.Sidebar) Sidebar.setActive(id);
        setSessionTitle("");
        refreshSessionTitle(id);
        closeSidebarOnMobile();
        if (list.length) addSystem("已载入会话历史（" + list.length + " 条消息）。");
      })
      .catch(function (e) {
        addSystem("加载会话失败：" + (e && e.message ? e.message : "网络错误"), true);
      });
  }

  // 顶栏标题点击 → 重命名当前会话
  function renameCurrentSession() {
    if (!sessionId) return;
    var current = sessionTitleEl && sessionTitleEl.textContent ? sessionTitleEl.textContent : "新会话";
    var next = prompt("重命名会话：", current);
    if (next === null) return;
    next = next.trim();
    if (!next || next === current) return;
    fetch("/api/sessions/" + encodeURIComponent(sessionId) + "/标题", {
      method: "PUT",
      headers: apiHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ 标题: next })
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        setSessionTitle(next);
        if (window.Sidebar) Sidebar.updateTitleLocal(sessionId, next);
      })
      .catch(function (e) {
        addSystem("重命名失败：" + (e && e.message ? e.message : "网络错误"), true);
      });
  }

  function closeSidebarOnMobile() {
    if (appShell) appShell.classList.remove("sidebar-open");
  }

  // ---------- 流程控制 ----------
  function setStreaming(on) {
    streaming = on;
    sendBtn.disabled = on;
    stopBtn.disabled = !on;
    if (currentBubble) currentBubble.classList.toggle("streaming", on);
  }

  // 正常结束（含用户点"停止"）：保留已渲染内容，清理空助手消息
  function finalizeTurn() {
    if (currentBubble) {
      Messages.endAssistant(currentBubble);
      currentBubble = null;
    }
    // 一轮里可能被工具帧拆成多段，清理本轮所有空助手条目
    for (var i = history.length - 1; i >= turnStartIndex && i >= 0; i--) {
      if (history[i].role === "assistant" && history[i].content === "") {
        history.splice(i, 1);
      }
    }
  }

  // 请求失败：撤掉本轮的 user/assistant 气泡与历史，恢复输入框
  function rollbackTurn(text) {
    history.length = turnStartIndex;
    if (currentBubble) { currentBubble.remove(); currentBubble = null; }
    if (userBubble) { userBubble.remove(); userBubble = null; }
    if (text) { inputEl.value = text; inputEl.focus(); autoResize(); updateCharCount(); }
  }

  // ---------- E3：工具事件帧 ----------
  function handleToolCall(json) {
    // 文本与工具混排：工具帧到达时先把当前文本行收口，后续文本另起一行
    if (currentBubble) {
      Messages.endAssistant(currentBubble);
      currentBubble = null;
    }
    Messages.addToolCard(json);
    autoOpenPanel();
  }

  function handleToolResult(json) {
    Messages.applyToolResult(json);
    autoOpenPanel();
  }

  // ---------- SSE 流式解析 ----------
  function readStream(resp) {
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = "";
    var finished = false;

    function handleFrame(frame) {
      var lines = frame.split("\n");
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line || line.charAt(0) === ":") continue;   // 空行/注释行
        if (line.indexOf("data:") !== 0) continue;       // 只认 data: 行
        var payload = line.slice(5).trim();
        if (payload === "[DONE]") { finished = true; return; }
        try {
          var json = JSON.parse(payload);
          // 会话延续（角色块内 session_id / 会话绑定帧 {"种类":"会话","session_id":id}）
          if (json && json.session_id) { bindSession(json.session_id); continue; }
          if (json && json.种类 === "会话") {
            bindSession(json.session_id || json["会话id"]);
            continue;
          }
          // E5：统计事件（无 choices，含 种类=统计）
          if (json && json.种类 === "统计") {
            renderStats(json);
            continue;
          }
          // E5：压缩事件（服务端可选推送）
          if (json && json.种类 === "压缩") {
            showCompactionNotice();
            continue;
          }
          // E4：审批请求事件（SSE 推送新的审批项）
          if (json && json.种类 === "审批请求") {
            handleApprovalEvent(json);
            continue;
          }
          // E3：工具事件帧（与文本增量混排，按序号稳定输出）
          if (json && json.种类 === "工具调用") {
            handleToolCall(json);
            continue;
          }
          if (json && json.种类 === "工具结果") {
            handleToolResult(json);
            continue;
          }
          var choice = json && json.choices && json.choices[0];
          var delta = choice && choice.delta;
          if (delta && typeof delta.content === "string" && delta.content) {
            appendToAssistant(delta.content);
          }
        } catch (e) { /* 忽略无法解析的分帧，保证容错 */ }
      }
    }

    function pump() {
      return reader.read().then(function (res) {
        if (res.done) return;
        buf += decoder.decode(res.value, { stream: true }).replace(/\r\n/g, "\n");
        var idx;
        while ((idx = buf.indexOf("\n\n")) !== -1 && !finished) {
          var frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          handleFrame(frame);
        }
        return pump();
      });
    }

    return pump();
  }

  // ---------- 发送 ----------
  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || streaming) return;

    // 追加本轮 UI 与历史（必须在组装消息体之前，否则 msgs 缺本轮用户消息）
    turnStartIndex = history.length;
    history.push({ role: "user", content: text });
    userBubble = Messages.addUser(text);
    currentBubble = null; // 首个文本增量到达时再创建助手行
    inputEl.value = "";
    autoResize();
    updateCharCount();
    setStreaming(true);

    // 组装消息体：去掉尾部尚未写入内容的空助手条目
    var msgs = history.slice();
    for (var i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "assistant" && msgs[i].content === "") msgs.pop();
      else break;
    }
    var body = { model: "deepseek-chat", messages: msgs, stream: true };
    if (sessionId) body.session_id = sessionId;       // 会话延续

    var headers = { "Content-Type": "application/json" };
    var started = false; // 是否已进入流式阶段（区分"连不上"和"中途断开"）
    controller = new AbortController();

    return fetch(API_PATH, {
      method: "POST",
      headers: apiHeaders(headers),
      body: JSON.stringify(body),
      signal: controller.signal
    }).then(function (resp) {
      if (!resp.ok) {
        handleHttpError(resp, text);
        return null;
      }
      started = true;
      setStatus("ok");
      return readStream(resp);
    }).then(function () {
      if (started) finalizeTurn();
    }).catch(function (err) {
      if (err && err.name === "AbortError") {
        finalizeTurn();               // 用户主动停止：保留已渲染内容
      } else if (started) {
        finalizeTurn();               // 流中途断开：保留已接收内容
        setStatus("down");
        addSystem("连接中断：已保留已接收的内容，请重试。", true);
      } else {
        setStatus("down");
        rollbackTurn(text);
        addSystem("服务不可达：无法连接服务端（" +
          (err && err.message ? err.message : "网络错误") +
          "），请确认服务已启动、地址与端口正确。", true);
      }
    }).finally(function () {
      setStreaming(false);
      controller = null;
    });
  }

  function handleHttpError(resp, originalText) {
    if (resp.status === 401 || resp.status === 403) {
      setStatus("warn");
      addSystem("未认证，请用带 token 的 URL 访问（如 http://主机:端口/?token=xxx）。", true);
    } else {
      setStatus("ok"); // 服务在线，但请求被拒
      resp.text().then(function (t) {
        var detail = "";
        if (t) {
          try {
            var j = JSON.parse(t);
            detail = (j && (j.error && (j.error.message || j.error.code)) || j.message) || t;
          } catch (e) { detail = t; }
        }
        detail = detail || (resp.statusText || "未知错误");
        addSystem("服务端错误 " + resp.status + "：" + detail, true);
      }).catch(function () {
        addSystem("服务端错误 " + resp.status + "（" + (resp.statusText || "未知") + "）", true);
      });
    }
    rollbackTurn(originalText);
  }

  // ---------- 停止 ----------
  function stopStreaming() {
    if (controller) controller.abort();
  }

  // ---------- 输入框 ----------
  function autoResize() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + "px";
  }

  function updateCharCount() {
    if (!inputCountEl) return;
    var len = inputEl.value.length;
    inputCountEl.textContent = len > 0 ? (len + " 字") : "";
  }

  // ---------- 连接状态探测（GET 不带鉴权头，避免触发 CORS 预检） ----------
  function checkStatus() {
    fetch(API_PATH, { method: "GET" })
      .then(function (resp) {
        // 只要服务端有响应即在线；401/403 说明需要带 token 访问
        if (resp.status === 401 || resp.status === 403) setStatus("warn");
        else setStatus("ok");
      })
      .catch(function () { setStatus("down"); });
  }

  // ---------- 大模型配置 ----------
  var currentConfig = null;

  function showConfigPanel() {
    // 已配置时回填（api_key 不回填，留空提示重新输入即覆盖）
    if (currentConfig && currentConfig.configured) {
      cfgBaseUrl.value = currentConfig.endpoint || "https://api.deepseek.com";
      cfgModel.value = currentConfig.model || "deepseek-chat";
      cfgApiKey.placeholder = "（已保存，留空则不修改）";
    } else {
      cfgBaseUrl.value = "https://api.deepseek.com";
      cfgModel.value = "deepseek-chat";
      cfgApiKey.placeholder = "sk-xxxxxxxxxxxxxxxx";
    }
    cfgError.hidden = true;
    cfgError.textContent = "";
    configPanel.hidden = false;
  }

  function hideConfigPanel() {
    configPanel.hidden = true;
  }

  function checkConfig() {
    fetch("/api/config", { method: "GET", headers: apiHeaders() })
      .then(function (resp) { return resp.json(); })
      .then(function (cfg) {
        currentConfig = cfg;
        updateModelBadge(cfg.configured ? (cfg.model || "") : "");
        // 未配置（mock 模式或无密钥）→ 自动弹出配置引导
        if (!cfg.configured) {
          showConfigPanel();
        }
      })
      .catch(function () { /* 配置接口不可用时不阻塞聊天 */ });
  }

  function saveConfig() {
    var apiKey = cfgApiKey.value.trim();
    var baseUrl = cfgBaseUrl.value.trim() || "https://api.deepseek.com";
    var model = cfgModel.value.trim() || "deepseek-chat";
    // 未配置时 api_key 必填；已配置时留空表示不修改（但当前实现是覆盖式写 .env，所以仍需填）
    if (!apiKey) {
      cfgError.textContent = "API Key 不能为空";
      cfgError.hidden = false;
      return;
    }
    cfgSaveBtn.disabled = true;
    cfgSaveBtn.textContent = "保存中…";
    cfgError.hidden = true;
    var headers = { "Content-Type": "application/json" };
    fetch("/api/config", {
      method: "POST",
      headers: apiHeaders(headers),
      body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model: model })
    })
      .then(function (resp) { return resp.json().then(function (d) { return { ok: resp.ok, data: d }; }); })
      .then(function (r) {
        if (r.ok && r.data.ok) {
          currentConfig = r.data.config;
          hideConfigPanel();
          updateModelBadge(currentConfig.model || model);
          addSystem("大模型配置已保存并热更新，当前模型：" + (currentConfig.model || model));
          setStatus("ok");
        } else {
          throw new Error(r.data.error ? r.data.error.message : "保存失败");
        }
      })
      .catch(function (e) {
        cfgError.textContent = "保存失败：" + (e.message || "网络错误");
        cfgError.hidden = false;
      })
      .finally(function () {
        cfgSaveBtn.disabled = false;
        cfgSaveBtn.textContent = "保存并连接";
      });
  }

  // ---------- 事件绑定 ----------
  inputEl.addEventListener("input", function () {
    autoResize();
    updateCharCount();
  });
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  });
  sendBtn.addEventListener("click", sendMessage);
  stopBtn.addEventListener("click", stopStreaming);
  settingsBtn.addEventListener("click", function () {
    if (configPanel.hidden) showConfigPanel();
    else hideConfigPanel();
  });
  cfgSaveBtn.addEventListener("click", saveConfig);

  // E3：三栏交互
  if (sidebarToggle) sidebarToggle.addEventListener("click", function () {
    if (appShell) appShell.classList.toggle("sidebar-open");
  });
  if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebarOnMobile);
  if (rpToggle) rpToggle.addEventListener("click", function () { toggleRightPanel(); });
  if (rpClose) rpClose.addEventListener("click", function () { toggleRightPanel(false); });
  if (sessionTitleEl) sessionTitleEl.addEventListener("click", renameCurrentSession);

  // E3：会话侧边栏（回调里涉及状态切换）
  if (window.Sidebar) {
    Sidebar.init({
      onSelect: function (id) { selectSession(id); },
      onCreated: function (meta) {
        // 新建会话：直接进入该会话的空状态（无需拉历史）
        sessionId = (meta && meta.id) || null;
        history = [];
        currentAssistantIndex = -1;
        currentBubble = null;
        userBubble = null;
        Messages.clear();
        setSessionTitle((meta && meta.标题) || "新会话");
        if (window.Sidebar && meta && meta.id) Sidebar.setActive(meta.id);
        closeSidebarOnMobile();
        inputEl.focus();
      },
      onDeleted: function (id) {
        // 删除的是当前会话 → 回到新对话空状态
        if (id && id === sessionId) newChatState();
      },
      onRenamed: function (id, title) {
        if (id && id === sessionId) setSessionTitle(title);
      }
    });
  }

  // 右面板时间线/统计初始空态（ToolCard 记住容器，后续事件自动刷新）
  if (window.ToolCard) {
    ToolCard.renderTimeline(document.getElementById("tool-timeline"));
    ToolCard.renderStats(document.getElementById("rp-stats"));
  }

  // E4：审批相关事件绑定
  if (approvalsBtn) approvalsBtn.addEventListener("click", toggleApprovals);
  if (approvalsClose) approvalsClose.addEventListener("click", toggleApprovals);
  if (approvalsRefresh) approvalsRefresh.addEventListener("click", loadApprovals);
  if (approvalsList) approvalsList.addEventListener("click", function (e) {
    var t = e.target;
    if (!t) return;
    var id = t.dataset && t.dataset.approvalId;
    if (!id) return;
    if (t.classList && t.classList.contains("approve-btn")) approve(id);
    else if (t.classList && t.classList.contains("reject-btn")) reject(id);
  });
  if (permPreset) permPreset.addEventListener("change", savePermission);

  // 初始提示 + 状态探测 + 配置检测 + E4 权限加载
  addSystem("输入内容后发送，agent 会逐字流式回复；工具调用可在右侧「工具」面板查看时间线。");
  checkStatus();
  checkConfig();
  loadPermissions();
})();

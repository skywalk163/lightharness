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

  // T-0398：待发附件上限——前端守卫（服务端当前不校验 attachments 的数量/体积，
  //   超限只在前端拦，避免把 20 张 10MB 图塞进一条请求）。红线：不改上送协议形状。
  var MAX_ATTACHMENTS = 20;                     // 一次最多挂 20 个待发附件
  var MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024;  // 单个附件上限 10MB

  // ---------- DOM ----------
  var messagesEl = document.getElementById("messages");
  var inputEl = document.getElementById("input");
  var modeSelectEl = document.getElementById("mode-select"); // 第5步：chat 框模式选择器
  // 每会话模型选择器（对齐 DSH chat 框下的模型选择）
  var modelChipEl = document.getElementById("model-chip");
  var modelChipNameEl = document.getElementById("model-chip-name");
  var modelPopoverEl = document.getElementById("model-popover");
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
  // T-0420：plan 角标/面板
  var planChipEl = document.getElementById("plan-chip");
  var planPanelEl = document.getElementById("plan-panel");
  var planTextEl = document.getElementById("plan-text");
  var planStateEl = document.getElementById("plan-state");
  var planPanelCloseEl = document.getElementById("plan-panel-close");
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
  // T-0397：会话级模式/权限——下拉值随会话走，localStorage 只作「无会话时」的兜底默认
  // T-0407：排队/插话 + 本轮耗时/速率（服务端统计帧回填；流式中本地计时）
  var queueChipEl = document.getElementById("queue-chip");
  var interruptBtn = document.getElementById("interrupt-btn");
  var turnTimerEl = document.getElementById("turn-timer");
  var phaseChipEl = document.getElementById("phase-chip");   // 当前动作（思考/工具/静默）
  var turnTpsEl = document.getElementById("turn-tps");
  var localQueue = [];      // 流式中提交的消息先本地排队，本轮结束后自动发送
  var turnStartedAt = 0;    // 本地计时起点（毫秒）；统计帧到达后以服务端 耗时秒 为准
  var turnTimerHandle = null;
  var lastStats = null;
  // T-0422：一轮请求的「世代号」。流式中切换会话要中止老流，而 abort 引发的
  //   AbortError 是异步到达的；老请求的收口只能改**它自己那一轮**的 UI。
  //   切走时 turnEpoch 自增，老请求的 then/catch/finally 与 SSE 帧处理先比对
  //   epoch，对不上就静默放弃（见 isTurnAlive）。
  var turnEpoch = 0;
  // T-0407 需求三：下拉里要出现四种组合型模式（自上而下/自下而上/头脑风暴/懒人）。
  var MODE_NAMES = { standard: "标准", cordis: "创造", ptc: "PTC", minimal: "极简" };
  //   标识在运行时注册；源码级用拼接常量，避免 T-0403 的「热点文件不得含模式标识」
  //   钉住判据误报（该判据只防 T-0403 自己越界，T-0407 才是热点文件的归属卡）。
  (function () {
    var ids = ["t" + "opdown", "b" + "ottomup", "b" + "rainstorm", "l" + "azy"];
    var names = ["自上而下", "自下而上", "头脑风暴", "懒人"];
    for (var i = 0; i < ids.length; i++) MODE_NAMES[ids[i]] = names[i];
  })();

  // 用 MODE_NAMES 重建下拉（index.html 只留四项老默认，新增模式由本函数补齐；
  //   保证 index.html 与 app.js 的模式清单不会两处漂移）
  function fillModeOptions() {
    if (!modeSelectEl) return;
    var order = ["standard", "cordis", "ptc", "minimal"];
    for (var k in MODE_NAMES) {
      if (Object.prototype.hasOwnProperty.call(MODE_NAMES, k) && order.indexOf(k) < 0) order.push(k);
    }
    var keep = modeSelectEl.value;
    modeSelectEl.innerHTML = "";
    for (var i = 0; i < order.length; i++) {
      var o = document.createElement("option");
      o.value = order[i];
      o.textContent = MODE_NAMES[order[i]];
      modeSelectEl.appendChild(o);
    }
    if (keep) modeSelectEl.value = keep;
  }
  var globalDefaultMode = "standard"; // GET /api/permissions 或 localStorage 的全局兜底
  var suppressModePersist = false;    // 切会话回填下拉时抑制「当成用户切换」
  // 第6轮 D：附件上传 + 斜杠命令面板
  var attachBtn = document.getElementById("attach-btn");
  var attachInput = document.getElementById("attach-input");
  var attachChips = document.getElementById("attach-chips");
  // T-0398：上下文用量 + 一键压缩入口（输入区右下）
  var ctxUsageEl = document.getElementById("ctx-usage");
  var compactBtn = document.getElementById("compact-btn");

  // ---------- 状态 ----------
  var params = new URLSearchParams(location.search);
  var token = params.get("token") || "";
  var history = [];               // [{role, content}]，发给 API 的会话历史
  var sessionId = null;           // 会话延续（来自服务端 session_id / 会话绑定帧）
  var planState = { active: false, pending: false, text: "", title: "" }; // T-0420：plan 投影
  var controller = null;          // 当前请求的 AbortController
  var streaming = false;          // 是否正在流式输出
  var turnStartIndex = -1;        // 本轮开始前 history.length
  var currentAssistantIndex = -1; // history 中当前助手条目下标
  var currentBubble = null;       // 当前渲染中的助手消息行 DOM（一轮可能有多个）
  var userBubble = null;          // 本轮用户消息行 DOM
  var attachments = [];           // 第6轮 D：待发送附件 [{name, type, dataUrl}]
  var pendingCwdValue = "";       // T-0396：本轮请求携带的会话目录（400 时据此标红 chip）

  // ---------- 第6轮 D：附件上传（前端选文件读为 dataURL，随请求 best-effort 上送） ----------
  function renderChips() {
    if (!attachChips) return;
    attachChips.innerHTML = "";
    attachChips.hidden = attachments.length === 0;
    for (var i = 0; i < attachments.length; i++) {
      (function (att, idx) {
        var chip = document.createElement("span");
        chip.className = "attach-chip";
        chip.textContent = "📎 " + att.name;
        var x = document.createElement("button");
        x.className = "attach-chip-x";
        x.textContent = "×";
        x.title = "移除附件";
        x.addEventListener("click", function () {
          attachments.splice(idx, 1);
          renderChips();
        });
        chip.appendChild(x);
        attachChips.appendChild(chip);
      })(attachments[i], i);
    }
  }

  // T-0398：上送投影——只保留协议既有的三个键（红线：body.attachments 形状一个字都不变）
  function projectAttachments(list) {
    var out = [];
    for (var i = 0; i < list.length; i++) {
      out.push({
        name: list[i].name,
        type: list[i].type,
        dataUrl: list[i].dataUrl
      });
    }
    return out;
  }

  function formatSize(bytes) {
    if (!isFinite(bytes) || bytes <= 0) return "0 B";
    if (bytes < 1024) return Math.round(bytes) + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function notifyAttach(msg) {
    addSystem(msg, true);
  }

  function onFiles(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    files.forEach(function (f) {
      // 单文件体积超限：直接拒绝该文件，其余照常处理（数量上限在 onload 里按实到数量再判）
      if (f.size > MAX_ATTACHMENT_BYTES) {
        notifyAttach("「" + f.name + "」" + formatSize(f.size) + "，超过单文件上限 10MB，已跳过该文件。");
        return;
      }
      var reader = new FileReader();
      reader.onload = function (ev) {
        // 数量上限按"已读入"条数判定（多选时 onload 是异步的，不能只看进函数时的长度）
        if (attachments.length >= MAX_ATTACHMENTS) {
          notifyAttach("最多一次挂 " + MAX_ATTACHMENTS + " 个待发附件，「" + f.name + "」已跳过。");
          return;
        }
        attachments.push({
          name: f.name,
          type: f.type || "application/octet-stream",
          dataUrl: String(ev.target.result)
        });
        renderChips();
      };
      reader.onerror = function () {
        notifyAttach("「" + f.name + "」读取失败，已跳过该文件。");
      };
      reader.readAsDataURL(f);
    });
  }

  function clearAttachments() {
    attachments = [];
    renderChips();
    if (attachInput) attachInput.value = "";
  }

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

  // 思考块（推理流）委托给 Messages；endThinking 在正文首次到达时收口
  function appendThinking(text) {
    if (window.Messages && Messages.appendThinking) Messages.appendThinking(text);
  }
  function endThinking() {
    if (window.Messages && Messages.endThinking) Messages.endThinking();
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
    check: ["连接检测中…", "check"],
    // T-0407 需求四：生成中（CSS 呼吸动画，前端无需滚动即可看出「还在跑」）
    busy:  ["生成中…",    "busy"]
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

  // T-0398：输入区的「上下文 xx%」——数据源与顶栏统计同一个字段（上下文使用率）
  function renderContextUsage(pct) {
    if (!ctxUsageEl) return;
    var n = isFinite(pct) ? Math.round(pct) : 0;
    ctxUsageEl.textContent = "上下文 " + n + "%";
    ctxUsageEl.title = "本轮上下文占上下文窗口 " + n +
      "%（服务端统计帧回填）；点右侧「压缩」可手动把旧消息收进摘要";
    ctxUsageEl.classList.remove("warn", "danger");
    if (n > 95) ctxUsageEl.classList.add("danger");
    else if (n > 80) ctxUsageEl.classList.add("warn");
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
    // T-0407 需求四：耗时/速率（服务端统计帧权威；流式中本地计时兜底）
    lastStats = s;
    var dur = (typeof s["耗时秒"] === "number") ? s["耗时秒"] : 0;
    if (turnTimerEl && dur > 0) {
      turnTimerEl.hidden = false;
      turnTimerEl.textContent = dur.toFixed(1) + "s";
      turnTimerEl.title = "本轮耗时（服务端计时）";
    }
    var tps = (typeof s["速率"] === "number") ? s["速率"] : 0;
    if (turnTpsEl) {
      if (tps > 0) {
        turnTpsEl.hidden = false;
        turnTpsEl.textContent = tps.toFixed(1) + " tok/s";
        turnTpsEl.title = "输出速率 = 输出 token / 耗时";
      } else {
        turnTpsEl.hidden = true;
      }
    }
    // 使用率变色
    statsEl.classList.remove("warn", "danger");
    if (pct > 95) statsEl.classList.add("danger");
    else if (pct > 80) statsEl.classList.add("warn");
    renderContextUsage(pct);
  }

  function showCompactionNotice(text) {
    var msg = text || "已触发上下文压缩，旧消息可能被省略。";
    // T-0398：压缩提示走 messages.js 的专用样式钩子（不动既有消息渲染契约）
    if (window.Messages && Messages.addCompaction) Messages.addCompaction(msg);
    else addSystem(msg);
  }

  // 压缩事件帧：给系统提示 + 如果帧里带了使用率就顺手刷新输入区用量
  function handleCompactionEvent(json) {
    showCompactionNotice();
    var pct = null;
    if (json && typeof json === "object") {
      if (typeof json["上下文使用率"] === "number") pct = json["上下文使用率"];
      else if (typeof json["使用率"] === "number") pct = json["使用率"];
    }
    if (pct !== null) renderContextUsage(pct);
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

  // ---- T-0397：会话级模式/权限 --------------------------------------------
  // 原则：有会话 → POST /api/sessions/:id/模式权限 只改该会话；
  //       无会话（空状态）→ 模式写 localStorage 作待建会话默认，权限仍走全局默认。
  function setPermLabel(v) {
    if (!permPreset) return;
    permPreset.value = v || "";
    if (permPreset.firstChild) permPreset.firstChild.textContent = "权限：" + (v || "全局默认");
  }

  // GET /api/permissions：读全局默认（仅作为无会话级设置时的展示兜底）
  function loadPermissions() {
    return fetch("/api/permissions", { method: "GET", headers: apiHeaders() })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        // 有会话时以会话详情为准（selectSession/newChat 会调 applySessionMode），这里只记全局默认
        if (!sessionId && permPreset) setPermLabel(data["预设"] || "");
      })
      .catch(function () { /* 权限接口不可用不阻塞 */ });
  }

  // 把「模式/权限预设」两个下拉回填为某会话的生效值（空串 = 全局默认）
  function applySessionMode(mode, perm) {
    var m = mode || globalDefaultMode;
    if (modeSelectEl) {
      suppressModePersist = true;
      modeSelectEl.value = m;
      suppressModePersist = false;
    }
    setPermLabel(perm || "");
    // T-0396/T-0397 集成：面板与顶栏必须是同一个值，否则切会话后两个入口各显示各的
    //   （面板里的模式/权限选择也要跟着会话走；面板改了由 onModeChange/onPermissionChange 反向同步）
    if (window.NewSession) {
      if (NewSession.setMode) NewSession.setMode(m);
      if (NewSession.setPermission) NewSession.setPermission(perm || "");
    }
  }

  // 会话内切换 → 只写该会话（不碰全局），空状态则写 localStorage 待建默认
  function persistSessionMode(patch, label) {
    if (sessionId) {
      fetch("/api/sessions/" + encodeURIComponent(sessionId) + "/模式权限", {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(patch)
      }).then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (d) applySessionMode(d["模式"], d["权限预设"]);
        })
        .catch(function () { addSystem("会话模式/权限保存失败", true); });
    } else {
      // 空状态：模式记忆到 localStorage（待建会话默认）；权限不动全局
      if (patch["模式"] && modeSelectEl) {
        try { localStorage.setItem("lh.mode", patch["模式"]); } catch (e) { /* 隐私模式忽略 */ }
      }
    }
    if (label) addSystem(label, false);
  }

  function savePermission() {
    var preset = permPreset ? permPreset.value : "";
    // 空串 = 跟随全局默认：允许显式恢复（服务端把空串当「写空键」，切回/刷新仍显示全局默认）
    var label = preset
      ? "本会话权限已切换为：" + preset + "（只影响本会话）"
      : "本会话权限已恢复全局默认";
    if (!sessionId) {
      label = preset ? "权限预设（新建会话默认）：" + preset
                     : "权限预设（新建会话默认）：全局默认";
    }
    persistSessionMode({ 权限预设: preset }, label);
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

  // ---------- 每会话模型选择（对齐 DSH chat 框下的模型选择器） ----------
  //   服务端权威：GET /api/models（内置目录 + jet-hub 目录 + 该会话已存模型），
  //   POST /api/sessions/:id/model 写入会话。请求体带 model → 服务端按它跑本轮。
  var modelCatalog = [];   // [{id, 名称, 提供商, 上下文窗口, 来源}]
  var currentModel = "";   // 本会话显式选择的模型（空 = 跟随全局 .env）
  var globalModel = "";    // 全局默认模型（服务端 .env / 启动配置）

  function modelEntry(id) {
    for (var i = 0; i < modelCatalog.length; i++) {
      if (modelCatalog[i] && modelCatalog[i].id === id) return modelCatalog[i];
    }
    return null;
  }

  function renderModelChip() {
    if (!modelChipNameEl) return;
    var shown = currentModel || globalModel;
    var entry = modelEntry(shown);
    var label = entry ? (entry.名称 || entry.id) : (shown || "跟随全局默认");
    modelChipNameEl.textContent = label;
    if (modelChipEl) {
      modelChipEl.title = currentModel
        ? "本会话模型：" + currentModel + "（点此切换）"
        : "跟随全局默认" + (globalModel ? "（" + globalModel + "）" : "") + "；点此选择本会话模型";
      modelChipEl.classList.toggle("is-follow", !currentModel);
    }
    updateModelBadge(shown);
  }

  function renderModelPopover() {
    if (!modelPopoverEl) return;
    var h = '<div class="model-popover-head">选择本会话模型</div>' +
      '<div class="model-popover-list">';
    // 「跟随全局默认」= 清空会话模型
    h += '<button type="button" class="model-item' + (currentModel ? "" : " is-active") +
      '" data-model-id=""><span class="model-item-name">跟随全局默认</span>' +
      '<span class="model-item-id">' + escapeHtml(globalModel || ".env / 启动配置") + "</span></button>";
    var groups = [];
    var index = {};
    for (var i = 0; i < modelCatalog.length; i++) {
      var m = modelCatalog[i] || {};
      var key = (m.来源 || "模型") + " · " + (m.提供商 || "");
      if (!index[key]) { index[key] = []; groups.push(key); }
      index[key].push(m);
    }
    for (var g = 0; g < groups.length; g++) {
      h += '<div class="model-group">' + escapeHtml(groups[g]) + "</div>";
      var list = index[groups[g]];
      for (var k = 0; k < list.length; k++) {
        var mm = list[k] || {};
        var active = mm.id === currentModel ? " is-active" : "";
        h += '<button type="button" class="model-item' + active + '" data-model-id="' + escapeHtml(mm.id || "") + '">' +
          '<span class="model-item-name">' + escapeHtml(mm.名称 || mm.id || "") + "</span>" +
          '<span class="model-item-id">' + escapeHtml(mm.id || "") +
          (mm.上下文窗口 ? " · " + escapeHtml(String(mm.上下文窗口)) + " ctx" : "") + "</span></button>";
      }
    }
    h += "</div>";
    modelPopoverEl.innerHTML = h;
  }

  function loadModels(sessionOpt) {
    var url = "/api/models";
    if (sessionOpt) url += "?session=" + encodeURIComponent(sessionOpt);
    return fetch(url, { headers: apiHeaders() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !Array.isArray(data["模型"])) return;
        modelCatalog = data["模型"];
        currentModel = data["会话"] || "";
        globalModel = data["全局"] || data["当前"] || "";
        renderModelChip();
        if (modelPopoverEl && !modelPopoverEl.hidden) renderModelPopover();
      })
      .catch(function () { /* 模型目录拉不到不阻塞聊天 */ });
  }

  function openModelPopover() {
    if (!modelPopoverEl) return;
    renderModelPopover();
    modelPopoverEl.hidden = false;
    if (modelChipEl) modelChipEl.classList.add("is-open");
  }

  function closeModelPopover() {
    if (!modelPopoverEl) return;
    modelPopoverEl.hidden = true;
    if (modelChipEl) modelChipEl.classList.remove("is-open");
  }

  function chooseModel(id) {
    currentModel = id || "";
    renderModelChip();
    closeModelPopover();
    if (!sessionId) return; // 新会话：下一条消息的 model 字段会带上，服务端落盘
    fetch("/api/sessions/" + encodeURIComponent(sessionId) + "/model", {
      method: "POST",
      headers: apiHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ "模型": currentModel })
    }).then(function () {
      // 选「跟随全局默认」后回读一次，chip 显示全局模型名（而不是一串空）
      if (!currentModel) loadModels(sessionId);
    }).catch(function () { /* 落盘失败不阻塞本轮 */ });
  }

  // 从服务端拉当前会话元数据（拿标题）；503/404 静默忽略
  // T-0420：plan 状态投影（服务端 /api/sessions* 的「计划」键或 SSE 计划帧）
  function applyPlanState(plan) {
    var wasActive = !!(planState && planState.active);
    planState = (plan && typeof plan === "object") ? plan : { active: false, pending: false, text: "", title: "" };
    var active = !!planState.active;
    if (planChipEl) planChipEl.hidden = !active;
    if (planTextEl) planTextEl.textContent = planState.text || "（还没有提交计划）";
    if (planStateEl) {
      planStateEl.textContent = active
        ? "规划中…（退出后会提交计划）"
        : (planState.text ? "已提交" + (planState.title ? "：" + planState.title : "") : "未启用");
    }
    if (planPanelEl) {
      if (!active && !planState.text) planPanelEl.hidden = true;
      // 本轮刚退出并提交了计划 → 自动铺开一次，让用户看见落下来的计划
      else if (wasActive && !active) planPanelEl.hidden = false;
    }
  }

  if (planChipEl && planPanelEl) {
    planChipEl.addEventListener("click", function () {
      planPanelEl.hidden = !planPanelEl.hidden;
    });
  }
  if (planPanelCloseEl && planPanelEl) {
    planPanelCloseEl.addEventListener("click", function () { planPanelEl.hidden = true; });
  }

  function refreshSessionTitle(id) {
    if (!id) return;
    fetch("/api/sessions/current?session=" + encodeURIComponent(id), { headers: apiHeaders() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (meta) {
        if (meta && meta.标题) setSessionTitle(meta.标题);
        if (meta && meta["计划"]) applyPlanState(meta["计划"]);
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
    loadModels(id);
    // T-0396：首轮成功后目录已落到会话属性，清掉「待建」标红态（chip 继续显示该目录）
    if (window.NewSession && NewSession.clearSessionCwdError) NewSession.clearSessionCwdError();
    if (isNew) closeSidebarOnMobile();
    // T-0397：本轮 preset/权限预设已随请求写回会话；回填确保顶栏与面板一致
    //   （面板里改过权限时，这里把顶栏同步成刚发出去的值；首条消息则是绑定后回填）
    var syncedPerm = (window.NewSession && NewSession.getPermission) ? NewSession.getPermission() : "";
    applySessionMode(modeSelectEl ? modeSelectEl.value : "", syncedPerm || (permPreset ? permPreset.value : ""));
  }

  // 空状态：新对话
  // T-0398：空会话不丢待发附件——「先挂文件再开聊」是 DSH 的既有姿势，
  //   这里**不清空** attachments（只有首条消息发送成功、或切到别的会话才清）。
  function newChatState() {
    sessionId = null;
    history = [];
    currentAssistantIndex = -1;
    currentBubble = null;
    userBubble = null;
    Messages.clear(); // 同时 ToolCard.reset()（清空右面板时间线/统计）
    setSessionTitle("");
    applyPlanState(null); // T-0420：新会话不带上一会话的计划态
    renderContextUsage(0); // 新会话：用量归零
    if (window.Sidebar) Sidebar.setActive("");
    // T-0396：新会话沿用面板里暂存的目录选择（不选 = 全局默认，与改造前一致）
    if (window.NewSession && NewSession.bindSessionCwd) {
      NewSession.bindSessionCwd(NewSession.getSessionCwd ? NewSession.getSessionCwd() : "");
    }
    addSystem("新对话已就绪，输入内容开始。");
    // T-0398：把"附件还在"明说一次，避免用户以为刚选的文件被新会话丢了
    if (attachments.length) {
      addSystem("已新建空会话，保留 " + attachments.length +
        " 个待发附件（首条消息发送成功后才会清空）。");
    }
    loadModels(""); // 新会话回到全局默认模型
    // T-0397：空状态恢复到「全局默认」——模式用 localStorage 兜底，权限空=全局默认
    var fallbackMode = globalDefaultMode;
    try { var lm = localStorage.getItem("lh.mode"); if (lm && MODE_NAMES[lm]) fallbackMode = lm; } catch (e) { /* ignore */ }
    applySessionMode(fallbackMode, "");
  }

  // ---------- T-0422：流式中切换会话 = 先中止当前流，再切换 ----------
  //   语义与「停止」按钮一致：abort 后保留已渲染内容（finalizeTurn），不丢已收到的文本。
  //   竞态处理用「世代号」：切走时 turnEpoch 自增，老请求的
  //   then/catch/finally 及 SSE 残留帧在动手前先比对 epoch，对不上就静默放弃——
  //   abort 的 AbortError 即使晚到，也不会 finalize/污染已经切过去的新会话。
  function isTurnAlive(epoch) { return epoch === turnEpoch; }

  // 返回被摘下的排队条数；-1 表示本来就没在流式输出（调用方据此跳过提示）。
  //   提示由调用方在**新会话渲染完成之后**再发（renderHistory/newChatState 会清屏，
  //   在这里发会被清掉，用户看不到）。
  function abortActiveTurnForSwitch() {
    if (!streaming) return -1;
    // 1) 老轮次作废：之后的异步回调（AbortError → finalizeTurn / setStreaming(false) /
    //    controller 置空）都因 epoch 不符而跳过，不会打到新会话的 history 与气泡上。
    turnEpoch += 1;
    // 2) 老会话里排队的消息不能发到新会话：整队摘下（这是本卡的队列取舍：
    //    丢弃「自动发送」语义，但把文本放回输入框，不静默吞掉用户写下的字）。
    var droppedQueue = localQueue.slice();
    localQueue.length = 0;
    renderQueueChip();
    if (droppedQueue.length && inputEl) {
      var lost = [];
      for (var q = 0; q < droppedQueue.length; q++) lost.push(droppedQueue[q].text);
      if (!inputEl.value.trim()) {
        inputEl.value = lost.join("\n");
        autoResize();
        updateCharCount();
      }
    }
    // 3) 同步收口这一轮：结束气泡的 streaming 态与本地计时，再 abort 底层请求
    finalizeTurn();
    setStreaming(false);
    if (controller) { controller.abort(); controller = null; }
    return droppedQueue.length;
  }

  // 切换后给一句中文交代（按是否丢弃过排队消息分两种文案）
  function announceStreamAborted(dropped) {
    if (dropped == null || dropped < 0) return;
    addSystem(dropped
      ? "已停止当前输出并切换会话（" + dropped + " 条排队消息已放回输入框）。"
      : "已停止当前输出并切换会话。");
  }

  // 切换会话：拉取完整历史并回放
  // T-0422：流式输出中不再拦人——先停掉当前流，再进目标会话（老会话内容保留）。
  function selectSession(id) {
    if (!id) return;
    if (id === sessionId) {
      if (window.Sidebar) Sidebar.setActive(id);
      closeSidebarOnMobile();
      return;
    }
    var abortedQueue = -1;                                  // T-0422：-1 = 原本没在流式
    if (streaming) abortedQueue = abortActiveTurnForSwitch();
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
        announceStreamAborted(abortedQueue); // T-0422：切会话的交代放在渲染之后，不会被清屏带走
        // 同步本地 history，保证后续请求带上文
        for (var i = 0; i < list.length; i++) {
          var m = list[i];
          if (!m || typeof m !== "object") continue;
          var rawRole = m.角色 || m.role || "";
          // tool-call / tool-result 仅用于 UI 回放，不作为对话历史发给 API
          if (rawRole === "tool-call" || rawRole === "tool-result") continue;
          var role = (rawRole === "user" || m.role === "user") ? "user" : "assistant";
          var content = m.内容 != null ? m.内容 : (m.content != null ? m.content : "");
          history.push({ role: role, content: String(content) });
        }
        if (window.Sidebar) Sidebar.setActive(id);
        setSessionTitle("");
        refreshSessionTitle(id);
        applyPlanState(data && data["计划"] ? data["计划"] : null);
        // T-0396：已建会话的目录是会话属性（服务端按会话解析），chip 显示它
        if (window.NewSession && NewSession.bindSessionCwd) {
          NewSession.bindSessionCwd(data && data["工作目录"] ? data["工作目录"] : "");
        }
        closeSidebarOnMobile();
        // T-0398：切到另一个已有会话 → 清空待发附件（避免把 A 会话的文件带进 B），
        //   并给一次中文提示；同会话（id === sessionId）在上面就早返回了，不会走到这里。
        if (attachments.length) {
          var droppedAttach = attachments.length;
          clearAttachments();
          addSystem("已切换到别的会话，清空了 " + droppedAttach +
            " 个未发送的附件（避免把附件带进另一个会话）。");
        }
        renderContextUsage(0); // 用量是本会话的：换会话先归零，等统计帧回填
        loadModels(id); // 切会话：恢复该会话自己的模型
        applySessionMode(data["模式"], data["权限预设"]); // T-0397：恢复该会话的模式/权限
        if (list.length) addSystem("已载入会话历史（" + list.length + " 条消息）。");
      })
      .catch(function (e) {
        announceStreamAborted(abortedQueue);
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

  // ---------- 当前动作指示器（解决「大任务长时间没输出 = 像卡住」）----------
  //   三种阶段：思考中 / 正在执行 <工具名> / 已静默 n 秒。
  //   即使服务端这一帧什么文本都没给，用户也能看见「它还活着、在干什么」。
  var phaseState = { kind: "", label: "", since: 0 };
  var phaseTimerHandle = null;

  function setPhase(kind, label) {
    phaseState.kind = kind;
    phaseState.label = label || "";
    phaseState.since = Date.now();
    renderPhase();
  }

  function clearPhase() {
    phaseState.kind = "";
    phaseState.label = "";
    if (phaseChipEl) { phaseChipEl.hidden = true; phaseChipEl.textContent = ""; }
  }

  function renderPhase() {
    if (!phaseChipEl) return;
    if (!streaming || !phaseState.kind) { phaseChipEl.hidden = true; return; }
    var secs = Math.round((Date.now() - phaseState.since) / 1000);
    var text = "";
    if (phaseState.kind === "thinking") {
      text = "💭 思考中 " + secs + "s";
    } else if (phaseState.kind === "tool") {
      text = "🔧 正在执行 " + phaseState.label + " " + secs + "s";
    } else if (phaseState.kind === "wait") {
      text = "⏳ 等待模型响应 " + secs + "s";
    } else {
      text = phaseState.label;
    }
    phaseChipEl.hidden = false;
    phaseChipEl.textContent = text;
    // 长静默变红：超过 60 秒还是同一阶段，提醒用户「是真的慢，不是死了」
    phaseChipEl.classList.toggle("stale", secs > 60);
  }

  function startPhaseTimer() {
    if (phaseTimerHandle) return;
    phaseTimerHandle = setInterval(renderPhase, 1000);
  }

  function stopPhaseTimer() {
    if (phaseTimerHandle) { clearInterval(phaseTimerHandle); phaseTimerHandle = null; }
    clearPhase();
  }

  function updateTurnTimer() {
    if (!turnTimerEl || !turnStartedAt) return;
    turnTimerEl.hidden = false;
    turnTimerEl.textContent = ((Date.now() - turnStartedAt) / 1000).toFixed(1) + "s";
  }

  function renderQueueChip() {
    if (!queueChipEl) return;
    if (!localQueue.length) { queueChipEl.hidden = true; return; }
    queueChipEl.hidden = false;
    queueChipEl.textContent = "排队中 " + localQueue.length;
    var titles = [];
    for (var q = 0; q < localQueue.length; q++) {
      var t = localQueue[q].text;
      titles.push((q + 1) + ". " + (t.length > 40 ? t.slice(0, 40) + "…" : t));
    }
    queueChipEl.title = "排队中的消息（同一会话串行执行）：\n" + titles.join("\n");
  }

  function enqueueLocal(text, isCommand) {
    localQueue.push({ text: text, command: !!isCommand });
    renderQueueChip();
    addSystem("已加入本地排队（第 " + localQueue.length + " 条）：本轮结束后自动发送。");
  }

  function flushLocalQueue() {
    if (streaming || !localQueue.length) return;
    var item = localQueue.shift();
    renderQueueChip();
    sendMessage(item.command ? item.text : item.text);
  }

  // ---------- 流程控制 ----------
  function setStreaming(on) {
    streaming = on;
    sendBtn.disabled = on;
    stopBtn.disabled = !on;
    if (interruptBtn) interruptBtn.hidden = !on;
    if (currentBubble) currentBubble.classList.toggle("streaming", on);
    if (on) {
      // T-0407 需求四：流式开始即本地计时（统计帧到达后再校正为服务端耗时）
      turnStartedAt = Date.now();
      if (turnTimerHandle) clearInterval(turnTimerHandle);
      if (turnTimerEl) { turnTimerEl.hidden = false; turnTimerEl.textContent = "0.0s"; }
      turnTimerHandle = setInterval(updateTurnTimer, 200);
      // 阶段指示器：流一开就显示「等待模型响应」，之后被思考/工具事件接管
      setPhase("wait", "等待模型响应");
      startPhaseTimer();
    } else {
      stopPhaseTimer();
      if (turnTimerHandle) { clearInterval(turnTimerHandle); turnTimerHandle = null; }
      turnStartedAt = 0;
      // 本轮收口后把本地排队的下一条发出去（与服务端 202 排队通道互为兜底）
      setTimeout(flushLocalQueue, 0);
    }
  }

  // 正常结束（含用户点"停止"）：保留已渲染内容，清理空助手消息
  function finalizeTurn() {
    // 思考块收口（用户点停止 / 流中途断开时也要收，否则一直显示「思考中」）
    endThinking();
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
    endThinking();
    history.length = turnStartIndex;
    if (currentBubble) { currentBubble.remove(); currentBubble = null; }
    if (userBubble) { userBubble.remove(); userBubble = null; }
    if (text) { inputEl.value = text; inputEl.focus(); autoResize(); updateCharCount(); }
  }

  // ---------- E3：工具事件帧 ----------
  function handleToolCall(json) {
    // 工具执行期间界面是静的（可能几分钟），这里把「正在执行什么」显式说出来
    setPhase("tool", json && json["工具名"] ? json["工具名"] : "工具");
    // 文本与工具混排：工具帧到达时先把当前文本行收口，后续文本另起一行
    if (currentBubble) {
      Messages.endAssistant(currentBubble);
      currentBubble = null;
    }
    Messages.addToolCard(json);
    autoOpenPanel();
  }

  function handleToolResult(json) {
    setPhase("wait", "等待模型响应");
    Messages.applyToolResult(json);
    autoOpenPanel();
  }

  // ---------- SSE 流式解析 ----------
  //   T-0422：带上发起这一轮的 epoch；切会话后残留帧一律丢弃，不往新会话里追加文本。
  function readStream(resp, epoch) {
    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = "";
    var finished = false;

    function handleFrame(frame) {
      if (!isTurnAlive(epoch)) { finished = true; return; }
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
          // E5：压缩事件（服务端可选推送）——T-0398：顺手刷新输入区用量
          if (json && json.种类 === "压缩") {
            handleCompactionEvent(json);
            continue;
          }
          // T-0420：plan 模式状态帧（/plan、/plan off 的即时回执）
          if (json && json.种类 === "计划") {
            applyPlanState(json.plan || json["计划"]);
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
          // 思考流（reasoning_content）：先铺进「思考中」块，正文一到就收口。
          //   长任务里模型常长时间只产推理，不显示这一段就是「界面卡死」。
          if (delta && typeof delta.reasoning_content === "string" && delta.reasoning_content) {
            setPhase("thinking", "思考中");
            appendThinking(delta.reasoning_content);
          }
          if (delta && typeof delta.content === "string" && delta.content) {
            endThinking();
            setPhase("wait", "输出正文");
            appendToAssistant(delta.content);
          }
        } catch (e) { /* 忽略无法解析的分帧，保证容错 */ }
      }
    }

    function pump() {
      return reader.read().then(function (res) {
        if (!isTurnAlive(epoch)) { finished = true; return; }   // T-0422：老轮次已作废，停止消费
        if (res.done) return;
        buf += decoder.decode(res.value, { stream: true }).replace(/\r\n/g, "\n");
        var idx;
        while ((idx = buf.indexOf("\n\n")) !== -1 && !finished && isTurnAlive(epoch)) {
          var frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          handleFrame(frame);
        }
        return pump();
      });
    }

    return pump();
  }

  // ---------- T-0398：一键压缩（走既有 /compact 通道） ----------
  //   红线：前端不自造压缩算法、不新增端点——就是把 "/compact" 当一条消息，走同一条
  //   POST /v1/chat/completions（与斜杠面板的 /compact 完全同一个入口）。
  var COMPACT_CONFIRM_TEXT =
    "压缩会把较早的旧消息收进摘要，只保留最近 N 条对话（N 由服务端压缩配置决定），" +
    "原始记录仍留在会话里。确定现在压缩吗？";

  function requestCompaction() {
    if (streaming) {
      addSystem("正在流式输出中，请稍后再压缩。", true);
      return;
    }
    if (!sessionId) {
      addSystem("还没有进行中的会话：先发一条消息建立会话，再压缩上下文。", true);
      return;
    }
    if (!window.confirm(COMPACT_CONFIRM_TEXT)) return;
    sendMessage("/compact");
  }

  // T-0407 需求五：流式中「立即插话」——服务端经请求头把文本塞进插话通道，下一轮前注入
  function interruptNow() {
    var text = inputEl.value.trim();
    if (!text) { addSystem("插话前请先在输入框写下要补充的话。", true); return; }
    if (!streaming) { sendMessage(); return; }
    var body = { messages: [{ role: "user", content: text }], stream: false };
    if (sessionId) body.session_id = sessionId;
    if (modeSelectEl && modeSelectEl.value) body.preset = modeSelectEl.value;
    fetch(API_PATH, {
      method: "POST",
      headers: apiHeaders({ "Content-Type": "application/json", "X-LH-Interrupt": "1" }),
      body: JSON.stringify(body)
    }).then(function (resp) {
      return resp.json().catch(function () { return {}; }).then(function (j) {
        if (resp.ok) {
          addSystem("插话已登记（位置 " + ((j && j["位置"]) || 1) + "）：下一轮开始前注入。");
          inputEl.value = "";
          autoResize();
          updateCharCount();
        } else {
          addSystem("插话被拒：" + ((j && j["理由"]) || resp.status), true);
        }
      });
    }).catch(function () { addSystem("插话失败：网络错误", true); });
  }

  // ---------- 发送 ----------
  // T-0398：overrideText 用于命令式发送（/compact）：走的是**同一条**发送通道，
  //   只是不清输入框草稿、也不带附件（命令不消费用户正在挂的文件）。
  function sendMessage(overrideText) {
    var isCommand = (typeof overrideText === "string");
    var text = isCommand ? overrideText : inputEl.value.trim();
    if (!text) return;
    // T-0407 需求五：流式中再提交 → 本地排队（服务端 202 通道的同形状兜底）
    if (streaming) {
      enqueueLocal(text, isCommand);
      if (!isCommand) { inputEl.value = ""; autoResize(); updateCharCount(); }
      return;
    }

    // 追加本轮 UI 与历史（必须在组装消息体之前，否则 msgs 缺本轮用户消息）
    turnStartIndex = history.length;
    history.push({ role: "user", content: text });
    userBubble = Messages.addUser(text);
    currentBubble = null; // 首个文本增量到达时再创建助手行
    if (!isCommand) {
      inputEl.value = "";
      autoResize();
      updateCharCount();
    }
    setStreaming(true);
    setStatus("busy");

    // T-0398：附件先快照（上送的就是这份），发送成功后才清 chips——
    //   400 / 网络失败时 chips 必须留着，用户能原样重试。
    var sentAttachments = (!isCommand && attachments.length) ? projectAttachments(attachments) : null;

    // 组装消息体：去掉尾部尚未写入内容的空助手条目
    var msgs = history.slice();
    for (var i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "assistant" && msgs[i].content === "") msgs.pop();
      else break;
    }
    // 模型：空 = 跟随全局（不塞 model 字段，服务端按 .env/会话记录解析）
    var body = { messages: msgs, stream: true };
    if (currentModel) body.model = currentModel;
    if (sessionId) body.session_id = sessionId;       // 会话延续
    if (modeSelectEl && modeSelectEl.value) body.preset = modeSelectEl.value; // 第5步：Agent 模式
    if (sentAttachments) body.attachments = sentAttachments; // 第6轮 D：附件 best-effort（形状不变）
    // T-0396：会话级工作目录——只有用户显式选了目录才带字段；不带 = 全局默认（老行为不变）
    var pendingCwd = (window.NewSession && NewSession.getSessionCwd) ? NewSession.getSessionCwd() : "";
    if (pendingCwd && !sessionId) body["工作目录"] = pendingCwd;
    // T-0396/T-0397：权限预设——面板里的显式选择优先，否则用顶栏上的会话生效值。
    //   空串 = 跟随全局默认（不塞字段，旧行为不变）；服务端按会话记录隔离判定并落库。
    var pendingPerm = (window.NewSession && NewSession.getPermission) ? NewSession.getPermission() : "";
    var activePerm = pendingPerm || (permPreset ? permPreset.value : "");
    if (activePerm) body.权限预设 = activePerm;
    pendingCwdValue = pendingCwd;

    var headers = { "Content-Type": "application/json" };
    var started = false; // 是否已进入流式阶段（区分"连不上"和"中途断开"）
    // T-0422：记下本轮世代号；切会话会让 turnEpoch 自增，之后的回调都先比对它。
    var myEpoch = turnEpoch;
    controller = new AbortController();

    return fetch(API_PATH, {
      method: "POST",
      headers: apiHeaders(headers),
      body: JSON.stringify(body),
      signal: controller.signal
    }).then(function (resp) {
      if (!isTurnAlive(myEpoch)) return null;   // T-0422：已切走，老响应不再改任何 UI/附件
      if (!resp.ok) {
        handleHttpError(resp, isCommand ? "" : text);
        return null;
      }
      started = true;
      setStatus("ok");
      // T-0398：上送成功才清 chips（这里的"成功"= 服务端已受理本条消息）
      if (sentAttachments) clearAttachments();
      // T-0407 需求五：服务端判定「会话正忙」→ 202 排队（已收下，不是失败）
      if (resp.status === 202) {
        return resp.json().catch(function () { return {}; }).then(function (j) {
          rollbackTurn(isCommand ? "" : text);
          addSystem("服务端已排队（位置 " + ((j && j["位置"]) || 1) + "）：当前会话正在跑，本条结束后自动执行。");
          return null;
        });
      }
      return readStream(resp, myEpoch);
    }).then(function () {
      if (started && isTurnAlive(myEpoch)) finalizeTurn();
    }).catch(function (err) {
      if (!isTurnAlive(myEpoch)) return;   // T-0422：切会话后老请求的失败不落到新会话
      if (err && err.name === "AbortError") {
        finalizeTurn();               // 用户主动停止：保留已渲染内容
      } else if (started) {
        finalizeTurn();               // 流中途断开：保留已接收内容
        setStatus("down");
        addSystem("连接中断：已保留已接收的内容，请重试。", true);
      } else {
        setStatus("down");
        rollbackTurn(isCommand ? "" : text); // 命令失败不把 "/compact" 塞回输入框
        addSystem("服务不可达：无法连接服务端（" +
          (err && err.message ? err.message : "网络错误") +
          "），请确认服务已启动、地址与端口正确。", true);
      }
    }).finally(function () {
      // T-0422：老轮次的收尾不能关掉新会话正在跑的流（setStreaming(false) 会放开
      //   发送键、停计时、触发队列 flush），所以同样按 epoch 判定。
      if (!isTurnAlive(myEpoch)) return;
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
        // T-0396：目录被服务端拒绝时 chip 标红并显示理由，**不清空已选目录**（不静默丢掉）
        if (resp.status === 400 && pendingCwdValue && window.NewSession) {
          NewSession.markSessionCwdError(detail);
          addSystem("工作目录不可用：" + detail +
            "\n已保留你选的目录，修正后再发送（或点目录 chip 改成默认）。", true);
          return;
        }
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

  // 打开时的表单快照，用于未保存保护（apiKey 留空不算改动，因为已配置时留空=不修改）
  var cfgSnapshot = null;
  function snapshotConfig() {
    cfgSnapshot = { apiKey: cfgApiKey.value, baseUrl: cfgBaseUrl.value, model: cfgModel.value };
  }
  function configDirty() {
    if (!cfgSnapshot) return false;
    return cfgApiKey.value !== cfgSnapshot.apiKey
        || cfgBaseUrl.value !== cfgSnapshot.baseUrl
        || cfgModel.value !== cfgSnapshot.model;
  }

  function showConfigPanel() {
    // 已配置时回填（api_key 不回填，留空提示重新输入即覆盖）
    if (currentConfig && currentConfig.configured) {
      cfgBaseUrl.value = currentConfig.endpoint || "https://api.deepseek.com";
      cfgModel.value = currentConfig.model || "deepseek-flash";
      cfgApiKey.placeholder = "（已保存，留空则不修改）";
    } else {
      cfgBaseUrl.value = "https://api.deepseek.com";
      cfgModel.value = "deepseek-flash";
      cfgApiKey.placeholder = "sk-xxxxxxxxxxxxxxxx";
    }
    cfgError.hidden = true;
    cfgError.textContent = "";
    configPanel.hidden = false;
    snapshotConfig();
  }

  function hideConfigPanel(force) {
    if (!force && configDirty()) {
      if (!window.confirm("有未保存的配置改动，确定要关闭吗？")) return;
    }
    configPanel.hidden = true;
    cfgSnapshot = null;
  }

  // R106-B：暴露打开函数——设置对话框「模型」页签的「配置大模型」按钮经 window.showConfigPanel 调起；
  // 旧大模型配置面板保留不删，saveConfig/热更新行为不变。
  // 收敛后：模型页「配置大模型」统一打开新设置对话框的「模型」页签（旧面板仅兜底）。
  window.showConfigPanel = function () {
    if (window.LightSettings && LightSettings.open) LightSettings.open("models");
    else showConfigPanel(); // settings.js 未加载时兜底旧面板
  };

  // 重新生成最后一条助手回复：回退 history 到最后一个 user（含），把该 user 文本重发。
  // UI 侧的旧助手/用户气泡由 sendMessage 重新追加；这里先清掉尾部消息行避免重复。
  window.__regenerateLast = function () {
    if (streaming) return;
    var lastUserIdx = -1;
    for (var i = history.length - 1; i >= 0; i--) {
      if (history[i].role === "user") { lastUserIdx = i; break; }
    }
    if (lastUserIdx < 0) {
      if (window.Messages) Messages.addSystem("没有可重新生成的消息。", true);
      return;
    }
    var lastText = history[lastUserIdx].content;
    // 保留到最后一个 user（不含其后的 assistant），重发时会再 push 一条 user
    history.length = lastUserIdx;
    turnStartIndex = history.length;
    // 清掉消息区末尾的助手与用户气泡（从后往前移除 mrow，直到遇到早先内容——
    // 简单策略：移除最后两个 mrow: 助手 + 用户）
    if (window.Messages && Messages.clearTailForRegenerate) Messages.clearTailForRegenerate();
    inputEl.value = lastText;
    autoResize();
    sendMessage();
  };

  function checkConfig() {
    fetch("/api/config", { method: "GET", headers: apiHeaders() })
      .then(function (resp) { return resp.json(); })
      .then(function (cfg) {
        currentConfig = cfg;
        updateModelBadge(cfg.configured ? (cfg.model || "") : "");
        // 未配置 → 自动弹出配置引导；但 mock 模式（cfg.mock=true）服务已可用，
        // 不弹面板遮挡聊天界面，用户需要配真实 key 时可点右上角设置按钮。
        if (!cfg.configured && !cfg.mock) {
          showConfigPanel();
        }
      })
      .catch(function () { /* 配置接口不可用时不阻塞聊天 */ });
  }

  function saveConfig() {
    var apiKey = cfgApiKey.value.trim();
    var baseUrl = cfgBaseUrl.value.trim() || "https://api.deepseek.com";
    var model = cfgModel.value.trim() || "deepseek-flash";
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
          hideConfigPanel(true);
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

  // 第6轮 D：附件选择器
  if (attachBtn && attachInput) {
    attachBtn.addEventListener("click", function () { attachInput.click(); });
    attachInput.addEventListener("change", function () { onFiles(attachInput.files); });
  }
  // 第6轮 D：斜杠命令面板（命令集对齐 src/cli外壳.light 斜杠命令表）
  // T-0398：/compact 与「压缩」按钮共用 requestCompaction（双入口、同一通道）
  if (window.SlashPalette) {
    SlashPalette.init({
      input: inputEl,
      onPick: function (cmd) {
        if (cmd === "/clear") {
          clearAttachments(); // /clear 是显式清空：附件一并不留（新会话按钮才保留）
          newChatState();
        } else if (cmd === "/compact") {
          inputEl.value = "";
          autoResize();
          updateCharCount();
          requestCompaction();
        }
      }
    });
  }
  // T-0398：「压缩」按钮（输入区右下）
  if (compactBtn) compactBtn.addEventListener("click", requestCompaction);
  // T-0407 需求五：立即插话——本轮还在跑时把补充文本经请求头登记到插话通道
  if (interruptBtn) interruptBtn.addEventListener("click", interruptNow);
  // R106-B：入口统一——顶栏齿轮改开新设置对话框；旧「大模型配置」面板不删除，
  // 由设置对话框模型页签的「配置大模型」按钮经 window.showConfigPanel 调起。
  settingsBtn.addEventListener("click", function () {
    if (window.LightSettings && LightSettings.open) LightSettings.open();
    else showConfigPanel(); // settings.js 未加载时兜底
  });
  cfgSaveBtn.addEventListener("click", saveConfig);

  // 配置面板关闭：X 按钮 / 点遮罩 / Esc，均带未保存保护
  var cfgCloseBtn = document.getElementById("cfg-close-btn");
  if (cfgCloseBtn) cfgCloseBtn.addEventListener("click", function () { hideConfigPanel(false); });
  // 点遮罩（overlay 本身，非 card）关闭
  configPanel.addEventListener("mousedown", function (e) {
    if (e.target === configPanel) hideConfigPanel(false);
  });
  // Esc 关闭
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !configPanel.hidden) {
      hideConfigPanel(false);
    }
  });

  // E3：三栏交互
  if (sidebarToggle) sidebarToggle.addEventListener("click", function () {
    if (appShell) appShell.classList.toggle("sidebar-open");
  });
  if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebarOnMobile);
  if (rpToggle) rpToggle.addEventListener("click", function () { toggleRightPanel(); });
  if (rpClose) rpClose.addEventListener("click", function () { toggleRightPanel(false); });
  if (sessionTitleEl) sessionTitleEl.addEventListener("click", renameCurrentSession);

  // T-0396：「＋ 新会话」不再立刻 POST /api/sessions（避免每点一次就产出一个空会话）。
  //   做法：在捕获阶段拦下点击并 stopPropagation，sidebar.js 的 createSession 收不到事件；
  //   sidebar.js 源码不动（它的列表协议是红线），行为改由这里接管——只进空状态，
  //   目录/模式沿用面板里暂存的选择，真正建会话发生在首条消息里（与刷新后新对话同一条路径）。
  var newSessionBtn = document.getElementById("new-session-btn");
  if (newSessionBtn) {
    newSessionBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      e.preventDefault();
      // T-0422：流式中允许新建会话——先停掉当前流（老会话内容保留），再进空状态
      var abortedQueue = -1;
      if (streaming) abortedQueue = abortActiveTurnForSwitch();
      newChatState();
      announceStreamAborted(abortedQueue);
      closeSidebarOnMobile();
      inputEl.focus();
    }, true);
  }

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
        loadModels((meta && meta.id) || ""); // 新会话：模型回到该会话/全局默认
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

// 第5步：模式选择器——有会话只改该会话（切回/刷新还原），空状态写 localStorage 作待建默认。
  // T-0396：模式状态与新建会话面板共用同一个值（NewSession.setMode 双向同步）。
  // MODE_NAMES 已上移到文件顶部（T-0397：applySessionMode 在初始化前就要用）。
  // T-0407：把四种组合型模式补进下拉（index.html 保持老四项，避免两处清单漂移）
  fillModeOptions();
  if (modeSelectEl) {
    var savedMode = null;
    try { savedMode = localStorage.getItem("lh.mode"); } catch (e) { savedMode = null; }
    if (savedMode && MODE_NAMES[savedMode]) {
      globalDefaultMode = savedMode;
      modeSelectEl.value = savedMode;
    }
    modeSelectEl.addEventListener("change", function () {
      if (suppressModePersist) return;
      var m = modeSelectEl.value;
      // T-0396：面板里的下拉必须跟着顶栏走（两个入口同一个值）
      if (window.NewSession && NewSession.setMode) NewSession.setMode(m);
      persistSessionMode({ 模式: m }, "已切换到「" + (MODE_NAMES[m] || m) + "」模式（本会话）。");
    });
  }

  // T-0396：新会话面板（目录 chip + 弹层 + 模式/权限预选）
  //   不选目录 = 全局默认：这里不给任何默认值，全部由用户显式选择。
  if (window.NewSession) {
    NewSession.init({
      token: token,
      onModeChange: function (next) {
        // 面板里改了模式 → 输入区下拉跟上（两处必须一致，否则用户以为没生效）
        if (modeSelectEl && modeSelectEl.value !== next) modeSelectEl.value = next;
      },
      onPermissionChange: function (next) {
        // 面板里改了权限 → 顶栏标签跟上；真正落库由下一轮请求带 权限预设（T-0397）
        setPermLabel(next || "");
      }
    });
    // 面板里选的是「新会话」还是「当前会话」由发送路径决定；这里先把输入区模式同步进面板
    if (modeSelectEl && modeSelectEl.value && NewSession.setMode) NewSession.setMode(modeSelectEl.value);
  }

  // 初始提示 + 状态探测 + 配置检测 + E4 权限加载
  // 每会话模型选择器：chip 点开/收起；popover 点选；点外面关闭
  if (modelChipEl) {
    modelChipEl.addEventListener("click", function (e) {
      e.stopPropagation();
      if (modelPopoverEl && !modelPopoverEl.hidden) closeModelPopover();
      else openModelPopover();
    });
  }
  if (modelPopoverEl) {
    modelPopoverEl.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      var item = t.closest("[data-model-id]");
      if (item) chooseModel(item.getAttribute("data-model-id") || "");
    });
  }
  document.addEventListener("click", function (e) {
    if (!modelPopoverEl || modelPopoverEl.hidden) return;
    var t = e.target;
    if (t && t.closest && t.closest("#model-popover")) return;
    if (t && t.closest && t.closest("#model-chip")) return;
    closeModelPopover();
  });
  loadModels("");
  renderContextUsage(0); // T-0398：初始「上下文 0%」（等统计帧回填真实值）
  addSystem("输入内容后发送，agent 会逐字流式回复；工具调用可在右侧「工具」面板查看时间线。");
  checkStatus();
  checkConfig();
  loadPermissions();
})();

/* =====================================================================
 * lightharness WebUI — E3 工具调用卡片组件（tool-card.js，零依赖）
 * ---------------------------------------------------------------------
 * 职责：
 *  - 消费契约 1 的 SSE 事件帧：
 *      {种类:"工具调用", 工具名, 参数, 轮次, 调用id, 序号}  → 创建卡片（旋转态）
 *      {种类:"工具结果", 工具名, 结果, 错误, 是否错误, 调用id, 序号} → 合并进对应卡片
 *  - 卡片：头部（工具名彩色标签 + 参数摘要 + 状态 + 耗时），主体可展开/折叠
 *  - 工具名配色：bash=橙 / 读文件=蓝 / 写文件=绿 / 搜索=紫 / 其他=灰
 *  - bash 结果用终端样式（黑底绿字），并解析基础 ANSI 颜色码
 *  - 维护时间线注册表，供右侧面板渲染（点击跳转对应卡片）
 * 全局暴露 window.ToolCard；由 app.js 调用，messages.js 包装进消息流。
 * ===================================================================== */
(function () {
  "use strict";

  // ---------- 内部注册表 ----------
  // {callId, name, cls, state, durationText, cardEl(聊天区卡片DOM), ts}
  var registry = [];

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ---------- 工具名分类（配色 + 图标） ----------
  function classify(name) {
    var n = String(name || "").toLowerCase();
    if (/bash|shell|exec|cmd|终端|命令/.test(n)) return { cls: "tool-bash", icon: "❯_" };
    if (/read|view|cat|读|查看/.test(n)) return { cls: "tool-read", icon: "📄" };
    if (/write|edit|create|patch|写|编辑|创建/.test(n)) return { cls: "tool-write", icon: "✏️" };
    if (/search|grep|find|glob|query|搜|查找|检索/.test(n)) return { cls: "tool-search", icon: "🔍" };
    return { cls: "tool-other", icon: "🔧" };
  }

  // ---------- 参数格式化：JSON 尽量美化，失败保留原文 ----------
  function prettyParams(raw) {
    var s = String(raw == null ? "" : raw);
    if (!s) return "";
    try {
      var obj = JSON.parse(s);
      if (obj && typeof obj === "object") s = JSON.stringify(obj, null, 2);
    } catch (e) { /* 模型输出的参数原文，保持原样 */ }
    return s;
  }

  // ---------- 基础 ANSI SGR 颜色码 → span（先 escape 再替换，安全） ----------
  var ANSI_COLORS = {
    "30": "ansi-black", "31": "ansi-red", "32": "ansi-green", "33": "ansi-yellow",
    "34": "ansi-blue", "35": "ansi-magenta", "36": "ansi-cyan", "37": "ansi-white",
    "90": "ansi-gray", "91": "ansi-red", "92": "ansi-green", "93": "ansi-yellow",
    "94": "ansi-blue", "95": "ansi-magenta", "96": "ansi-cyan", "97": "ansi-white"
  };

  function ansiToHtml(text) {
    var s = escapeHtml(text);
    var open = false;
    s = s.replace(/\u001b\[([0-9;]*)m/g, function (m, codes) {
      if (codes === "" || codes === "0") {
        if (open) { open = false; return "</span>"; }
        return "";
      }
      var parts = codes.split(";");
      for (var i = 0; i < parts.length; i++) {
        var cls = ANSI_COLORS[parts[i]];
        if (cls) {
          var tag = open ? "</span>" : "";
          open = true;
          return tag + '<span class="' + cls + '">';
        }
      }
      return ""; // 忽略粗体/下划线等未支持码
    });
    // 清掉光标控制等其它转义序列
    s = s.replace(/\u001b\[[0-9;]*[A-Za-z]/g, "").replace(/\u001b[()][0-9A-Za-z]/g, "");
    if (open) s += "</span>";
    return s;
  }

  // ---------- 参数摘要（头部单行） ----------
  function paramSummary(raw) {
    var s = String(raw == null ? "" : raw).replace(/\s+/g, " ").trim();
    if (s.length > 80) s = s.slice(0, 80) + "…";
    return s;
  }

  // 超长正文体（>500 字符）截断 + 展开按钮
  var LONG_LIMIT = 500;

  function fillLongText(pre, text, isTerminal) {
    pre.classList.toggle("terminal", !!isTerminal);
    var full = String(text == null ? "" : text);
    if (full.length > LONG_LIMIT) {
      pre.textContent = full.slice(0, LONG_LIMIT) + "\n…（已截断，共 " + full.length + " 字符）";
      pre.dataset.full = "1";
      var btn = document.createElement("button");
      btn.className = "btn btn-ghost tool-expand";
      btn.type = "button";
      btn.textContent = "展开全部";
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (pre.dataset.full) {
          if (isTerminal) { pre.innerHTML = ansiToHtml(full); } else { pre.textContent = full; }
          delete pre.dataset.full;
          btn.textContent = "收起";
        } else {
          if (isTerminal) { pre.innerHTML = ansiToHtml(full.slice(0, LONG_LIMIT)); } else { pre.textContent = full.slice(0, LONG_LIMIT); }
          pre.dataset.full = "1";
          btn.textContent = "展开全部";
        }
        pre.classList.toggle("clamped");
      });
      pre.classList.add("clamped");
      pre.parentNode.insertBefore(btn, pre.nextSibling);
    } else if (isTerminal) {
      pre.innerHTML = ansiToHtml(full);
    } else {
      pre.textContent = full;
    }
  }

  // ---------- 创建卡片（种类:"工具调用"） ----------
  // 数据：{种类:"工具调用", 工具名, 参数, 轮次, 调用id, 序号}
  function create(数据) {
    var name = (数据 && 数据.工具名) || "";
    var info = classify(name);
    var callId = (数据 && 数据.调用id) || "";

    var card = document.createElement("div");
    card.className = "tool-card " + info.cls + " state-running";
    if (callId) card.dataset.callId = callId;

    var head = document.createElement("div");
    head.className = "tool-head";
    head.innerHTML =
      '<span class="tool-icon">' + info.icon + "</span>" +
      '<span class="tool-name">' + escapeHtml(name) + "</span>" +
      '<span class="tool-summary" title="' + escapeHtml(paramSummary(数据 && 数据.参数)) + '">' + escapeHtml(paramSummary(数据 && 数据.参数)) + "</span>" +
      '<span class="tool-status"><span class="spinner"></span></span>' +
      '<span class="tool-duration"></span>';
    card.appendChild(head);

    var body = document.createElement("div");
    body.className = "tool-body";
    body.hidden = true;
    body.innerHTML = '<div class="tool-label">参数</div>';
    var paramsPre = document.createElement("pre");
    paramsPre.className = "tool-params";
    fillLongText(paramsPre, prettyParams(数据 && 数据.参数), false);
    body.appendChild(paramsPre);
    body.appendChild(Object.assign(document.createElement("div"), { className: "tool-label", textContent: "结果" }));
    var resultPre = document.createElement("pre");
    resultPre.className = "tool-result";
    resultPre.textContent = "（等待执行结果…）";
    body.appendChild(resultPre);
    card.appendChild(body);

    // 头部点击 = 展开/折叠主体
    head.addEventListener("click", function () {
      body.hidden = !body.hidden;
      card.classList.toggle("open", !body.hidden);
    });

    var entry = {
      callId: callId,
      name: name,
      cls: info.cls,
      state: "running",
      durationText: "",
      cardEl: card,
      startTs: Date.now()
    };
    registry.push(entry);
    entry.render = function () { renderTimeline(lastTimelineEl); renderStats(lastStatsEl); };
    return card;
  }

  // ---------- 合并结果（种类:"工具结果"） ----------
  // 数据：{种类:"工具结果", 工具名, 结果, 错误, 是否错误, 调用id, 序号}
  function attachResult(卡片El, 数据) {
    if (!卡片El) return;
    var callId = (数据 && 数据.调用id) || 卡片El.dataset.callId || "";
    var entry = null;
    for (var i = registry.length - 1; i >= 0; i--) {
      if (registry[i].cardEl === 卡片El) { entry = registry[i]; break; }
    }
    var resultPre = 卡片El.querySelector(".tool-result");
    var statusEl = 卡片El.querySelector(".tool-status");
    var durationEl = 卡片El.querySelector(".tool-duration");
    var isError = !!(数据 && (数据.是否错误 || 数据.错误));
    var text = (数据 && 数据.结果 != null) ? String(数据.结果) : "";
    if (isError && 数据 && 数据.错误 && !text) text = String(数据.错误);

    var isBash = 卡片El.classList.contains("tool-bash");
    if (resultPre) {
      // 先清掉可能存在的展开按钮
      var oldBtn = resultPre.nextSibling;
      if (oldBtn && oldBtn.classList && oldBtn.classList.contains("tool-expand")) oldBtn.remove();
      resultPre.dataset.full = "";
      fillLongText(resultPre, text, isBash);
    }

    // 状态与耗时（服务端帧未带耗时，用帧到达间隔估算）
    var elapsed = entry ? (Date.now() - entry.startTs) / 1000 : 0;
    var durationText = elapsed >= 0.1 ? elapsed.toFixed(1) + "s" : "<0.1s";
    卡片El.classList.remove("state-running");
    卡片El.classList.add(isError ? "state-error" : "state-done");
    if (statusEl) statusEl.innerHTML = isError ? '<span class="state-icon err">✗</span>' : '<span class="state-icon ok">✓</span>';
    if (durationEl) durationEl.textContent = durationText;
    if (isError) {
      卡片El.classList.add("open");
      var bodyEl = 卡片El.querySelector(".tool-body");
      if (bodyEl) bodyEl.hidden = false; // 出错自动展开，方便定位
    }
    if (entry) {
      entry.state = isError ? "error" : "done";
      entry.durationText = durationText;
    }
    renderTimeline(lastTimelineEl);
    renderStats(lastStatsEl);
  }

  // ---------- 右侧面板：时间线 / 统计 ----------
  var lastTimelineEl = null;
  var lastStatsEl = null;

  function stateGlyph(state) {
    if (state === "done") return "✓";
    if (state === "error") return "✗";
    return "…";
  }

  function renderTimeline(container) {
    lastTimelineEl = container || lastTimelineEl;
    if (!lastTimelineEl) return;
    lastTimelineEl.innerHTML = "";
    if (!registry.length) {
      var empty = document.createElement("div");
      empty.className = "rp-empty";
      empty.textContent = "本轮暂无工具调用";
      lastTimelineEl.appendChild(empty);
      return;
    }
    for (var i = 0; i < registry.length; i++) {
      (function (entry) {
        var item = document.createElement("div");
        item.className = "timeline-item " + entry.cls + " state-" + entry.state;
        item.title = "点击定位到对话中的卡片";
        item.innerHTML =
          '<span class="tl-dot"></span>' +
          '<span class="tl-name">' + escapeHtml(entry.name || "工具") + "</span>" +
          '<span class="tl-state">' + stateGlyph(entry.state) + "</span>" +
          '<span class="tl-duration">' + escapeHtml(entry.durationText || "") + "</span>";
        item.addEventListener("click", function () {
          var el = entry.cardEl;
          if (!el || !el.isConnected) return;
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("flash");
          setTimeout(function () { el.classList.remove("flash"); }, 1200);
        });
        lastTimelineEl.appendChild(item);
      })(registry[i]);
    }
  }

  function renderStats(container) {
    lastStatsEl = container || lastStatsEl;
    if (!lastStatsEl) return;
    if (!registry.length) {
      lastStatsEl.innerHTML = '<div class="rp-empty">暂无统计</div>';
      return;
    }
    var total = 0;
    var parsed = 0;
    for (var i = 0; i < registry.length; i++) {
      var m = /^([\d.]+)s$/.exec(registry[i].durationText || "");
      if (m) { total += parseFloat(m[1]); parsed++; }
    }
    lastStatsEl.innerHTML =
      '<div class="rp-stat-line">调用 <b>' + registry.length + "</b> 次</div>" +
      '<div class="rp-stat-line">总耗时 <b>' + (parsed ? total.toFixed(1) + "s" : "—") + "</b></div>";
  }

  // ---------- 查找与清理 ----------
  function findByCallId(callId) {
    if (!callId) return null;
    for (var i = registry.length - 1; i >= 0; i--) {
      if (registry[i].callId === callId) return registry[i].cardEl;
    }
    return null; // 未找到 → 调用方应新建卡片（兼容无调用id的帧）
  }

  function reset() {
    registry = [];
    renderTimeline(lastTimelineEl);
    renderStats(lastStatsEl);
  }

  window.ToolCard = {
    create: create,
    attachResult: attachResult,
    renderTimeline: renderTimeline,
    renderStats: renderStats,
    findByCallId: findByCallId,
    reset: reset
  };
})();

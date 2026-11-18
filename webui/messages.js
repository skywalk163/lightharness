/* =====================================================================
 * lightharness WebUI — E3 消息渲染组件（messages.js，零依赖）
 * ---------------------------------------------------------------------
 * 职责：五种消息的 DOM 渲染
 *  1. 用户消息：右侧，浅色气泡，带头像
 *  2. 助手消息：左侧，深色气泡，带头像 + 流式光标 + 轻量 Markdown
 *     （``` 代码块带语言标签与复制按钮、行内 `code`、**加粗**、换行）
 *  3. 工具调用：包装 ToolCard 卡片进入消息流（依赖 tool-card.js）
 *  4. 工具结果：合并进对应卡片（按 调用id 定位）
 *  5. 系统消息：居中灰字（错误态红色）
 * 另提供：会话历史回放（E2 记录：{角色, 内容}）、清空、复制文本。
 * 全局暴露 window.Messages；由 app.js 调用。
 * ===================================================================== */
(function () {
  "use strict";

  var messagesEl = null;

  function root() {
    if (!messagesEl) messagesEl = document.getElementById("messages");
    return messagesEl;
  }

  // ---------- 基础工具 ----------
  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // 复制文本：优先 navigator.clipboard，降级 textarea + execCommand
  function copyText(text, done) {
    var cb = function () { if (done) done(true); };
    var fail = function () { if (done) done(false); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(cb, function () { legacyCopy(text) ? cb() : fail(); });
    } else {
      legacyCopy(text) ? cb() : fail();
    }
  }

  function legacyCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      ta.remove();
      return ok;
    } catch (e) { return false; }
  }

  // ---------- 轻量 Markdown（零依赖，参考 DeepSeek/DSH 消息面）----------
  // 设计：先整体 escape（防注入），再在转义后的文本上做行内/块级置换。
  // 行内：`code`、**粗体**、*斜体*、~~删除线~~、[文本](http(s)://...)、换行。
  function inlineMarkdown(s) {
    var e = escapeHtml(s);
    // 链接：仅允许 http/https/mailto，防 javascript: 注入。转义后的 &amp; 需还原到 URL。
    e = e.replace(/\[([^\]\n]+)\]\((https?:\/\/[^)\s]+|mailto:[^)\s]+)\)/g,
      function (_, label, url) {
        var safe = url.replace(/&amp;/g, "&").replace(/"/g, "%22");
        return '<a href="' + safe + '" target="_blank" rel="noopener noreferrer">' + label + "</a>";
      });
    e = e.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    e = e.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
    e = e.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    e = e.replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
    return e;
  }

  // 把一段“非代码块”纯文本按行渲染为块级 HTML（标题/列表/引用/表格/段落）。
  function renderTextBlock(text) {
    var lines = String(text == null ? "" : text).split("\n");
    var out = [];
    var para = [];               // 连续普通文本行合并为一段（段内 <br>，减少 DOM 碎片）
    function flushPara() {
      if (para.length) {
        out.push('<div class="md-p">' + para.join("<br>") + "</div>");
        para = [];
      }
    }
    var i = 0;
    function isTableSep(line) {
      return /^\s*\|?[\s:\-|]+\|[\s:\-|]*$/.test(line) && line.indexOf("-") >= 0;
    }
    function tableCells(line) {
      var t = line.trim();
      if (t.charAt(0) === "|") t = t.slice(1);
      if (t.charAt(t.length - 1) === "|") t = t.slice(0, -1);
      return t.split("|").map(function (c) { return c.trim(); });
    }
    while (i < lines.length) {
      var line = lines[i];

      // 表格：表头行 + 分隔行 + 数据行
      if (line.indexOf("|") >= 0 && i + 1 < lines.length && isTableSep(lines[i + 1])) {
        flushPara();
        var head = tableCells(line);
        var html = '<table class="md-table"><thead><tr>';
        for (var h = 0; h < head.length; h++) html += "<th>" + inlineMarkdown(head[h]) + "</th>";
        html += "</tr></thead><tbody>";
        i += 2;
        while (i < lines.length && lines[i].indexOf("|") >= 0 && lines[i].trim() !== "") {
          var cells = tableCells(lines[i]);
          html += "<tr>";
          for (var c = 0; c < head.length; c++) html += "<td>" + inlineMarkdown(cells[c] || "") + "</td>";
          html += "</tr>";
          i++;
        }
        html += "</tbody></table>";
        out.push(html);
        continue;
      }

      // 标题：# / ## / ###（最多三级，避免大字号撑破气泡）
      var hm = /^\s*(#{1,3})\s+(.*)$/.exec(line);
      if (hm) {
        flushPara();
        var lv = hm[1].length;
        out.push("<h" + lv + ' class="md-h">' + inlineMarkdown(hm[2]) + "</h" + lv + ">");
        i++;
        continue;
      }

      // 引用：> 文本
      if (/^\s*>\s?/.test(line)) {
        flushPara();
        var q = [];
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
          q.push(inlineMarkdown(lines[i].replace(/^\s*>\s?/, "")));
          i++;
        }
        out.push('<blockquote class="md-quote">' + q.join("<br>") + "</blockquote>");
        continue;
      }

      // 无序列表：- / * / + 开头
      if (/^\s*[-*+]\s+/.test(line)) {
        flushPara();
        var ul = ['<ul class="md-list">'];
        while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
          ul.push("<li>" + inlineMarkdown(lines[i].replace(/^\s*[-*+]\s+/, "")) + "</li>");
          i++;
        }
        ul.push("</ul>");
        out.push(ul.join(""));
        continue;
      }

      // 有序列表：1. 开头
      if (/^\s*\d+\.\s+/.test(line)) {
        flushPara();
        var ol = ['<ol class="md-list">'];
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
          ol.push("<li>" + inlineMarkdown(lines[i].replace(/^\s*\d+\.\s+/, "")) + "</li>");
          i++;
        }
        ol.push("</ol>");
        out.push(ol.join(""));
        continue;
      }

      // 空行：段落分隔（折叠连续空行）
      if (line.trim() === "") {
        flushPara();
        if (out.length && out[out.length - 1] !== '<div class="md-gap"></div>') {
          out.push('<div class="md-gap"></div>');
        }
        i++;
        continue;
      }

      // 普通文本行：先攒着，遇到块级/空行/结束时一次性合成一段
      para.push(inlineMarkdown(line));
      i++;
    }
    flushPara();

    // 收尾：去掉开头/结尾多余的段落间隔（流式输出时更干净）
    while (out.length && out[0] === '<div class="md-gap"></div>') out.shift();
    while (out.length && out[out.length - 1] === '<div class="md-gap"></div>') out.pop();
    return out.join("");
  }

  // 轻量代码高亮（零依赖，输入已是 escapeHtml 后的安全串）：
  //   字符串 → 注释 → 关键字 → 数字/内置量，着色用 span。按语言挑选关键字表。
  var HL_KEYWORDS = {
    py: "def class return if elif else for while in import from as try except finally with lambda None True False and or not pass break continue yield async await",
    js: "function var let const return if else for while class new import from export async await try catch finally throw typeof null undefined true false this of in do switch case break continue",
    ts: "function var let const return if else for while class new import from export async await try catch finally throw type interface enum null undefined true false this of in",
    java: "public private protected class interface extends implements return if else for while new import package static final void int long double String boolean true false null try catch",
    go: "func package import return if else for range var const type struct interface map chan go defer nil true false",
    sh: "if then else elif fi for while do done case esac function return export local echo cd set",
    sql: "SELECT FROM WHERE INSERT INTO UPDATE DELETE CREATE TABLE DROP ALTER JOIN ON GROUP BY ORDER LIMIT AS AND OR NOT NULL"
  };
  function highlightCode(escaped, lang) {
    var key = String(lang || "").toLowerCase();
    if (key === "python") key = "py";
    if (key === "javascript") key = "js";
    if (key === "typescript") key = "ts";
    if (key === "bash" || key === "shell" || key === "zsh") key = "sh";
    var kw = HL_KEYWORDS[key] || HL_KEYWORDS.js;
    var words = kw.split(/\s+/).filter(Boolean);
    // 逐行处理，避免跨行注释吞掉整段
    var lines = escaped.split("\n");
    for (var li = 0; li < lines.length; li++) {
      var line = lines[li];
      // 已经含 span 的片段不再二次着色：用占位符保护字符串/注释
      var slots = [];
      function hold(html) { slots.push(html); return "\u0000k" + (slots.length - 1) + "k\u0000"; }
      // 字符串（单/双/反引号，转义后引号仍为 &quot; / 实际字符）
      line = line.replace(/(&quot;[^&]*?&quot;|'[^']*?'|`[^`]*?`)/g, function (m) {
        return hold('<span class="hl-str">' + m + "</span>");
      });
      // 注释：# 或 //（行尾）——仅当不在占位符内（占位符是 \0n\0，不含 # //）
      var ci = line.search(/(#|\/\/)/);
      if (ci >= 0 && line.slice(ci).indexOf("\u0000") < 0) {
        line = line.slice(0, ci) + hold('<span class="hl-com">' + line.slice(ci) + "</span>");
      }
      // 关键字（词边界）
      if (words.length) {
        var re = new RegExp("\\b(" + words.join("|") + ")\\b", "g");
        line = line.replace(re, '<span class="hl-kw">$1</span>');
      }
      // 数字
      line = line.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="hl-num">$1</span>');
      // 还原占位符
      line = line.replace(/\u0000k(\d+)k\u0000/g, function (_, idx) { return slots[Number(idx)]; });
      lines[li] = line;
    }
    return lines.join("\n");
  }

  // 块级：先按 ``` 切出代码块，非代码块走 renderTextBlock。
  function renderMarkdown(text) {
    var parts = String(text == null ? "" : text).split("```");
    var html = "";
    for (var i = 0; i < parts.length; i++) {
      if (i % 2 === 1) {
        var block = parts[i];
        var lang = "";
        var nl = block.indexOf("\n");
        if (nl >= 0) {
          var first = block.slice(0, nl).trim();
          if (/^[A-Za-z0-9_+\-#]{1,16}$/.test(first)) {
            lang = first;
            block = block.slice(nl + 1);
          }
        }
        html +=
          '<div class="codeblock">' +
          '<div class="codeblock-head">' +
          '<span class="codeblock-lang">' + escapeHtml(lang || "代码") + "</span>" +
          '<button type="button" class="btn btn-ghost code-copy">复制</button>' +
          "</div>" +
          "<pre><code>" + highlightCode(escapeHtml(block.replace(/\n$/, "")), lang) + "</code></pre>" +
          "</div>";
      } else {
        html += renderTextBlock(parts[i]);
      }
    }
    return html;
  }

  // ---------- 行构造 ----------
  function mkRow(cls, avatarText) {
    var row = document.createElement("div");
    row.className = "mrow " + cls;
    var av = document.createElement("div");
    av.className = "avatar " + cls;
    av.textContent = avatarText;
    row.appendChild(av);
    root().appendChild(row);
    stickToBottom();
    return row;
  }

  function stickToBottom() {
    var el = root();
    if (!el) return;
    var max = el.scrollHeight - el.clientHeight;
    if (max <= 0 || el.scrollTop > max - 80) el.scrollTop = el.scrollHeight;
  }

  // 1. 用户消息（右侧）
  function addUser(text) {
    var row = mkRow("user", "你");
    var bubble = document.createElement("div");
    bubble.className = "mbubble";
    bubble.innerHTML = inlineMarkdown(text);
    row.appendChild(bubble);
    stickToBottom();
    return row;
  }

  // 2. 助手消息（左侧，初始空 + 流式光标）
  function beginAssistant() {
    var row = mkRow("assistant", "L");
    var bubble = document.createElement("div");
    bubble.className = "mbubble";
    var span = document.createElement("span");
    span.className = "mtext";
    var cursor = document.createElement("span");
    cursor.className = "cursor";
    bubble.appendChild(span);
    bubble.appendChild(cursor);
    row.appendChild(bubble);
    return row;
  }

  // 用完整文本重绘助手气泡（流式期间每帧调用）
  function setAssistant(row, fullText) {
    if (!row) return;
    var span = row.querySelector(".mtext");
    if (span) span.innerHTML = renderMarkdown(fullText);
    stickToBottom();
  }

  function endAssistant(row) {
    if (!row) return;
    row.classList.remove("streaming");
    var cursor = row.querySelector(".cursor");
    if (cursor) cursor.remove();
    // 空回复不残留空泡
    var span = row.querySelector(".mtext");
    if (span && !span.textContent && !row.querySelector(".codeblock")) { row.remove(); return; }
    // 操作条：复制全文 + 重新生成（回放的静态消息不显示重生成）
    if (span && !row.querySelector(".msg-actions")) {
      var actions = document.createElement("div");
      actions.className = "msg-actions";
      actions.innerHTML =
        '<button type="button" class="msg-act msg-copy" title="复制整条回复">复制</button>' +
        (row.classList.contains("static") ? "" :
         '<button type="button" class="msg-act msg-regen" title="重新生成这条回复">↻ 重新生成</button>');
      var bubble = row.querySelector(".mbubble");
      if (bubble) bubble.appendChild(actions);
    }
  }

  // 3. 工具调用卡片行（依赖 window.ToolCard）
  function addToolCard(数据) {
    var row = mkRow("tool", "🔧");
    var wrap = document.createElement("div");
    wrap.className = "tool-wrap";
    var card = window.ToolCard ? window.ToolCard.create(数据 || {}) : document.createElement("div");
    wrap.appendChild(card);
    row.appendChild(wrap);
    stickToBottom();
    return card;
  }

  // 4. 工具结果 → 合并进卡片；找不到对应卡片（无调用id等）时降级为系统行
  function applyToolResult(数据) {
    var callId = 数据 && 数据.调用id;
    var card = null;
    if (window.ToolCard) {
      card = callId ? window.ToolCard.findByCallId(callId) : null;
      if (!card) {
        // 结果先于调用到达（理论上不该发生）：补一张卡片再合并
        card = addToolCard(数据);
      }
      window.ToolCard.attachResult(card, 数据);
    }
    return card;
  }

  // 5. 系统消息（居中灰字；isError → 红色）
  function addSystem(text, isError) {
    var div = document.createElement("div");
    div.className = "sys" + (isError ? " error" : "");
    div.textContent = text;
    root().appendChild(div);
    stickToBottom();
    return div;
  }

  // ---------- 会话历史回放（E2 记录：{角色, 内容, ...}） ----------
  function parseJsonSafe(v) {
    if (v && typeof v === "object") return v;
    try { return JSON.parse(String(v || "")); } catch (e) { return {}; }
  }
  function renderHistory(list) {
    clear();
    if (!Array.isArray(list)) return;
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      if (!m || typeof m !== "object") continue;
      var role = m.角色 || m.role || "";
      var content = m.内容 != null ? m.内容 : (m.content != null ? m.content : "");
      if (role === "user") {
        addUser(String(content));
      } else if (role === "tool-call") {
        // 工具调用：还原为工具卡片（旋转态）
        var payload = parseJsonSafe(content);
        if (window.Messages && window.Messages.addToolCard) {
          window.Messages.addToolCard({
            种类: "工具调用", 工具名: payload["工具名"] || "", 参数: payload["参数"] || "",
            调用id: payload["调用id"] || "", 轮次: payload["轮次"] || 0, 序号: i
          });
        }
      } else if (role === "tool-result") {
        // 工具结果：合并进对应卡片（找不到调用卡时降级为系统行，避免丢失信息）
        var rp = parseJsonSafe(content);
        var data = { 种类: "工具结果", 工具名: rp["工具名"] || "", 结果: rp["结果"] || "",
          错误: rp["错误"] || "", 是否错误: rp["是否错误"] === true,
          调用id: rp["调用id"] || "", 序号: i };
        if (window.Messages && window.Messages.applyToolResult && data["调用id"]) {
          window.Messages.applyToolResult(data);
        } else if (rp["结果"]) {
          addSystem("[工具结果" + (data["工具名"] ? " " + data["工具名"] : "") + "] " + String(rp["结果"]).slice(0, 300));
        }
      } else if (role === "assistant") {
        var row = beginAssistant();
        setAssistant(row, String(content));
        endAssistant(row);
        row.classList.add("static");
      }
    }
  }

  function clear() {
    var el = root();
    if (el) el.innerHTML = "";
    if (window.ToolCard) window.ToolCard.reset();
  }

  // ---------- 代码块复制按钮（事件委托，绑定一次） ----------
  function bindCopy() {
    var el = root();
    if (!el || el.dataset.copyBound) return;
    el.dataset.copyBound = "1";
    el.addEventListener("click", function (ev) {
      var btn = ev.target;
      if (!btn || !btn.classList) return;
      // 复制整个代码块
      if (btn.classList.contains("code-copy")) {
        var block = btn.closest(".codeblock");
        var pre = block ? block.querySelector("pre") : null;
        if (!pre) return;
        copyText(pre.textContent, function (ok) {
          var old = btn.textContent;
          btn.textContent = ok ? "已复制" : "复制失败";
          setTimeout(function () { btn.textContent = old; }, 1200);
        });
        return;
      }
      // 复制整条助手回复（纯文本，去掉操作条文字）
      if (btn.classList.contains("msg-copy")) {
        var row = btn.closest(".mrow");
        var textEl = row ? row.querySelector(".mtext") : null;
        var raw = textEl ? textEl.innerText || textEl.textContent : "";
        copyText(raw, function (ok) {
          var old = btn.textContent;
          btn.textContent = ok ? "已复制" : "复制失败";
          setTimeout(function () { btn.textContent = old; }, 1200);
        });
        return;
      }
      // 重新生成：交给 app.js 注册的回调
      if (btn.classList.contains("msg-regen")) {
        if (typeof window.__regenerateLast === "function") window.__regenerateLast();
        return;
      }
    });
  }

  bindCopy();

  window.Messages = {
    addUser: addUser,
    beginAssistant: beginAssistant,
    setAssistant: setAssistant,
    endAssistant: endAssistant,
    addToolCard: addToolCard,
    applyToolResult: applyToolResult,
    addSystem: addSystem,
    renderMarkdown: renderMarkdown,
    renderHistory: renderHistory,
    clearTailForRegenerate: function () {
      var el = root();
      if (!el) return;
      var rows = el.querySelectorAll(".mrow");
      // 从末尾移除助手行与其用户行（最多各一条）
      var removedAssistant = false;
      for (var i = rows.length - 1; i >= 0; i--) {
        var r = rows[i];
        if (r.classList.contains("assistant") && !removedAssistant) { r.remove(); removedAssistant = true; }
        else if (r.classList.contains("user")) { r.remove(); break; }
        else if (r.classList.contains("tool")) { r.remove(); }
      }
    },
    clear: clear,
    copyText: copyText,
    escapeHtml: escapeHtml
  };
})();

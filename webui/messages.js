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
          "<pre><code>" + escapeHtml(block.replace(/\n$/, "")) + "</code></pre>" +
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
    if (span && !span.textContent && !row.querySelector(".codeblock")) row.remove();
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
  function renderHistory(list) {
    clear();
    if (!Array.isArray(list)) return;
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      if (!m || typeof m !== "object") continue;
      var role = m.角色 || m.role || "";
      var content = m.内容 != null ? m.内容 : (m.content != null ? m.content : "");
      if (role === "user") addUser(String(content));
      else if (role === "assistant") {
        var row = beginAssistant();
        setAssistant(row, String(content));
        endAssistant(row);
        row.classList.add("static");
      }
      // 其余角色（tool 等）由事件流回放，历史接口不重复渲染
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
      if (!btn || !btn.classList || !btn.classList.contains("code-copy")) return;
      var block = btn.closest(".codeblock");
      var pre = block ? block.querySelector("pre") : null;
      if (!pre) return;
      copyText(pre.textContent, function (ok) {
        var old = btn.textContent;
        btn.textContent = ok ? "已复制" : "复制失败";
        setTimeout(function () { btn.textContent = old; }, 1200);
      });
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
    clear: clear,
    copyText: copyText,
    escapeHtml: escapeHtml
  };
})();

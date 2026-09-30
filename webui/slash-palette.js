/* =====================================================================
 * lightharness WebUI — 斜杠命令面板（slash-palette.js，零依赖）
 * ---------------------------------------------------------------------
 * 对齐上游 apps/web 的 slash command palette：
 *  - 用户在输入框首位敲 "/" 时，在输入框上方弹出命令候选浮层
 *  - 支持 ↑/↓ 移动高亮、Enter/Tab 选中、Esc 关闭
 *  - 命令集与 src/cli外壳.light 的 斜杠命令表 对齐：
 *    /help /clear /model /compact /save /resume /exit
 *  - 选中后把命令回填到输入框（/clear /exit 等由宿主解释或在 app.js 接管）；
 *    本组件纯展示与键盘导航，不触碰发送逻辑。
 * 全局暴露 window.SlashPalette。
 * ===================================================================== */
(function () {
  "use strict";

  var COMMANDS = [
    { cmd: "/help",    desc: "显示可用命令与快捷键" },
    { cmd: "/clear",   desc: "清空当前会话上下文（新对话）" },
    { cmd: "/model",   desc: "切换当前模型" },
    { cmd: "/compact", desc: "手动触发上下文压缩" },
    { cmd: "/save",    desc: "立即保存当前会话" },
    { cmd: "/resume",  desc: "恢复历史会话" },
    { cmd: "/exit",    desc: "退出会话（关闭面板）" }
  ];

  var panel = null;
  var inputEl = null;
  var opts = {};        // { onPick(cmd) }
  var items = [];      // 当前过滤后的命令
  var activeIdx = 0;
  var open = false;

  function ensurePanel() {
    if (panel) return panel;
    panel = document.createElement("div");
    panel.className = "slash-palette";
    panel.hidden = true;
    document.body.appendChild(panel);
    return panel;
  }

  function render() {
    if (!items.length) { close(); return; }
    var p = ensurePanel();
    p.innerHTML = "";
    for (var i = 0; i < items.length; i++) {
      (function (it, idx) {
        var row = document.createElement("div");
        row.className = "slash-item" + (idx === activeIdx ? " active" : "");
        var c = document.createElement("span");
        c.className = "slash-cmd";
        c.textContent = it.cmd;
        var d = document.createElement("span");
        d.className = "slash-desc";
        d.textContent = it.desc;
        row.appendChild(c);
        row.appendChild(d);
        row.addEventListener("mousedown", function (e) {
          e.preventDefault();   // 抢在 input blur 前选中
          pick(idx);
        });
        p.appendChild(row);
      })(items[i], i);
    }
    // 定位到输入框上方
    if (inputEl) {
      var r = inputEl.getBoundingClientRect();
      p.style.left = r.left + "px";
      p.style.bottom = (window.innerHeight - r.top + 6) + "px";
      p.style.width = Math.max(r.width, 260) + "px";
    }
    p.hidden = false;
    open = true;
  }

  function close() {
    if (panel) panel.hidden = true;
    open = false;
    items = [];
  }

  function pick(idx) {
    var it = items[idx];
    if (!it) return;
    close();
    if (inputEl) {
      inputEl.value = it.cmd + " ";
      inputEl.focus();
    }
    if (typeof opts.onPick === "function") opts.onPick(it.cmd);
  }

  // 输入变化时：仅当内容以 "/" 开头、且 "/" 后还没有空格时才弹出
  function onInput() {
    if (!inputEl) return;
    var v = inputEl.value;
    if (v.charAt(0) !== "/" || v.indexOf(" ") !== -1) { close(); return; }
    var q = v.toLowerCase();
    items = [];
    for (var i = 0; i < COMMANDS.length; i++) {
      if (COMMANDS[i].cmd.indexOf(q) === 0) items.push(COMMANDS[i]);
    }
    activeIdx = 0;
    render();
  }

  function onKeydown(e) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (items.length) activeIdx = (activeIdx + 1) % items.length;
      render();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (items.length) activeIdx = (activeIdx - 1 + items.length) % items.length;
      render();
    } else if (e.key === "Enter" || e.key === "Tab") {
      if (open) { e.preventDefault(); pick(activeIdx); }
    } else if (e.key === "Escape") {
      e.preventDefault(); close();
    }
  }

  function init(userOpts) {
    opts = userOpts || {};
    inputEl = opts.input || document.getElementById("input");
    if (!inputEl) return;
    inputEl.addEventListener("input", onInput);
    inputEl.addEventListener("keydown", onKeydown, true); // 捕获阶段，抢在发送前
    document.addEventListener("click", function (e) {
      if (open && panel && !panel.contains(e.target) && e.target !== inputEl) close();
    });
  }

  window.SlashPalette = { init: init, close: close, commands: COMMANDS };
})();

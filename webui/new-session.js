/* =====================================================================
 * lightharness WebUI — 新会话面板（new-session.js，零依赖）
 * ---------------------------------------------------------------------
 * 对齐上游 DSH 落地页：目录 / 模式 / 权限 都在「开聊之前」可选。
 *
 * 契约（只增不改，别处依赖的键一个不动）：
 *  - 目录 chip（#cwd-chip）：显示「待建会话」或「当前会话」的 cwd；未选时显示「默认」。
 *    点击弹出面板 #cwd-popover：
 *      · 手输绝对路径输入框（#cwd-input）
 *      · 最近 5 条目录（localStorage 键 lh.recentCwd，只存路径字符串）
 *      · 「校验」按钮（失焦也校验）→ GET /api/cwd/check?工作目录=<urlencoded>（只读，无副作用）
 *      · 「设为全局默认」按钮 → 既有 POST /api/cwd（会 chdir + 落 settings.json，明确提示）
 *  - 空会话（还没有 session_id）选目录后，chip 显示「本会话：/x」，首条消息 body 带 工作目录；
 *    服务端 400 时由宿主（app.js）调用 markSessionCwdError() 把 chip 标红并显示理由，**不丢目录**。
 *  - 模式（standard/cordis/ptc/minimal）与权限（全放行/按类别/全拒绝/自定义）下拉：
 *    本卡只做 UI 暂存 + 随请求携带；权限真正按会话生效是 T-0397，所以这里必须有
 *    「全局默认 / 未落库」态，不得假装已生效。
 *  - 「＋ 新会话」不再立刻 POST /api/sessions（避免生产空会话）：只进空状态，
 *    目录沿用面板里暂存的选择，按「不选 = 全局默认」的老行为走。
 *
 * 红线：
 *  - 不选目录 = 全局默认，行为与改造前完全一致（老用户零感知）。
 *  - 不引第三方 UI 库；不改 index.html 既有 id；不动 sidebar.js 的列表协议。
 *  - localStorage 只存路径字符串与模式名，不存 token / 不存权限细节。
 *
 * 全局暴露 window.NewSession；由 app.js 初始化并接管发送/绑定时机。
 * ===================================================================== */
(function () {
  "use strict";

  var RECENT_KEY = "lh.recentCwd";
  var RECENT_MAX = 5;
  var MODE_KEY = "lh.mode";
  // 上次真正用过的会话目录：只用于「刷新后 chip 仍显示该目录」。
  //   键不存在（老用户/没选过）→ 什么都不做，行为与改造前完全一致。
  var LAST_CWD_KEY = "lh.lastCwd";
  var MODE_NAMES = { standard: "标准", cordis: "创造", ptc: "PTC", minimal: "极简" };
  var PERM_NAMES = ["全放行", "按类别", "全拒绝", "自定义"];

  var el = {};              // DOM 句柄
  var opts = {};            // {onModeChange(mode), onRequestNewSession()}
  var token = "";           // 鉴权令牌（仅内存）

  // ---- 状态 ----
  var sessionCwd = "";      // 本会话暂存/生效的 cwd（"" = 全局默认）
  var sessionCwdState = ""; // "" 正常 / "error" 服务端拒了 / "checking" 校验中 / "ok" 校验通过
  var sessionCwdError = ""; // 服务端/校验给的拒绝理由（标红时展示）
  var globalCwd = "";       // 全局默认目录（GET /api/cwd）
  var globalCwdSource = ""; // "设置" | "启动"
  var pendingCheck = 0;     // 校验请求序号（防旧响应覆盖新输入）
  var mode = "standard";    // 当前模式
  var permPreset = "";      // "" = 跟随全局（未落库）；否则 全放行/按类别/全拒绝/自定义
  var globalPermPreset = ""; // 顶栏已有权限管理器的当前值（GET /api/permissions）
  var popoverOpen = false;

  // ---------- 小工具 ----------
  function lsGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function lsSet(key, val) {
    try { window.localStorage.setItem(key, val); } catch (e) { /* 隐私模式忽略 */ }
  }
  function trimStr(v) { return String(v == null ? "" : v).replace(/^\s+|\s+$/g, ""); }

  function readRecent() {
    var raw = lsGet(RECENT_KEY);
    if (!raw) return [];
    try {
      var arr = JSON.parse(raw);
      if (!arr || Object.prototype.toString.call(arr) !== "[object Array]") return [];
      var out = [];
      for (var i = 0; i < arr.length && out.length < RECENT_MAX; i++) {
        var p = typeof arr[i] === "string" ? trimStr(arr[i]) : "";
        if (p && out.indexOf(p) < 0) out.push(p);
      }
      return out;
    } catch (e) { return []; }
  }

  // 最近目录只存路径字符串（卡面要求），去重、只留前 5 条
  function pushRecent(dir) {
    var p = trimStr(dir);
    if (!p) return;
    var list = readRecent();
    var next = [p];
    for (var i = 0; i < list.length && next.length < RECENT_MAX; i++) {
      if (list[i] !== p) next.push(list[i]);
    }
    lsSet(RECENT_KEY, JSON.stringify(next));
  }

  function clearRecent() {
    lsSet(RECENT_KEY, JSON.stringify([]));
    renderPopover();
  }

  // 长路径中间省略，chip 不会被撑破（纯展示，title 里给全文）
  function shortPath(p) {
    var s = String(p || "");
    if (s.length <= 34) return s;
    var head = s.slice(0, 14);
    var tail = s.slice(s.length - 16);
    return head + "…" + tail;
  }

  // ---------- chip 渲染 ----------
  function renderChip() {
    if (!el.chip || !el.chipName) return;
    var label = "";
    if (sessionCwd) {
      label = "本会话：" + shortPath(sessionCwd);
    } else {
      label = "默认";
    }
    el.chipName.textContent = label;
    var parts = [];
    if (sessionCwd) {
      parts.push("本会话目录：" + sessionCwd);
    } else {
      parts.push("未选目录：跟随全局默认");
    }
    if (globalCwd) parts.push("全局默认：" + globalCwd + (globalCwdSource ? "（" + globalCwdSource + "）" : ""));
    parts.push("点此选择目录");
    el.chip.title = parts.join("\n");

    var isErr = sessionCwdState === "error";
    var isBusy = sessionCwdState === "checking";
    el.chip.classList.toggle("is-session", !!sessionCwd && !isErr);
    el.chip.classList.toggle("is-follow", !sessionCwd && !isErr);
    el.chip.classList.toggle("is-error", isErr);
    el.chip.classList.toggle("is-busy", isBusy);

    if (el.chipError) {
      el.chipError.textContent = isErr ? (sessionCwdError || "该目录不可用") : "";
      el.chipError.hidden = !isErr;
    }
  }

  // ---------- 弹层面板渲染 ----------
  function renderPopover() {
    if (!el.popover) return;
    var h = "";
    h += '<div class="ns-pop-head">' +
      '<span class="ns-pop-title">选择工作目录</span>' +
      '<button type="button" class="ns-pop-close" data-ns-act="close" title="关闭（Esc）" aria-label="关闭">×</button>' +
      "</div>";
    h += '<div class="ns-pop-body">';
    h += '<label class="ns-field-label" for="cwd-input">绝对路径</label>';
    h += '<div class="ns-cwd-row">' +
      '<input type="text" id="cwd-input" class="ns-cwd-input" autocomplete="off" spellcheck="false" ' +
      'placeholder="例如 /home/user/project" value="' + escapeAttr(sessionCwd) + '">' +
      '<button type="button" class="btn ns-cwd-check" data-ns-act="check">校验</button>' +
      "</div>";
    h += '<div class="ns-cwd-msg" id="cwd-check-msg">' +
      (sessionCwdState === "error" && sessionCwdError
        ? '<span class="ns-bad">' + escapeHtml(sessionCwdError) + "</span>"
        : (sessionCwdState === "ok" && sessionCwd
          ? '<span class="ns-good">校验通过，可作本会话目录</span>'
          : '<span class="ns-dim">未校验。留空 = 跟随全局默认（老行为不变）。</span>')) +
      "</div>";
    // 最近 5 条
    var recent = readRecent();
    h += '<div class="ns-recent-head">最近目录' +
      (recent.length ? '<button type="button" class="ns-recent-clear" data-ns-act="clear-recent">清空</button>' : "") +
      "</div>";
    if (recent.length) {
      h += '<div class="ns-recent-list">';
      for (var i = 0; i < recent.length; i++) {
        h += '<button type="button" class="ns-recent-item" data-ns-dir="' + escapeAttr(recent[i]) + '">' +
          '<span class="ns-recent-path">' + escapeHtml(recent[i]) + "</span></button>";
      }
      h += "</div>";
    } else {
      h += '<div class="ns-recent-empty">暂无（选过的目录会出现在这里，只存路径）</div>';
    }
    // 全局默认提示 + 设为全局
    h += '<div class="ns-global-row">';
    h += '<span class="ns-global-text">全局默认：' +
      (globalCwd ? escapeHtml(globalCwd) : "（服务启动目录）") +
      (globalCwdSource ? ' <span class="ns-dim">' + escapeHtml(globalCwdSource) + "</span>" : "") +
      "</span>";
    h += '<button type="button" class="btn ns-cwd-global" data-ns-act="set-global">设为全局默认</button>';
    h += "</div>";
    h += '<div class="ns-global-warn">⚠ 「设为全局默认」是**全局生效**：会切换服务进程的工作目录并写入设置，影响所有新会话，不只是这一个。</div>';

    // 模式 / 权限
    h += '<div class="ns-split"></div>';
    h += '<div class="ns-two-col">';
    h += '<div class="ns-col"><label class="ns-field-label" for="ns-mode-select">模式</label>' +
      '<select id="ns-mode-select" class="ns-select">';
    var modeOrder = ["standard", "cordis", "ptc", "minimal"];
    for (var m = 0; m < modeOrder.length; m++) {
      var mv = modeOrder[m];
      h += '<option value="' + escapeAttr(mv) + '"' + (mode === mv ? " selected" : "") + ">" +
        escapeHtml(MODE_NAMES[mv] || mv) + "</option>";
    }
    h += "</select></div>";
    h += '<div class="ns-col"><label class="ns-field-label" for="ns-perm-select">权限</label>' +
      '<select id="ns-perm-select" class="ns-select">';
    h += '<option value=""' + (permPreset === "" ? " selected" : "") + ">全局默认" +
      (globalPermPreset ? "（" + escapeHtml(globalPermPreset) + "）" : "") + "</option>";
    for (var p = 0; p < PERM_NAMES.length; p++) {
      var pv = PERM_NAMES[p];
      h += '<option value="' + escapeAttr(pv) + '"' + (permPreset === pv ? " selected" : "") + ">" +
        escapeHtml(pv) + "</option>";
    }
    h += "</select></div>";
    h += "</div>";
    h += '<div class="ns-hint">模式随下一条消息生效；权限在本卡只**暂存并随请求携带**，' +
      '真正按会话生效是后续任务（T-0397），所以这里标「未落库」是诚实状态，不是 bug。</div>';
    h += "</div>";
    h += '<div class="ns-pop-foot">';
    h += '<button type="button" class="btn ns-cwd-reset" data-ns-act="reset">恢复默认</button>';
    h += '<button type="button" class="btn btn-send ns-cwd-apply" data-ns-act="apply">用这个目录</button>';
    h += "</div>";
    el.popover.innerHTML = h;
    bindPopoverInner();
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function escapeAttr(s) { return escapeHtml(s); }

  function bindPopoverInner() {
    if (!el.popover) return;
    var input = el.popover.querySelector("#cwd-input");
    if (input) {
      input.addEventListener("input", function () { setMsg("", ""); });
      // 失焦校验：手输完离开输入框就告诉用户这路径行不行（只读，不会切目录）
      input.addEventListener("blur", function () {
        var v = trimStr(input.value);
        if (v) checkPath(v);
      });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          applyCurrentInput();
        }
      });
    }
    var modeSel = el.popover.querySelector("#ns-mode-select");
    if (modeSel) {
      modeSel.addEventListener("change", function () { setMode(modeSel.value); });
    }
    var permSel = el.popover.querySelector("#ns-perm-select");
    if (permSel) {
      permSel.addEventListener("change", function () {
        permPreset = permSel.value || "";
        renderChip();
        // T-0397：面板与顶栏的权限标签共用同一个值（落库仍走下一轮请求，见 app.js）
        if (typeof opts.onPermissionChange === "function") opts.onPermissionChange(permPreset);
      });
    }
  }

  function setMsg(kind, text) {
    var box = el.popover && el.popover.querySelector("#cwd-check-msg");
    if (!box) return;
    if (!text) {
      box.innerHTML = '<span class="ns-dim">未校验。留空 = 跟随全局默认（老行为不变）。</span>';
      return;
    }
    box.innerHTML = '<span class="' + (kind === "bad" ? "ns-bad" : "ns-good") + '">' +
      escapeHtml(text) + "</span>";
  }

  // ---------- 后端交互 ----------
  function apiHeaders(extra) {
    var headers = extra || {};
    if (token) headers["X-Auth-Token"] = token;
    return headers;
  }

  // GET /api/cwd：全局默认目录（只读）
  function loadGlobalCwd() {
    return fetch("/api/cwd", { method: "GET", headers: apiHeaders() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        globalCwd = data["工作目录"] || "";
        globalCwdSource = data["来源"] || "";
        renderChip();
        if (popoverOpen) renderPopover();
      })
      .catch(function () { /* 拉不到全局目录不阻塞选目录 */ });
  }

  // GET /api/cwd/check：只读校验（卡面新端点；绝不 chdir、绝不写 settings.json）
  function checkPath(path) {
    var dir = trimStr(path);
    if (!dir) { setMsg("", ""); return Promise.resolve(null); }
    var seq = ++pendingCheck;
    sessionCwdState = "checking";
    renderChip();
    setMsg("", "");
    return fetch("/api/cwd/check?工作目录=" + encodeURIComponent(dir), {
      method: "GET",
      headers: apiHeaders()
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (seq !== pendingCheck) return null; // 旧响应，丢弃
        if (!data) {
          sessionCwdState = "error";
          sessionCwdError = "校验接口不可用（服务端未更新？）";
          renderChip();
          setMsg("bad", sessionCwdError);
          return null;
        }
        if (data["可读"]) {
          sessionCwdState = "ok";
          sessionCwdError = "";
          renderChip();
          setMsg("good", "校验通过：" + (data["绝对路径"] || dir));
          return data;
        }
        sessionCwdState = "error";
        sessionCwdError = data["错误"] || "目录不可用";
        renderChip();
        setMsg("bad", sessionCwdError);
        return data;
      })
      .catch(function (e) {
        if (seq !== pendingCheck) return null;
        sessionCwdState = "error";
        sessionCwdError = "校验请求失败：" + (e && e.message ? e.message : "网络错误");
        renderChip();
        setMsg("bad", sessionCwdError);
        return null;
      });
  }

  // 「设为全局默认」：走既有 POST /api/cwd（明确是全局生效），成功后刷新全局提示
  function setGlobalDefault(btn) {
    var dir = "";
    var input = el.popover && el.popover.querySelector("#cwd-input");
    if (input) dir = trimStr(input.value);
    if (!dir) dir = sessionCwd || globalCwd;
    if (!dir) { setMsg("bad", "先填一个目录，再设为全局默认"); return; }
    var needConfirm = true;
    try {
      needConfirm = !window.confirm(
        "把以下目录设为【全局默认】？\n\n" + dir +
        "\n\n这是全局生效：会切换服务进程的工作目录并写入设置，影响所有新会话。"
      );
    } catch (e) { needConfirm = false; }
    if (needConfirm) return;
    if (btn) { btn.disabled = true; btn.textContent = "设置中…"; }
    fetch("/api/cwd", {
      method: "POST",
      headers: apiHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ "工作目录": dir })
    })
      .then(function (r) {
        return r.json().then(function (d) { return { ok: r.ok, data: d }; });
      })
      .then(function (res) {
        if (!res.ok) {
          throw new Error((res.data && res.data["错误"]) || "服务端拒绝");
        }
        globalCwd = (res.data && res.data["工作目录"]) || dir;
        globalCwdSource = "设置";
        pushRecent(globalCwd);
        renderChip();
        renderPopover();
        setMsg("good", "已设为全局默认：" + globalCwd);
      })
      .catch(function (e) {
        setMsg("bad", "设为全局默认失败：" + (e && e.message ? e.message : "网络错误"));
        if (btn) { btn.disabled = false; btn.textContent = "设为全局默认"; }
      });
  }

  // GET /api/permissions：顶栏已有的全局权限预设（只用于把「全局默认」写实）
  function loadGlobalPermission() {
    return fetch("/api/permissions", { method: "GET", headers: apiHeaders() })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        globalPermPreset = data["预设"] || "";
        if (popoverOpen) renderPopover();
      })
      .catch(function () { /* 权限接口不可用不影响选目录 */ });
  }

  // ---------- 交互 ----------
  function openPopover() {
    if (!el.popover) return;
    popoverOpen = true;
    renderPopover();
    el.popover.hidden = false;
    if (el.chip) el.chip.classList.add("is-open");
    loadGlobalCwd();
    loadGlobalPermission();
    var input = el.popover.querySelector("#cwd-input");
    if (input) { try { input.focus(); } catch (e) { /* 忽略 */ } }
  }

  function closePopover() {
    if (!el.popover) return;
    popoverOpen = false;
    el.popover.hidden = true;
    if (el.chip) el.chip.classList.remove("is-open");
  }

  // 把输入框/最近项里的目录落到「本会话」，并做一次校验（校验失败也先收下，标红提醒）
  function applyPath(dir, quiet) {
    var p = trimStr(dir);
    sessionCwd = p;
    sessionCwdError = "";
    sessionCwdState = "";
    if (!p) {
      renderChip();
      if (popoverOpen) renderPopover();
      return Promise.resolve(true);
    }
    return checkPath(p).then(function (data) {
      var ok = !!(data && data["可读"]);
      // T-0396 主控补丁：校验端点会把相对路径按服务进程 cwd 解析后回显绝对路径，
      //   而建会话（T-0395）只收绝对路径。校验通过了就该用服务端解析出的绝对路径，
      //   否则「校验通过 → 首条消息 400」自相矛盾；最近目录也只存绝对路径。
      if (ok) {
        var abs = trimStr(data["绝对路径"]);
        if (abs) sessionCwd = abs;
        pushRecent(sessionCwd || p);
      }
      renderChip();
      if (popoverOpen) renderPopover();
      if (ok && !quiet) closePopover();
      return ok;
    });
  }

  function applyCurrentInput() {
    var input = el.popover && el.popover.querySelector("#cwd-input");
    var v = input ? trimStr(input.value) : sessionCwd;
    if (!v) { resetToDefault(); return; }
    return applyPath(v, false);
  }

  function resetToDefault() {
    sessionCwd = "";
    sessionCwdState = "";
    sessionCwdError = "";
    try { window.localStorage.removeItem(LAST_CWD_KEY); } catch (e) { /* 忽略 */ }
    renderChip();
    if (popoverOpen) renderPopover();
  }

  function setMode(next) {
    if (!next) return;
    mode = next;
    lsSet(MODE_KEY, next);
    if (typeof opts.onModeChange === "function") opts.onModeChange(next);
    renderChip();
  }

  // ---------- 对外接口 ----------
  // 绑定会话：切到已有会话时把该会话的 cwd 显示出来（服务端已按会话解析）
  function bindSessionCwd(cwd) {
    sessionCwd = trimStr(cwd);
    sessionCwdState = "";
    sessionCwdError = "";
    // 记住「上次用过的目录」：刷新后 chip 仍能显示它，而不是退回「默认」
    if (sessionCwd) lsSet(LAST_CWD_KEY, sessionCwd);
    else { try { window.localStorage.removeItem(LAST_CWD_KEY); } catch (e) { /* 忽略 */ } }
    renderChip();
    if (popoverOpen) renderPopover();
  }

  // 服务端 400 的落点：chip 标红 + 理由，**不清空 sessionCwd**（不静默丢掉目录）
  function markSessionCwdError(reason) {
    if (!sessionCwd) return;
    sessionCwdState = "error";
    sessionCwdError = trimStr(reason) || "服务端拒绝了该目录";
    renderChip();
    if (popoverOpen) renderPopover();
  }

  function clearSessionCwdError() {
    if (sessionCwdState !== "error") return;
    sessionCwdState = "";
    sessionCwdError = "";
    renderChip();
  }

  // 发送前取值：空串表示「不选目录」（请求不带 工作目录 字段 → 老行为不变）
  function getSessionCwd() { return sessionCwd; }

  function getMode() { return mode || "standard"; }

  // 权限："" = 跟随全局（不随请求携带）；否则带上暂存的预设
  function getPermission() { return permPreset || ""; }

  // T-0397：切会话时把该会话的生效权限回填到面板（空串 = 全局默认），
  //   否则面板会拿着上一个会话的选择去覆盖当前会话。
  function setPermission(perm) {
    permPreset = trimStr(perm);
    renderChip();
    if (popoverOpen) renderPopover();
  }

  function init(userOpts) {
    opts = userOpts || {};
    token = opts.token || "";
    el.chip = document.getElementById("cwd-chip");
    el.chipName = document.getElementById("cwd-chip-name");
    el.chipError = document.getElementById("cwd-chip-error");
    el.popover = document.getElementById("cwd-popover");
    if (el.chip) {
      el.chip.addEventListener("click", function (e) {
        e.stopPropagation();
        if (popoverOpen) closePopover();
        else openPopover();
      });
    }
    if (el.popover) {
      el.popover.addEventListener("click", function (e) {
        var t = e.target;
        if (!t || !t.closest) return;
        var dirBtn = t.closest("[data-ns-dir]");
        if (dirBtn) {
          applyPath(dirBtn.getAttribute("data-ns-dir"), false);
          return;
        }
        var actBtn = t.closest("[data-ns-act]");
        if (!actBtn) return;
        var act = actBtn.getAttribute("data-ns-act");
        if (act === "close") closePopover();
        else if (act === "check") {
          var input = el.popover.querySelector("#cwd-input");
          if (input && trimStr(input.value)) checkPath(trimStr(input.value));
          else setMsg("bad", "先输入一个目录再校验");
        }
        else if (act === "clear-recent") clearRecent();
        else if (act === "set-global") setGlobalDefault(actBtn);
        else if (act === "reset") resetToDefault();
        else if (act === "apply") applyCurrentInput();
      });
    }
    // 点外面/Esc 收起（与模型 popover 同款体验）
    document.addEventListener("click", function (e) {
      if (!popoverOpen) return;
      var t = e.target;
      if (t && t.closest && (t.closest("#cwd-popover") || t.closest("#cwd-chip"))) return;
      closePopover();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && popoverOpen) closePopover();
    });
    // 恢复上次模式（沿用既有 lh.mode）
    var saved = lsGet(MODE_KEY);
    if (saved && MODE_NAMES[saved]) mode = saved;
    // 恢复上次用过的会话目录（刷新后 chip 不退回「默认」；没选过的老用户无此键 → 不变）
    var lastCwd = lsGet(LAST_CWD_KEY);
    if (lastCwd && trimStr(lastCwd)) sessionCwd = trimStr(lastCwd);
    renderChip();
    loadGlobalCwd();
    loadGlobalPermission();
  }

  window.NewSession = {
    init: init,
    bindSessionCwd: bindSessionCwd,
    markSessionCwdError: markSessionCwdError,
    clearSessionCwdError: clearSessionCwdError,
    getSessionCwd: getSessionCwd,
    getMode: getMode,
    setMode: setMode,
    getPermission: getPermission,
    setPermission: setPermission,
    open: openPopover,
    close: closePopover,
    // 诊断/测试用（浏览器手工冒烟时会用到）
    _state: function () {
      return {
        sessionCwd: sessionCwd,
        sessionCwdState: sessionCwdState,
        sessionCwdError: sessionCwdError,
        globalCwd: globalCwd,
        globalCwdSource: globalCwdSource,
        mode: mode,
        permPreset: permPreset,
        globalPermPreset: globalPermPreset,
        recent: readRecent()
      };
    }
  };
})();

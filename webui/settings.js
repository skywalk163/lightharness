/* =====================================================================
 * lightharness WebUI — 设置对话框（settings.js，零依赖）
 * ---------------------------------------------------------------------
 * 职责：按实拍截图复刻 dsh 设置对话框，四页签（通用设置 / 模型 / 内置插件 /
 *      Agent 预设），通用设置 9 行由服务端「行集」驱动渲染。
 * 数据契约（src/web服务器.light 提供）：
 *   GET  /api/settings          → {页签,页签标识,页签说明,通用设置,模型,内置插件,Agent预设}
 *   GET  /api/settings/document → {路径,可用}
 *   POST /api/settings          body {"行":<行id>,"值":<新值>} → 200 {"状态":"ok","行集":[...]}；
 *                               非法 → 400 {"错误":<消息>}
 * 兼容性：通用设置 若没有「行集」（旧形状 {"内置插件":{"按模式":{...}}}）不崩，
 *        渲染一行提示「通用设置行集尚未接入」，其余三个页签照常渲染。
 * R106-B 新增：
 *   - 设置生效：GET /api/settings/effective?系统偏好=dark|light（matchMedia 上报，服务端权威解析 system）
 *     → data-theme / --msg-font-size / data-link-target / data-lang 应用到页面；降级项显式提示，不静默。
 *   - 入口统一：顶栏齿轮（app.js 改绑 LightSettings.open）；模型页签「配置大模型」按钮经
 *     window.showConfigPanel 调起旧面板（app.js 暴露），旧面板不删除。
 *   - 快捷键编辑器面板：替换原「宿主面未接入」2 秒提示；数据全走 GET/POST /api/shortcuts，
 *     保留/冲突规则不在前端重算，错误文案一律回显服务端返回的「错误」字段（规则权威在 D 线模块）。
 * 依赖：无第三方库；样式见 settings.css；入口按钮见 index.html 的 .settings-entry。
 * 全局暴露 window.LightSettings（含纯渲染函数，供本地 mock 断言使用）
 *           与 window.SettingsApply（纯换算函数导出点，供 .scratch/r106b_assert.mjs 驱动）。
 * ===================================================================== */
(function () {
  "use strict";

  var G = (typeof window !== "undefined") ? window
        : (typeof globalThis !== "undefined") ? globalThis : {};
  var HAS_DOM = (typeof document !== "undefined" && !!document && !!document.createElement);

  // ---------- 工具 ----------
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function svg(body, size) {
    var n = size || 16;
    return '<svg viewBox="0 0 24 24" width="' + n + '" height="' + n + '" ' +
      'fill="none" stroke="currentColor" stroke-width="1.6" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + body + "</svg>";
  }

  // 线性风格内联 SVG（禁用 emoji）
  var ICONS = {
    gear: svg('<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'),
    layers: svg('<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'),
    sliders: svg('<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>'),
    user: svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
    sun: svg('<circle cx="12" cy="12" r="4.2"/><line x1="12" y1="1.8" x2="12" y2="4.2"/><line x1="12" y1="19.8" x2="12" y2="22.2"/><line x1="4.4" y1="4.4" x2="6" y2="6"/><line x1="18" y1="18" x2="19.6" y2="19.6"/><line x1="1.8" y1="12" x2="4.2" y2="12"/><line x1="19.8" y1="12" x2="22.2" y2="12"/><line x1="4.4" y1="19.6" x2="6" y2="18"/><line x1="18" y1="6" x2="19.6" y2="4.4"/>'),
    moon: svg('<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'),
    monitor: svg('<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'),
    x: svg('<line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/>'),
    dot: svg('<circle cx="12" cy="12" r="6"/>')
  };

  var APPEARANCE_ICON = { light: "sun", dark: "moon", system: "monitor" };

  var DEFAULT_TABS = [
    { id: "general", label: "通用设置", icon: "gear" },
    { id: "models", label: "模型", icon: "layers" },
    { id: "builtin-plugins", label: "内置插件", icon: "sliders" },
    { id: "agent-presets", label: "Agent预设", icon: "user" }
  ];

  // ---------- 状态 ----------
  var ST = {
    open: false,
    tab: "general",
    data: null,          // GET /api/settings 全量结构
    rows: [],            // 通用设置.行集（服务端顺序为准）
    generalRaw: null,    // 通用设置 原始对象（可能是旧形状）
    doc: null,           // GET /api/settings/document → {路径,可用}
    loadError: "",
    loading: false,
    timers: {},          // 行 id → 防抖定时器
    prev: {},            // 行 id → 变更前的值（失败回滚用）
    pendingConfirm: null, // {rowId, value}
    // R106-B：快捷键面板状态
    scOpen: false,       // 面板是否打开（替代通用设置行渲染）
    scData: null,        // GET /api/shortcuts 响应 {"文档","自定义计数","目录"}
    scError: "",         // 面板级错误（服务不可用等）
    scMsg: "",           // 服务端回显消息（400 错误文案原样展示）
    scConfirmAll: false, // 「恢复全部默认」确认条
    scRecId: null        // 录制态的命令 id（null = 未在录制）
  };

  var el = {}; // DOM 缓存

  // ---------- API（沿用 sidebar.js / app.js 的 fetch 写法风格） ----------
  function authToken() {
    try {
      return (typeof location !== "undefined" && location.search)
        ? (new URLSearchParams(location.search).get("token") || "") : "";
    } catch (e) { return ""; }
  }

  function api(method, url, body) {
    var initObj = { method: method, headers: {} };
    var tk = authToken();
    if (tk) initObj.headers["X-Auth-Token"] = tk;
    if (body != null) {
      initObj.headers["Content-Type"] = "application/json";
      initObj.body = JSON.stringify(body);
    }
    return fetch(url, initObj).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!res.ok) {
          var raw = data && (data["错误"] || data.error || data.message);
          var msg = typeof raw === "string" ? raw
                  : (raw && typeof raw === "object") ? JSON.stringify(raw)
                  : ("HTTP " + res.status);
          var err = new Error(msg);
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  // ---------- 纯渲染：页签导航 ----------
  function tabsOf(data) {
    var labels = data && data["页签"];
    var ids = data && data["页签标识"];
    if (!Array.isArray(labels) || !labels.length) return DEFAULT_TABS;
    var out = [];
    for (var i = 0; i < labels.length; i++) {
      var fallback = DEFAULT_TABS[i] || { id: String(i), label: labels[i], icon: "dot" };
      out.push({
        id: (Array.isArray(ids) && ids[i]) ? ids[i] : fallback.id,
        label: labels[i],
        icon: fallback.icon
      });
    }
    return out;
  }

  function renderNavHtml(tabs, activeTab) {
    var list = Array.isArray(tabs) && tabs.length ? tabs : DEFAULT_TABS;
    var disabled = !ST.data;
    var h = "";
    for (var i = 0; i < list.length; i++) {
      var t = list[i];
      var cls = "settings-nav-item" +
        (t.id === activeTab ? " is-active" : "") + (disabled ? " is-disabled" : "");
      h += '<button type="button" class="' + cls + '" data-tab-id="' + esc(t.id) + '">' +
           (ICONS[t.icon] || ICONS.dot) +
           '<span class="settings-nav-label">' + esc(t.label) + "</span></button>";
    }
    return h;
  }

  // ---------- 纯渲染：单个控件的 HTML（选项一律来自「选项」数组，禁止写死） ----------
  function renderControlHtml(row) {
    var id = esc(row.id);
    var type = row["类型"] || "";
    var val = row["值"];
    var opts = Array.isArray(row["选项"]) ? row["选项"] : [];
    var i, o;

    if (type === "下拉") {
      var h = '<select class="settings-select" data-row-id="' + id + '">';
      for (i = 0; i < opts.length; i++) {
        o = opts[i] || {};
        h += '<option value="' + esc(o["值"]) + '"' +
             (String(o["值"]) === String(val) ? " selected" : "") + ">" +
             esc(o["标签"] != null ? o["标签"] : o["值"]) + "</option>";
      }
      h += "</select>";
      return h;
    }

    if (type === "卡片三选") {
      var c = '<div class="settings-cards" data-row-id="' + id + '">';
      for (i = 0; i < opts.length; i++) {
        o = opts[i] || {};
        var iconKey = APPEARANCE_ICON[String(o["值"])] || "dot";
        c += '<button type="button" class="settings-card' +
             (String(o["值"]) === String(val) ? " is-active" : "") +
             '" data-value="' + esc(o["值"]) + '" aria-pressed="' +
             (String(o["值"]) === String(val) ? "true" : "false") + '">' +
             (ICONS[iconKey] || ICONS.dot) +
             '<span>' + esc(o["标签"] != null ? o["标签"] : o["值"]) + "</span></button>";
      }
      c += "</div>";
      return c;
    }

    if (type === "数字") {
      var min = row["最小"], max = row["最大"];
      var n = '<input type="number" class="settings-number" data-row-id="' + id + '" value="' +
        esc(val) + '"' +
        (min != null ? ' min="' + esc(min) + '"' : "") +
        (max != null ? ' max="' + esc(max) + '"' : "") + ">";
      n += '<span class="settings-unit">' + esc(row["单位"] != null ? row["单位"] : "px") + "</span>";
      return n;
    }

    if (type === "开关") {
      var on = (val === true || val === "true" || val === "真");
      return '<button type="button" class="settings-switch' + (on ? " is-on" : "") +
        '" data-row-id="' + id + '" role="switch" aria-checked="' + (on ? "true" : "false") +
        '"><span class="settings-switch-knob"></span></button>';
    }

    if (type === "按钮") {
      return '<button type="button" class="settings-line-btn" data-row-id="' + id + '">' +
        esc(row["按钮"] != null ? row["按钮"] : "编辑快捷键") + "</button>";
    }

    // 未知类型：只读展示，不崩
    return '<span class="settings-row-desc">' + esc(val) + "</span>";
  }

  function renderRowHtml(row) {
    var desc = row["描述"] || "";
    return '<div class="settings-row" data-row-id="' + esc(row.id) + '">' +
      '<div class="settings-row-main">' +
        '<div class="settings-row-title">' + esc(row["标题"] != null ? row["标题"] : row.id) + "</div>" +
        (desc ? '<div class="settings-row-desc">' + esc(desc) + "</div>" : "") +
        '<div class="settings-row-error" hidden></div>' +
        '<div class="settings-row-hint" hidden></div>' +
      "</div>" +
      '<div class="settings-row-ctrl">' + renderControlHtml(row) + "</div>" +
      "</div>";
  }

  function renderRowsHtml(rows) {
    var h = "";
    for (var i = 0; i < rows.length; i++) h += renderRowHtml(rows[i]);
    return h;
  }

  // ---------- 纯渲染：四个页签内容 ----------
  function renderGeneralHtml(general) {
    var rows = general && Array.isArray(general["行集"]) ? general["行集"] : [];
    if (!rows.length) {
      // 旧形状（A 线未合流）：不崩，给一行提示；顺带把已有只读数据显示出来
      var h = '<div class="settings-note">通用设置行集尚未接入</div>';
      var pm = general && general["内置插件"] && general["内置插件"]["按模式"];
      if (pm && typeof pm === "object") {
        var keys = Object.keys(pm);
        h += '<div class="settings-row"><div class="settings-row-main">' +
             '<div class="settings-row-title">内置插件（按模式，只读）</div>' +
             '<div class="settings-row-desc">数据来自 通用设置.内置插件.按模式，等待「行集」接入后落到正式控件</div>' +
             "</div><div class=\"settings-row-ctrl\"><span class=\"settings-row-desc\">";
        for (var k = 0; k < keys.length; k++) {
          h += esc(keys[k]) + "：" + esc(pm[keys[k]]) + (k < keys.length - 1 ? "　" : "");
        }
        h += "</span></div></div>";
      }
      return h;
    }
    return renderRowsHtml(rows);
  }

  function renderModelHtml(model) {
    if (model == null) return '<div class="settings-note">暂无模型数据</div>';
    if (typeof model === "string") return '<div class="settings-note">' + esc(model) + "</div>";
    var txt = model["说明"] != null ? model["说明"] : "";
    if (!txt) txt = "模型清单由宿主设置服务提供";
    var h = '<div class="settings-note">' + esc(txt) + "</div>";
    if (model["来源"]) h += '<div class="settings-row-desc">来源：' + esc(model["来源"]) + "</div>";
    if (Array.isArray(model["列表"]) && model["列表"].length) {
      for (var i = 0; i < model["列表"].length; i++) {
        var m = model["列表"][i] || {};
        h += '<div class="settings-row"><div class="settings-row-main">' +
             '<div class="settings-row-title">' + esc(m["名称"] != null ? m["名称"] : m["id"]) + "</div>" +
             (m["描述"] ? '<div class="settings-row-desc">' + esc(m["描述"]) + "</div>" : "") +
             '</div><div class="settings-row-ctrl"><span class="settings-row-desc">' +
             esc(m["值"] != null ? m["值"] : "") + "</span></div></div>";
      }
    }
    return h;
  }

  function renderPluginsHtml(plugins) {
    if (plugins == null) return '<div class="settings-note">暂无内置插件数据</div>';
    var list = Array.isArray(plugins["按模式概览"]) ? plugins["按模式概览"] : [];
    var h = "";
    if (plugins["说明"]) h += '<div class="settings-note">' + esc(plugins["说明"]) + "</div>";
    if (!list.length) {
      return h + '<div class="settings-note">宿主插件注册表未提供「按模式概览」</div>';
    }
    for (var i = 0; i < list.length; i++) {
      var p = list[i] || {};
      var count = p["展平后"] != null ? p["展平后"]
                : (p["展平后计数"] != null ? p["展平后计数"]
                : (Array.isArray(p["插件行"]) ? p["插件行"].length : 0));
      h += '<div class="settings-plugin-row">' +
        '<div class="settings-plugin-head">' +
          '<span class="settings-plugin-name">' + esc(p["名称"] != null ? p["名称"] : p["id"]) + "</span>" +
          '<span class="settings-plugin-count" title="展平后计数">' + esc(count) + " 项</span>" +
        "</div>" +
        (p["描述"] ? '<div class="settings-plugin-desc">' + esc(p["描述"]) + "</div>" : "") +
        "</div>";
    }
    return h;
  }

  function foldHtml(title, body) {
    if (body == null || String(body).trim() === "" || body === false) return "";
    return '<details class="settings-fold"><summary>' + esc(title) + "</summary>" +
           '<div class="settings-fold-body">' + esc(body) + "</div></details>";
  }

  function renderAgentsHtml(agents) {
    if (agents == null) return '<div class="settings-note">暂无 Agent 预设数据</div>';
    var list = Array.isArray(agents["预设列表"]) ? agents["预设列表"] : [];
    if (!list.length) return '<div class="settings-note">宿主未提供 Agent 预设列表</div>';
    var h = "";
    for (var i = 0; i < list.length; i++) {
      var a = list[i] || {};
      var block = (a["区块"] && typeof a["区块"] === "object") ? a["区块"] : a;
      h += '<div class="settings-preset-card">' +
        '<div class="settings-preset-head">' +
          '<span class="settings-preset-name">' + esc(a["名称"] != null ? a["名称"] : a["id"]) + "</span>" +
          (a["是否内置"] === true || a["是否内置"] === "真" ? '<span class="settings-badge">内置</span>' : "") +
          (a["是否默认"] === true || a["是否默认"] === "真"
            ? '<span class="settings-badge is-default">新任务默认</span>' : "") +
        "</div>" +
        (a["描述"] ? '<div class="settings-preset-desc">' + esc(a["描述"]) + "</div>" : "") +
        foldHtml("模式说明", block["模式说明"]) +
        foldHtml("如何使用", block["如何使用"]) +
        "</div>";
    }
    return h;
  }

  function tabDescHtml(data, tabId) {
    var m = data && data["页签说明"];
    if (m && typeof m === "object" && m[tabId]) {
      return '<div class="settings-tab-desc">' + esc(m[tabId]) + "</div>";
    }
    return "";
  }

  function renderContentHtml() {
    if (ST.loadError) {
      return '<div class="settings-error-box">' + esc(ST.loadError) +
        '<div><button type="button" class="settings-retry">刷新重试</button></div></div>';
    }
    if (ST.loading) return '<div class="settings-loading">正在加载设置…</div>';
    var d = ST.data || {};
    var body = "";
    if (ST.tab === "general") body = renderGeneralHtml(d["通用设置"]);
    else if (ST.tab === "models") body = renderModelHtml(d["模型"]);
    else if (ST.tab === "builtin-plugins") body = renderPluginsHtml(d["内置插件"]);
    else if (ST.tab === "agent-presets") body = renderAgentsHtml(d["Agent预设"]);
    else body = '<div class="settings-note">该页签暂无内容</div>';
    return tabDescHtml(d, ST.tab) + body;
  }

  // ---------- fullAccess 确认层（文案固定，见任务书 §版式规格） ----------
  var CONFIRM_TITLE = "确认启用完全权限？";
  var CONFIRM_TEXT = "启用完全权限后，新会话将减少确认步骤，并且可以直接执行更多操作，" +
    "包括敏感操作、文件修改或外部命令。仅建议在你信任后续任务时使用。";
  var CONFIRM_CHECK = "我已了解风险，并愿意继续";
  var CONFIRM_GO = "启用完全权限";
  var CONFIRM_CANCEL = "取消";

  function confirmHtml() {
    return '<div class="settings-confirm-card" role="dialog" aria-modal="true" aria-label="' +
      esc(CONFIRM_TITLE) + '">' +
      '<h3 class="settings-confirm-title">' + esc(CONFIRM_TITLE) + "</h3>" +
      '<p class="settings-confirm-text">' + esc(CONFIRM_TEXT) + "</p>" +
      '<label class="settings-confirm-check">' +
        '<input type="checkbox" class="settings-confirm-box">' +
        "<span>" + esc(CONFIRM_CHECK) + "</span></label>" +
      '<div class="settings-confirm-actions">' +
        '<button type="button" class="settings-confirm-cancel">' + esc(CONFIRM_CANCEL) + "</button>" +
        '<button type="button" class="settings-confirm-go" disabled>' + esc(CONFIRM_GO) + "</button>" +
      "</div></div>";
  }

  // ---------- DOM 构建 ----------
  function buildDialog() {
    if (el.overlay || !HAS_DOM) return;
    var wrap = document.createElement("div");
    wrap.className = "settings-overlay";
    wrap.innerHTML =
      '<div class="settings-dialog" role="dialog" aria-modal="true" aria-label="设置">' +
        '<div class="settings-head">' +
          '<h2 class="settings-head-title">设置</h2>' +
          '<div class="settings-head-mid">' +
            '<code class="settings-docpath" hidden title=""></code>' +
          "</div>" +
          '<div class="settings-head-right">' +
            '<button type="button" class="settings-btn-ghost settings-open-file" hidden>打开配置文件</button>' +
            '<button type="button" class="settings-x" aria-label="关闭" title="关闭（Esc）">' +
              ICONS.x + "</button>" +
          "</div>" +
        "</div>" +
        '<div class="settings-degrade" hidden></div>' +
        '<div class="settings-body">' +
          '<nav class="settings-nav"></nav>' +
          '<div class="settings-content"></div>' +
        "</div>" +
        '<div class="settings-confirm">' + confirmHtml() + "</div>" +
      "</div>";
    document.body.appendChild(wrap);

    el.overlay = wrap;
    el.dialog = wrap.querySelector(".settings-dialog");
    el.degrade = wrap.querySelector(".settings-degrade");
    el.docPath = wrap.querySelector(".settings-docpath");
    el.openFile = wrap.querySelector(".settings-open-file");
    el.xBtn = wrap.querySelector(".settings-x");
    el.nav = wrap.querySelector(".settings-nav");
    el.content = wrap.querySelector(".settings-content");
    el.confirm = wrap.querySelector(".settings-confirm");
    el.confirmBox = wrap.querySelector(".settings-confirm-box");
    el.confirmGo = wrap.querySelector(".settings-confirm-go");
    el.confirmCancel = wrap.querySelector(".settings-confirm-cancel");

    // 关闭：X / 点遮罩（对话框内部点击不关）
    el.xBtn.addEventListener("click", close);
    el.overlay.addEventListener("mousedown", function (e) {
      if (e.target === el.overlay && !isConfirmOpen()) close();
    });
    // 页签切换
    el.nav.addEventListener("click", function (e) {
      var btn = closest(e.target, ".settings-nav-item");
      if (!btn || btn.classList.contains("is-disabled")) return;
      // R106-B：从快捷键面板切页签 → 先退回普通渲染
      if (ST.scOpen) { ST.scOpen = false; ST.scRecId = null; }
      ST.tab = btn.getAttribute("data-tab-id") || "general";
      renderNav();
      renderContent();
    });
    // 控件变更 / 点击
    el.content.addEventListener("change", onContentChange);
    el.content.addEventListener("click", onContentClick);
    // 确认层
    el.confirmCancel.addEventListener("click", function () { cancelConfirm(); });
    el.confirmGo.addEventListener("click", function () { acceptConfirm(); });
    el.confirmBox.addEventListener("change", function () {
      el.confirmGo.disabled = !el.confirmBox.checked;
    });
    el.openFile.addEventListener("click", onOpenFile);
  }

  function closest(node, selector) {
    var n = node;
    while (n && n !== document.body) {
      if (n.nodeType === 1 && typeof n.matches === "function" && n.matches(selector)) return n;
      n = n.parentNode;
    }
    return null;
  }

  function renderNav() {
    if (!el.nav) return;
    el.nav.innerHTML = renderNavHtml(tabsOf(ST.data), ST.tab);
  }

  function renderContent() {
    if (!el.content) return;
    el.content.innerHTML = renderContentHtml();
  }

  function renderHeadDoc() {
    if (!el.docPath || !el.openFile) return;
    var doc = ST.doc || null;
    var path = doc && doc["路径"] ? String(doc["路径"]) : "";
    var usable = !!(doc && (doc["可用"] === true || doc["可用"] === "真"));
    if (path && usable) {
      el.docPath.textContent = path;
      el.docPath.title = path;
      el.docPath.hidden = false;
      el.openFile.hidden = false;
    } else {
      el.docPath.hidden = true;
      el.openFile.hidden = true;
    }
  }

  // ---------- 打开 / 关闭 / 加载 ----------
  function open() {
    buildDialog();
    if (!el.overlay) return;
    ST.open = true;
    ST.loadError = "";
    ST.loading = true;
    el.overlay.classList.add("is-open");
    renderNav();
    renderContent();
    load();
    refreshEffective(); // R106-B：打开对话框即应用一次（否则刷新后设置不生效）
  }

  function close() {
    if (!el.overlay) return;
    ST.open = false;
    ST.scOpen = false;
    ST.scRecId = null;
    stopKeyCapture();
    cancelConfirm();
    for (var k in ST.timers) { clearTimeout(ST.timers[k]); delete ST.timers[k]; }
    ST.prev = {};
    el.overlay.classList.remove("is-open");
  }

  function load() {
    var pData = api("GET", "/api/settings").then(null, function (e) { return { __err: e }; });
    var pDoc = api("GET", "/api/settings/document").then(null, function (e) { return { __err: e }; });
    return Promise.all([pData, pDoc]).then(function (rs) {
      var d = rs[0], doc = rs[1];
      if (!d || d.__err || typeof d !== "object" || Array.isArray(d)) {
        ST.loadError = "连接异常，刷新重试";
        ST.data = null;
        ST.generalRaw = null;
        ST.rows = [];
      } else {
        ST.data = d;
        ST.generalRaw = d["通用设置"] || null;
        ST.rows = (ST.generalRaw && Array.isArray(ST.generalRaw["行集"]))
          ? ST.generalRaw["行集"] : [];
        ST.loadError = "";
      }
      // 配置文档路径：优先 /api/settings/document，回退 通用设置.配置文档
      ST.doc = (doc && !doc.__err && typeof doc === "object") ? doc
             : (ST.generalRaw && ST.generalRaw["配置文档"]) || null;
      ST.loading = false;
      renderHeadDoc();
      renderNav();
      renderContent();
    });
  }

  // ---------- 控件交互 → 保存 ----------
  function findRow(rowId) {
    for (var i = 0; i < ST.rows.length; i++) {
      if (String(ST.rows[i].id) === String(rowId)) return ST.rows[i];
    }
    return null;
  }

  function onContentChange(e) {
    var t = e.target;
    if (!t) return;
    var rowId = t.getAttribute && t.getAttribute("data-row-id");
    if (!rowId) return;
    var row = findRow(rowId);
    if (!row) return;
    if (t.classList.contains("settings-select")) {
      requestChange(rowId, t.value);
    } else if (t.classList.contains("settings-number")) {
      var v = Number(t.value);
      if (isNaN(v)) { syncRowControl(rowId); return; }
      if (row["最小"] != null && v < Number(row["最小"])) v = Number(row["最小"]);
      if (row["最大"] != null && v > Number(row["最大"])) v = Number(row["最大"]);
      t.value = String(v);
      requestChange(rowId, v);
    }
  }

  function onContentClick(e) {
    // R106-B：快捷键面板打开时，点击全走面板处理器
    if (ST.scOpen) { handleScClick(e); return; }
    var target = e.target;
    if (!target || !target.closest) return;
    var t = target;

    if (t.classList && t.classList.contains("settings-retry")) { open(); return; }

    // 外观卡片（点到图标/文字也要命中）
    var card = t.closest(".settings-card");
    if (card) {
      var wrap1 = card.parentNode;
      var rowId1 = wrap1 && wrap1.getAttribute ? wrap1.getAttribute("data-row-id") : "";
      if (rowId1) requestChange(rowId1, card.getAttribute("data-value"));
      return;
    }

    // 开关（点到圆点也要命中）
    var sw = t.closest(".settings-switch");
    if (sw) {
      var rowId2 = sw.getAttribute("data-row-id");
      var row = findRow(rowId2);
      if (!row) return;
      var next = !sw.classList.contains("is-on");
      sw.classList.toggle("is-on", next);
      sw.setAttribute("aria-checked", next ? "true" : "false");
      requestChange(rowId2, next);
      return;
    }

    // 快捷键：R106-B —— 替换「宿主面未接入」2 秒提示，改为打开真实编辑器面板
    var lineBtn = t.closest(".settings-line-btn");
    if (lineBtn) {
      if (lineBtn.getAttribute("data-row-id") === "shortcuts") {
        openShortcuts();
        return;
      }
      var rowEl = lineBtn.closest(".settings-row");
      var hint = rowEl ? rowEl.querySelector(".settings-row-hint") : null;
      if (hint) {
        hint.textContent = "宿主面未接入";
        hint.hidden = false;
        setTimeout(function () { hint.hidden = true; }, 2000);
      }
    }
  }

  // 值变更入口：fullAccess 需先过确认层；否则直接提交
  function requestChange(rowId, value) {
    var row = findRow(rowId);
    if (!row) return;
    if (row.id === "permission" && String(value) === "fullAccess" &&
        String(row["值"]) !== "fullAccess") {
      showConfirm(rowId, value);
      return;
    }
    applyChange(rowId, value);
  }

  function applyChange(rowId, value) {
    var row = findRow(rowId);
    if (!row) return;
    if (ST.prev[rowId] === undefined) ST.prev[rowId] = row["值"];
    row["值"] = value;
    clearRowError(rowId);
    clearTimeout(ST.timers[rowId]);
    ST.timers[rowId] = setTimeout(function () {
      delete ST.timers[rowId];
      save(rowId);
    }, 300);
  }

  function save(rowId) {
    var row = findRow(rowId);
    if (!row) return;
    var value = row["值"];
    return api("POST", "/api/settings", { 行: rowId, 值: value })
      .then(function (res) {
        if (res && Array.isArray(res["行集"])) {
          ST.rows = res["行集"];
          if (ST.generalRaw) ST.generalRaw["行集"] = res["行集"];
          ST.prev[rowId] = undefined;
          renderContent();
          refreshEffective(); // R106-B：保存成功后按返回重新应用
          return;
        }
        if (res && (res["状态"] === "ok" || res["状态"] === "OK")) {
          ST.prev[rowId] = undefined;
          clearRowError(rowId);
          refreshEffective(); // R106-B：保存成功后重新应用
          return;
        }
        failRow(rowId, res && res["错误"] ? String(res["错误"]) : "服务端未返回合法行集");
      })
      .then(null, function (e) {
        failRow(rowId, (e && e.message) ? e.message : String(e));
      });
  }

  function failRow(rowId, detail) {
    var old = ST.prev[rowId];
    ST.prev[rowId] = undefined;
    var row = findRow(rowId);
    if (row && old !== undefined) row["值"] = old;
    setRowError(rowId, "保存失败，请重试");
    if (detail && typeof console !== "undefined" && console.warn) {
      console.warn("[settings] 保存失败：" + detail);
    }
    syncRowControl(rowId);
  }

  function setRowError(rowId, msg) {
    if (!el.content) return;
    var node = el.content.querySelector('.settings-row[data-row-id="' + rowId + '"] .settings-row-error');
    if (!node) return;
    node.textContent = msg;
    node.hidden = false;
  }

  function clearRowError(rowId) {
    if (!el.content) return;
    var node = el.content.querySelector('.settings-row[data-row-id="' + rowId + '"] .settings-row-error');
    if (node) { node.hidden = true; node.textContent = ""; }
  }

  // 回滚控件（用当前数据重建该行控件）
  function syncRowControl(rowId) {
    if (!el.content) return;
    var row = findRow(rowId);
    if (!row) return;
    var ctrl = el.content.querySelector('.settings-row[data-row-id="' + rowId + '"] .settings-row-ctrl');
    if (ctrl) ctrl.innerHTML = renderControlHtml(row);
  }

  // ---------- fullAccess 确认层 ----------
  function isConfirmOpen() {
    return !!(el.confirm && el.confirm.classList.contains("is-open"));
  }

  function showConfirm(rowId, value) {
    ST.pendingConfirm = { rowId: rowId, value: value };
    el.confirmBox.checked = false;
    el.confirmGo.disabled = true;
    el.confirm.classList.add("is-open");
  }

  // 取消 / 关闭：回滚该行控件到变更前的值
  function cancelConfirm() {
    var p = ST.pendingConfirm;
    ST.pendingConfirm = null;
    if (el.confirm) el.confirm.classList.remove("is-open");
    if (el.confirmBox) el.confirmBox.checked = false;
    if (el.confirmGo) el.confirmGo.disabled = true;
    if (p) syncRowControl(p.rowId);
  }

  function acceptConfirm() {
    var p = ST.pendingConfirm;
    if (!p || !el.confirmBox.checked) return;
    ST.pendingConfirm = null;
    el.confirm.classList.remove("is-open");
    el.confirmBox.checked = false;
    el.confirmGo.disabled = true;
    applyChange(p.rowId, p.value);
  }

  // ---------- 打开配置文件（宿主未提供打开能力：退化为复制路径） ----------
  function onOpenFile() {
    if (!el.openFile) return;
    var path = ST.doc && ST.doc["路径"] ? String(ST.doc["路径"]) : "";
    if (!path) return;
    var done = function () {
      var old = "打开配置文件";
      el.openFile.textContent = "已复制路径";
      setTimeout(function () { el.openFile.textContent = old; }, 1500);
    };
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(path).then(done, done);
        return;
      }
    } catch (e) { /* 忽略，走提示 */ }
    done();
  }

  // ---------- 全局键盘：Esc 关闭（快捷键面板/确认层优先） ----------
  if (HAS_DOM) {
    document.addEventListener("keydown", function (e) {
      if (!ST.open || e.key !== "Escape") return;
      if (ST.scOpen) { closeShortcuts(); return; }
      if (isConfirmOpen()) cancelConfirm();
      else close();
    });
  }

  // =====================================================================
  // R106-B：设置生效（纯换算函数，挂 window.SettingsApply）
  // 单一真值源原则（修订 A2）：前端只上报系统偏好（matchMedia），服务端把 system
  // 解析成 light/dark 终值；前端不得自行判定 system，否则两套真值源必然打架。
  // =====================================================================
  function 组装生效查询(系统偏好值) {
    var v = (系统偏好值 === "dark") ? "dark" : "light"; // 缺省/非法一律 light（与 C 线解析一致）
    return "?系统偏好=" + v;
  }

  function 主题属性(生效参数) {
    var v = 生效参数 && 生效参数["主题"];
    return { 属性: "data-theme", 值: (v === "dark") ? "dark" : "light" };
  }

  function 字号变量(生效参数) {
    if (!生效参数) return null;
    var n = Number(生效参数["字号"]);
    if (isNaN(n) || n < 12 || n > 17 || Math.floor(n) !== n) return null; // 越界/类型错 → 不应用
    return { 变量: "--msg-font-size", 值: n + "px" };
  }

  function 链接目标属性(生效参数) {
    if (!生效参数) return null;
    var v = 生效参数["链接目标"];
    if (v === "_self" || v === "sidebar") return { 属性: "data-link-target", 值: "_self" };
    if (v === "_blank" || v === "newTab") return { 属性: "data-link-target", 值: "_blank" };
    return null;
  }

  function 降级提示(生效参数) {
    var items = (生效参数 && Array.isArray(生效参数["降级项"])) ? 生效参数["降级项"] : [];
    var parts = [];
    for (var i = 0; i < items.length; i++) {
      var it = String(items[i]);
      if (it === "语言") parts.push("英文文案未接入（降级项）");
      else if (it === "权限") parts.push("权限预设为自定义档，按默认档位回落（降级项）");
      else parts.push(it + " 暂未落地（降级项）");
    }
    return parts.join("；");
  }

  // 应用函数：消费纯换算结果落到 DOM（纯函数不读 DOM，本函数不做换算）
  function applyEffective(eff) {
    if (!eff || typeof eff !== "object") return;
    var root = document.documentElement;
    var th = 主题属性(eff);
    root.setAttribute(th.属性, th.值);
    var fz = 字号变量(eff);
    if (fz && root.style && root.style.setProperty) root.style.setProperty(fz.变量, fz.值);
    var lt = 链接目标属性(eff);
    if (lt) root.setAttribute(lt.属性, lt.值);
    var lang = eff["语言"];
    if (lang === "zh" || lang === "en") root.setAttribute("data-lang", lang);
    if (el.degrade) {
      var tip = 降级提示(eff);
      if (tip) { el.degrade.textContent = tip; el.degrade.hidden = false; }
      else { el.degrade.hidden = true; el.degrade.textContent = ""; }
    }
  }

  function 系统偏好() {
    try {
      if (typeof window.matchMedia === "function") {
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }
    } catch (e) { /* 旧浏览器无 matchMedia → light */ }
    return "light";
  }

  function refreshEffective() {
    if (typeof fetch !== "function") return;
    var url = "/api/settings/effective" + 组装生效查询(系统偏好());
    return api("GET", url)
      .then(function (eff) { applyEffective(eff); })
      .then(null, function (e) {
        // /api/settings/effective 不可用 → 不报错、不白屏，跳过应用
        if (typeof console !== "undefined" && console.warn) {
          console.warn("[settings] 生效参数获取失败，跳过应用：" + ((e && e.message) || e));
        }
      });
  }

  // =====================================================================
  // R106-B：快捷键编辑器面板（R105 遗留 #3 收口，替换「宿主面未接入」提示）
  // 数据全走 C 线 GET/POST /api/shortcuts；保留/冲突规则权威在 D 线模块（src/快捷键.light），
  // 前端不重算——错误文案一律回显服务端返回的「错误」字段。
  // =====================================================================
  function countCustom(目录列表) {
    var n = 0;
    for (var i = 0; i < 目录列表.length; i++) {
      var r = 目录列表[i] || {};
      if (r["是否自定义"] === true || r["是否自定义"] === "真") n++;
    }
    return n;
  }

  function findScEntry(id) {
    var d = ST.scData;
    var list = d && Array.isArray(d["目录"]) ? d["目录"] : [];
    for (var i = 0; i < list.length; i++) {
      if (String(list[i] && list[i]["id"]) === String(id)) return list[i];
    }
    return null;
  }

  function scPlatform() {
    try {
      if (typeof navigator !== "undefined" && navigator.platform &&
          String(navigator.platform).indexOf("Mac") >= 0) return "macos";
    } catch (e) { /* 平台探测失败 → 非 mac */ }
    return "other";
  }

  function openShortcuts() {
    ST.scOpen = true;
    ST.scData = null;
    ST.scError = "";
    ST.scMsg = "";
    ST.scConfirmAll = false;
    ST.scRecId = null;
    renderShortcuts();
    loadShortcuts();
  }

  function closeShortcuts() {
    ST.scOpen = false;
    ST.scConfirmAll = false;
    ST.scRecId = null;
    stopKeyCapture();
    renderContent();
  }

  function loadShortcuts() {
    return api("GET", "/api/shortcuts")
      .then(function (d) {
        ST.scData = d;
        ST.scMsg = "";
        renderShortcuts();
      })
      .then(null, function (e) {
        // /api/shortcuts 不可用（404/503）→ 面板内明显提示并禁用录入，不静默、不白屏
        ST.scData = null;
        ST.scError = "快捷键服务不可用（" + ((e && e.status) || (e && e.message) || "网络错误") + "），面板只读";
        renderShortcuts();
      });
  }

  function postShortcuts(载荷) {
    return api("POST", "/api/shortcuts", 载荷)
      .then(function (res) {
        if (res && Array.isArray(res["目录"])) {
          if (ST.scData) ST.scData["目录"] = res["目录"];
          else ST.scData = { "目录": res["目录"], "文档": null };
          ST.scData["自定义计数"] = countCustom(ST.scData["目录"]);
        }
        ST.scMsg = (res && (res["状态"] === "ok")) ? "已保存" : "";
        ST.scConfirmAll = false;
        stopKeyCapture();
        ST.scRecId = null;
        renderShortcuts();
      })
      .then(null, function (e) {
        // 错误文案一律回显服务端返回的「错误」字段（400），前端不重算保留/冲突规则
        ST.scMsg = (e && e.message) ? e.message : "保存失败";
        ST.scConfirmAll = false;
        stopKeyCapture();
        ST.scRecId = null;
        renderShortcuts();
      });
  }

  // 录入：捕获期 keydown → 组装键串 → POST（Esc 取消录制，对齐上游 record-help）
  function startKeyCapture(命令id) {
    if (!ST.scData) return;
    ST.scRecId = 命令id;
    ST.scMsg = "";
    renderShortcuts();
    if (!HAS_DOM) return;
    stopKeyCapture();
    ST.scKeyHandler = function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "Escape") {
        stopKeyCapture();
        ST.scRecId = null;
        renderShortcuts();
        return;
      }
      var ks = 组装键串(e, scPlatform());
      if (!ks) return; // 仅修饰键按下 → 继续等待
      postShortcuts({ 命令: ST.scRecId, 键: ks });
    };
    document.addEventListener("keydown", ST.scKeyHandler, true);
  }

  function stopKeyCapture() {
    if (ST.scKeyHandler && HAS_DOM) {
      document.removeEventListener("keydown", ST.scKeyHandler, true);
    }
    ST.scKeyHandler = null;
  }

  // 纯函数：keydown 事件 → 键串（Mod/Ctrl/Alt/Shift + 键名），对齐 D 线键串层口径。
  // 主修饰键（mac=meta、其它=control）回显 Mod；其余修饰键按 control→alt→shift→meta 排列。
  function 组装键串(事件, 平台 = "other") {
    if (!事件 || !事件.key) return "";
    var MODS = { Shift: 1, Control: 1, Alt: 1, Meta: 1 };
    if (MODS[事件.key]) return ""; // 仅修饰键按下 → 不是有效键位
    var mac = (平台 === "macos");
    var phys = { control: !!事件.ctrlKey, alt: !!事件.altKey, shift: !!事件.shiftKey, meta: !!事件.metaKey };
    var primaryPhys = mac ? "meta" : "control";
    var disp = { control: "Ctrl", alt: "Alt", shift: "Shift", meta: "Meta" };
    var order = ["control", "alt", "shift", "meta"];
    var out = [];
    if (phys[primaryPhys]) out.push("Mod");
    for (var i = 0; i < order.length; i++) {
      var m = order[i];
      if (phys[m] && m !== primaryPhys) out.push(disp[m]);
    }
    var key = String(事件.key);
    if (key === " ") key = "Space";
    else if (key.length === 1) key = key.toUpperCase();
    out.push(key);
    return out.join("+");
  }

  // 纯函数：目录对象 → 面板 HTML（顶部自定义计数 + 按分组分节的行集）
  function 渲染快捷键目录(目录对象) {
    var list = null, count = null;
    if (Array.isArray(目录对象)) { list = 目录对象; }
    else if (目录对象 && typeof 目录对象 === "object") {
      list = Array.isArray(目录对象["目录"]) ? 目录对象["目录"] : null;
      count = 目录对象["自定义计数"];
    }
    if (!list) return '<div class="settings-note">暂无快捷键目录</div>';
    if (count === null || count === undefined) count = countCustom(list);
    var h = "";
    // 自定义计数文案（{count} 项已自定义；count=0 时不显示）
    if (count > 0) h += '<div class="settings-sc-count">' + esc(count) + " 项已自定义</div>";
    // 按分组分节（保持首现顺序：应用操作 / 消息输入 / 菜单与弹层 / 审批区域）
    var seen = [], groups = {};
    for (var i2 = 0; i2 < list.length; i2++) {
      var g = String((list[i2] && list[i2]["分组"]) || "其它");
      if (!groups[g]) { groups[g] = []; seen.push(g); }
      groups[g].push(list[i2]);
    }
    for (var j = 0; j < seen.length; j++) {
      h += '<div class="settings-sc-group" data-sc-group="' + esc(seen[j]) + '">' +
           '<div class="settings-sc-group-title">' + esc(seen[j]) + "</div>";
      var rows = groups[seen[j]];
      for (var k = 0; k < rows.length; k++) {
        var row = rows[k] || {};
        var custom = row["是否自定义"] === true || row["是否自定义"] === "真";
        var keyTxt = (row["当前键"] != null && row["当前键"] !== "") ? row["当前键"] : "暂无快捷键";
        h += '<div class="settings-sc-row' + (custom ? " is-custom" : "") +
             '" data-sc-id="' + esc(row["id"]) + '">' +
             '<span class="settings-sc-label">' + esc(row["标签"] != null ? row["标签"] : row["id"]) + "</span>" +
             '<span class="settings-sc-key">' + esc(keyTxt) + "</span>" +
             (custom
               ? '<span class="settings-sc-actions">' +
                 '<button type="button" class="settings-sc-btn" data-sc-act="remove">移除</button>' +
                 '<button type="button" class="settings-sc-btn" data-sc-act="reset">恢复默认</button></span>'
               : "") +
             "</div>";
      }
      h += "</div>";
    }
    return h;
  }

  function renderShortcuts() {
    if (!el.content) return;
    var h = '<div class="settings-sc-head">' +
      '<button type="button" class="settings-sc-back">‹ 返回设置</button>' +
      '<span class="settings-sc-title">快捷键</span>' +
      (ST.scData && !ST.scError
        ? '<button type="button" class="settings-sc-btn settings-sc-resetall">恢复全部默认</button>'
        : "") +
      "</div>";
    if (ST.scConfirmAll) {
      h += '<div class="settings-sc-confirm">恢复全部默认快捷键？' +
        '<button type="button" class="settings-sc-btn" data-sc-act="confirm-yes">确认恢复</button>' +
        '<button type="button" class="settings-sc-btn" data-sc-act="confirm-no">取消</button></div>';
    }
    if (ST.scError) {
      h += '<div class="settings-error-box">' + esc(ST.scError) + "</div>";
    } else if (!ST.scData) {
      h += '<div class="settings-loading">正在加载快捷键…</div>';
    } else {
      if (ST.scMsg) h += '<div class="settings-sc-msg">' + esc(ST.scMsg) + "</div>";
      if (ST.scRecId) {
        h += '<div class="settings-sc-recording">正在录制「' + esc(ST.scRecId) +
             "」：按下组合键（Esc 取消）</div>";
      }
      h += 渲染快捷键目录(ST.scData);
      h += '<div class="settings-sc-hint">浏览器可用组合：Mod+/、Mod+Shift+,、Mod+Shift+.。' +
           "Mod 在 Mac 上为 Command，其他系统为 Ctrl。</div>";
    }
    el.content.innerHTML = h;
  }

  function handleScClick(e) {
    var t = e.target;
    if (!t || !t.closest) return;
    if (t.closest(".settings-sc-back")) { closeShortcuts(); return; }
    if (t.closest(".settings-sc-resetall")) { ST.scConfirmAll = true; ST.scMsg = ""; renderShortcuts(); return; }
    var btn = t.closest(".settings-sc-btn");
    if (btn) {
      var act = btn.getAttribute("data-sc-act");
      if (act === "confirm-yes") { postShortcuts({ 重置: true }); return; }
      if (act === "confirm-no") { ST.scConfirmAll = false; renderShortcuts(); return; }
      if ((act === "remove" || act === "reset") && ST.scData) {
        var rowEl2 = btn.closest(".settings-sc-row");
        var id2 = rowEl2 ? rowEl2.getAttribute("data-sc-id") : "";
        // wire 契约（§2.3）只有 {"命令","键"} 与 {"重置":真}：单条恢复/移除用默认键串重提；
        // 命令行默认键为空串时服务端回 400，错误文案原样展示（契约缺口在汇报中登记）。
        var entry = findScEntry(id2);
        var 键串 = (entry && entry["默认键"]) ? entry["默认键"] : "";
        postShortcuts({ 命令: id2, 键: 键串 });
      }
      return;
    }
    var rowEl = t.closest(".settings-sc-row");
    if (rowEl && ST.scData) {
      var id = rowEl.getAttribute("data-sc-id");
      if (id) startKeyCapture(id);
    }
  }

  // ---------- 导出（含纯渲染函数，供本地 mock 断言） ----------
  var exported = {
    open: open,
    close: close,
    load: load,
    escapeHtml: esc,
    tabsOf: tabsOf,
    renderNavHtml: renderNavHtml,
    renderRowHtml: renderRowHtml,
    renderRowsHtml: renderRowsHtml,
    renderControlHtml: renderControlHtml,
    renderGeneralHtml: renderGeneralHtml,
    renderModelHtml: renderModelHtml,
    renderPluginsHtml: renderPluginsHtml,
    renderAgentsHtml: renderAgentsHtml,
    renderContentHtml: renderContentHtml,
    confirmHtml: confirmHtml,
    ICONS: ICONS,
    CONFIRM_TEXT: CONFIRM_TEXT,
    _state: ST,
    // 下划线：内部实现，仅用于本地 mock 自测（真实运行不依赖）
    _api: api,
    _applyChange: applyChange,
    _save: save
  };
  G.LightSettings = exported;

  // R106-B：纯换算函数导出点（.scratch/r106b_assert.mjs 驱动用）
  G.SettingsApply = {
    组装生效查询: 组装生效查询,
    主题属性: 主题属性,
    字号变量: 字号变量,
    链接目标属性: 链接目标属性,
    降级提示: 降级提示,
    组装键串: 组装键串,
    渲染快捷键目录: 渲染快捷键目录
  };

  // ---------- 入口按钮自绑定 ----------
  function autoInit() {
    if (!HAS_DOM) return;
    var entry = document.getElementById("app-settings-btn");
    if (entry) entry.addEventListener("click", open);
    refreshEffective(); // R106-B：页面加载即应用一次（刷新后保存值直接生效；端点不可用则跳过）
  }
  if (HAS_DOM) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoInit);
    else autoInit();
  }
})();

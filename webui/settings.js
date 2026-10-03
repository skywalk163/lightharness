/* =====================================================================
 * lightharness WebUI — 设置对话框（settings.js，零依赖）
 * ---------------------------------------------------------------------
 * 职责：按实拍截图复刻 dsh 设置对话框，四页签（通用设置 / 模型 / 内置插件 /
 *      Agent 预设），通用设置 9 行由服务端「行集」驱动渲染。
 *      R107-D：模型 / 内置插件 / Agent 预设 三页已改为「真实渲染」（消费 A/B/C 线
 *      契约形状），可列出清单、可点开详情、模型页可编辑、密钥永不回显；并按
 *      status ∈ ok|loading|unavailable 区分加载中 / 不可用态。
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
 * R108-G 新增（前端消费 C/D/F 三线新数据）：
 *   - 引导：GET/POST /api/settings/onboarding，两步渲染（welcome-notice / deepseek-official），
 *     密钥永不回显；页面级首访浮层（.settings-ob-page）与设置内浮层（.settings-ob-layer）共用同一渲染/保存逻辑。
 *   - 侧栏插件面板：GET /api/settings/plugin-panel，只读渲染（无任何写控件）；
 *     本仓可用恒假 → 只出「本部署没有可管理的 profile，无法安装或启停插件。」不可用态。
 *   - 多 provider + 发现：GET /api/settings/providers + POST /discover（§2.2 route 校验、
 *     「获取可用模型」按钮三态、候选弹窗 12 条文案逐字）；route 校验正则前端实现，注释声明上游只在客户端做的偏离。
 * 全局暴露 window.LightSettings（含纯渲染函数，供本地 mock 断言使用）
 *           与 window.SettingsApply（纯换算函数导出点，供 .scratch/r106b_assert.mjs 驱动）
 *           与 window.SettingsPanels（R108-G：C/F 线纯渲染函数导出点，供 .scratch/r108g_assert.mjs 驱动）。
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
    scRecId: null,        // 录制态的命令 id（null = 未在录制）
    // R108-G：C / D / F 线新数据（独立端点，加载失败不阻塞四页签渲染）
    onboarding: null,     // GET /api/settings/onboarding（C 线）
    obOpen: false,        // 引导浮层是否打开（覆盖设置内容）
    obBusy: false,        // 引导「保存中…」
    obErr: "",            // 引导保存失败逐字回显
    pluginPanel: null,    // GET /api/settings/plugin-panel（F 线）
    providers: null,      // GET /api/settings/providers（D 线目录）
    providersView: {      // provider 添加表单/发现候选的前端视图状态
      baseURL: "", 显示名: "", api: "", 协议选项: [], 地址空: false, 发现中: false,
      候选: null, 搜索: "", 选中: [], 无匹配: false
    }
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

  // §2.1 模型页（真实数据 + 可编辑；密钥永不回显，T-7）
  function 字段(label, control) {
    return '<div class="settings-model-field">' +
      '<label class="settings-model-field-label">' + esc(label) + "</label>" + control + "</div>";
  }

  // 提供商编辑卡（默认折叠；点「编辑」展开——原生 <details> 不依赖 JS）
  // ⛔ 密钥 input 恒 value=""；任何环节都不把明文写进 DOM/state。
  function 渲染提供商编辑卡(p, model) {
    var cred = p["凭据"] || {};
    var configured = (cred["configured"] === true || cred["configured"] === "真");
    var keyPlaceholder = configured ? "已配置——输入新值可替换" : "输入 API 密钥";
    var protos = Array.isArray(model["协议选项"]) ? model["协议选项"] : [];
    var sel = '<select class="settings-select" data-field="api"><option value="">未选择</option>';
    for (var i = 0; i < protos.length; i++) {
      var o = protos[i] || {};
      sel += '<option value="' + esc(o["值"]) + '">' + esc(o["标签"] != null ? o["标签"] : o["值"]) + "</option>";
    }
    sel += "</select>";

    var h = '<details class="settings-model-edit" data-edit-provider="' + esc(p["provider"] || "") + '">' +
      '<summary class="settings-model-edit-summary">编辑</summary>' +
      '<div class="settings-model-edit-body">';
    // API 密钥（password，永不回显，value 恒空）
    h += 字段("API 密钥",
      '<input type="password" class="settings-input settings-model-key" data-field="api_key" ' +
      'placeholder="' + esc(keyPlaceholder) + '" value="" autocomplete="off">');
    // API 地址（存储键 baseURL）
    h += 字段("API 地址",
      '<input type="text" class="settings-input" data-field="base_url" value="">');
    // API 协议（存储键 api；选项标签逐字）
    h += 字段("API 协议", sel);
    // 显示名称
    h += 字段("显示名称",
      '<input type="text" class="settings-input" data-field="display_name" value="' + esc(p["显示名"] || "") + '">');
    // 自定义设置（折叠；其余字段在 cordis.patch.yml 的提示）
    h += foldHtml("自定义设置", "其余字段在 cordis.patch.yml 中，请直接编辑对应段。");
    // 模型目录区
    h += '<div class="settings-model-catalog"><div class="settings-model-catalog-title">模型目录</div>';
    var rows = Array.isArray(model["模型行"]) ? model["模型行"] : [];
    if (model["模型目录继承"] === true) {
      h += '<div class="settings-note">正在使用适配器默认模型</div>';
    } else if (!rows.length) {
      h += '<div class="settings-note">模型选择器中将不显示任何模型；目录外 ID 仍可直接发送。</div>';
    } else {
      h += '<div class="settings-model-catalog-list">';
      for (var j = 0; j < rows.length; j++) {
        var m = rows[j] || {};
        var advBody = "上下文窗口：" + esc(m["上下文窗口"] != null ? m["上下文窗口"] : "") +
          "<br>最大输出：" + esc(m["最大输出"] != null ? m["最大输出"] : "使用提供商默认值") +
          "<br>输入类型：" + esc(Array.isArray(m["输入类型"]) ? m["输入类型"].join("、") : "");
        h += '<div class="settings-model-row-item" data-model-id="' + esc(m["id"] || "") + '">' +
          '<span class="settings-model-row-name">' + esc(m["name"] != null ? m["name"] : m["id"]) + "</span>" +
          '<span class="settings-model-row-id">' + esc(m["id"] || "") + "</span>" +
          '<button type="button" class="settings-sc-btn settings-model-row-del" data-model-act="del" ' +
          'data-model-id="' + esc(m["id"] || "") + '">删除模型</button>' +
          '<details class="settings-model-row-adv"><summary>模型选项</summary>' +
          '<div class="settings-model-row-adv-body">' + advBody + "</div></details></div>";
      }
      h += "</div>";
    }
    h += '<div class="settings-model-catalog-actions">' +
      '<button type="button" class="settings-sc-btn" data-model-act="reset" ' +
      'data-provider="' + esc(p["provider"] || "") + '">恢复默认模型</button>' +
      '<button type="button" class="settings-sc-btn" data-model-act="add">添加模型</button>' +
      "</div>";
    // 底部 取消 / 保存 + 错误回显位
    h += '<div class="settings-model-edit-error" hidden></div>' +
      '<div class="settings-model-edit-actions">' +
      '<button type="button" class="settings-confirm-cancel settings-model-cancel">取消</button>' +
      '<button type="button" class="settings-confirm-go settings-model-save" ' +
      'data-provider="' + esc(p["provider"] || "") + '">保存</button>' +
      "</div></div></details>";
    return h;
  }

  function renderModelHtml(model, status) {
    if (status === "loading") return '<div class="settings-loading">正在加载设置…</div>';
    if (status === "unavailable" || model == null)
      return '<div class="settings-error-box">模型服务不可用，暂时无法编辑。请检查后端连接后重试。</div>';
    var txt = (model["说明"] != null) ? model["说明"] : "填入各提供商的 API 密钥即可使用其模型。";
    var h = '<div class="settings-note">' + esc(txt) + "</div>";
    if (model["只读"] === true || model["只读"] === "真")
      h += '<div class="settings-note">当前部署的设置文档为只读。</div>';
    // R108-G：模型页签内接入 D 线「添加模型提供商」表单与候选弹窗（§2.2）
    if (ST.providers != null) {
      h += 渲染添加表单(
        Array.isArray(ST.providers["提供商行"]) ? ST.providers["提供商行"] : [], ST.providersView);
    }
    if (ST.providersView && ST.providersView["fetchErr"]) {
      h += '<div class="settings-provider-error">' + esc(ST.providersView["fetchErr"]) + "</div>";
    }
    var provs = Array.isArray(model["提供商行"]) ? model["提供商行"] : [];
    for (var i = 0; i < provs.length; i++) {
      var p = provs[i] || {};
      var cred = p["凭据"] || {};
      var configured = (cred["configured"] === true || cred["configured"] === "真");
      var dotClass = configured ? "is-ok" : "is-missing";
      var dotAria = configured ? "API 密钥已配置" : "API 密钥缺失";
      var canDel = (p["可删除"] === true || p["可删除"] === "真");
      // §2.2：provider 行 = 显示名 + route + 凭据圆点 + 可删除才出删除 + 已声明才出「自定义」标签
      var 已声明 = (p["已声明"] === true || p["已声明"] === "真");
      h += '<div class="settings-model-provider" data-provider="' + esc(p["provider"] || "") + '">' +
        '<span class="settings-cred-dot ' + dotClass + '" aria-label="' + esc(dotAria) + '"></span>' +
        '<span class="settings-model-provider-name">' + esc(p["显示名"] != null ? p["显示名"] : p["provider"]) + "</span>" +
        '<span class="settings-model-provider-id">' + esc(p["provider"] || "") + "</span>" +
        (已声明 ? '<span class="settings-badge settings-badge-custom">自定义</span>' : "") +
        '<span class="settings-model-provider-actions">' +
        '<button type="button" class="settings-line-btn settings-model-edit-btn">编辑</button>' +
        (canDel ? '<button type="button" class="settings-sc-btn settings-model-del-btn">删除</button>' : "") +
        "</span></div>";
      h += 渲染提供商编辑卡(p, model);
    }
    // R108-G：发现候选弹窗叠加（同一视图状态驱动；候选为真实数组且非空才叠加，避免失败后空 overlay 挡住表单）
    if (ST.providersView && Array.isArray(ST.providersView["候选"]) && ST.providersView["候选"].length > 0)
      h += 渲染候选弹窗(ST.providersView);
    return h;
  }

  // §2.2 插件页：事实表单元
  function 事实项(label, value) {
    return "<dt>" + esc(label) + "</dt><dd>" + esc(value == null ? "" : value) + "</dd>";
  }

  // 单个成员行（会话/全局通用）：点击就地展开事实表（原生 <details>）
  function 渲染插件成员(m) {
    var enabled = m["启用"];
    var tagClass = (enabled === "disabled") ? "disabled" : (enabled === "conditional") ? "conditional" : "enabled";
    var tagText = (enabled === "disabled") ? "已停用"
                : (enabled === "conditional") ? "条件启用" : "已启用";
    var headTitle = (m["标题"] != null && m["标题"] !== "") ? m["标题"] : (m["moduleName"] || m["entryId"] || "");
    var h = '<details class="settings-plugin-member" data-entry-id="' + esc(m["entryId"] || "") + '">' +
      '<summary class="settings-plugin-member-summary">' +
        '<span class="settings-plugin-member-title">' + esc(headTitle) + "</span>" +
        '<span class="settings-plugin-member-tag settings-tag-' + tagClass + '">' + tagText + "</span>" +
      "</summary>" +
      '<div class="settings-plugin-member-body"><dl class="settings-fact">' +
        事实项("完整名称", m["moduleName"]) +
        事实项("来自", m["来自预设"]) +
        事实项("配置状态", m["配置状态"]) +
        事实项("运行状态", (m["运行状态"] != null && m["运行状态"] !== "") ? m["运行状态"] : "未运行") +
        (m["禁用条件"] != null && m["禁用条件"] !== "" ? 事实项("禁用条件", m["禁用条件"]) : "") +
        ((m["由预设提供"] === true || m["由预设提供"] === "真")
          ? 事实项("启用于", Array.isArray(m["启用于"]) ? m["启用于"].join(" · ") : "") : "") +
      "</dl></div></details>";
    return h;
  }

  function renderPluginsHtml(plugins, status) {
    if (status === "loading") return '<div class="settings-loading">正在加载设置…</div>';
    if (status === "unavailable" || plugins == null)
      return '<div class="settings-error-box">插件服务不可用，暂时无法列出插件。请检查后端连接后重试。</div>';
    var h = "";
    if (plugins["说明"]) h += '<div class="settings-note">' + esc(plugins["说明"]) + "</div>";
    var groups = Array.isArray(plugins["分组"]) ? plugins["分组"] : [];
    if (!groups.length)
      return h + '<div class="settings-note">暂无插件分组数据。</div>';
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i] || {};
      var openAttr = (g["默认展开"] === true || g["默认展开"] === "真") ? " open" : "";
      h += '<div class="settings-plugin-group"' + openAttr + '>' +
        '<div class="settings-plugin-group-head">' +
          '<span class="settings-plugin-group-name">' + esc(g["分组"] || "") + "</span>" +
          (g["副标题"] ? '<span class="settings-plugin-group-sub">' + esc(g["副标题"]) + "</span>" : "") +
          '<span class="settings-plugin-count">' + esc(g["计数"] != null ? g["计数"] : 0) + " 个</span>" +
          (g["当前预设"] != null ? '<span class="settings-plugin-group-preset">当前预设：' + esc(g["当前预设"]) + "</span>" : "") +
        "</div>";
      var items = Array.isArray(g["项"]) ? g["项"] : [];
      if (!items.length) {
        h += '<div class="settings-note">暂无插件。</div>';
      } else {
        for (var j = 0; j < items.length; j++) h += 渲染插件成员(items[j]);
      }
      h += "</div>";
    }
    return h;
  }

  function foldHtml(title, body) {
    if (body == null || String(body).trim() === "" || body === false) return "";
    return '<details class="settings-fold"><summary>' + esc(title) + "</summary>" +
           '<div class="settings-fold-body">' + esc(body) + "</div></details>";
  }

  // §2.3 预设页：单卡渲染（含「查看配置」详情展开 + 设为新任务默认）
  function 渲染预设卡(card, agents) {
    var isDefault = (card["是否默认"] === true || card["是否默认"] === "真");
    var devTools = (agents["开发者工具"] === true || agents["开发者工具"] === "真");
    var h = '<div class="settings-preset-card" data-preset-id="' + esc(card["id"] || "") + '">' +
      '<div class="settings-preset-head">' +
        '<span class="settings-preset-name">' + esc(card["名称"] != null ? card["名称"] : card["id"]) + "</span>" +
        (card["是否内置"] === true || card["是否内置"] === "真" ? '<span class="settings-badge">内置</span>' : "") +
        (isDefault ? '<span class="settings-badge is-default">新任务默认</span>' : "") +
        (card["失败原因"] != null && card["失败原因"] !== "" ? '<span class="settings-badge is-broken">加载失败</span>' : "") +
      "</div>" +
      (card["描述"] ? '<div class="settings-preset-desc">' + esc(card["描述"]) + "</div>" : "");
    var help = (card["帮助"] && typeof card["帮助"] === "object") ? card["帮助"] : {};
    h += foldHtml("模式说明", help["模式说明"]);
    h += foldHtml("如何使用", help["如何使用"]);
    // 「查看配置」详情（成员 / 计数 / 禁用 / 默认）
    var cfg = card["配置"] || {};
    var rows = Array.isArray(cfg["行"]) ? cfg["行"] : [];
    h += '<details class="settings-preset-config" data-config-preset="' + esc(card["id"] || "") + '">' +
      '<summary class="settings-preset-config-summary">查看配置</summary>' +
      '<div class="settings-preset-config-body">' +
        '<div class="settings-preset-config-meta">成员数：' + esc(cfg["成员数"] != null ? cfg["成员数"] : rows.length) +
          "　" + (isDefault ? "新任务默认" : "非默认") + "</div>" +
        '<pre class="settings-preset-config-pre">' + esc(cfg["文本"] || "") + "</pre>" +
        '<dl class="settings-fact">';
    for (var k = 0; k < rows.length; k++) {
      var r = rows[k] || {};
      h += '<div class="settings-preset-config-row">' +
        "<dt>" + esc(r["entryId"] || "") + "</dt>" +
        "<dd>" + esc(r["moduleName"] || "") + "　启用：" + esc(String(r["启用"])) +
        (r["禁用条件"] ? "　禁用条件：" + esc(r["禁用条件"]) : "") + "</dd></div>";
    }
    h += "</dl></div></details>";
    // 动作
    h += '<div class="settings-preset-actions">';
    if (isDefault) {
      h += '<button type="button" class="settings-line-btn" disabled>新任务默认</button>';
    } else {
      h += '<button type="button" class="settings-sc-btn settings-preset-setdefault" data-preset-id="' +
        esc(card["id"] || "") + '"' +
        (devTools ? "" : ' disabled title="请先在通用设置中开启代码工作工具，再设置默认值"') +
        ">设为新任务默认</button>";
    }
    h += "</div></div>";
    return h;
  }

  function renderAgentsHtml(agents, status) {
    if (status === "loading") return '<div class="settings-loading">正在加载设置…</div>';
    if (status === "unavailable" || agents == null)
      return '<div class="settings-error-box">Agent 预设服务不可用，暂时无法查看。请检查后端连接后重试。</div>';
    var h = "";
    if (agents["说明"]) h += '<div class="settings-note">' + esc(agents["说明"]) + "</div>";
    var groups = Array.isArray(agents["分组"]) ? agents["分组"] : [];
    if (!groups.length) return h + '<div class="settings-note">暂无 Agent 预设分组。</div>';
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i] || {};
      var cards = Array.isArray(g["预设"]) ? g["预设"] : [];
      h += '<div class="settings-preset-group">' +
        '<div class="settings-preset-group-title">' + esc(g["分组"] || "") + "</div>";
      if (!cards.length) {
        h += '<div class="settings-note">暂无自定义预设。</div>';
      } else {
        for (var j = 0; j < cards.length; j++) h += 渲染预设卡(cards[j], agents);
      }
      h += "</div>";
    }
    return h;
  }

  // =====================================================================
  // R108 任务线 G：前端消费（C / D / F 三线新数据）
  //   C 线 → GET /api/settings/onboarding    引导状态（任务书 §2.1）
  //   F 线 → GET /api/settings/plugin-panel  插件面板只读（任务书 §2.4）
  //   D 线 → GET /api/settings/providers + POST /discover 多 provider 与发现（§2.2）
  // 铁律（沿用 R107）：
  //   · 密钥永不回显：不写 DOM、不进任何 state、不落任何返回串。
  //   · 保留 / 校验类文案一律回显服务端或 D 线返回值，前端不自造。
  // =====================================================================

  // ---------- G-1：首次引导（C 线） ----------
  // 渲染引导(引导, status, 错误) -> HTML；status ∈ ok|loading|unavailable
  //   错误：保存失败 / 密钥为空时由调用方传入，逐字回显（welcomeError / keyRequired）。
  //   当前步骤为空 → 返回 ""（不显示引导时不留下任何占位 DOM 或空白块）。
  function 渲染引导(引导, status, 错误, busy) {
    if (status === "loading") return '<div class="settings-loading">正在加载设置…</div>';
    if (status === "unavailable" || 引导 == null || typeof 引导 !== "object")
      return '<div class="settings-error-box">引导服务不可用，暂时无法获取。请检查后端连接后重试。</div>';
    var 当前 = 引导["当前步骤"];
    if (当前 == null || 当前 === "") return "";
    var 步集 = Array.isArray(引导["步骤"]) ? 引导["步骤"] : [];
    for (var i = 0; i < 步集.length; i++) {
      if ((步集[i] || {})["id"] === 当前) return 渲染引导步(步集[i], 错误, busy === true);
    }
    return "";
  }

  // 渲染引导步(步, 错误, busy) -> 单步卡片（标题 / 正文 / 主次按钮；deepseek-official 含密码框）
  //   ⛔ 密钥 input 恒 value=""，任何环节都不把明文写进 DOM/state。
  function 渲染引导步(步, 错误, busy) {
    var 主文案 = 步["主按钮"] != null ? 步["主按钮"] : "";
    // busy 态：仅 deepseek-official 有「保存中…」逐字文案（§2.1）
    if (busy === true && 步["id"] === "deepseek-official") 主文案 = "保存中…";
    var h = '<div class="settings-onboarding" data-step="' + esc(步["id"] || "") + '">' +
      '<h3 class="settings-onboarding-title">' + esc(步["标题"] || "") + "</h3>";
    var 正文 = 步["正文"];
    if (Array.isArray(正文)) {
      for (var i = 0; i < 正文.length; i++)
        h += '<p class="settings-onboarding-text">' + esc(正文[i]) + "</p>";
    } else if (正文 != null && 正文 !== "") {
      var 段 = String(正文).split("\n");
      for (var j = 0; j < 段.length; j++) {
        var t = 段[j].trim();
        if (t) h += '<p class="settings-onboarding-text">' + esc(t) + "</p>";
      }
    }
    if (步["id"] === "deepseek-official") {
      h += '<label class="settings-onboarding-label" for="settings-onboarding-key">API Key</label>' +
        '<input type="password" id="settings-onboarding-key" class="settings-input settings-onboarding-key" ' +
        'placeholder="sk-..." value="" autocomplete="off"' + (busy === true ? " disabled" : "") + '>' +
        '<div class="settings-onboarding-err" hidden></div>';
    }
    if (错误 != null && 错误 !== "")
      h += '<div class="settings-onboarding-err-msg">' + esc(错误) + "</div>";
    h += '<div class="settings-onboarding-actions">' +
      '<button type="button" class="settings-confirm-go settings-onboarding-main" ' +
      'data-step="' + esc(步["id"] || "") + '"' + (busy === true ? ' disabled aria-busy="true"' : "") + ">" +
      esc(主文案) + "</button>";
    if (步["次按钮"] != null && 步["次按钮"] !== "")
      h += '<button type="button" class="settings-confirm-cancel settings-onboarding-skip" ' +
        'data-step="' + esc(步["id"] || "") + '"' + (busy === true ? " disabled" : "") + ">" +
        esc(步["次按钮"]) + "</button>";
    h += "</div></div>";
    return h;
  }

  // ---------- G-2：侧栏插件面板（F 线，只读） ----------
  // 只读原因文案(原因) -> 逐字；management-required / unaddressable
  function 只读原因文案(原因) {
    if (原因 === "management-required") return "插件管理所需，不能停用或卸载";
    if (原因 === "unaddressable") return "当前 profile 的 patch 无法唯一定位这一项";
    return "";
  }

  // 相位文案(相位) -> 逐字；pending/loading/active/failed/unloading；空（null）→ 未运行
  function 相位文案(相位) {
    if (相位 == null || 相位 === "") return "未运行";
    if (相位 === "pending") return "等待依赖";
    if (相位 === "loading") return "加载中";
    if (相位 === "active") return "运行中";
    if (相位 === "failed") return "异常";
    if (相位 === "unloading") return "卸载中";
    return "";
  }

  // 组件计数文案(行列表) -> 「共 n 个 · x 运行中 · y 已停用 · z 异常」；仅 >0 项追加，' · ' 连接（逐字）
  function 组件计数文案(行列表) {
    var 行 = Array.isArray(行列表) ? 行列表 : [];
    var 运行中 = 0, 已停用 = 0, 异常 = 0;
    for (var i = 0; i < 行.length; i++) {
      var r = 行[i] || {};
      if (r["相位"] === "active") 运行中++;
      if (r["已启用"] === false || r["已启用"] === "假") 已停用++;
      if (r["相位"] === "failed") 异常++;
    }
    var t = "共 " + 行.length + " 个";
    if (运行中 > 0) t += " · " + 运行中 + " 运行中";
    if (已停用 > 0) t += " · " + 已停用 + " 已停用";
    if (异常 > 0) t += " · " + 异常 + " 异常";
    return t;
  }

  // 渲染插件卡(卡) -> 只读卡片（标题/版本/标签/描述/只读启用开关/组件计数/组件行）
  //   ⛔ 不渲染任何写控件（无安装 / 启用 / 停用 / 卸载）；开关仅只读展示，title=只读原因逐字。
  function 渲染插件卡(卡) {
    var 标题 = (卡["标题"] != null && 卡["标题"] !== "") ? 卡["标题"] : (卡["name"] || "");
    var 只读原因 = 只读原因文案(卡["只读原因"]);
    var h = '<div class="settings-pp-card" data-pkg="' + esc(卡["name"] || "") + '">' +
      '<div class="settings-pp-card-head">' +
        '<span class="settings-pp-card-title">' + esc(标题) + "</span>";
    if (卡["版本"] != null && 卡["版本"] !== "")
      h += '<span class="settings-pp-card-version">' + esc("v" + 卡["版本"]) + "</span>";
    var 标签 = Array.isArray(卡["标签"]) ? 卡["标签"] : [];
    for (var i = 0; i < 标签.length; i++) {
      if (标签[i] === "实验性" || 标签[i] === "异常")
        h += '<span class="settings-pp-card-tag is-' + esc(标签[i]) + '">' + esc(标签[i]) + "</span>";
    }
    var on = (卡["已启用"] === true || 卡["已启用"] === "真");
    h += '<span class="settings-pp-toggle ' + (on ? "is-on" : "") + '" ' +
      'role="switch" aria-checked="' + (on ? "true" : "false") + '"' +
      (只读原因 ? ' title="' + esc(只读原因) + '"' : "") + "></span>";
    h += "</div>";
    if (卡["描述"] != null && 卡["描述"] !== "")
      h += '<p class="settings-pp-card-desc">' + esc(卡["描述"]) + "</p>";
    h += '<div class="settings-pp-card-meta">' +
      '<span class="settings-pp-card-count">' + esc(组件计数文案(卡["组件"])) + "</span>" +
      '<span class="settings-pp-card-pkg">' + esc(卡["name"] || "") + "</span>" +
      (只读原因 ? '<span class="settings-pp-card-reason" title="' + esc(只读原因) + '">' + esc(只读原因) + "</span>" : "") +
      "</div>";
    var 行集 = Array.isArray(卡["组件"]) ? 卡["组件"] : [];
    h += '<div class="settings-pp-card-parts">';
    if (行集.length) {
      h += '<div class="settings-pp-card-parts-title">包含的组件</div>';
      for (var j = 0; j < 行集.length; j++) {
        var r = 行集[j] || {};
        var rOn = (r["已启用"] === true || r["已启用"] === "真");
        var rReason = 只读原因文案(r["只读原因"]);
        h += '<div class="settings-pp-row" data-row-id="' + esc(r["rowId"] || "") + '">' +
          '<span class="settings-pp-row-name">' + esc(r["moduleName"] || r["rowId"] || "") + "</span>" +
          '<span class="settings-pp-row-state">' + esc(rOn ? "已启用" : "已关闭") + "</span>" +
          '<span class="settings-pp-row-phase">' + esc(相位文案(r["相位"])) + "</span>" +
          (rReason ? '<span class="settings-pp-row-reason" title="' + esc(rReason) + '">' + esc(rReason) + "</span>" : "") +
          "</div>";
      }
    } else {
      var 工具表 = Array.isArray(卡["工具表"]) ? 卡["工具表"] : [];
      if (工具表.length) {
        h += '<div class="settings-pp-card-parts-title">工具清单（' + 工具表.length + "）</div>";
        for (var k = 0; k < 工具表.length; k++) {
          h += '<div class="settings-pp-row"><span class="settings-pp-row-name">' + esc(工具表[k]) + '</span></div>';
        }
      } else {
        h += '<div class="settings-note">这个插件包不包含任何组件。</div>';
      }
    }
    h += "</div>";
    // R111：光明插件只支持启停（内置分发，不可卸载/在线安装）
    h += '<div class="settings-pp-card-actions">' +
      '<button type="button" class="settings-pp-btn" data-pp-act="toggle" data-pkg="' + esc(卡["name"] || "") + '" data-on="' + (on ? "1" : "0") + '">' + (on ? "停用" : "启用") + "</button>" +
      "</div>";
    return h + "</div></div>";
  }
  function 渲染插件组(组) {
    var 卡集 = Array.isArray(组["卡片"]) ? 组["卡片"] : [];
    if (!卡集.length) return "";
    var h = '<section class="settings-pp-group" data-group="' + esc(组["分组"] || "") + '">' +
      '<div class="settings-pp-group-head">' +
        '<span class="settings-pp-group-name">' + esc(组["分组"] || "") + "</span>" +
        '<span class="settings-pp-group-count">' + esc(组["计数"] != null ? 组["计数"] : 卡集.length) + " 个</span>" +
      "</div>";
    for (var i = 0; i < 卡集.length; i++) h += 渲染插件卡(卡集[i]);
    return h + "</section>";
  }

  // 渲染插件面板(面板, status, 选项) -> HTML；⛔ 不渲染任何写控件
  //   本仓 可用 恒 假 → 只出不可用态（逐字「本部署没有可管理的 profile…」）。
  //   选项.headless：不渲染页头（用于已自带标题的页面级浮层）。
  function 渲染插件面板(面板, status, 选项) {
    if (status === "loading") return '<div class="settings-loading">正在加载插件…</div>';
    if (status === "unavailable" || 面板 == null || typeof 面板 !== "object")
      return '<div class="settings-error-box">插件面板服务不可用，暂时无法获取。请检查后端连接后重试。</div>';
    var 选项2 = (选项 && typeof 选项 === "object") ? 选项 : {};
    var h = "";
    if (选项2["headless"] !== true) {
      h += '<div class="settings-pp-head">' +
        '<h3 class="settings-pp-title">插件</h3>' +
        '<p class="settings-pp-intro">光明插件启停</p>' +
        '<p class="settings-pp-info">下列为 lightplugin 内置光明插件（以工具形式挂到 agent）。点「停用」即从 agent 工具表摘除，「启用」即恢复。</p></div>';
    }
    if (面板["刷新中"] === true || 面板["刷新中"] === "真")
      h += '<div class="settings-note">正在刷新…</div>';
    if (面板["错误"] != null && 面板["错误"] !== "")
      h += '<div class="settings-pp-error">' + esc(面板["错误"]) + "</div>";
    var 可用 = (面板["可用"] === true || 面板["可用"] === "真");
    if (!可用) {
      var 文 = (面板["不可用文案"] != null && 面板["不可用文案"] !== "")
        ? 面板["不可用文案"] : "本部署没有可管理的 profile，无法安装或启停插件。";
      return h + '<div class="settings-note settings-pp-unavailable">' + esc(文) + "</div>";
    }
    var 组集 = Array.isArray(面板["分组"]) ? 面板["分组"] : [];
    // R112：添加插件输入框（接受 GitHub URL 或 owner/repo）
    h += '<div class="settings-pp-install">' +
      '<input type="text" class="settings-pp-input" data-pp-install-input placeholder="GitHub 地址或 owner/repo，回车添加插件" />' +
      '<button type="button" class="settings-pp-btn" data-pp-act="install">添加</button>' +
      "</div>";
    if (!组集.length) return h + '<div class="settings-note">暂无光明插件。</div>';
    for (var i = 0; i < 组集.length; i++) h += 渲染插件组(组集[i]);
    return h;
  }

  // ---------- G-3：多 provider + 模型发现（D 线） ----------
  // route 校验正则（逐字取 §2.2）：^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$
  //   上游理由：deriveKeyRef 会大写并把非字母数字段换成 _，凭据引用必须是 POSIX shell
  //   标识符 ⇒ 首字符不能是数字。上游只在客户端做此校验（宿主侧无同名正则），
  //   本仓在纯渲染面实现，注释声明这一偏离。
  var ROUTE_RE = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;

  // 校验路由(route, 已有行集) -> {合法, 消息}；错误文案逐字取 §2.2，前端不重算规则
  function 校验路由(route, 已有行集) {
    var s = String(route == null ? "" : route);
    if (s === "") return { 合法: true, 消息: "" };
    if (!ROUTE_RE.test(s))
      return { 合法: false, 消息: "需以小写字母开头，之后可用小写字母、数字和短横线。" };
    var 行集 = Array.isArray(已有行集) ? 已有行集 : [];
    for (var i = 0; i < 行集.length; i++) {
      if (String((行集[i] || {})["provider"] || "") === s)
        return { 合法: false, 消息: "已有提供商使用了这个 ID。" };
    }
    return { 合法: true, 消息: "" };
  }

  // 渲染提供商行(p) -> 显示名 + route + 凭据圆点 + 可删除才出删除 + 已声明才出「自定义」标签
  function 渲染提供商行(p) {
    var 凭据 = p["凭据"] || {};
    var configured = (凭据["configured"] === true || 凭据["configured"] === "真");
    var dotClass = configured ? "is-ok" : "is-missing";
    var dotAria = configured ? "API 密钥已配置" : "API 密钥缺失";
    var 可删 = (p["可删除"] === true || p["可删除"] === "真");
    var 自定义 = (p["已声明"] === true || p["已声明"] === "真");
    var h = '<div class="settings-model-provider settings-provider-row" data-provider="' + esc(p["provider"] || "") + '">' +
      '<span class="settings-cred-dot ' + dotClass + '" aria-label="' + esc(dotAria) + '"></span>' +
      '<span class="settings-model-provider-name">' + esc(p["显示名"] != null ? p["显示名"] : p["provider"]) + "</span>" +
      '<span class="settings-model-provider-id">' + esc(p["provider"] || "") + "</span>" +
      (自定义 ? '<span class="settings-badge settings-badge-custom">自定义</span>' : "") +
      '<span class="settings-model-provider-actions">';
    if (可删) h += '<button type="button" class="settings-sc-btn settings-provider-del">删除</button>';
    h += "</span></div>";
    if (p["错误"] != null && p["错误"] !== "")
      h += '<div class="settings-provider-error">' + esc(p["错误"]) + "</div>";
    return h;
  }

  // 协议选项列表(视图) -> 协议白名单选项（逐字取自 §2.2/D 线返回值；视图无则回默认三项）
  function 协议选项列表(视图) {
    var 表 = (视图 && Array.isArray(视图["协议选项"])) ? 视图["协议选项"] : [];
    if (!表.length) {
      表 = [
        { 值: "anthropic-messages", 标签: "Anthropic Messages" },
        { 值: "openai-completions", 标签: "OpenAI Chat Completions" },
        { 值: "openai-responses", 标签: "OpenAI Responses" }
      ];
    }
    return 表;
  }

  // 渲染添加表单(已有行集, 视图) -> 「添加模型提供商」折叠区 + route 校验 + 获取可用模型按钮
  //   · route 校验三态由 校验路由() 产出，错误文案逐字回显（容器恒渲染，运行时输入即时显示）。
  //   · 获取按钮：busy=「正在询问提供商…」；缺地址时 title=「请先填写 API 地址，再获取。」（逐字）。
  function 渲染添加表单(已有行集, 视图) {
    var 校验 = (视图 && 视图["校验"]) || {};
    var route = 校验["route"] != null ? 校验["route"] : "";
    var 消息 = 校验["消息"] || "";
    var h = '<details class="settings-provider-add" open>' +
      '<summary class="settings-provider-add-summary">添加模型提供商</summary>' +
      '<div class="settings-provider-add-body">';
    h += 字段("Provider ID",
      '<input type="text" class="settings-input settings-provider-route" data-field="route" ' +
      'value="' + esc(route) + '"' + (消息 ? ' aria-invalid="true"' : "") + '>' +
      // 错误容器恒渲染；运行时输入经 onProviderRouteInput 就地回显（§2.2 逐字）
      '<div class="settings-provider-route-err"' + (消息 ? "" : " hidden") + ">" +
        esc(消息) + "</div>");
    h += 字段("API 地址",
      '<input type="text" class="settings-input settings-provider-baseurl" data-field="base_url" ' +
      'value="' + esc((视图 && 视图["baseURL"]) || "") + '">');
    // ⛔ API 密钥：password + value 恒空，永不回显；发现请求仅本次使用，不落任何 state。
    h += 字段("API 密钥",
      '<input type="password" class="settings-input settings-provider-key" data-field="api_key" ' +
      'value="" autocomplete="off">');
    h += 字段("显示名称",
      '<input type="text" class="settings-input" data-field="display_name" ' +
      'value="' + esc((视图 && 视图["显示名"]) || "") + '">');
    var 选项 = 协议选项列表(视图);
    var sel = '<select class="settings-select" data-field="api"><option value="">未选择</option>';
    for (var i = 0; i < 选项.length; i++) {
      var o = 选项[i] || {};
      sel += '<option value="' + esc(o["值"]) + '"' +
        ((视图 && 视图["api"] === o["值"]) ? " selected" : "") + '>' +
        esc(o["标签"] != null ? o["标签"] : o["值"]) + "</option>";
    }
    sel += "</select>";
    h += 字段("API 协议", sel);
    var 缺地址 = (视图 && (视图["地址空"] === true || 视图["地址空"] === "真"));
    var busy = (视图 && (视图["发现中"] === true || 视图["发现中"] === "真"));
    h += '<div class="settings-provider-add-actions">' +
      '<button type="button" class="settings-sc-btn settings-provider-fetch" ' +
      (缺地址 ? 'title="请先填写 API 地址，再获取。"' : "") +
      (busy ? ' disabled aria-busy="true"' : "") + ">" +
      esc(busy ? "正在询问提供商…" : "获取可用模型") + "</button>" +
      '<button type="button" class="settings-confirm-go settings-provider-submit">添加</button>' +
      "</div></div></details>";
    return h;
  }

  // 渲染候选弹窗(视图) -> 发现结果弹窗（标题/说明/搜索/全选/取消全选/添加所选/无匹配/空结果逐字）
  function 渲染候选弹窗(视图) {
    var 候选 = Array.isArray(视图["候选"]) ? 视图["候选"] : [];
    var h = '<div class="settings-fetch-overlay"><div class="settings-fetch-dialog" role="dialog" ' +
      'aria-label="选择要添加的模型">' +
      '<div class="settings-fetch-head">' +
        '<h3 class="settings-fetch-title">选择要添加的模型</h3>' +
        '<p class="settings-fetch-desc">以下是模型提供商的可用模型，勾选要添加的模型。</p>' +
        '<input type="search" class="settings-input settings-fetch-search" data-field="search" ' +
        'placeholder="搜索模型" value="' + esc((视图["搜索"]) || "") + '">' +
        '<div class="settings-fetch-tools">' +
          '<button type="button" class="settings-line-btn settings-fetch-all">全选</button>' +
          '<button type="button" class="settings-line-btn settings-fetch-none">取消全选</button>' +
        "</div></div>";
    if (!候选.length) {
      h += '<div class="settings-note">该提供商没有列出任何模型，请手动添加。</div>';
    } else if (视图["无匹配"] === true) {
      h += '<div class="settings-note">没有匹配的模型。</div>';
    } else {
      h += '<div class="settings-fetch-list">';
      var 选中 = Array.isArray(视图["选中"]) ? 视图["选中"] : [];
      for (var i = 0; i < 候选.length; i++) {
        var c = 候选[i] || {};
        var on = 选中.indexOf(c["id"]) >= 0;
        h += '<label class="settings-fetch-item">' +
          '<input type="checkbox" data-fetch-id="' + esc(c["id"] || "") + '"' + (on ? " checked" : "") + '>' +
          '<span class="settings-fetch-item-name">' + esc(c["name"] != null ? c["name"] : c["id"]) + "</span>" +
          '<span class="settings-fetch-item-id">' + esc(c["id"] || "") + "</span>" +
          (c["contextWindow"] != null
            ? '<span class="settings-fetch-item-ctx">上下文窗口：' + esc(c["contextWindow"]) + "</span>" : "") +
          (c["maxTokens"] != null
            ? '<span class="settings-fetch-item-ctx">最大输出：' + esc(c["maxTokens"]) + "</span>" : "") +
        "</label>";
      }
      h += "</div>";
    }
    h += '<div class="settings-fetch-actions">' +
      '<button type="button" class="settings-confirm-go settings-fetch-adopt">添加所选</button>' +
      '<button type="button" class="settings-confirm-cancel settings-fetch-close">取消</button>' +
    "</div></div></div>";
    return h;
  }

  // 渲染提供商页(目录, 视图) -> provider 行列表 + 添加表单 + 可选候选弹窗
  //   目录 = GET /api/settings/providers 响应（§2.2 提供商行形状）
  //   视图 = {校验, baseURL, 显示名, api, 协议选项, 地址空, 发现中, 候选, 搜索, 选中, 无匹配}
  function 渲染提供商页(目录, 视图) {
    if (视图 == null) 视图 = {};
    var 行集 = (目录 && Array.isArray(目录["提供商行"])) ? 目录["提供商行"] : [];
    var h = 渲染添加表单(行集, 视图);
    h += '<div class="settings-provider-list">';
    if (!行集.length) {
      h += '<div class="settings-note">目录中的提供商都已添加。</div>';
    } else {
      for (var i = 0; i < 行集.length; i++) h += 渲染提供商行(行集[i]);
    }
    h += "</div>";
    if (视图["候选"]) h += 渲染候选弹窗(视图);
    return h;
  }

  function tabDescHtml(data, tabId) {
    var m = data && data["页签说明"];
    if (m && typeof m === "object" && m[tabId]) {
      return '<div class="settings-tab-desc">' + esc(m[tabId]) + "</div>";
    }
    return "";
  }

  // 三页的「加载中 / 不可用」状态：loading 由 ST.loading 决定；
  // 数据缺失且曾发生加载错误（端点 404/503/网络）→ 不可用态（不静默、不白屏）。
  function 页状态(tab) {
    if (ST.loading) return "loading";
    var key = (tab === "models") ? "模型"
            : (tab === "builtin-plugins") ? "内置插件"
            : (tab === "agent-presets") ? "Agent预设" : null;
    var dat = key ? (ST.data || {})[key] : null;
    if (dat == null && ST.loadError) return "unavailable";
    return "ok";
  }

  // R108-G：C / F 线独立端点的加载/不可用态（与四页签分开判定）
  function gStatus(v) {
    if (ST.loading) return "loading";
    if (v == null && ST.loadError) return "unavailable";
    return "ok";
  }

  // R108-G：引导浮层（数据驱动；当前步骤为空 → 隐藏且内容清空，不留占位 DOM）
  function renderOnboarding() {
    if (!el.obLayer) return;
    var html = 渲染引导(ST.onboarding, ST.onboarding ? "ok" : "unavailable", ST.obErr, ST.obBusy === true);
    if (!html) { el.obLayer.hidden = true; el.obLayer.innerHTML = ""; return; }
    el.obLayer.innerHTML = html;
    el.obLayer.hidden = false;
    // 聚焦密码框（deepseek-official 步）
    var key = el.obLayer.querySelector(".settings-onboarding-key");
    if (key) { try { key.focus(); } catch (e) { /* 无 DOM 环境忽略 */ } }
  }

  // ---------- R108-G：侧栏插件面板浮层（F 线只读；无任何写控件） ----------
  function buildPluginPanel() {
    if (el.ppLayer || !HAS_DOM) return;
    if (!document.body || !document.body.appendChild) return; // 本地 mock 沙箱无完整 DOM
    var wrap = document.createElement("div");
    if (!wrap || !wrap.querySelector) return;
    wrap.className = "settings-pp-page";
    wrap.hidden = true; // 创建即隐藏，显式 openPluginPanel 才显示
    wrap.innerHTML = '<div class="settings-pp-page-inner" role="dialog" aria-label="插件">' +
      '<div class="settings-pp-page-head">' +
        '<h3 class="settings-pp-title">插件</h3>' +
        '<button type="button" class="settings-x settings-pp-close" aria-label="关闭" title="关闭">' +
          ICONS.x + "</button>" +
      "</div>" +
      '<div class="settings-pp-page-body"></div></div>';
    document.body.appendChild(wrap);
    el.ppLayer = wrap;
    el.ppBody = wrap.querySelector(".settings-pp-page-body");
    wrap.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      if (t.closest(".settings-pp-close") || t === wrap) { closePluginPanel(); return; }
      // R110：插件安装/启停/卸载分发
      var actBtn = t.closest("[data-pp-act]");
      if (actBtn) {
        var act = actBtn.getAttribute("data-pp-act");
        if (act === "install") { doPpInstall(actBtn); return; }
        if (act === "toggle") { doPpToggle(actBtn); return; }
        if (act === "uninstall") { doPpUninstall(actBtn); return; }
      }
    });
  }

  // R110：安装/启停/卸载插件（POST 后端，完成后重拉面板）
  function ppBusy(on) {
    if (!el.ppBody) return;
    var btns = el.ppBody.querySelectorAll("[data-pp-act]");
    for (var i = 0; i < btns.length; i++) btns[i].disabled = !!on;
  }
  function ppReload() {
    ST.pluginPanel = null;
    if (typeof fetch !== "function") { renderPluginPanel(); return; }
    api("GET", "/api/settings/plugin-panel")
      .then(function (d) { if (d && typeof d === "object" && !Array.isArray(d)) ST.pluginPanel = d; })
      .then(null, function () { ST.pluginPanel = null; })
      .then(renderPluginPanel);
  }
  function doPpInstall(btn) {
    var input = el.ppBody && el.ppBody.querySelector("[data-pp-install-input]");
    var spec = input ? input.value.trim() : "";
    if (!spec) return;
    ppBusy(true);
    btn.textContent = "安装中…";
    api("POST", "/api/settings/plugin-panel/install", { spec: spec })
      .then(ppReload, function (err) { alert("安装失败：" + (err && err.message ? err.message : err)); ppReload(); })
      .then(function () { ppBusy(false); });
  }
  function doPpToggle(btn) {
    var pkg = btn.getAttribute("data-pkg") || "";
    var nowOn = btn.getAttribute("data-on") === "1";
    ppBusy(true);
    api("POST", "/api/settings/plugin-panel/set-enabled", { id: pkg, enabled: !nowOn })
      .then(ppReload, function (err) { alert("操作失败：" + (err && err.message ? err.message : err)); ppReload(); })
      .then(function () { ppBusy(false); });
  }
  function doPpUninstall(btn) {
    var pkg = btn.getAttribute("data-pkg") || "";
    if (!pkg) return;
    if (!confirm("确认卸载插件 " + pkg + "？")) return;
    ppBusy(true);
    btn.textContent = "卸载中…";
    api("POST", "/api/settings/plugin-panel/uninstall", { name: pkg })
      .then(ppReload, function (err) { alert("卸载失败：" + (err && err.message ? err.message : err)); ppReload(); })
      .then(function () { ppBusy(false); });
  }

  function renderPluginPanel() {
    if (!HAS_DOM) return;
    buildPluginPanel();
    if (!el.ppBody) return;
    // 加载态 / 不可用态由 渲染插件面板 内部分支（status 由数据决定）；
    // 页面浮层自带标题 → headless 渲染，避免标题重复。
    var status = ST.pluginPanel ? "ok" : (ST.loading ? "loading" : "unavailable");
    el.ppBody.innerHTML = 渲染插件面板(ST.pluginPanel, status, { headless: true });
  }

  function openPluginPanel() {
    buildPluginPanel();
    if (!el.ppLayer) return;
    el.ppLayer.hidden = false;
    if (!ST.pluginPanel) {
      if (typeof fetch === "function") {
        api("GET", "/api/settings/plugin-panel")
          .then(function (d) {
            if (d && typeof d === "object" && !Array.isArray(d)) ST.pluginPanel = d;
            renderPluginPanel();
          })
          .then(null, function () { renderPluginPanel(); });
      } else {
        renderPluginPanel();
      }
      return;
    }
    renderPluginPanel();
  }

  function closePluginPanel() {
    if (!el.ppLayer) return;
    el.ppLayer.hidden = true;
  }

  // ---------- R108-G：引导保存（deepseek-official 步走凭据端点；welcome 步走引导确认端点） ----------
  //   root：密钥输入框所在容器（设置内浮层 el.obLayer 或页面级浮层 el.obPage）
  function onOnboardingSave(btn, root) {
    var 步 = btn && btn.getAttribute ? btn.getAttribute("data-step") : "";
    if (!步) return;
    if (ST.obBusy) return;
    ST.obErr = "";
    if (步 === "welcome-notice") {
      // POST /api/settings/onboarding {"步骤":"welcome-notice"} → C 线落盘扁平键
      ST.obBusy = true;
      renderOnboarding();     // busy 态立即重渲染（次按钮禁用等）
      renderPageOnboarding();
      api("POST", "/api/settings/onboarding", { 步骤: 步 })
        .then(function () {
          ST.obBusy = false;
          return load(); // 重读 → 当前步骤推进到 deepseek-official 或清空
        })
        .then(null, function () {
          ST.obBusy = false;
          ST.obErr = "暂时无法保存确认状态，请重试。";
          renderOnboarding();
          renderPageOnboarding();
        });
      return;
    }
    if (步 === "deepseek-official") {
      var host = root || el.obLayer;
      var keyEl = host ? host.querySelector(".settings-onboarding-key") : null;
      var key = keyEl ? String(keyEl.value || "") : "";
      if (!key) {
        ST.obErr = "请输入 API 密钥后继续。";
        renderOnboarding();
        renderPageOnboarding();
        return;
      }
      // 密钥仅本次请求使用：POST /api/settings/credential {"密钥":key}；⛔ 不回显、不落 state
      ST.obBusy = true;
      renderOnboarding();     // busy 态立即重渲染：主按钮「保存中…」+ 密钥框/按钮 disabled（§2.1）
      renderPageOnboarding();
      api("POST", "/api/settings/credential", { 密钥: key })
        .then(function () {
          ST.obBusy = false;
          return load();
        })
        .then(null, function () {
          ST.obBusy = false;
          ST.obErr = "暂时无法保存确认状态，请重试。";
          renderOnboarding();
          renderPageOnboarding();
        });
      return;
    }
  }

  // R108-G：引导「稍后配置」（跳过 deepseek-official；welcome 步无次按钮）
  function onOnboardingSkip(btn) {
    var 步 = btn && btn.getAttribute ? btn.getAttribute("data-step") : "";
    if (步 !== "deepseek-official") return;
    api("POST", "/api/settings/onboarding", { 步骤: 步 })
      .then(function () { return load(); })
      .then(null, function () {
        ST.obErr = "暂时无法保存确认状态，请重试。";
        renderOnboarding();
      });
  }

  // R108-G：provider 表单 route 实时校验（错误文案逐字回显，前端不自造规则）
  function onProviderRouteInput(e) {
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains("settings-provider-route")) return;
    var route = String(t.value || "");
    var 行集 = (ST.providers && Array.isArray(ST.providers["提供商行"])) ? ST.providers["提供商行"] : [];
    var r = 校验路由(route, 行集);
    var err = t.parentNode ? t.parentNode.querySelector(".settings-provider-route-err") : null;
    if (r["消息"]) {
      if (err) { err.textContent = r["消息"]; err.hidden = false; }
      t.setAttribute("aria-invalid", "true");
    } else {
      if (err) { err.textContent = ""; err.hidden = true; }
      t.removeAttribute("aria-invalid");
    }
  }

  // R108-G：获取可用模型（D 线 POST /discover；仅本次使用密钥）
  function onProviderFetch(btn) {
    var det = btn && btn.closest ? btn.closest(".settings-provider-add") : null;
    if (!det || ST.providersView["发现中"]) return;
    var get = function (sel) { var n = det.querySelector(sel); return n ? n.value : ""; };
    var base = String(get('[data-field="base_url"]') || "");
    var api0 = String(get('[data-field="api"]') || "");
    if (!base) {
      ST.providersView["地址空"] = true;
      renderContent();
      return;
    }
    ST.providersView["地址空"] = false;
    ST.providersView["发现中"] = true;
    ST.providersView["baseURL"] = base;
    ST.providersView["api"] = api0;
    ST.providersView["fetchErr"] = ""; // 新一次发现前清空上次失败文案（否则旧错误残留）
    renderContent();
    // 密钥不落 providersView（⛔ 不回显）；端点自身也不返回明文
    var keyEl = det.querySelector('[data-field="api_key"]');
    var key = keyEl ? String(keyEl.value || "") : "";
    api("POST", "/api/settings/providers/discover", { baseURL: base, api: api0, apiKey: key })
      .then(function (res) {
        ST.providersView["发现中"] = false;
        ST.providersView["候选"] = (res && Array.isArray(res["候选"])) ? res["候选"] : [];
        ST.providersView["选中"] = [];
        ST.providersView["搜索"] = "";
        ST.providersView["无匹配"] = false;
        renderContent();
      })
      .then(null, function (e) {
        ST.providersView["发现中"] = false;
        ST.providersView["候选"] = [];
        ST.providersView["选中"] = [];
        // 端点 400 逐字回显（缺地址 / 其它）
        ST.providersView["fetchErr"] = (e && e.message) ? e.message : "获取失败";
        renderContent();
      });
  }

  // R108-G：候选弹窗交互（搜索过滤 / 全选 / 取消全选 / 关闭 / 添加所选）
  function onFetchSearch(e) {
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains("settings-fetch-search")) return;
    var q = String(t.value || "").trim();
    ST.providersView["搜索"] = q;
    var 候选 = ST.providersView["候选"] || [];
    if (!q) { ST.providersView["无匹配"] = false; renderContent(); return; }
    var hit = 0;
    for (var i = 0; i < 候选.length; i++) {
      var c = 候选[i] || {};
      var s = String(c["name"] != null ? c["name"] : c["id"]) + " " + String(c["id"] || "");
      if (s.indexOf(q) >= 0) hit++;
    }
    ST.providersView["无匹配"] = (hit === 0);
    renderContent();
  }

  function 过滤候选() {
    var 候选 = ST.providersView["候选"] || [];
    var q = ST.providersView["搜索"] || "";
    if (!q) return 候选;
    var out = [];
    for (var i = 0; i < 候选.length; i++) {
      var c = 候选[i] || {};
      var s = String(c["name"] != null ? c["name"] : c["id"]) + " " + String(c["id"] || "");
      if (s.indexOf(q) >= 0) out.push(c);
    }
    return out;
  }

  function onFetchAll() { // 全选
    var 候选 = 过滤候选();
    var 选中 = [];
    for (var i = 0; i < 候选.length; i++) 选中.push(候选[i]["id"]);
    ST.providersView["选中"] = 选中;
    renderContent();
  }
  function onFetchNone() { ST.providersView["选中"] = []; renderContent(); } // 取消全选
  function onFetchClose() {
    ST.providersView["候选"] = null;
    ST.providersView["选中"] = [];
    ST.providersView["搜索"] = "";
    ST.providersView["无匹配"] = false;
    renderContent();
  }
  function onFetchAdopt(btn) {
    var list = btn && btn.closest ? btn.closest(".settings-fetch-dialog") : null;
    if (!list) return;
    var boxes = list.querySelectorAll('input[data-fetch-id]');
    var picked = [];
    for (var i = 0; i < boxes.length; i++) if (boxes[i].checked) picked.push(boxes[i].getAttribute("data-fetch-id"));
    if (!picked.length) { onFetchClose(); return; }
    onFetchClose();
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
    else if (ST.tab === "models") body = renderModelHtml(d["模型"], 页状态("models"));
    else if (ST.tab === "builtin-plugins") body = renderPluginsHtml(d["内置插件"], 页状态("builtin-plugins"));
    else if (ST.tab === "agent-presets") body = renderAgentsHtml(d["Agent预设"], 页状态("agent-presets"));
    // R108-G：F 线插件面板 / C 线引导 两个独立数据面
    else if (ST.tab === "plugin-panel") body = 渲染插件面板(ST.pluginPanel, gStatus(ST.pluginPanel));
    else if (ST.tab === "onboarding") body = 渲染引导(ST.onboarding, gStatus(ST.onboarding), ST.obErr, ST.obBusy === true);
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
        // R108-G：引导覆盖层（数据驱动；当前步骤为空时不显示，不留占位 DOM）
        '<div class="settings-ob-layer" hidden></div>' +
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
    el.obLayer = wrap.querySelector(".settings-ob-layer");

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
    // R108-G：引导浮层事件（独立于 el.content）
    el.obLayer.addEventListener("click", onObClick);
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
    ST.obOpen = false; // R108-G：关闭时同步收起引导浮层
    stopKeyCapture();
    cancelConfirm();
    for (var k in ST.timers) { clearTimeout(ST.timers[k]); delete ST.timers[k]; }
    ST.prev = {};
    if (el.obLayer) { el.obLayer.hidden = true; el.obLayer.innerHTML = ""; }
    el.overlay.classList.remove("is-open");
  }

  function load() {
    var pData = api("GET", "/api/settings").then(null, function (e) { return { __err: e }; });
    var pDoc = api("GET", "/api/settings/document").then(null, function (e) { return { __err: e }; });
    // R108-G：C / D / F 三端点并行拉取；任一失败只把该键留空（不阻塞四页签渲染）
    var pOb = api("GET", "/api/settings/onboarding").then(null, function (e) { return { __err: e }; });
    var pPp = api("GET", "/api/settings/plugin-panel").then(null, function (e) { return { __err: e }; });
    var pPr = api("GET", "/api/settings/providers").then(null, function (e) { return { __err: e }; });
    return Promise.all([pData, pDoc, pOb, pPp, pPr]).then(function (rs) {
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
      ST.onboarding = (rs[2] && !rs[2].__err && typeof rs[2] === "object" && !Array.isArray(rs[2])) ? rs[2] : null;
      ST.pluginPanel = (rs[3] && !rs[3].__err && typeof rs[3] === "object" && !Array.isArray(rs[3])) ? rs[3] : null;
      ST.providers = (rs[4] && !rs[4].__err && typeof rs[4] === "object" && !Array.isArray(rs[4])) ? rs[4] : null;
      ST.loading = false;
      renderHeadDoc();
      renderNav();
      renderContent();
      // R108-G：引导覆盖层由数据驱动（当前步骤为空 → 不显示，不留占位 DOM）
      renderOnboarding();
      renderPageOnboarding();
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
    // R108-G：provider route 实时校验 / 候选弹窗搜索
    if (t.classList && t.classList.contains("settings-provider-route")) { onProviderRouteInput(e); return; }
    if (t.classList && t.classList.contains("settings-fetch-search")) { onFetchSearch(e); return; }
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

  // ---------- R107-D：模型页编辑交互（密钥永不回显；错误文案回显服务端） ----------
  function 当前模型() {
    return (ST.data && ST.data["模型"]) ? ST.data["模型"] : null;
  }

  // 保存：把可编辑字段 + 当前模型目录 POST 给 E 线端点；响应绝不含密钥明文
  function onModelSave(btn) {
    var details = btn && btn.closest ? btn.closest(".settings-model-edit") : null;
    if (!details) return;
    var get = function (sel) { var elv = details.querySelector(sel); return elv ? elv.value : ""; };
    var model = 当前模型();
    var firstId = (model && Array.isArray(model["模型行"]) && model["模型行"][0]) ? model["模型行"][0]["id"] : "";
    var payload = {
      行: "model",
      api_key: get('[data-field="api_key"]'),
      base_url: get('[data-field="base_url"]'),
      api: get('[data-field="api"]'),
      display_name: get('[data-field="display_name"]'),
      model: firstId,
      models: model ? model["模型行"] : []
    };
    var errBox = details.querySelector(".settings-model-edit-error");
    if (errBox) { errBox.hidden = true; errBox.textContent = ""; }
    api("POST", "/api/settings/model", payload)
      .then(function (res) {
        if (res && res["凭据"] && model && Array.isArray(model["提供商行"]) && model["提供商行"][0]) {
          model["提供商行"][0]["凭据"] = res["凭据"]; // 只更新 {configured,source,writable}
        }
        renderContent();
      })
      .then(null, function (e) {
        var msg = (e && e.message) ? e.message : "保存失败";
        if (errBox) { errBox.textContent = msg; errBox.hidden = false; }
        else if (typeof console !== "undefined" && console.warn) console.warn("[settings] 模型保存失败：" + msg);
      });
  }

  // 模型目录客户端增删（运行时直接改 ST.data，保存时一并 POST）
  function onModelAdd(details) {
    var model = 当前模型();
    if (!model) return;
    model["模型目录继承"] = false;
    if (!Array.isArray(model["模型行"])) model["模型行"] = [];
    model["模型行"].push({ id: "", name: "", 上下文窗口: "", 最大输出: "", 输入类型: ["text"] });
    renderContent();
  }
  function onModelDel(details, id) {
    var model = 当前模型();
    if (!model || !Array.isArray(model["模型行"])) return;
    model["模型行"] = model["模型行"].filter(function (r) { return r["id"] !== id; });
    model["模型目录继承"] = false;
    renderContent();
  }
  function onModelReset(details) {
    var model = 当前模型();
    if (!model) return;
    model["模型目录继承"] = true;
    renderContent();
  }

  // 设为新任务默认（C 线校验在服务端完成；非法 → 服务端回 400 {错误}）
  function onPresetSetDefault(btn) {
    var id = btn && btn.getAttribute ? btn.getAttribute("data-preset-id") || "" : "";
    if (!id) return;
    api("POST", "/api/settings", { 行: "agentPresetDefault", 值: id })
      .then(function (res) {
        if (res && res["错误"]) throw new Error(res["错误"]);
        return load(); // 刷新整页，默认标记随之更新
      })
      .then(null, function (e) {
        var msg = (e && e.message) ? e.message : "设置失败";
        if (typeof console !== "undefined" && console.warn) console.warn("[settings] 设为默认失败：" + msg);
      });
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

    // R107-D：模型页编辑卡内的动作（保存 / 取消 / 模型目录增删复位）
    if (t.closest(".settings-model-save")) { onModelSave(t.closest(".settings-model-save")); return; }
    if (t.closest(".settings-model-cancel")) {
      var det = t.closest(".settings-model-edit");
      if (det) det.open = false;
      return;
    }
    var mAct = t.closest("[data-model-act]");
    if (mAct) {
      var act = mAct.getAttribute("data-model-act");
      var mDet = t.closest(".settings-model-edit");
      if (act === "add") onModelAdd(mDet);
      else if (act === "reset") onModelReset(mDet);
      else if (act === "del") onModelDel(mDet, mAct.getAttribute("data-model-id"));
      return;
    }

    // R107-D：预设卡「设为新任务默认」
    var sd = t.closest(".settings-preset-setdefault");
    if (sd) { onPresetSetDefault(sd); return; }

    // R108-G：引导浮层主/次按钮
    if (t.closest(".settings-onboarding-main")) { onOnboardingSave(t.closest(".settings-onboarding-main")); return; }
    if (t.closest(".settings-onboarding-skip")) { onOnboardingSkip(t.closest(".settings-onboarding-skip")); return; }
    // R108-G：provider 表单 / 候选弹窗
    if (t.closest(".settings-provider-fetch")) { onProviderFetch(t.closest(".settings-provider-fetch")); return; }
    if (t.closest(".settings-fetch-close")) { onFetchClose(); return; }
    if (t.closest(".settings-fetch-all")) { onFetchAll(); return; }
    if (t.closest(".settings-fetch-none")) { onFetchNone(); return; }
    if (t.closest(".settings-fetch-adopt")) { onFetchAdopt(t.closest(".settings-fetch-adopt")); return; }
    if (t.closest(".settings-provider-del")) {
      // D 线删除序列：先凭据后配置；本仓恒为内置提供商（可删除=假）不触发；保留兜底
      var pRow = t.closest(".settings-provider-row");
      if (pRow) {
        var prov = pRow.getAttribute("data-provider");
        if (prov && window.confirm) window.confirm("删除 " + prov + "？");
      }
      return;
    }
  }

  // R108-G：引导浮层点击（浮层独立于 el.content，单独绑 onContentClick 以复用同一套分支）
  function onObClick(e) {
    var target = e.target;
    if (!target || !target.closest) return;
    var t = target;
    if (t.closest(".settings-onboarding-main")) { onOnboardingSave(t.closest(".settings-onboarding-main")); return; }
    if (t.closest(".settings-onboarding-skip")) { onOnboardingSkip(t.closest(".settings-onboarding-skip")); return; }
    if (t === el.obLayer && !ST.obBusy) {
      // 点击浮层空白：welcome-notice 不可跳过 → 不关闭；deepseek-official 可跳过
      var step = el.obLayer.querySelector ? el.obLayer.querySelector("[data-step]") : null;
      if (step && step.getAttribute("data-step") === "deepseek-official") onOnboardingSkip(step);
      return;
    }
  }

  // ---------- R108-G：页面级首访引导浮层（首次进入页面即显示，独立于设置对话框） ----------
  // 数据来自同一个 C 线端点；渲染与保存逻辑复用 渲染引导步 / onOnboardingSave。
  function buildPageOnboarding() {
    if (el.obPage || !HAS_DOM) return;
    if (!document.body || !document.body.appendChild) return; // 本地 mock 沙箱无完整 DOM
    var wrap = document.createElement("div");
    if (!wrap || !wrap.querySelector) return;
    wrap.className = "settings-ob-page";
    wrap.hidden = true; // 创建即隐藏，数据驱动 renderPageOnboarding 才显示
    wrap.innerHTML = '<div class="settings-ob-page-inner"></div>';
    document.body.appendChild(wrap);
    el.obPage = wrap;
    el.obPageInner = wrap.querySelector(".settings-ob-page-inner");
    el.obPage.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.closest) return;
      if (t.closest(".settings-onboarding-main")) {
        onOnboardingSave(t.closest(".settings-onboarding-main"), el.obPageInner);
        return;
      }
      if (t.closest(".settings-onboarding-skip")) {
        onOnboardingSkip(t.closest(".settings-onboarding-skip"));
        return;
      }
      // 点遮罩：仅 deepseek-official（可跳过）允许跳过
      if (t === el.obPage && !ST.obBusy) {
        var step = el.obPageInner.querySelector("[data-step]");
        if (step && step.getAttribute("data-step") === "deepseek-official") onOnboardingSkip(step);
      }
    });
  }

  function renderPageOnboarding() {
    if (!HAS_DOM) return;
    buildPageOnboarding();
    if (!el.obPage) return;
    var html = 渲染引导(ST.onboarding, ST.onboarding ? "ok" : "unavailable", ST.obErr, ST.obBusy === true);
    if (!html) { el.obPage.hidden = true; el.obPageInner.innerHTML = ""; return; }
    el.obPageInner.innerHTML = html;
    el.obPage.hidden = false;
    var key = el.obPageInner.querySelector(".settings-onboarding-key");
    if (key) { try { key.focus(); } catch (e) { /* 无 DOM 环境忽略 */ } }
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
  // R107-D：三页纯渲染函数导出点（.scratch/r106b_assert.mjs R107 段驱动用）
  G.SettingsApply = {
    组装生效查询: 组装生效查询,
    主题属性: 主题属性,
    字号变量: 字号变量,
    链接目标属性: 链接目标属性,
    降级提示: 降级提示,
    组装键串: 组装键串,
    渲染快捷键目录: 渲染快捷键目录,
    // 三页渲染（消费 A/B/C 线契约形状；status ∈ ok|loading|unavailable）
    渲染模型页: renderModelHtml,
    渲染插件页: renderPluginsHtml,
    渲染预设页: renderAgentsHtml,
    // R108-G：多 provider + 发现（消费 D 线契约）
    渲染提供商页: 渲染提供商页,
    渲染提供商行: 渲染提供商行,
    渲染添加表单: 渲染添加表单,
    渲染候选弹窗: 渲染候选弹窗,
    校验路由: 校验路由
  };

  // R108-G：C / F 线纯渲染导出点（.scratch/r108g_assert.mjs 驱动用）
  G.SettingsPanels = {
    渲染引导: 渲染引导,
    渲染引导步: 渲染引导步,
    渲染插件面板: 渲染插件面板,
    渲染插件卡: 渲染插件卡,
    渲染插件组: 渲染插件组,
    组件计数文案: 组件计数文案,
    只读原因文案: 只读原因文案,
    相位文案: 相位文案
  };

  // ---------- 入口按钮自绑定 ----------
  function autoInit() {
    if (!HAS_DOM) return;
    var entry = document.getElementById("app-settings-btn");
    if (entry) entry.addEventListener("click", open);
    // R108-G：侧栏「插件」入口 → 只读插件面板浮层
    var pluginEntry = document.getElementById("app-plugin-btn");
    if (pluginEntry) pluginEntry.addEventListener("click", openPluginPanel);
    refreshEffective(); // R106-B：页面加载即应用一次（刷新后保存值直接生效；端点不可用则跳过）
    // R108-G：首访引导浮层（首次进入页面即显示；数据来自 C 线端点，独立于设置对话框）
    if (ST.loading === false) {
      loadPageOnboarding();
    }
  }

  function loadPageOnboarding() {
    if (typeof fetch !== "function") return; // 无 fetch 环境（本地 mock 沙箱）不发起请求
    api("GET", "/api/settings/onboarding")
      .then(function (d) {
        if (d && typeof d === "object" && !Array.isArray(d)) ST.onboarding = d;
        renderPageOnboarding();
      })
      .then(null, function () {
        ST.onboarding = null;
        renderPageOnboarding();
      });
  }

  if (HAS_DOM) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoInit);
    else autoInit();
  }
})();

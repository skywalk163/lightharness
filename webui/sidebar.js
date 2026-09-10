/* =====================================================================
 * lightharness WebUI — E3 会话侧边栏组件（sidebar.js，零依赖）
 * ---------------------------------------------------------------------
 * 职责：
 *  - 左侧边栏：新建会话按钮 + 会话列表（服务端已按最后更新倒序，直接渲染）
 *  - 列表项：标题 + 消息数角标 + 相对时间 + 悬停删除按钮
 *  - 交互：单击切换会话 / 双击重命名（PUT /api/sessions/:id/标题）/
 *          删除（confirm 后 DELETE /api/sessions/:id）
 *  - 当前会话高亮（蓝左边框）；空状态 / 持久化未启用(503) 降级提示
 * 依赖 E2 API（web服务器.light）：
 *  - GET    /api/sessions            → 元数据数组 [{id,标题,创建时间,最后更新,消息数,文件}]
 *  - POST   /api/sessions            body {"标题"} → 新元数据（含 id）
 *  - PUT    /api/sessions/:id/标题   body {"标题"} → 元数据
 *  - DELETE /api/sessions/:id        → {"删除": id}
 * 全局暴露 window.Sidebar；由 app.js 传入回调：onSelect/onCreated/onDeleted/onRenamed。
 * ===================================================================== */
(function () {
  "use strict";

  var listEl = null;
  var newBtnEl = null;
  var opts = {}; // {onSelect(id), onCreated(meta), onDeleted(id), onRenamed(id, title)}
  var items = []; // 最近一次拉取的元数据数组
  var activeId = "";

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // ---------- 相对时间：刚刚 / N分钟前 / N小时前 / N天前 / 日期 ----------
  function relativeTime(时间戳) {
    var s = String(时间戳 == null ? "" : 时间戳).trim();
    if (!s) return "";
    var t = Date.parse(s.replace(" ", "T"));
    if (isNaN(t)) return s;
    var diff = (Date.now() - t) / 1000;
    if (diff < 0) diff = 0;
    if (diff < 60) return "刚刚";
    if (diff < 3600) return Math.floor(diff / 60) + " 分钟前";
    if (diff < 86400) return Math.floor(diff / 3600) + " 小时前";
    if (diff < 7 * 86400) return Math.floor(diff / 86400) + " 天前";
    return s.slice(0, 10).replace("T", " ");
  }

  // ---------- API ----------
  function api(method, url, body) {
    var initObj = { method: method, headers: {} };
    if (body != null) {
      initObj.headers["Content-Type"] = "application/json";
      initObj.body = JSON.stringify(body);
    }
    return fetch(url, initObj).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!res.ok) {
          var msg = (data && (data.error || data.message)) || "HTTP " + res.status;
          var err = new Error(msg);
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  // ---------- 渲染 ----------
  function render() {
    if (!listEl) return;
    listEl.innerHTML = "";
    if (!items.length) {
      listEl.innerHTML = '<div class="sb-empty">暂无会话，点击上方按钮新建</div>';
      return;
    }
    for (var i = 0; i < items.length; i++) {
      listEl.appendChild(mkItem(items[i]));
    }
  }

  function mkItem(meta) {
    var id = meta.id || "";
    var title = meta.标题 || "新会话";
    var count = Number(meta.消息数 || 0);

    var div = document.createElement("div");
    div.className = "sitem" + (id === activeId ? " active" : "");
    div.dataset.id = id;
    div.title = title;

    var main = document.createElement("div");
    main.className = "sitem-main";
    main.innerHTML =
      '<span class="sitem-title">' + escapeHtml(title) + "</span>" +
      (count > 0 ? '<span class="sitem-badge">' + count + "</span>" : "");
    div.appendChild(main);

    var metaRow = document.createElement("div");
    metaRow.className = "sitem-meta";
    metaRow.innerHTML =
      '<span class="sitem-time">' + escapeHtml(relativeTime(meta.最后更新)) + "</span>" +
      '<button type="button" class="sitem-del" title="删除会话">×</button>';
    div.appendChild(metaRow);

    // 单击：切换会话
    div.addEventListener("click", function () {
      if (typeof opts.onSelect === "function") opts.onSelect(id, meta);
    });

    // 双击：重命名（内联输入框）
    var titleSpan = main.querySelector(".sitem-title");
    titleSpan.addEventListener("dblclick", function (ev) {
      ev.stopPropagation();
      startRename(div, titleSpan, id, title);
    });

    // 删除：阻止冒泡，confirm 后删除
    var delBtn = metaRow.querySelector(".sitem-del");
    delBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (!window.confirm("删除会话「" + title + "」？该操作不可恢复。")) return;
      api("DELETE", "/api/sessions/" + encodeURIComponent(id))
        .then(function () {
          refresh();
          if (id === activeId && typeof opts.onDeleted === "function") opts.onDeleted(id);
        })
        .catch(function (e) {
          if (window.Messages) window.Messages.addSystem("删除失败：" + e.message, true);
        });
    });

    return div;
  }

  // ---------- 重命名（内联） ----------
  function startRename(itemEl, titleSpan, id, oldTitle) {
    var input = document.createElement("input");
    input.type = "text";
    input.className = "sitem-rename";
    input.value = oldTitle;
    input.maxLength = 100;
    titleSpan.replaceWith(input);
    input.focus();
    input.select();

    var done = false;
    var commit = function () {
      if (done) return;
      done = true;
      var next = input.value.trim();
      input.replaceWith(titleSpan);
      if (!next || next === oldTitle) return;
      api("PUT", "/api/sessions/" + encodeURIComponent(id) + "/标题", { 标题: next })
        .then(function (meta) {
          var span = itemEl.querySelector(".sitem-title");
          if (span) span.textContent = next;
          itemEl.title = next;
          for (var i = 0; i < items.length; i++) {
            if (items[i].id === id) { items[i].标题 = next; break; }
          }
          if (typeof opts.onRenamed === "function") opts.onRenamed(id, next);
        })
        .catch(function (e) {
          if (window.Messages) window.Messages.addSystem("重命名失败：" + e.message, true);
        });
    };
    var cancel = function () {
      if (done) return;
      done = true;
      input.replaceWith(titleSpan);
    };
    input.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") commit();
      else if (ev.key === "Escape") cancel();
    });
    input.addEventListener("blur", commit);
  }

  // ---------- 拉取 + 刷新 ----------
  function refresh() {
    return api("GET", "/api/sessions")
      .then(function (list) {
        items = Array.isArray(list) ? list : [];
        render();
        syncActive();
      })
      .catch(function (e) {
        items = [];
        if (listEl) {
          var msg = e.status === 503 ? "会话持久化未启用，仅本次对话可用" : "会话列表加载失败：" + e.message;
          listEl.innerHTML = '<div class="sb-empty warn">' + escapeHtml(msg) + "</div>";
        }
      });
  }

  // 新建会话：POST 后回调 onCreated（app.js 切换到新会话）
  function createSession() {
    if (!newBtnEl) return;
    newBtnEl.disabled = true;
    api("POST", "/api/sessions", { 标题: "新会话" })
      .then(function (meta) {
        newBtnEl.disabled = false;
        return refresh().then(function () {
          if (typeof opts.onCreated === "function") opts.onCreated(meta);
        });
      })
      .catch(function (e) {
        newBtnEl.disabled = false;
        if (window.Messages) window.Messages.addSystem("新建会话失败：" + e.message, true);
      });
  }

  // ---------- 状态同步 ----------
  function setActive(id) {
    activeId = id || "";
    syncActive();
  }

  function syncActive() {
    if (!listEl) return;
    var nodes = listEl.querySelectorAll(".sitem");
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].classList.toggle("active", nodes[i].dataset.id === activeId);
    }
  }

  // 重命名后本地同步标题（不触发整表刷新，避免闪烁）
  function updateTitleLocal(id, title) {
    for (var i = 0; i < items.length; i++) {
      if (items[i].id === id) {
        items[i].标题 = title;
        break;
      }
    }
    render();
    syncActive();
  }

  // ---------- 初始化 ----------
  function init(userOpts) {
    opts = userOpts || {};
    listEl = document.getElementById("session-list");
    newBtnEl = document.getElementById("new-session-btn");
    if (newBtnEl) newBtnEl.addEventListener("click", createSession);
    refresh();
  }

  window.Sidebar = {
    init: init,
    refresh: refresh,
    setActive: setActive,
    updateTitleLocal: updateTitleLocal,
    relativeTime: relativeTime
  };
})();

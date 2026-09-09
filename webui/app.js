/* lightharness WebUI — 前端应用逻辑（零依赖，ES6+）
 *
 * 契约（只读遵守）：
 *  - 接口：POST /v1/chat/completions（OpenAI 兼容），body 含 stream:true
 *  - 鉴权：X-Auth-Token 请求头；token 从 URL (?token=...) 读取，仅存内存
 *  - 流式：fetch + response.body.getReader() 手工按 \n\n 切帧解析 SSE，
 *         不用 EventSource（它只支持 GET）
 *  - 错误永不白屏：401 / 4xx / 5xx / 网络失败均有明确提示
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

  // ---------- 状态 ----------
  var params = new URLSearchParams(location.search);
  var token = params.get("token") || "";
  var history = [];               // [{role, content}]，发给 API 的会话历史
  var sessionId = null;           // 会话延续（来自服务端 session_id）
  var controller = null;          // 当前请求的 AbortController
  var streaming = false;          // 是否正在流式输出
  var turnStartIndex = -1;        // 本轮开始前 history.length
  var currentAssistantIndex = -1; // history 中当前助手条目下标
  var currentBubble = null;       // 当前渲染中的助手气泡 DOM
  var userBubble = null;          // 本轮用户气泡 DOM

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

  // ---------- 渲染 ----------
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // 轻量渲染：普通文本 + ``` 代码块（<pre> 等宽），不做完整 markdown
  function renderContent(text) {
    var parts = text.split("```");
    var html = "";
    for (var i = 0; i < parts.length; i++) {
      if (i % 2 === 1) {
        html += "<pre>" + escapeHtml(parts[i]) + "</pre>";
      } else {
        html += escapeHtml(parts[i]).replace(/\n/g, "<br>");
      }
    }
    return html;
  }

  function stickToBottom() {
    var max = messagesEl.scrollHeight - messagesEl.clientHeight;
    if (max <= 0 || messagesEl.scrollTop > max - 80) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  function addBubble(role, text) {
    var div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = renderContent(text);
    messagesEl.appendChild(div);
    stickToBottom();
    return div;
  }

  function addSystem(text, isError) {
    var div = document.createElement("div");
    div.className = "sys" + (isError ? " error" : "");
    div.textContent = text;
    messagesEl.appendChild(div);
    stickToBottom();
    return div;
  }

  function appendToAssistant(delta) {
    if (!currentBubble) return;
    history[currentAssistantIndex].content += delta;
    currentBubble.innerHTML = renderContent(history[currentAssistantIndex].content);
    stickToBottom();
  }

  // ---------- 流程控制 ----------
  function setStreaming(on) {
    streaming = on;
    sendBtn.disabled = on;
    stopBtn.disabled = !on;
    if (currentBubble) currentBubble.classList.toggle("streaming", on);
  }

  // 正常结束（含用户点“停止”）：保留已渲染内容，清理空助手消息
  function finalizeTurn() {
    if (currentBubble) {
      currentBubble.classList.remove("streaming");
      currentBubble = null;
    }
    var last = history[currentAssistantIndex];
    if (last && last.content === "") {
      history.splice(currentAssistantIndex, 1); // 空消息不留在历史里
    }
  }

  // 请求失败：撤掉本轮的 user/assistant 气泡与历史，恢复输入框
  function rollbackTurn(text) {
    history.length = turnStartIndex;
    if (currentBubble) { currentBubble.remove(); currentBubble = null; }
    if (userBubble) { userBubble.remove(); userBubble = null; }
    if (text) { inputEl.value = text; inputEl.focus(); autoResize(); }
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
          if (json && json.session_id) sessionId = json.session_id; // 会话延续
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

    // 组装消息体：去掉尾部尚未写入内容的空助手条目
    var msgs = history.slice();
    for (var i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "assistant" && msgs[i].content === "") msgs.pop();
      else break;
    }
    var body = { model: "deepseek-chat", messages: msgs, stream: true };
    if (sessionId) body.session_id = sessionId;       // 会话延续

    // 追加本轮 UI 与历史
    turnStartIndex = history.length;
    history.push({ role: "user", content: text });
    currentAssistantIndex = history.push({ role: "assistant", content: "" }) - 1;
    userBubble = addBubble("user", text);
    currentBubble = addBubble("assistant", "");
    inputEl.value = "";
    autoResize();
    setStreaming(true);

    var headers = { "Content-Type": "application/json" };
    if (token) headers["X-Auth-Token"] = token;

    var started = false; // 是否已进入流式阶段（区分“连不上”和“中途断开”）
    controller = new AbortController();

    return fetch(API_PATH, {
      method: "POST",
      headers: headers,
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

  // ---------- 事件绑定 ----------
  inputEl.addEventListener("input", autoResize);
  inputEl.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  });
  sendBtn.addEventListener("click", sendMessage);
  stopBtn.addEventListener("click", stopStreaming);

  // 初始提示 + 状态探测
  addSystem("输入内容后发送，agent 会逐字流式回复。");
  checkStatus();
})();
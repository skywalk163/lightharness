# -*- coding: utf-8 -*-
"""T-0454：前端可观测判据（错误帧可见 / 结束原因可见 / streaming 看门狗 / 压缩不阻塞）。

对齐 hive/tasks/T-0454.md 判据：
  1. node --check webui/app.js、webui/messages.js 全绿；
  2. 静态契约：handleFrame 内存在 json.error 分支、消费 结束原因、setStreaming 挂看门狗
     （子串断言，反跑能变红）；
  3. 行为测试（node + 手写最小 DOM 桩跑真实文件，pytest 起 node）：
     a. 喂 {"error":{"message":"boom","type":"driver_error"}} → .sys.error 气泡含 boom；
        [{"error":{...}}] 数组形状同样覆盖；
     b. 喂 {"种类":"统计","结束原因":"max-steps","步数上限":96} → 提示含「步数上限」
        且出现「继续」按钮，点击即发「继续」；
     c. streaming=true 后假时钟推进 31s 无帧 → 自动 setStreaming(false) 且本地队列被 flush；
     d. 喂 {"种类":"压缩"} → 出现压缩提示（含「继续」指引），streaming 状态不变；
  4. 反跑：把 json.error 分支禁掉，用例 3a 立红（src 原文件不动，shadow 注入无竞态）。

实现说明（零依赖红线）：
  - DOM/时钟/存储桩全部由本文件在运行时写入 tmp（`t0454_harness.js`），不引 jsdom；
  - 行为用例走**真链路**：stub fetch + ReadableStream 喂 SSE chunk → 真实
    sendMessage/readStream/handleFrame 消费 → 断言真实 messages.js 渲染出的气泡；
  - app.js 的测试钩子 window.__lhTest 仅在 window.__LH_TEST__ 为真时挂载（生产不挂）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBUI = os.path.join(ROOT, 'webui')
APP_JS = os.path.join(WEBUI, 'app.js')
MESSAGES_JS = os.path.join(WEBUI, 'messages.js')
STYLE_CSS = os.path.join(WEBUI, 'style.css')
NODE_TIMEOUT = 60

# app.js 错误帧分支的反跑锚点（T-0454 判据 4）
ERROR_BRANCH_ANCHOR = 'if (errObj) {'


def _run_node(args, timeout=NODE_TIMEOUT):
    env = dict(os.environ)
    env['NODE_OPTIONS'] = ''
    proc = subprocess.run(['node'] + args, capture_output=True, timeout=timeout, env=env)
    out = proc.stdout.decode('utf-8', errors='replace')
    err = proc.stderr.decode('utf-8', errors='replace')
    return proc.returncode, out, err


# ---------------------------------------------------------------------
# 判据 1：node --check 语法
# ---------------------------------------------------------------------

def test_node语法检查():
    for path in (APP_JS, MESSAGES_JS):
        rc, out, err = _run_node(['--check', path])
        assert rc == 0, ('语法检查失败', path, out, err)


# ---------------------------------------------------------------------
# 判据 2：静态契约（子串断言；删任一要素立红）
# ---------------------------------------------------------------------

def test_静态契约():
    src = open(APP_JS, 'r', encoding='utf-8').read()
    # 错误帧分支：json.error 判定 + 「驱动失败」文案 + down 状态
    assert 'json.error' in src, '缺少 json.error 分支判定'
    assert ERROR_BRANCH_ANCHOR in src, '缺少错误帧分支锚点'
    assert '驱动失败：' in src, '缺少「驱动失败」可读文案'
    # 结束原因消费（T-0453 四值闭集）
    for token in ('结束原因', 'max-steps', 'max-tokens', 'aborted', '步数上限', '继续'):
        assert token in src, ('缺少结束原因消费', token)
    # streaming 看门狗：30s 静默自愈
    for token in ('STREAM_WATCHDOG_MS', 'checkStreamWatchdog', 'touchStream', '连接可能已断开'):
        assert token in src, ('缺少看门狗要素', token)
    # 压缩提示补「继续」指引 + 测试钩子存在
    assert '本轮结束后发「继续」即可接着做' in src, '压缩提示缺「继续」指引'
    assert '__lhTest' in src and '__LH_TEST__' in src, '缺少测试专用调试钩子'
    css = open(STYLE_CSS, 'r', encoding='utf-8').read()
    assert '.continue-btn' in css, 'style.css 缺「继续」按钮样式'


# ---------------------------------------------------------------------
# 行为测试 harness（判据 3）：node + DOM 桩 + 真 fetch/readStream 链路
# ---------------------------------------------------------------------

_HARNESS_JS = r'''/* T-0454 行为测试 harness：手写最小 DOM 桩，跑真实 messages.js + app.js。 */
'use strict';
const fs = require('fs');
const path = require('path');

const appJsPath = process.argv[2];
const caseName = process.argv[3];

// ---------- 假时钟 ----------
let __lhNow = 1000000;
global.Date.now = function () { return __lhNow; };
global.__lhAdvance = function (ms) { __lhNow += ms; };

// ---------- DOM 桩 ----------
function makeClassList(el) {
  const set = new Set();
  return {
    add(c) { set.add(c); },
    remove(c) { set.delete(c); },
    toggle(c, force) {
      if (force === undefined) { set.has(c) ? set.delete(c) : set.add(c); }
      else if (force) set.add(c); else set.delete(c);
    },
    contains(c) { return set.has(c); },
    _set: set
  };
}

function makeEl(tag) {
  const handlers = {};
  const children = [];
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    children: children,
    style: {},
    dataset: {},
    attrs: {},
    textContent: '',
    innerHTML: '',
    value: '',
    hidden: false,
    disabled: false,
    title: '',
    type: '',
    className: '',
    classList: null,
    handlers: handlers,
    appendChild(c) { children.push(c); return c; },
    removeChild(c) { const i = children.indexOf(c); if (i >= 0) children.splice(i, 1); return c; },
    insertBefore(c) { children.push(c); return c; },
    remove() {},
    addEventListener(type, fn) { (handlers[type] = handlers[type] || []).push(fn); },
    removeEventListener() {},
    click() { (handlers.click || []).forEach(fn => fn({ target: el, stopPropagation() {}, preventDefault() {} })); },
    focus() {},
    select() {},
    setAttribute(k, v) { el.attrs[k] = v; },
    getAttribute(k) { return el.attrs[k] !== undefined ? el.attrs[k] : null; },
    closest() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    contains() { return false; },
    scrollIntoView() {},
    removeAttribute() {}
  };
  el.classList = makeClassList(el);
  return el;
}

const elCache = new Map();
global.document = {
  getElementById(id) {
    if (!elCache.has(id)) elCache.set(id, makeEl('div'));
    return elCache.get(id);
  },
  createElement(tag) { return makeEl(tag); },
  createTextNode(t) { return { textContent: String(t) }; },
  addEventListener() {},
  removeEventListener() {},
  body: makeEl('body'),
  documentElement: makeEl('html'),
  querySelector() { return null; },
  querySelectorAll() { return []; }
};

// node 21+ 的 global.navigator 是只读 getter，须用 defineProperty 注入
Object.defineProperty(global, 'navigator', {
  value: { userAgent: 't0454-stub' }, configurable: true, writable: true
});
Object.defineProperty(global, 'location', {
  value: { search: '', protocol: 'http:', host: 'localhost:0', pathname: '/' },
  configurable: true, writable: true
});
global.localStorage = {
  _m: {},
  getItem(k) { return this._m[k] !== undefined ? this._m[k] : null; },
  setItem(k, v) { this._m[k] = String(v); },
  removeItem(k) { delete this._m[k]; }
};
global.window = global;
global.confirm = function () { return true; };
global.alert = function () {};
global.requestAnimationFrame = function (fn) { return setTimeout(fn, 0); };
global.matchMedia = function () { return { matches: false, addEventListener() {}, removeEventListener() {} }; };

// fetch 桩：默认永不 resolve（挂住加载期副作用）；测试用 __lhSetFetcher 注入场景。
let fetchImpl = function () { return new Promise(function () {}); };
global.__lhSetFetcher = function (fn) { fetchImpl = fn; };
global.fetch = function (url, opts) { return fetchImpl(url, opts); };

// ---------- SSE 假流 ----------
// 语义对齐真实 ReadableStream：read() 在空队列时挂起，push/end 唤醒挂起的 read。
function makeSseStream(chunks) {
  const queue = chunks.slice();
  const enc = new TextEncoder();
  let pending = null;   // 挂起的 read 的 resolve
  function tryDeliver() {
    if (!pending || !queue.length) return;
    const r = pending;
    pending = null;
    r(queue.shift());
  }
  return {
    chunks: queue,
    push(sse) { queue.push({ done: false, value: enc.encode(sse) }); tryDeliver(); },
    end() { queue.push({ done: true }); tryDeliver(); },
    body: {
      getReader() {
        return {
          read() {
            if (queue.length) return Promise.resolve(queue.shift());
            return new Promise(function (resolve) { pending = resolve; });
          }
        };
      }
    }
  };
}

function sseFrame(obj) {
  return 'data: ' + JSON.stringify(obj) + '\n\n';
}

const DONE_CHUNK = 'data: [DONE]\n\n';
global.__lhMakeSseStream = makeSseStream;
global.__lhSseFrame = sseFrame;
global.__lhDONE = DONE_CHUNK;

global.__lhRequests = [];   // 记录 sendMessage 发出的每笔请求 body

// ---------- 加载真实文件 ----------
global.__LH_TEST__ = true;   // app.js 测试钩子开关（生产恒为 undefined）
eval(fs.readFileSync(path.join(path.dirname(appJsPath), 'messages.js'), 'utf-8'));
eval(fs.readFileSync(appJsPath, 'utf-8'));

const T = global.__lhTest;
if (!T) { console.error('app.js 未挂载 __lhTest 测试钩子'); process.exit(1); }

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function sysRows() {
  const root = document.getElementById('messages');
  return root.children.filter(c => String(c.className).indexOf('sys') >= 0);
}

function errorRows() {
  return sysRows().filter(c => String(c.className).indexOf('error') >= 0);
}

function findButton(row, cls) {
  const stack = [row];
  while (stack.length) {
    const cur = stack.pop();
    for (const c of cur.children) {
      if (String(c.className).indexOf(cls) >= 0) return c;
      stack.push(c);
    }
  }
  return null;
}

function allText() {
  return sysRows().map(r => String(r.textContent)).join('\n');
}

// 标准发送：fetcher 收到请求即返回（挂住的）SSE 流，测试用句柄控制后续帧
function armSend() {
  let stream = null;
  global.__lhSetFetcher(function (url, opts) {
    const body = opts && opts.body ? JSON.parse(opts.body) : {};
    global.__lhRequests.push(body);
    stream = makeSseStream([]);
    return Promise.resolve({ ok: true, status: 200, body: stream.body });
  });
  return () => stream;
}

// ---------- 场景 ----------
const CASES = {
  // 判据 3a：错误帧两种形状都要出可读错误气泡
  async errorFrame() {
    const getStream = armSend();
    const p = T.sendMessage('hi');
    await sleep(20);
    const st = getStream();
    st.push(sseFrame({ error: { message: 'boom', type: 'driver_error' } }));
    await sleep(20);
    const errs = errorRows();
    if (!errs.length || errs.map(r => String(r.textContent)).join('\n').indexOf('boom') < 0 ||
        errs.map(r => String(r.textContent)).join('\n').indexOf('驱动失败') < 0) {
      throw new Error('对象形错误帧未渲染 .sys.error 气泡（含 boom/驱动失败）: ' + allText());
    }
    st.push(sseFrame([{ error: { message: 'boom2' } }]));
    await sleep(20);
    const txt = allText();
    if (txt.indexOf('boom2') < 0) throw new Error('数组形错误帧未渲染: ' + txt);
    if (T.state().streaming !== true) throw new Error('错误帧不应改变 streaming 生命周期（由 [DONE]/收尾统一收口）');
    st.push(global.__lhDONE);
    st.end();   // 真实服务端 [DONE] 后关流：read 返回 done，pump 链才能 resolve
    await p;
  },

  // 判据 3b：max-steps → 提示含「步数上限」+「继续」按钮；点击即发「继续」
  async endReasonMaxSteps() {
    const getStream = armSend();
    const p = T.sendMessage('hi');
    await sleep(20);
    const st = getStream();
    st.push(sseFrame({ '种类': '统计', '结束原因': 'max-steps', '步数上限': 96 }));
    await sleep(20);
    const txt = allText();
    if (txt.indexOf('步数上限') < 0) throw new Error('统计帧未渲染结束原因提示: ' + txt);
    const rows = sysRows();
    let btn = null;
    for (const r of rows) {
      const b = findButton(r, 'continue-btn');
      if (b) { btn = b; break; }
    }
    if (!btn) throw new Error('max-steps 未出现「继续」按钮');
    // 真实时序：统计帧（含结束原因）先到、流随后 [DONE] 收口，用户在收口后点「继续」
    st.push(global.__lhDONE);
    st.end();
    await p;
    btn.click();
    await sleep(20);
    const last = global.__lhRequests[global.__lhRequests.length - 1];
    const lastMsg = last && last.messages && last.messages.length
      ? last.messages[last.messages.length - 1].content : '';
    if (lastMsg !== '继续') throw new Error('点击「继续」未发出「继续」消息: ' + JSON.stringify(last || {}));
    if (btn.disabled !== true) throw new Error('按钮点击后未防重复（disabled）');
  },

  // 判据 3c：假时钟推进 31s 无帧 → 自愈：streaming=false + 队列 flush + 提示
  async watchdog() {
    const getStream = armSend();
    const p = T.sendMessage('第一轮');
    await sleep(20);
    if (T.state().streaming !== true) throw new Error('流未进入 streaming 状态');
    // 流式中再提交一条 → 本地排队
    T.enqueueLocal('排队的继续');
    await sleep(5);
    if (T.state().queue !== 1) throw new Error('本地排队失败: queue=' + T.state().queue);
    // 假时钟推进 31s（无任何帧）
    global.__lhAdvance(31000);
    T.checkStreamWatchdog();
    // 自愈瞬间（flush 的 setTimeout(0) 尚未跑）：streaming 必须已是 false
    if (T.state().streaming !== false) throw new Error('看门狗未自愈（streaming 仍为 true）');
    const txt = allText();
    if (txt.indexOf('连接可能已断开') < 0) throw new Error('看门狗未给可读提示: ' + txt);
    // flush 重发排队消息（setStreaming(false) 内 setTimeout(flushLocalQueue, 0)），
    //   重发会开新流 → streaming 回到 true 属正常；这里只钉住「队列清空 + 重发发生」。
    await sleep(30);
    if (T.state().queue !== 0) throw new Error('看门狗自愈未 flush 本地队列: queue=' + T.state().queue);
    if (global.__lhRequests.length < 2) throw new Error('flush 未重发排队消息（请求数 ' + global.__lhRequests.length + '）');
    const last = global.__lhRequests[global.__lhRequests.length - 1];
    const lastMsg = last && last.messages && last.messages.length
      ? last.messages[last.messages.length - 1].content : '';
    if (lastMsg !== '排队的继续') throw new Error('重发内容不对: ' + lastMsg);
  },

  // 判据 3d：压缩帧 → 提示出现、streaming 状态不变
  async compactionNoBlock() {
    const getStream = armSend();
    const p = T.sendMessage('hi');
    await sleep(20);
    const st = getStream();
    st.push(sseFrame({ '种类': '压缩', '上下文使用率': 55 }));
    await sleep(20);
    const txt = allText();
    if (txt.indexOf('压缩') < 0) throw new Error('压缩提示未渲染: ' + txt);
    if (txt.indexOf('继续') < 0) throw new Error('压缩提示缺「继续」指引: ' + txt);
    if (T.state().streaming !== true) throw new Error('压缩帧改变了 streaming 状态（不许阻塞本轮）');
    st.push(global.__lhDONE);
    st.end();
    await p;
    if (T.state().streaming !== false) throw new Error('正常收尾后 streaming 应为 false');
  }
};

(async function () {
  const fn = CASES[caseName];
  if (!fn) { console.error('未知场景: ' + caseName); process.exit(2); }
  try {
    await fn();
    console.log('CASE_OK ' + caseName);
    process.exit(0);
  } catch (e) {
    console.error('CASE_FAIL ' + caseName + ': ' + (e && e.message ? e.message : e));
    process.exit(1);
  }
})();
'''


def _run_case(tmp_path, case, app_src=None, tag='t0454'):
    """写 harness + app.js（可变异）到 tmp，node 跑指定场景。"""
    src = app_src if app_src is not None else open(APP_JS, 'r', encoding='utf-8').read()
    app_copy = tmp_path / ('%s_%s_app.js' % (tag, case))
    app_copy.write_text(src, encoding='utf-8')
    # messages.js 原样复制到同目录并固定命名（harness 从 app.js 同目录按名加载）
    (tmp_path / 'messages.js').write_text(
        open(MESSAGES_JS, 'r', encoding='utf-8').read(), encoding='utf-8')
    harness = tmp_path / ('%s_%s_harness.js' % (tag, case))
    harness.write_text(_HARNESS_JS, encoding='utf-8')
    return _run_node([str(harness), str(app_copy), case])


def _assert_case_ok(rc, out, err, case):
    assert rc == 0, ('行为用例失败', case, out[-800:], err[-800:])


# ---------------------------------------------------------------------
# 判据 3：行为测试（node + DOM 桩）
# ---------------------------------------------------------------------

def test_错误帧渲染为可读气泡(tmp_path):
    rc, out, err = _run_case(tmp_path, 'errorFrame')
    _assert_case_ok(rc, out, err, 'errorFrame')
    assert 'CASE_OK' in out, out


def test_结束原因提示与继续按钮(tmp_path):
    rc, out, err = _run_case(tmp_path, 'endReasonMaxSteps')
    _assert_case_ok(rc, out, err, 'endReasonMaxSteps')
    assert 'CASE_OK' in out, out


def test_看门狗假时钟自愈并flush队列(tmp_path):
    rc, out, err = _run_case(tmp_path, 'watchdog')
    _assert_case_ok(rc, out, err, 'watchdog')
    assert 'CASE_OK' in out, out


def test_压缩帧不改变streaming状态(tmp_path):
    rc, out, err = _run_case(tmp_path, 'compactionNoBlock')
    _assert_case_ok(rc, out, err, 'compactionNoBlock')
    assert 'CASE_OK' in out, out


# ---------------------------------------------------------------------
# 判据 4：反跑 —— 把 json.error 分支禁掉，用例 3a 立红（src 原文件不动）
# ---------------------------------------------------------------------

def test_反跑_删掉错误帧分支_用例3a立红(tmp_path):
    original = open(APP_JS, 'r', encoding='utf-8').read()
    assert original.count(ERROR_BRANCH_ANCHOR) == 1, \
        ('反跑锚点丢失或多处（错误帧分支）', ERROR_BRANCH_ANCHOR)
    mutated = original.replace(
        ERROR_BRANCH_ANCHOR,
        'if (false) { /* T-0454 反跑：错误帧分支已禁用 */', 1)
    rc, out, err = _run_case(tmp_path, 'errorFrame', app_src=mutated, tag='t0454mut')
    assert rc != 0, (
        '反跑失败：禁用错误帧分支后用例 3a 仍通过（判据假绿！）', out[-800:], err[-800:])
    assert 'CASE_FAIL errorFrame' in out or 'CASE_FAIL errorFrame' in err, (out, err)
    # src 原文件全程未被修改
    assert open(APP_JS, 'r', encoding='utf-8').read() == original, 'webui/app.js 被反跑污染'

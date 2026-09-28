# lightharness 独立 EXE 发布现状

## 实测结论

| 方案 | 状态 | 原因 |
|---|---|---|
| LLVM 原生编译 Web 服务器 | ❌ 不可行 | LLVM 后端只支持纯计算，不支持 asyncio/http.server/文件系统等 Python stdlib |
| PyInstaller 打包中文模块 | ⚠️ 受阻 | 180+ 个中文 .light 模块，Windows GBK 编码下模块名乱码 |
| PyInstaller 打包启动器 | ⚠️ 部分通 | 中文问题通过 UTF-8 launcher 解决，但 asyncio 等 stdlib 依赖未打全 |

## 已经验证通过的

- **LLVM 原生后端编译纯计算程序**：✅ 已验证，比 Python 解释快 8.3 倍（127ms vs 1049ms）
- **独立 exe 产物**：`benchmark.light` → `benchmark.exe`（原生机器码，无需 Python）
- **Web 服务器运行**：`python 运行.py examples/运行Web服务器.light` 正常启动

## 为什么 Web 服务器暂时不能编译成独立 exe

1. **LLVM 后端限制**：原生编译腿只支持整数/浮点/字符串运算，不支持 `asyncio`、`http.server`、`json`、文件系统等 Python 运行时
2. **中文模块名**：lightharness 有 180+ 个 `.light` 模块（web服务器.light、认证.light、会话存储.light...），PyInstaller 在 Windows 上用 GBK 编码读取时中文模块名乱码
3. **stdlib 依赖链**：Web 服务器依赖 Python 的 asyncio/event loop/socket，这些在原生编译下没有等价物

## 可行的发布路线

### 当前可用（推荐）
```
# 客户机器只需装 Python 3.10+
python 运行.py examples/运行Web服务器.light
```

### 短期（1-2 周）
- 把核心纯计算模块（JSON 序列化、压缩、令牌估算）用 LLVM 编译成独立 .pyd/.exe 加速
- Web 服务器壳仍用 Python，但计算密集部分走原生

### 中期
- light-merge 的 LLVM 后端扩展 IO 支持（绑定 Python C API）
- 或用 Nuitka 全量编译（支持 asyncio 和中文模块）
- 目标：单文件 `lightharness.exe`，客户无需装 Python

## 性能数据回顾

| 后端 | 运行时间 | 适用场景 |
|---|---|---|
| SRC（Python 解释） | 1049ms | 开发调试，零依赖 |
| ANTLR | 1003ms | 兼容测试 |
| LLVM（原生 O2） | **127ms** | 纯计算模块，快 8.3 倍 |

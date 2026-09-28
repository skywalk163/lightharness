# lightharness Nuitka 打包踩坑记录

## 问题清单与解决方案

### 1. 中文模块名 GBK 乱码
**现象**：Nuitka 在 Windows 上用 GBK 读取 .py 文件，中文模块名编译后乱码。
**方案**：build_py.py 维护 `module_map.json`（中文→英文映射表），编译时转英文名，src/ 下 .light 保持中文名不动。

### 2. import 缺少别名
**现象**：`name '外部命令' is not defined`。
**根因**：`import 外部命令` 被替换成 `import mod_23e997e540`，但后续代码仍用 `外部命令.xxx()` 调用。
**方案**：替换时加别名：`import mod_xxx as 中文名`。

### 3. Windows 非阻塞 socket errno 不匹配
**现象**：浏览器连不上端口，`Connection reset`。
**根因**：Windows 上非阻塞 socket 没数据时 errno=10035 (WSAEWOULDBLOCK)，代码只检查 EAGAIN=11/EWOULDBLOCK=11。
**方案**：`是否EAGAIN()` 里加 `errno == 10035` 判断。

### 4. fallback 缺内置函数
**现象**：`module '_light_builtin' has no attribute 'xxx'`，反复出现（`环境变量`、`深拷贝`、`随机整数` 等）。
**根因**：onefile 解压后 `stdlib/builtins.py` 加载路径不确定，走了 except fallback 分支，fallback 里手动挂的属性不完整。
**方案**：
- 写扫描脚本对比所有 `_light_builtin.xxx()` 调用和已定义属性
- 在 fallback 追加段统一补全（`环境变量`、`单调时钟`、`深拷贝`、`随机整数` 等 60+ 个）
- **关键教训**：补丁脚本要精确 anchor（`格式化时间` 行后插入），不要找 `else:` 行（会误判 if-else 的 else）

### 5. two 个 fallback 分支不一致
**现象**：`深拷贝` 在一个分支有，另一个没有。
**根因**：try/except/else 结构里，except 分支和追加段的属性列表不同步。
**方案**：在追加段（`查找目录列表` 后）统一补 `副本`/`浅拷贝`/`深拷贝`/`冻结`。

### 6. 纯导出模块无函数体
**现象**：.light 文件只有 `导出` 声明，无函数体。
**方案**：复制 `stdlib/*.py` 实现文件按映射表覆盖到 build_py/。

### 7. signal.py 覆盖标准库
**现象**：stdlib/signal.py 和 Python 标准库冲突。
**方案**：重命名为 `light_signal.py`。

### 8. exe 被占用导致编译失败
**现象**：`PermissionError: 拒绝访问`。
**方案**：打包前 `Get-Process lightharness | Stop-Process -Force`。

### 9. Windows 命令执行
**现象**：bash 工具坏的。
**方案**：`stdlib/外部命令.py` 检测 win32，自动包装成 `powershell.exe -NoProfile -Command "..."`。

## 验证流程

1. 启动 exe，确认输出 `web 服务已启动 http://127.0.0.1:PORT/?token=xxx`
2. `netstat -ano | findstr LISTENING` 确认端口在监听
3. `curl.exe` 发 chat API 请求，确认返回 JSON 不是 500 错误
4. **Playwright 端到端测试**：打开页面 → 输入消息 → 确认 AI 正常流式回复

## 打包命令

```bash
# 1. 编译 .light → .py
python build_py.py

# 2. Nuitka 打包
vcvars64.bat && python -m nuitka --msvc=14.2 --onefile \
  --output-dir=nuitka_final --output-filename=lightharness.exe \
  --include-data-dir=webui=webui \
  --include-data-dir=stdlib=stdlib \
  build_py\main.py
```

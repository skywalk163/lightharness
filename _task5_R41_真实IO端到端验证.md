# 任务5（R41·P1）交付报告 —— 真实IO端到端验证

> 日期：2026-09-16 ｜ 负责人：主Agent（路M兼做）｜ 状态：**完成（Windows本机 + 0.82 FreeBSD 双平台 rc=0）**
> 目标：用**真实文件IO + 真实网络IO**跑一条端到端会话（不再内存 mock/回放），并在 0.82 复测。零源码修改。

---

## 一、端到端链（真实发生，非内存模拟）

`examples/test_R41_真实IO端到端.light` 把任务1（真实文件系统提供者）与任务2（真实HTTP客户端+web服务器）串联成一条完整链：

1. 本机起 web服务器（127.0.0.1，内核分配端口），mock 客户端回应带标记文本；
2. **真实HTTP客户端**（非阻塞 socket）`GET /health` → 200；
3. **真实HTTP客户端** `POST /v1/chat/completions` → 200，拿到网络真实响应体（含标记）；
4. 把网络响应用「真实文件系统提供者.原子写文件提供」**原子写到真实磁盘文件**（真实文件IO，临时文件+os.replace）；
5. 用「真实文件系统提供者.读文件提供」读回，断言**落盘内容与网络响应体逐字一致**；
6. 查信息 / 文件存在(布尔在数据字段) / 列目录 三条真实文件IO 形状校验；
7. 沙箱越界拒绝：`../` 逃逸写入 → PERMISSION_DENIED。

---

## 二、双平台验证结果

| 平台 | 结果 |
|---|---|
| Windows 10 本机 | **rc=0**（任务5 全部断言通过…） |
| 0.82 FreeBSD 15.1-STABLE amd64（python3.11） | **rc=0**（同上，经 SSH 同步临时副本远程执行） |

0.82 同步方式：复用任务3/4 留在 `/tmp/r41-1789552701` 的临时副本，SFTP 增量上传 5 个本轮回增文件（真实文件系统提供者.light / 真实HTTP客户端.light / web服务器.light / HTTP服务端.light / 端到端示例），远程 `LIGHT_MERGE=... python3.11 运行.py ...` 执行。0.82 只读执行，未改源。

---

## 三、调试中修的两处（均为示例脚本层面，非产品缺陷）

1. **`删目录树` 误导入**：示例初版从 `文件系统` 导入 `删目录树` 报 ImportError——它是内建全局函数，不在 `文件系统` 导出。删除该导入即通。
2. **越界路径写错**：初版用 `沙盒 + "/../逃逸.txt"`，因沙盒在根内，`..` 只回到根目录、未逃出根，沙箱正确放行 → 断言"越界被拒"失败。改为直接 `"../逃逸.txt"`（从当前目录逃出 HARNESS_ROOT），PERMISSION_DENIED 正确触发。这反向印证：**沙箱护栏确实在工作**——从根内回退一级不误伤，只有真逃逸才拒。

---

## 四、语言缺陷账
本轮任务5 **未暴露新的 light 内建缺失**：复用任务1/2 已验证的文件/网络内建全部可用。既有 L-159（无字节串字面量）/L-160/L-161 归任务2登记，本轮无新增。

---

## 五、运行方式
```bash
# Windows 本机
cd G:/dswork/duan-light-merge/lightharness
G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe 运行.py examples/test_R41_真实IO端到端.light
# 0.82 FreeBSD（SSH 远程）
cd /tmp/r41-1789552701/lightharness
LIGHT_MERGE=/tmp/r41-1789552701/light-merge python3.11 运行.py examples/test_R41_真实IO端到端.light
```

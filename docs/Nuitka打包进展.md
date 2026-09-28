# lightharness Nuitka 独立 EXE 进展报告

## 已完成

1. **Nuitka 4.2.2 安装成功**（用 VS2019 BuildTools 的 MSVC 14.2 编译器）
2. **201 个 .light 模块批量编译成 .py**（build_py/ 目录）
3. **87 个 stdlib 模块编译成 .py**
4. **lightharness.exe 生成成功**（8.4MB，onefile 模式）
5. **hello.exe 验证通过**（Nuitka 编译链路完全打通）

## 当前阻塞

**中文模块名编码问题**：Nuitka 在 Windows 上用 GBK 编码读取 .py 文件，导致中文模块名（web服务器、HTTP服务端、编码解码等）乱码。

错误示例：
```
ImportError: cannot import name 'URL解码' from '编码解码'
（实际乱码成 URL瑙ｇ爜 / 缂栫爜瑙ｇ爜）
```

## 根本原因

光明语言的模块名是中文（web服务器.light、认证.light、会话存储.light...），编译成 Python 后：
- .py 文件本身是 UTF-8 编码
- Nuitka 在 Windows 上用系统编码（GBK）读取
- 中文模块名在 GBK ↔ UTF-8 转换中乱码

## 解决方案（按推荐排序）

### 方案 1：模块名英文化（推荐，根治）
- 把所有 .light 模块名改成英文（web_server.light、auth.light、session.light...）
- 同步修改所有 import 语句
- 工程量：~200 个文件，但可以脚本化
- 收益：彻底解决编码问题，未来所有打包工具都能用

### 方案 2：Nuitka 加 UTF-8 模式
- 研究 Nuitka 是否支持 `--python-flag=-X utf8` 或类似参数
- 让 Nuitka 用 UTF-8 读取源码
- 需要查 Nuitka 文档

### 方案 3：放弃 Nuitka，用其他工具
- PyInstaller 对中文模块名支持更好（但之前也有编码问题）
- 或直接用 `python 运行.py` 启动，配合一个 .bat 启动器

## 当前可用方式

```bash
# 客户机器装 Python 3.10+，然后：
python 运行.py examples/运行Web服务器.light

# 或用 .bat 启动器（双击即可）
```

## 编译命令记录（未来用）

```bash
# 1. 激活 MSVC 环境
"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

# 2. 编译所有 .light 到 build_py/
python build_py.py

# 3. 用 Nuitka 打包
python -m nuitka --msvc=14.2 --onefile \
  --output-dir=nuitka_final --output-filename=lightharness.exe \
  --include-data-dir=webui=webui \
  --include-data-dir=stdlib=stdlib \
  build_py/main.py
```

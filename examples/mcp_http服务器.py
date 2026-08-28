# -*- coding: utf-8 -*-
"""mcp_http服务器.py —— 极简 HTTP MCP 测试服务器（stdio 版的 HTTP 对应）。

监听 127.0.0.1:18765，POST / 接受 JSON-RPC 2.0，返回 JSON 响应。
工具：echo(text) / add(a,b) / get_image()（返回 image 块，用于 v2 图片投影测试）。

用法：python examples/mcp_http服务器.py  （前台运行，Ctrl+C 停止）
"""
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 18765

TOOLS = [
    {"name": "echo", "description": "回显输入文本", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}},
    {"name": "add", "description": "两数相加", "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}},
    {"name": "get_image", "description": "返回一张图片块（测试图片投影）", "inputSchema": {"type": "object"}},
]


class MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            req = json.loads(raw)
        except Exception:
            self._send_json({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}, 400)
            return

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params", {})

        # 通知（无 id）：不响应
        if req_id is None:
            self._send_json({}, 202)
            return

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "test-mcp-http", "version": "1.0.0"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            if name == "echo":
                content = [{"type": "text", "text": args.get("text", "")}]
            elif name == "add":
                content = [{"type": "text", "text": str(args.get("a", 0) + args.get("b", 0))}]
            elif name == "get_image":
                content = [{"type": "image", "mimeType": "image/png", "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}]
            else:
                self._send_json({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}, 200)
                return
            result = {"content": content, "isError": False}
        else:
            self._send_json({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}, 200)
            return

        self._send_json({"jsonrpc": "2.0", "id": req_id, "result": result}, 200)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = PORT
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = HTTPServer(("127.0.0.1", port), MCPHandler)
    print(f"MCP HTTP 测试服务器运行在 http://127.0.0.1:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

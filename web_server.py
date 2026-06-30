"""
WebUI 服务：聊天记录浏览
"""

import json
import logging
import secrets
from pathlib import Path

from aiohttp import web

logger = logging.getLogger("astrbot")

LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>登录 - 聊天记录 WebUI</title>
<style>
  body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
  .box { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); width: 300px; }
  h2 { margin-top: 0; text-align: center; }
  input { width: 100%; padding: 0.5rem; margin: 0.5rem 0 1rem; box-sizing: border-box; border: 1px solid #ddd; border-radius: 4px; }
  button { width: 100%; padding: 0.6rem; background: #4a90e2; color: white; border: none; border-radius: 4px; cursor: pointer; }
  button:hover { background: #357abd; }
  .error { color: red; font-size: 0.9rem; text-align: center; }
</style>
</head>
<body>
<div class="box">
  <h2>聊天记录 WebUI</h2>
  <form method="post" action="/login">
    <input type="password" name="password" placeholder="请输入密码" autofocus>
    <button type="submit">登录</button>
  </form>
  {error}
</div>
</body>
</html>"""


class WebServer:
    """聊天记录备份 WebUI 服务器"""

    def __init__(self, plugin, host: str = "0.0.0.0", port: int = 8866, password: str = ""):
        self.plugin = plugin
        self.host = host
        self.port = port
        self.password = password
        # 存储已登录的 session token
        self._tokens: set[str] = set()
        self.app = web.Application()
        self.runner = None
        self.site = None
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/chats", self.handle_list_chats)
        self.app.router.add_get("/api/chat/{filename}", self.handle_get_chat)
        self.app.router.add_get("/api/stats", self.handle_stats)
        if self.password:
            self.app.router.add_get("/login", self.handle_login_page)
            self.app.router.add_post("/login", self.handle_login)

    def _check_auth(self, request: web.Request) -> bool:
        """检查请求是否已通过认证"""
        if not self.password:
            return True
        token = request.cookies.get("auth_token")
        return token in self._tokens

    def _auth_redirect(self) -> web.Response:
        return web.HTTPFound("/login")

    async def handle_login_page(self, request: web.Request) -> web.Response:
        html = LOGIN_HTML.replace("{error}", "")
        return web.Response(text=html, content_type="text/html")

    async def handle_login(self, request: web.Request) -> web.Response:
        data = await request.post()
        if data.get("password") == self.password:
            token = secrets.token_hex(32)
            self._tokens.add(token)
            response = web.HTTPFound("/")
            response.set_cookie("auth_token", token, httponly=True, max_age=86400 * 30)
            return response
        html = LOGIN_HTML.replace("{error}", '<p class="error">密码错误</p>')
        return web.Response(text=html, content_type="text/html", status=401)

    async def start(self):
        """启动 Web 服务器"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            pwd_hint = "（已启用密码保护）" if self.password else "（无密码保护）"
            logger.info(f"📊 聊天记录 WebUI 已启动: http://{self.host}:{self.port} {pwd_hint}")
            return True
        except Exception as e:
            logger.error(f"❌ WebUI 启动失败: {e}")
            return False

    async def stop(self):
        """停止 Web 服务器"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("📊 聊天记录 WebUI 已停止")

    async def handle_index(self, request):
        """返回首页 HTML"""
        if not self._check_auth(request):
            return self._auth_redirect()

        static_dir = Path(__file__).parent / "static"
        index_file = static_dir / "index.html"

        if index_file.exists():
            html = index_file.read_text(encoding="utf-8")
        else:
            html = "<h1>404 - index.html not found</h1>"

        return web.Response(text=html, content_type="text/html")

    async def handle_list_chats(self, request):
        """获取聊天列表"""
        if not self._check_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        chats = []
        data_dir = self.plugin.data_dir
        filter_type = request.query.get("type", "all")

        if data_dir.exists():
            for f in data_dir.glob("*.jsonl"):
                parts = f.stem.rsplit("_", 1)
                if len(parts) == 2:
                    chat_id, chat_type = parts
                else:
                    chat_id = f.stem
                    chat_type = "unknown"

                if filter_type != "all" and chat_type != filter_type:
                    continue

                msg_count = 0
                last_msg = None
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        lines = fp.readlines()
                        msg_count = len(lines)
                        if lines:
                            last_msg = json.loads(lines[-1])
                except Exception:
                    pass

                chats.append(
                    {
                        "filename": f.name,
                        "chat_id": chat_id,
                        "type": chat_type,
                        "message_count": msg_count,
                        "size_kb": round(f.stat().st_size / 1024, 1),
                        "last_message": (
                            last_msg.get("content", "")[:50] if last_msg else ""
                        ),
                        "last_time": last_msg.get("timestamp", "") if last_msg else "",
                    }
                )

        chats.sort(key=lambda x: x["last_time"], reverse=True)
        return web.json_response(chats)

    async def handle_get_chat(self, request):
        """获取单个聊天的消息"""
        if not self._check_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        filename = request.match_info["filename"]
        file_path = self.plugin.data_dir / filename

        if not file_path.exists():
            return web.json_response({"error": "Chat not found"}, status=404)

        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("size", 50))

        messages = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                total = len(lines)

                start = max(0, total - page * page_size)
                end = total - (page - 1) * page_size

                for line in lines[start:end]:
                    try:
                        messages.append(json.loads(line.strip()))
                    except Exception:
                        pass

                messages.reverse()

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

        return web.json_response(
            {"messages": messages, "total": total, "page": page, "page_size": page_size}
        )

    async def handle_stats(self, request):
        """获取统计信息"""
        if not self._check_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        data_dir = self.plugin.data_dir
        stats = {
            "total_chats": 0,
            "total_messages": 0,
            "total_size_mb": 0,
            "private_chats": 0,
            "group_chats": 0,
        }

        if data_dir.exists():
            for f in data_dir.glob("*.jsonl"):
                stats["total_chats"] += 1
                stats["total_size_mb"] += f.stat().st_size / (1024 * 1024)

                if "_private" in f.name:
                    stats["private_chats"] += 1
                elif "_group" in f.name:
                    stats["group_chats"] += 1

                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        stats["total_messages"] += len(fp.readlines())
                except Exception:
                    pass

        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        return web.json_response(stats)

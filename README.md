# 🦊 AstrBot 聊天记录备份插件

实时备份聊天记录，防止对话历史丢失。

## ✨ 功能特点

- 📝 **实时备份**：每条消息即时保存，不会丢失
- 💬 **完整记录**：同时保存用户消息和机器人回复
- 📁 **分类存储**：按 QQ 号/群号分别保存
- ⚡ **高效写入**：使用 JSONL 格式追加写入，性能优异
- 🔧 **灵活配置**：支持白名单、黑名单等设置
- 🌐 **WebUI 浏览**：内置可视化界面，方便查看记录

## 📦 安装

在 AstrBot 中使用以下命令安装：

```
plugin i https://github.com/Omnitopia/astrbot_plugin_history
```

或者在 WebUI 的插件市场中搜索「聊天记录备份」。

## 🌐 WebUI 访问

启用 WebUI 后，根据你的部署方式访问：

**本地部署**
```
http://localhost:8866
```

**Docker 部署**

启动容器时必须添加端口映射，否则无法访问：
```bash
docker run ... -p 8866:8866 ...
```
然后访问 `http://localhost:8866`

**云服务器 / VPS**

需要两步：
1. 在云服务商控制台找到「安全组」或「防火墙」，添加一条入站规则（一般是「+添加」/「新建规则」选项）：协议 TCP、端口 8866、来源 0.0.0.0/0
2. 用服务器公网 IP 访问：`http://公网IP:8866`

> ⚠️ 云服务器部署时 WebUI 暴露在公网，建议设置 `webui_password` 开启密码保护（见下方配置项）

> 📝 端口号可在插件配置中修改（默认 8866）

## ⚙️ 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_private` | bool | true | 是否备份私聊消息 |
| `enable_group` | bool | true | 是否备份群聊消息 |
| `group_whitelist` | list | [] | 群聊白名单（为空则全部备份） |
| `group_blacklist` | list | [] | 群聊黑名单 |
| `save_system_info` | bool | true | 是否保存时间戳、昵称等信息 |
| `max_file_size_mb` | int | 10 | 单文件最大大小（MB） |
| `enable_webui` | bool | true | 是否启用 WebUI |
| `webui_port` | int | 8866 | WebUI 端口号 |
| `webui_password` | str | "" | WebUI 访问密码，为空则不启用验证（云服务器部署建议设置）|

## 📁 数据存储

备份文件保存在 AstrBot 数据目录下：

```
{astrbot_data}/plugin_data/astrbot_plugin_history/
├── 123456789_private.jsonl    # 私聊记录
├── 987654321_group.jsonl      # 群聊记录
└── ...
```

### 文件格式（JSONL）

每行一条 JSON 记录，便于追加写入和处理：

```jsonl
{"timestamp": "2026-02-09T10:30:00", "role": "user", "content": "你好！", "sender_id": "123456789", "sender_name": "用户A"}
{"timestamp": "2026-02-09T10:30:05", "role": "assistant", "content": "你好呀～有什么可以帮你的吗？"}
```

## 🔄 文件轮转

当单个备份文件超过 `max_file_size_mb` 设置的大小时，会自动创建新文件：

```
123456789_private.jsonl                    # 当前文件
123456789_private_20260209_120000.jsonl    # 历史文件
```

## ❓ 常见问题

### Q: 会影响机器人性能吗？
A: 几乎不会。插件使用 JSONL 追加写入模式，每条消息只需几毫秒即可保存。

### Q: 一天大概占用多少空间？
A: 取决于消息量。一般来说，每天 100 条私聊 + 500 条群聊约占用 1-3 MB。

### Q: 可以导出用于 AI 微调吗？
A: 可以！JSONL 格式非常适合转换为微调数据集。

### Q: Docker 部署后 WebUI 访问不了？
A: 需要在启动容器时添加端口映射 `-p 8866:8866`，详见上方「WebUI 访问」章节。

### Q: 云服务器部署，担心 WebUI 被陌生人访问？
A: 在插件配置中设置 `webui_password`，开启后访问 WebUI 需要输入密码。本地和 Docker 部署不需要设置。

## 🦊 关于

由 [OmniTopia](https://github.com/Omnitopia) 开发 - 全一的乌托邦

让每一段对话都不会丢失 💕

# 聊天助手网页版（FastAPI）

浏览器里打开一个聊天页面，输入消息即可调用 `chat.py` 同款模型（`qwen4-max`、郭德纲风格系统提示词、`temperature=1.2`、`top_p=0.9`）。API Key 只在后端 `.env` 中，不会发送到浏览器。

## 启动

当前电脑的 `yolov8` 环境已经装好依赖，双击 `run.bat`，或在 PowerShell 里运行：

```powershell
cd d:\daima\20261127\work
.\run.bat
```

如果 PowerShell 禁止运行脚本，用 `run.bat` 就不会有执行策略问题。也可以手动启动：

```powershell
D:\Users\Student\anaconda3\envs\yolov8\python.exe app.py
```

然后打开 <http://127.0.0.1:8010>。接口文档在 <http://127.0.0.1:8010/docs>。

> 端口用 8010，是因为当前的 8000 已经被之前的旧版聊天服务占用。想换端口就改 `work/.env` 里的 `PORT`。

如果换到别的 Python 环境，先安装依赖：

```powershell
python -m pip install -r requirements.txt
python app.py
```

## 配置

配置在 `work/.env`（参考 `.env.example`）：

| 变量 | 作用 |
|---|---|
| `CHAT_API_KEY` | 接口密钥，必填 |
| `CHAT_BASE_URL` | OpenAI 兼容接口地址 |
| `CHAT_MODEL` | 模型名，默认 `qwen4-max` |
| `CHAT_ENABLE_THINKING` | 是否开启思考过程，默认 `false` |
| `CHAT_MAX_HISTORY` | 每次请求带多少条历史消息 |
| `HOST` / `PORT` | 监听地址和端口，默认 `127.0.0.1:8010` |

## 文件

```
work/
├── app.py               FastAPI 后端：页面、健康检查、流式聊天接口
├── static/index.html    前端：聊天界面、流式显示、停止、参数设置
├── .env                 本地密钥配置（不要外传）
├── .env.example         配置模板
├── requirements.txt
├── run.bat              双击启动（推荐）
└── run.ps1              用 yolov8 环境启动
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 聊天页面 |
| GET | `/api/health` | 模型名、Key 是否配置 |
| POST | `/api/chat` | 一次性返回完整回答（JSON） |
| POST | `/api/chat/stream` | SSE 流式返回 |
| GET | `/docs` | Swagger 文档 |

请求体：

```json
{
  "message": "你好",
  "system": "",
  "history": [{"role": "user", "content": "上一轮问题"}],
  "temperature": 1.2,
  "top_p": 0.9
}
```

`system` 留空时使用默认的郭德纲风格人设。`history` 只放之前的消息，不要放当前 `message`。

## 注意

- `.env` 里有真实 Key，不要提交或发给别人。`chat.py` 里也有明文 Key，如果要分享代码，建议先去控制台轮换一次。
- 默认只监听 `127.0.0.1`，同一局域网的其他设备访问不到。改成 `HOST=0.0.0.0` 可局域网访问，但不要直接把带 Key 的服务暴露到公网。
- 页面是纯文本显示回答，没有做 Markdown 渲染。

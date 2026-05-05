# Prompt 优化器

一个基于 AI 的提示词优化工具，支持豆包、Kimi AI、OpenAI、DeepSeek 等多个服务商。

## 功能特点

- 🔮 **多 AI 模型支持**：豆包、Kimi AI、OpenAI、DeepSeek、本地模型
- 🎨 **精美界面**：深色/浅色主题，玻璃态设计
- 📱 **移动端优化**：响应式布局，适配手机和平板
- ✨ **内置优化系统**：自动优化你的 Prompt
- 🔒 **安全架构**：后端代理 API 调用，避免跨域问题

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

### 3. 访问应用

在浏览器中打开：http://localhost:8000

## 使用说明

### 选择 AI 服务商

1. 在顶部左侧选择 AI 服务商（默认为豆包）
2. 选择对应的模型
3. 填写你的 API Key
4. 输入要优化的 Prompt
5. 点击"立即优化"按钮

### 获取豆包 API Key

1. 访问 [火山引擎控制台](https://console.volcengine.com/ark)
2. 创建一个豆包（Doubao）模型接入点
3. 生成并复制你的 API Key
4. 将 API Key 填入应用中即可使用

### 支持的服务商

| 服务商 | 模型列表 | API 获取地址 |
|--------|----------|--------------|
| 豆包 | doubao-pro-4k, doubao-lite-4k, doubao-lite-32k, doubao-pro-32k | [火山引擎控制台](https://console.volcengine.com/ark) |
| Kimi AI | moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k | [Moonshot 官网](https://platform.moonshot.cn/) |
| OpenAI | gpt-4o, gpt-4-turbo, gpt-3.5-turbo | [OpenAI 官网](https://platform.openai.com/) |
| DeepSeek | deepseek-chat | [DeepSeek 官网](https://platform.deepseek.com/) |
| 本地模型 | 自定义 | Ollama 或其他本地服务 |

## 技术架构

### 前端

- 原生 HTML/CSS/JavaScript
- 响应式设计
- 深色/浅色主题切换

### 后端

- FastAPI 框架
- CORS 跨域处理
- API 请求代理

### API 接口

文档地址：http://localhost:8000/docs

## 项目结构

```
/workspace/
├── prompt_optimizer_v2.html    # 前端页面
├── main.py                     # 后端服务
├── requirements.txt            # Python 依赖
└── README.md                   # 本说明文件
```

## 常见问题

### Q: 为什么需要后端服务？

A: 直接在浏览器中调用第三方 API 会遇到跨域（CORS）问题，后端服务作为代理处理这些请求。

### Q: API Key 安全吗？

A: API Key 仅在浏览器和你的后端服务器之间传输，不会发送到任何第三方（除了对应的 AI 服务商）。

### Q: 如何停止服务？

A: 在终端中按 `Ctrl + C` 即可停止服务。

## 开发说明

如需修改前端，直接编辑 `prompt_optimizer_v2.html` 即可，修改后刷新浏览器页面。

如需修改后端，编辑 `main.py` 后重启服务。

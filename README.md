# Book2TTS Web 控制台

基于 Django 的书籍有声化工作台，提供从电子书解析、文本处理到音频分发的全流程工具。所有功能围绕 `src/web` 架构构建，支持精细化的积分治理、任务管理与多模态 AI 协作。

## 🚀 核心能力

- **工作台（Workbench）**
  - EPUB/PDF 导入：自动解析目录与页面，支持多页合并、原文预览与资源提取。
  - 音频生产：对接多语音服务（Edge、Azure 等），支持进度跟踪、任务队列、字幕生成与章节导出。
  - OCR 工具：嵌入火山引擎识别与缓存策略，扫描版 PDF 可按页或批量识别。
  - LLM 助手：提供自动排版、翻译、对话脚本生成、章节提取等操作，并记录 token 消耗与积分扣减。
  - 资产管理：音频列表、任务队列、章节信息、原始页面图片等入口集中管理。

- **用户侧功能**
  - 个人资料页：展示剩余积分、积分规则、配额调整记录。
  - RSS 订阅：为发布的音频生成 Podcast 兼容的 RSS Feed，可按用户、书籍或 Token 维度访问。
  - 运营记录：所有 LLM/OCR/音频操作都会生成 `OperationRecord`，方便审计与追踪。

- **积分治理**
  - `PointsConfig` 支持“音频生成”“OCR 处理”“LLM 调用”等规则配置，界面动态渲染，无硬编码。
  - `PointsManager` 统一查询与缓存，支持千 token 计费、默认值初始化与后台管理。
  - 扣分动作伴随操作记录与剩余积分快照，可在工作台和个人资料的“积分规则”对话框查看。

## 🏗️ 架构概览

| 模块 | 说明 |
| ---- | ---- |
| `src/web/manage.py` | Django 入口 |
| `workbench/` | 书籍工作台（视图、模板、任务、静态资源）|
| `home/` | 用户主页、积分与 RSS 功能 |
| `books/` | 数据模型（书籍、音频、对话脚本等）|
| `tasks.py` | Celery 任务：文本转对话、音频合成、章节生成等 |
| `utils/` | OCR、字幕、积分等辅助模块 |
| `templates/` | Tailwind + DaisyUI 风格的页面组件 |

### 关键技术
- **后端**：Django + Celery + Redis
- **文档处理**：PyMuPDF、ebooklib、BeautifulSoup
- **AI 能力**：LiteLLM（统一接入多个 LLM）、Edge/Azure TTS、火山引擎 OCR
- **前端**：Tailwind CSS、DaisyUI、HTMX、Alpine.js（模板内联）
- **音频处理**：FFmpeg、edge-tts、多角色合成

## ⚙️ 环境与部署

### 依赖
- Python 3.10+（推荐 3.12）
- Redis（任务队列 / 缓存）
- FFmpeg（字幕与音频后处理）

### 安装
```bash
# 克隆代码
git clone https://github.com/pingfury/book2tts.git
cd book2tts

# 安装依赖（建议使用 uv）
uv sync
# 或
pip install -r requirements.lock
```

### 配置
复制 `.env.example`（如存在）或自行创建 `.env`，常用变量：
```
DEBUG=true
SECRET_KEY=replace_with_your_value
REDIS_URL=redis://localhost:6379/0

# LLM / TTS / OCR 配置按需启用
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=...
EDGE_TTS_PROXY=...
VOLCENGINE_ACCESS_KEY=...
VOLCENGINE_SECRET_KEY=...
LLM_PROVIDER=...
```

### 初始化数据库
```bash
cd src/web
python manage.py migrate
python manage.py createsuperuser
```

### 启动服务
```bash
# 启动 Django
python manage.py runserver

#（可选）启动 Celery 任务
celery -A book_tts worker -l info
```
访问 `http://localhost:8000/` 即可进入工作台。

## 📚 目录速览（web 部分）
```
src/web/
├── book_tts/           # Django 配置、URL、Celery 设置
├── home/               # 个人中心、积分、RSS
├── workbench/          # 书籍工作台核心逻辑
│   ├── templates/      # HTMX/Tailwind 页面
│   ├── views/          # 业务视图（book/audio/dialogue/text...）
│   ├── tasks.py        # Celery 任务
│   └── utils/          # OCR、字幕、积分等工具
├── static/             # 前端静态资源
└── manage.py           # 项目入口
```

## 🧪 本地开发建议
- 启用 `DEBUG=true` 方便调试模板与静态文件。
- 使用 `python manage.py test` 运行现有单元测试。
- 若修改积分配置、操作记录等数据模型，记得同步更新后台管理与前端展示。
- Celery 任务依赖 Redis，确保本地服务可用或修改为 `CELERY_TASK_ALWAYS_EAGER=True` 进行同步调试。

## 🗺️ 后续规划
- 可视化任务队列与音频发布统计
- LLM 调用策略与消费报表
- 更细粒度的权限与协作流

欢迎提交 Issue 或 PR，一起完善 Book2TTS Web 控制台。EOF

# bili2text-new 📺

B站视频下载与文案提取工具 — 输入BV号，自动下载视频并转写为文字文案。

## 功能特性

- 🎥 **视频下载** — 基于 yt-dlp，稳定可靠，支持多P分段下载
- 📝 **字幕直取** — 有CC/AI字幕的视频可直接获取文案，无需下载和识别
- 🎵 **音频提取** — ffmpeg 自动从视频中提取音频
- ✂️ **音频分割** — 长音频按时长切片，逐段转录
- 🤖 **语音转文字** — faster-whisper 离线识别，支持 GPU 加速
- 💾 **自动保存** — 转录结果自动保存为文本文件

## 对比原版

| 特性 | bili2text (原版) | bili2text-new |
|------|-----------------|---------------|
| 下载工具 | you-get（经常失效） | yt-dlp（活跃维护） |
| 语音识别 | openai-whisper（需 PyTorch，体积大） | faster-whisper（轻量快速） |
| 字幕直取 | ❌ | ✅ B站API直接获取 |
| 多P分段 | ❌ | ✅ 支持 |
| GPU 加速 | 需完整 CUDA Toolkit | pip 安装 nvidia 包即可 |
| 依赖数量 | 40+ | 2 核心包 + ffmpeg |

## 快速开始

### 1. 安装前置

- **Python 3.10+**
- **ffmpeg**（必须）

安装 ffmpeg：

```bash
# Windows（推荐 scoop）
scoop install ffmpeg
# 或 winget
winget install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 2. 克隆并安装

```bash
git clone https://gitee.com/sheng-20/bili-text.git
cd bili-text

# 创建虚拟环境
python -m venv .env

# 激活虚拟环境
# Windows:
.env\Scripts\activate
# macOS/Linux:
source .env/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 运行

**Windows 一键启动：** 双击 `start.bat`

**或手动运行：**

```bash
python main.py
```

## 使用方法

### 交互模式（推荐）

```bash
python main.py
```

按提示输入BV号或链接即可。程序会自动：
1. 检查视频是否有字幕（有则直接获取，无需下载）
2. 无字幕则下载视频 → 提取音频 → 语音识别

### 命令行模式

```bash
# 完整流程：下载 → 转录
python main.py BV1xx411c7mD

# 直接获取字幕（不下载视频，速度最快）
python main.py --subtitle BV1xx411c7mD

# 查看视频信息
python main.py --info BV1xx411c7mD

# 只下载视频，不转录
python main.py --download BV1xx411c7mD

# 下载指定分P
python main.py BV1xx411c7mD --page 1
python main.py BV1xx411c7mD --page 1-3
python main.py BV1xx411c7mD --page 1,3,5

# 使用 medium 模型（更准确）
python main.py BV1xx411c7mD --model medium

# 转录已有视频目录
python main.py --transcribe downloads/video/BV1xx411c7mD

# 自定义提示词
python main.py BV1xx411c7mD --prompt "以下是关于机器学习的中文演讲。"

# 检查环境依赖
python main.py --check
```

## 配置

编辑 `config.env` 文件自定义配置：

```env
# Whisper 模型大小 (tiny/small/medium/large)
WHISPER_MODEL=small

# 计算设备 (auto/cpu/cuda)
WHISPER_DEVICE=auto

# 计算精度 (auto/float16/int8)
WHISPER_COMPUTE_TYPE=auto

# 音频分割长度（秒）
SLICE_LENGTH=45

# B站 Cookie（可选，用于下载更高清视频）
# BILIBILI_COOKIE=SESSDATA=你的值
```

### Whisper 模型选择

| 模型 | 参数量 | 速度 | 中文准确度 | 显存需求 |
|------|--------|------|-----------|----------|
| tiny | 39M | ⚡⚡⚡⚡ | ★★ | ~1GB |
| small | 244M | ⚡⚡⚡ | ★★★★ | ~2GB |
| medium | 769M | ⚡⚡ | ★★★★★ | ~5GB |
| large | 1550M | ⚡ | ★★★★★+ | ~10GB |

**推荐：** 日常用 `small`，追求准确度用 `medium`，`tiny` 仅用于快速测试。

## GPU 加速

程序会自动检测 NVIDIA GPU 并使用 CUDA 加速，无需手动安装 CUDA Toolkit。

如需 GPU 支持，安装额外的 nvidia 包：

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

程序会在启动时自动：
1. 检测 pip 安装的 NVIDIA CUDA 库
2. 将 DLL 路径加入搜索路径
3. 如果 CUDA 加载失败，自动回退到 CPU 模式

## Cookie 导出

部分高清视频需要登录才能下载。导出 Cookie 的方法：

### 方法一：浏览器插件（推荐）

1. 安装 Chrome 插件 [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. 打开 bilibili.com 并登录
3. 点击插件图标，导出 cookies
4. 保存为 `cookies.txt` 放到项目根目录

### 方法二：辅助脚本

双击 `export_cookies.bat`，会尝试从浏览器自动提取 Cookie。

### 方法三：手动填写

1. 打开 bilibili.com 并登录
2. 按 F12 → Application → Cookies → `https://www.bilibili.com`
3. 找到 `SESSDATA` 的值
4. 填入 `config.env`：`BILIBILI_COOKIE=SESSDATA=你的值`

**优先级：** `cookies.txt` 文件 > `config.env` 中的 `BILIBILI_COOKIE`

## 项目结构

详细结构说明见 [STRUCTURE.md](STRUCTURE.md)。

```
bili2text-new/
├── main.py                 # 主程序入口
├── config.py               # 配置加载
├── config.env              # 用户配置
├── downloader.py           # 视频下载 (yt-dlp)
├── audio_processor.py      # 音频处理 (ffmpeg)
├── transcriber.py          # 语音识别 (faster-whisper)
├── subtitle_fetcher.py     # 字幕获取 (B站API)
├── requirements.txt        # 依赖列表
├── start.bat               # Windows 启动脚本
├── export_cookies.bat      # Cookie 导出脚本
├── downloads/              # 下载目录
│   ├── video/              #   视频文件
│   ├── audio/              #   提取的音频
│   └── temp/               #   临时切片
├── models/                 # Whisper 模型缓存
└── outputs/                # 文案输出
```

## 常见问题

### 下载失败，提示需要会员？

需要导出浏览器 Cookie 后重试，参见上方 [Cookie 导出](#cookie-导出) 部分。

### RuntimeError: Library cublas64_12.dll is not found？

这是 CUDA DLL 路径问题。确保安装了 `nvidia-cublas-cu12` 和 `nvidia-cudnn-cu12`：

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

程序已内置自动回退机制，CUDA 加载失败会自动切换到 CPU 模式。

### 转录速度太慢？

- 有 NVIDIA GPU 的确保安装了 nvidia 包（见上方 GPU 加速部分）
- 没有GPU的使用 `tiny` 或 `base` 模型
- 缩短音频分割长度（如 `SLICE_LENGTH=30`）对速度帮助不大

### 中文转录效果不好？

- 升级模型大小：`small` → `medium` 效果提升明显
- 使用 `--prompt` 参数提供上下文提示，如 `--prompt "以下是关于烹饪的中文视频"`

### ffmpeg 未找到？

确保已安装 ffmpeg 并添加到系统 PATH，或运行 `python main.py --check` 检查环境。

## 许可证

MIT License

## 使用须知

**用户在使用本工具时，必须遵守用户所在地区的相关版权法律和规定。请确保您有权利下载和转换的视频内容，尊重创作者的劳动成果。**

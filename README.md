# bili2text-new 📺

B站视频下载与文案提取工具 - 根据BV号下载视频，提取音频，自动转写为文字。

## 功能 🚀

- 🎥 **下载视频** - 根据 BV 号下载 B 站视频，支持多 P 分段下载
- 🎵 **提取音频** - 自动从视频中提取音频
- 💬 **音频分割** - 将长音频按时长分割，提高转录效率
- 🤖 **语音转文字** - 使用 faster-whisper 将语音转换为文字
- 📝 **保存文案** - 转录结果自动保存为文本文件

## 对比原版的优势 ✨

| 特性 | bili2text (原版) | bili2text-new |
|------|-----------------|---------------|
| 下载工具 | you-get（经常失效） | yt-dlp（活跃维护） |
| 语音识别 | openai-whisper（需 PyTorch，巨大） | faster-whisper（轻量快速） |
| 分段下载 | 不支持 | ✅ 支持 |
| 环境管理 | 无 | ✅ .env 虚拟环境 |
| 依赖数量 | 40+ | 2 个核心包 + ffmpeg |
| 安装难度 | 高 | 低 |

## 安装 📦

### 1. 前置要求

- Python 3.10+
- ffmpeg（必须）

安装 ffmpeg：

```bash
# Windows (推荐用 scoop)
scoop install ffmpeg
# 或者用 winget
winget install ffmpeg

# Mac
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### 2. 克隆项目

```bash
git clone <repo-url>
cd bili2text-new
```

### 3. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv .env

# 激活虚拟环境
# Windows:
.env\Scripts\activate
# Mac/Linux:
source .env/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 使用方法 📘

### 交互模式（推荐新手）

```bash
# 激活虚拟环境后
python main.py
```

按提示输入 BV 号即可。

### 命令行模式

```bash
# 完整流程：下载 → 转录
python main.py BV1xx411c7mD

# 只下载第 1P
python main.py BV1xx411c7mD --page 1

# 下载第 1 到 3 P
python main.py BV1xx411c7mD --page 1-3

# 查看视频信息（不下载）
python main.py --info BV1xx411c7mD

# 只下载视频，不转录
python main.py --download BV1xx411c7mD

# 使用 medium 模型（更准确但更慢）
python main.py BV1xx411c7mD --model medium

# 只转录已有视频
python main.py --transcribe downloads/video/BV1xx411c7mD

# 检查环境
python main.py --check
```

### 分段下载说明

如果视频有多个分P（多集），工具会：
1. 自动检测分P数量
2. 逐个下载每个分P
3. 每个分P独立转录
4. 分别保存文案文件

## 配置 ⚙️

编辑 `config.env` 文件进行配置：

```env
# Whisper 模型大小
WHISPER_MODEL=small

# 计算设备 (auto/cpu/cuda)
WHISPER_DEVICE=auto

# 音频分割长度（秒）
SLICE_LENGTH=45

# B站 Cookie（可选，下载更高清视频）
# BILIBILI_COOKIE=your_cookie_here
```

### Whisper 模型选择

| 模型 | 大小 | 速度 | 准确度 | 显存需求 |
|------|------|------|--------|----------|
| tiny | 39M | ⚡⚡⚡ | ★★ | ~1GB |
| base | 74M | ⚡⚡⚡ | ★★★ | ~1GB |
| small | 244M | ⚡⚡ | ★★★★ | ~2GB |
| medium | 769M | ⚡ | ★★★★★ | ~5GB |
| large | 1550M | 🐌 | ★★★★★+ | ~10GB |

推荐：日常使用 `small`，追求准确度用 `medium`。

## 项目结构 📁

```
bili2text-new/
├── .env/                  # Python 虚拟环境
├── config.env             # 配置文件
├── config.py              # 配置加载
├── main.py                # 主程序入口
├── downloader.py          # 视频下载模块 (yt-dlp)
├── audio_processor.py     # 音频处理模块 (ffmpeg)
├── transcriber.py         # 语音转文字模块 (faster-whisper)
├── requirements.txt       # 依赖列表
├── .gitignore
└── README.md
├── downloads/             # 下载目录（自动创建）
│   ├── video/             # 视频文件
│   ├── audio/             # 提取的音频
│   └── temp/              # 临时文件
└── outputs/               # 文案输出（自动创建）
```

## 常见问题 ❓

### Q: 下载失败怎么办？
A: yt-dlp 会自动处理大部分情况。如果下载高清视频失败，可以尝试在 `config.env` 中设置 BILIBILI_COOKIE。

### Q: 转录速度太慢？
A: 尝试使用更小的模型（tiny/base），或确保有 NVIDIA GPU 并安装 CUDA。

### Q: ffmpeg 未找到？
A: 确保已安装 ffmpeg 并添加到系统 PATH。运行 `python main.py --check` 检查环境。

### Q: 中文转录效果不好？
A: 使用 `medium` 或 `large` 模型可以显著提高中文转录准确度。

## 许可证 📄

MIT License

## 使用须知 🖥️

**用户在使用本工具时，必须遵守用户所在地区的相关版权法律和规定。请确保您有权利下载和转换的视频内容，尊重创作者的劳动成果。**

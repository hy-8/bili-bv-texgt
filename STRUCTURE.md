# 项目结构

## 目录树

```
bili2text-new/
│
├── main.py                  # 主程序入口（CLI + 交互模式）
├── config.py                # 配置加载（默认值 + config.env 合并）
├── config.env               # 用户配置文件
├── downloader.py            # 视频下载模块（yt-dlp）
├── audio_processor.py       # 音频处理模块（ffmpeg 提取 + 分割）
├── transcriber.py           # 语音转文字模块（faster-whisper）
├── subtitle_fetcher.py      # 字幕获取模块（B站API直接获取CC/AI字幕）
├── requirements.txt         # Python 依赖列表
├── start.bat                # Windows 一键启动脚本
├── export_cookies.bat       # Cookie 导出辅助脚本
├── .gitignore
├── README.md
├── STRUCTURE.md             # 本文件
│
├── .env/                    # Python 虚拟环境（不入库）
│
├── downloads/               # 下载目录（自动创建）
│   ├── video/               #   视频文件（按BV号建子目录）
│   │   └── BV1xx411c7mD/
│   │       └── 视频标题.mp4
│   ├── audio/               #   提取的音频（MP3）
│   │   └── BV1xx411c7mD.mp3
│   └── temp/                #   临时文件（音频切片）
│       └── BV1xx411c7mD/
│           └── slices/
│               ├── 1.mp3
│               ├── 2.mp3
│               └── ...
│
├── models/                  # Whisper 模型缓存（不入库）
│   └── models--Systran--faster-whisper-small/
│       └── snapshots/
│           └── <hash>/
│               ├── model.bin
│               ├── tokenizer.json
│               └── ...
│
└── outputs/                 # 文案输出目录
    ├── BV1xx411c7mD.txt
    └── BV1xx411c7mD_P2.txt
```

## 模块说明

### main.py — 主程序入口

- `interactive_mode()` — 交互式引导（输入BV号 → 检查字幕 → 选择模式 → 下载/转录）
- `cmd_full()` — 命令行完整流程（下载 → 音频 → 转录）
- `cmd_info()` — 仅查看视频信息
- `cmd_download()` — 仅下载视频
- `cmd_transcribe()` — 仅转录已有视频
- `cmd_subtitle()` — 直接获取字幕文案
- `parse_pages()` — 解析分P参数（支持 `1,3,5` 和 `1-3` 格式）
- `_normalize_bv()` — 从链接中提取BV号

### config.py — 配置管理

- `DEFAULT_CONFIG` — 默认配置字典
- `_parse_env_file()` — 解析 config.env 文件
- `get_config()` — 返回合并后的配置（默认 + 文件覆盖）
- `reset_config()` — 清除配置缓存

**配置项：**

| 键 | 默认值 | 说明 |
|---|---|---|
| `VIDEO_DIR` | `downloads/video` | 视频下载目录 |
| `AUDIO_DIR` | `downloads/audio` | 音频输出目录 |
| `OUTPUT_DIR` | `outputs` | 文案输出目录 |
| `TEMP_DIR` | `downloads/temp` | 临时文件目录 |
| `MODEL_DIR` | `models` | Whisper 模型缓存目录 |
| `WHISPER_MODEL` | `small` | 默认模型大小 |
| `WHISPER_DEVICE` | `auto` | 计算设备（auto/cpu/cuda） |
| `WHISPER_COMPUTE_TYPE` | `auto` | 计算精度（auto/float16/int8） |
| `SLICE_LENGTH` | `45` | 音频分割秒数 |
| `BILIBILI_COOKIE` | `""` | B站 Cookie |

### downloader.py — 视频下载

- `get_video_info()` — 获取视频元信息（标题、时长、分P数）
- `download_video()` — 下载单个/指定P的视频
- `download_all_pages()` — 下载所有分P
- `_build_ydl_opts()` — 构建 yt-dlp 选项（含 Cookie 支持）
- `_find_ffmpeg_location()` — 查找 ffmpeg 路径
- `_ensure_ffmpeg_path()` — 确保 ffmpeg 在 PATH 中

**Cookie 优先级：** `cookies.txt` 文件 > `config.env` 中的 `BILIBILI_COOKIE`

### audio_processor.py — 音频处理

- `extract_audio()` — 从视频提取音频为 MP3（高质量 -q:a 2）
- `split_audio()` — 按时长分割音频（默认 45 秒/段）
- `process_audio()` — 完整流程：提取 + 分割
- `find_audio_source()` — 自动查找目录中的音频源
- `probe_audio_streams()` — 检测文件的音视频流

### transcriber.py — 语音转文字

- `load_model()` — 加载 faster-whisper 模型（支持 CUDA 自动检测 + 回退 CPU）
- `transcribe_file()` — 转录单个音频文件
- `transcribe_directory()` — 批量转录目录下所有音频片段
- `transcribe_and_save()` — 转录并保存为文本文件
- `_setup_cuda_path()` — 自动添加 pip 安装的 NVIDIA CUDA DLL 路径
- `_get_device()` — 自动检测 CUDA 可用性
- `_get_compute_type()` — 根据设备选择计算精度

**GPU 支持流程：**
1. `_setup_cuda_path()` 在模块加载时将 `nvidia-cublas-cu12` 等 pip 包的 DLL 加入搜索路径
2. `_get_device()` 通过 ctranslate2 或 PyTorch 检测 CUDA
3. `load_model()` 如果 CUDA 加载失败自动回退 CPU + int8

### subtitle_fetcher.py — 字幕获取

- `fetch_subtitles()` — 获取视频所有分P的字幕
- `get_video_pages()` — 获取分P信息（cid 列表）
- `get_subtitle_info()` — 获取单P的字幕列表
- `get_subtitle_text()` — 下载并解析字幕 JSON → 纯文本
- `save_subtitles()` — 保存字幕为文本文件
- `_get_cookie_headers()` — 构建带 Cookie 的请求头

**字幕优先级：** zh-CN > zh-Hans > zh > en > en-US

## 数据流

```
BV号输入
  │
  ├─ 有字幕？── 是 ──→ B站API获取字幕 ──→ 保存为 .txt
  │
  └─ 无字幕 ──→ yt-dlp 下载视频
                  │
                  └─ ffmpeg 提取音频 (MP3)
                      │
                      └─ ffmpeg 分割音频 (45s/段)
                          │
                          └─ faster-whisper 逐段转录
                              │
                              └─ 拼接文本 → 保存为 .txt
```

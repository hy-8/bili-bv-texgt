"""
音频处理模块 - 使用 ffmpeg 提取和分割音频

支持:
- 从视频中提取音频为 MP3
- 按时长分割音频
- 自动检测音频流
"""

import os
import glob
import subprocess
import shutil
from config import get_config


def _find_ffmpeg() -> str:
    """查找系统中的 ffmpeg"""
    # 1. 直接在 PATH 中找
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    # 2. 常见的安装路径
    common_paths = [
        r"D:\tools\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe",
        r"D:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        os.path.expanduser(r"~\scoop\apps\ffmpeg\current\bin\ffmpeg.exe"),
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    raise FileNotFoundError(
        "未找到 ffmpeg！请安装 ffmpeg 并添加到 PATH。\n"
        "下载地址: https://www.gyan.dev/ffmpeg/builds/\n"
        "或使用: winget install ffmpeg\n"
        "或使用: scoop install ffmpeg"
    )


def _run_ffmpeg(args: list, check: bool = True) -> subprocess.CompletedProcess:
    """执行 ffmpeg 命令"""
    ffmpeg_path = _find_ffmpeg()
    cmd = [ffmpeg_path] + args
    return subprocess.run(
        cmd,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )


def probe_audio_streams(file_path: str) -> dict:
    """检测文件中的音视频流"""
    result = _run_ffmpeg(["-i", file_path], check=False)
    stderr = result.stderr or ""
    return {
        "has_audio": "Audio:" in stderr,
        "has_video": "Video:" in stderr,
    }


def find_audio_source(video_dir: str) -> str:
    """
    在下载目录中查找包含音频的媒体文件

    Args:
        video_dir: 视频下载目录

    Returns:
        第一个包含音频流的文件路径
    """
    if not os.path.isdir(video_dir):
        # 可能是直接文件路径
        if os.path.isfile(video_dir) and video_dir.endswith(".mp4"):
            streams = probe_audio_streams(video_dir)
            if streams["has_audio"]:
                return video_dir
        raise FileNotFoundError(f"目录或文件不存在: {video_dir}")

    # 支持的媒体格式
    media_exts = (".mp4", ".flv", ".mkv", ".avi", ".m4a", ".aac", ".mp3", ".wav", ".webm")
    media_files = []
    for file in os.listdir(video_dir):
        if file.lower().endswith(media_exts):
            media_files.append(os.path.join(video_dir, file))

    if not media_files:
        raise FileNotFoundError(f"未找到媒体文件: {video_dir}")

    # 优先选纯音频，其次选含音频的视频
    audio_only = []
    audio_video = []
    for fp in sorted(media_files):
        streams = probe_audio_streams(fp)
        if streams["has_audio"] and not streams["has_video"]:
            audio_only.append(fp)
        elif streams["has_audio"]:
            audio_video.append(fp)

    if audio_only:
        return audio_only[0]
    if audio_video:
        return audio_video[0]

    raise FileNotFoundError(f"未找到含音频流的文件: {video_dir}")


def extract_audio(video_dir: str, output_name: str = None) -> str:
    """
    从视频中提取音频为 MP3

    Args:
        video_dir: 视频下载目录
        output_name: 输出文件名（不含扩展名），默认使用时间戳

    Returns:
        输出的 MP3 文件路径
    """
    import time

    config = get_config()
    audio_dir = config["AUDIO_DIR"]
    os.makedirs(audio_dir, exist_ok=True)

    source = find_audio_source(video_dir)
    print(f"[音频] 源文件: {source}")

    if output_name is None:
        output_name = time.strftime("%Y%m%d_%H%M%S")

    output_path = os.path.join(audio_dir, f"{output_name}.mp3")

    print(f"[音频] 正在提取音频到: {output_path}")
    _run_ffmpeg([
        "-y",
        "-i", source,
        "-vn",                    # 不要视频
        "-acodec", "libmp3lame",  # MP3 编码
        "-q:a", "2",              # 高质量
        output_path,
    ])
    print(f"[音频] 提取完成")

    return output_path


def split_audio(mp3_path: str, folder_name: str = None, slice_length: int = None) -> str:
    """
    将音频文件按指定时长分割

    Args:
        mp3_path: 输入的 MP3 文件路径
        folder_name: 分割文件的文件夹名，默认使用输入文件名
        slice_length: 每段时长（秒），默认从配置读取

    Returns:
        分割文件所在目录路径
    """
    config = get_config()

    if slice_length is None:
        slice_length = config["SLICE_LENGTH"]

    if folder_name is None:
        folder_name = os.path.splitext(os.path.basename(mp3_path))[0]

    target_dir = os.path.join(config["TEMP_DIR"], folder_name, "slices")
    os.makedirs(target_dir, exist_ok=True)

    # 临时文件名模板
    temp_pattern = os.path.join(target_dir, "%03d.mp3")

    print(f"[分割] 正在分割音频，每段 {slice_length} 秒...")
    _run_ffmpeg([
        "-y",
        "-i", mp3_path,
        "-f", "segment",
        "-segment_time", str(slice_length),
        "-q:a", "0",
        temp_pattern,
    ])

    # 重命名为序号
    generated = sorted(glob.glob(os.path.join(target_dir, "*.mp3")))
    for idx, fp in enumerate(generated, start=1):
        final_path = os.path.join(target_dir, f"{idx}.mp3")
        if os.path.abspath(fp) != os.path.abspath(final_path):
            os.replace(fp, final_path)

    print(f"[分割] 分割完成，共 {len(generated)} 段")
    return target_dir


def process_audio(video_dir: str, output_name: str = None) -> str:
    """
    完整的音频处理流程：提取 + 分割

    Args:
        video_dir: 视频下载目录
        output_name: 输出文件名

    Returns:
        分割后的音频目录路径
    """
    import time

    if output_name is None:
        output_name = time.strftime("%Y%m%d_%H%M%S")

    mp3_path = extract_audio(video_dir, output_name)
    slice_dir = split_audio(mp3_path, output_name)
    return slice_dir


if __name__ == "__main__":
    # 测试
    path = input("输入视频目录: ")
    result = process_audio(path)
    print(f"分割结果: {result}")

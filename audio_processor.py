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


def _is_decodable_audio(file_path: str) -> bool:
    """Return True when ffmpeg can decode at least one audio stream."""
    if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 0:
        return False

    result = _run_ffmpeg([
        "-v", "error",
        "-i", file_path,
        "-map", "0:a:0",
        "-f", "null",
        "-",
    ], check=False)
    return result.returncode == 0


def _rebuild_slice(mp3_path: str, output_path: str, start_time: int, slice_length: int) -> None:
    """Rebuild one slice directly from the source audio."""
    _run_ffmpeg([
        "-y",
        "-i", mp3_path,
        "-ss", str(start_time),
        "-t", str(slice_length),
        "-vn",
        "-map", "0:a:0",
        "-acodec", "libmp3lame",
        "-q:a", "0",
        output_path,
    ])


def _media_sort_key(file_path: str):
    """按分P序号和文件名排序，保证多P视频按 p01/p02 或 1/2 顺序合并。"""
    import re

    name = os.path.basename(file_path)
    match = re.search(r"(?:^|[\s_-])[pP]?(\d{1,4})(?:[\s._-]|$)", name)
    if match:
        return (int(match.group(1)), name)
    return (10**9, name)


def find_audio_sources(video_dir: str) -> list:
    """
    在下载目录中查找所有包含音频的媒体文件

    Args:
        video_dir: 视频下载目录

    Returns:
        包含音频流的文件路径列表
    """
    # 支持的媒体格式
    media_exts = (".mp4", ".flv", ".mkv", ".avi", ".m4a", ".aac", ".mp3", ".wav", ".webm", ".mov", ".wmv", ".ts")

    if not os.path.isdir(video_dir):
        # 可能是直接文件路径
        if os.path.isfile(video_dir) and video_dir.lower().endswith(media_exts):
            streams = probe_audio_streams(video_dir)
            if streams["has_audio"]:
                return [video_dir]
        raise FileNotFoundError(f"目录或文件不存在: {video_dir}")

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
        return sorted(audio_only, key=_media_sort_key)
    if audio_video:
        return sorted(audio_video, key=_media_sort_key)

    raise FileNotFoundError(f"未找到含音频流的文件: {video_dir}")


def find_audio_source(video_dir: str) -> str:
    """在下载目录中查找第一个包含音频的媒体文件。"""
    return find_audio_sources(video_dir)[0]


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

    sources = find_audio_sources(video_dir)
    print(f"[音频] 共找到 {len(sources)} 个音频源")
    for idx, source in enumerate(sources, start=1):
        print(f"  P{idx}: {source}")

    if output_name is None:
        output_name = time.strftime("%Y%m%d_%H%M%S")

    output_path = os.path.join(audio_dir, f"{output_name}.mp3")

    print(f"[音频] 正在提取音频到: {output_path}")
    if len(sources) == 1:
        _run_ffmpeg([
            "-y",
            "-i", sources[0],
            "-vn",                    # 不要视频
            "-acodec", "libmp3lame",  # MP3 编码
            "-q:a", "2",              # 高质量
            output_path,
        ])
    else:
        concat_list = os.path.join(config["TEMP_DIR"], f"{output_name}_concat.txt")
        os.makedirs(os.path.dirname(concat_list), exist_ok=True)
        with open(concat_list, "w", encoding="utf-8") as f:
            for source in sources:
                safe_path = os.path.abspath(source).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")
        try:
            _run_ffmpeg([
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list,
                "-vn",
                "-acodec", "libmp3lame",
                "-q:a", "2",
                output_path,
            ])
        finally:
            if os.path.exists(concat_list):
                os.remove(concat_list)
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
    for old_file in glob.glob(os.path.join(target_dir, "*.mp3")):
        os.remove(old_file)

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
        if not _is_decodable_audio(final_path):
            print(f"[Split] Rebuilding invalid slice: {idx}.mp3")
            _rebuild_slice(mp3_path, final_path, (idx - 1) * slice_length, slice_length)
            if not _is_decodable_audio(final_path):
                raise RuntimeError(f"Failed to rebuild invalid audio slice: {final_path}")

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

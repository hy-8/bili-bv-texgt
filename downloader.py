"""
视频下载模块 - 使用 yt-dlp 下载B站视频

支持:
- BV号下载
- 多P视频分段下载
- 自动提取视频标题
- Cookie 支持（更高清画质）
"""

import os
import re
import json
import sys
import yt_dlp
from config import get_config


def _find_ffmpeg_location() -> str:
    """找到 ffmpeg 所在目录，供 yt-dlp 使用"""
    import shutil
    # 先从 PATH 找
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return os.path.dirname(ffmpeg)
    # 从已知路径找
    common_paths = [
        r"D:\tools\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe",
        r"D:\tools\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return os.path.dirname(p)
    return ""


def _ensure_ffmpeg_path():
    """确保 yt-dlp 能找到 ffmpeg"""
    import shutil
    if shutil.which("ffmpeg"):
        return
    # 当前 PATH 中没有 ffmpeg，手动添加已知路径
    ffmpeg_dirs = [
        r"D:\tools\ffmpeg-8.1-essentials_build\bin",
        r"D:\tools\ffmpeg\bin",
        r"C:\ffmpeg\bin",
    ]
    for d in ffmpeg_dirs:
        if os.path.exists(os.path.join(d, "ffmpeg.exe")):
            current_path = os.environ.get("PATH", "")
            if d not in current_path:
                os.environ["PATH"] = d + os.pathsep + current_path
            return


def _build_ydl_opts(output_dir: str, cookie: str = None) -> dict:
    """构建 yt-dlp 选项"""
    _ensure_ffmpeg_path()
    ffmpeg_loc = _find_ffmpeg_location()

    opts = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        # 优先尝试合并最佳视频+音频，不行则下载最佳预合并格式
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        # 进度钩子
        "progress_hooks": [_download_progress_hook],
    }

    # 告诉 yt-dlp ffmpeg 在哪里
    if ffmpeg_loc:
        opts["ffmpeg_location"] = ffmpeg_loc

    if cookie:
        opts["cookiefile"] = None
        opts["http_headers"] = {"Cookie": cookie}

    return opts


def _download_progress_hook(d):
    """下载进度回调"""
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "N/A")
        speed = d.get("_speed_str", "N/A")
        eta = d.get("_eta_str", "N/A")
        sys.stdout.write(f"\r  下载进度: {percent} | 速度: {speed} | 剩余: {eta}   ")
        sys.stdout.flush()
    elif d["status"] == "finished":
        sys.stdout.write("\r  下载完成，正在合并...                    \n")
        sys.stdout.flush()


def _normalize_bv(bv_input: str) -> str:
    """标准化BV号"""
    bv_input = bv_input.strip()
    # 如果是完整链接，提取BV号
    pattern = r"(BV[A-Za-z0-9]+)"
    match = re.search(pattern, bv_input)
    if match:
        return match.group(1)
    # 如果只是数字部分
    if not bv_input.upper().startswith("BV"):
        return "BV" + bv_input
    return bv_input


def get_video_info(bv_input: str) -> dict:
    """获取视频信息（不下载）"""
    bv = _normalize_bv(bv_input)
    url = f"https://www.bilibili.com/video/{bv}"
    config = get_config()

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    cookie = config.get("BILIBILI_COOKIE", "")
    if cookie:
        opts["http_headers"] = {"Cookie": cookie}

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "bv": bv,
            "title": info.get("title", "未知标题"),
            "duration": info.get("duration", 0),
            "pages": info.get("n_entries", 1),
            "description": info.get("description", ""),
            "uploader": info.get("uploader", ""),
        }


def download_video(bv_input: str, page: int = None) -> str:
    """
    下载B站视频

    Args:
        bv_input: BV号 或 完整B站链接
        page: 指定下载的分P号（None=全部下载）

    Returns:
        下载目录路径
    """
    bv = _normalize_bv(bv_input)
    url = f"https://www.bilibili.com/video/{bv}"
    config = get_config()

    # 创建以BV号命名的下载目录
    output_dir = os.path.join(config["VIDEO_DIR"], bv)
    os.makedirs(output_dir, exist_ok=True)

    # 如果指定了分P，URL加上 ?p=xx
    if page is not None:
        url = f"{url}?p={page}"

    cookie = config.get("BILIBILI_COOKIE", "")
    opts = _build_ydl_opts(output_dir, cookie)

    print(f"[下载] 正在下载: {bv}" + (f" P{page}" if page else ""))
    print(f"[下载] 保存到: {output_dir}")

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    print(f"[下载] 下载完成: {output_dir}")
    return output_dir


def download_all_pages(bv_input: str) -> list:
    """
    下载视频的所有分P（分段下载）

    Args:
        bv_input: BV号

    Returns:
        所有下载目录路径列表
    """
    bv = _normalize_bv(bv_input)
    info = get_video_info(bv)
    total_pages = info["pages"]

    print(f"[信息] 视频标题: {info['title']}")
    print(f"[信息] 共 {total_pages} 个分P")

    if total_pages <= 1:
        path = download_video(bv)
        return [path]

    results = []
    for page in range(1, total_pages + 1):
        print(f"\n{'='*50}")
        print(f"[下载] 正在下载第 {page}/{total_pages} P")
        print(f"{'='*50}")
        path = download_video(bv, page=page)
        results.append(path)

    print(f"\n[完成] 全部 {total_pages} 个分P下载完成！")
    return results


if __name__ == "__main__":
    # 测试
    bv = input("请输入BV号: ")
    info = get_video_info(bv)
    print(json.dumps(info, ensure_ascii=False, indent=2))

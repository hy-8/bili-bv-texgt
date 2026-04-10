"""
字幕获取模块 - 通过B站API直接获取视频字幕/文案

不需要下载视频，直接获取B站自带的字幕（CC字幕/AI字幕）
支持：
- 自动获取视频所有分P的字幕
- 支持中文/英文字幕
- 无需登录即可获取公开字幕
- 需要 Cookie 获取部分视频的字幕信息
"""

import os
import re
import json
import urllib.request
import urllib.parse
from config import get_config


def _normalize_bv(bv_input: str) -> str:
    """标准化BV号"""
    bv_input = bv_input.strip()
    pattern = r"(BV[A-Za-z0-9]+)"
    match = re.search(pattern, bv_input)
    if match:
        return match.group(1)
    if not bv_input.upper().startswith("BV"):
        return "BV" + bv_input
    return bv_input


def _get_cookie_headers() -> dict:
    """获取请求头（含Cookie）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
    }
    config = get_config()
    cookie = config.get("BILIBILI_COOKIE", "")
    cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

    if os.path.exists(cookie_file):
        # 从 cookies.txt 读取
        cookies = {}
        with open(cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        if cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
    elif cookie:
        headers["Cookie"] = cookie

    return headers


def _api_request(url: str) -> dict:
    """发送API请求"""
    headers = _get_cookie_headers()
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_video_pages(bv: str) -> list:
    """
    获取视频分P信息

    Returns:
        [{"cid": 123, "page": 1, "title": "标题"}, ...]
    """
    bv = _normalize_bv(bv)
    url = f"https://api.bilibili.com/x/player/pagelist?bvid={bv}"
    data = _api_request(url)

    if data.get("code") != 0:
        raise RuntimeError(f"获取分P信息失败: {data.get('message', '未知错误')}")

    pages = []
    for item in data.get("data", []):
        pages.append({
            "cid": item["cid"],
            "page": item["page"],
            "title": item["part"],
        })
    return pages


def get_subtitle_info(bv: str, cid: int) -> list:
    """
    获取字幕列表信息

    Returns:
        [{"id": 123, "lan": "zh-CN", "lan_doc": "中文（中国）", "subtitle_url": "..."}, ...]
    """
    bv = _normalize_bv(bv)
    url = f"https://api.bilibili.com/x/player/v2?bvid={bv}&cid={cid}"
    data = _api_request(url)

    if data.get("code") != 0:
        raise RuntimeError(f"获取字幕信息失败: {data.get('message', '未知错误')}")

    subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
    return subtitles


def get_subtitle_text(subtitle_url: str) -> str:
    """
    下载字幕内容并转为纯文本

    Args:
        subtitle_url: 字幕URL（可能是相对路径）

    Returns:
        字幕纯文本
    """
    # 补全URL
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    elif not subtitle_url.startswith("http"):
        subtitle_url = "https://aisubtitle.hdslb.com" + subtitle_url

    headers = _get_cookie_headers()
    req = urllib.request.Request(subtitle_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        subtitle_data = json.loads(resp.read().decode("utf-8"))

    # 解析字幕 JSON，格式: {"body": [{"from": 0.0, "to": 1.0, "content": "文本"}, ...]}
    text_parts = []
    for item in subtitle_data.get("body", []):
        content = item.get("content", "").strip()
        if content:
            text_parts.append(content)

    return "\n".join(text_parts)


def fetch_subtitles(bv_input: str) -> dict:
    """
    获取视频的所有字幕

    Args:
        bv_input: BV号

    Returns:
        {
            "has_subtitle": True/False,
            "subtitles": {
                "P1_标题": {"zh-CN": "字幕文本", "en": "..."},
                ...
            },
            "pages": [{"cid": ..., "page": 1, "title": "..."}],
        }
    """
    bv = _normalize_bv(bv_input)

    # 1. 获取分P信息
    pages = get_video_pages(bv)
    if not pages:
        raise RuntimeError("未找到视频分P信息")

    result = {
        "has_subtitle": False,
        "subtitles": {},
        "pages": pages,
    }

    # 2. 逐P获取字幕
    for page_info in pages:
        cid = page_info["cid"]
        page_num = page_info["page"]
        page_title = page_info["title"]
        key = f"P{page_num}_{page_title}" if len(pages) > 1 else page_title

        try:
            subtitle_info = get_subtitle_info(bv, cid)
        except Exception as e:
            print(f"  [字幕] P{page_num} 获取字幕信息失败: {e}")
            continue

        if not subtitle_info:
            print(f"  [字幕] P{page_num} 无字幕")
            continue

        page_subtitles = {}
        for sub in subtitle_info:
            lan = sub.get("lan", "")
            lan_doc = sub.get("lan_doc", lan)
            sub_url = sub.get("subtitle_url", "")

            if not sub_url:
                continue

            print(f"  [字幕] P{page_num} 正在获取: {lan_doc}")
            try:
                text = get_subtitle_text(sub_url)
                if text.strip():
                    page_subtitles[lan] = text
                    result["has_subtitle"] = True
            except Exception as e:
                print(f"  [字幕] P{page_num} 获取 {lan_doc} 失败: {e}")

        if page_subtitles:
            result["subtitles"][key] = page_subtitles

    return result


def save_subtitles(subtitles_data: dict, output_name: str) -> str:
    """
    将字幕保存为文本文件

    Args:
        subtitles_data: fetch_subtitles 返回的数据
        output_name: 输出文件名（不含扩展名）

    Returns:
        保存的文件路径
    """
    config = get_config()
    output_dir = config["OUTPUT_DIR"]
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, f"{output_name}.txt")

    lines = []
    for page_key, lang_subtitles in subtitles_data["subtitles"].items():
        if len(subtitles_data["subtitles"]) > 1:
            lines.append(f"{'='*40}")
            lines.append(f"{page_key}")
            lines.append(f"{'='*40}")

        # 优先中文，然后英文，然后其他
        for lan in ["zh-CN", "zh-Hans", "zh", "en", "en-US"]:
            if lan in lang_subtitles:
                lines.append(lang_subtitles[lan])
                lines.append("")  # 空行分隔
                break
        else:
            # 取第一个可用的
            for text in lang_subtitles.values():
                lines.append(text)
                lines.append("")
                break

    text = "\n".join(lines).strip()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    return output_path

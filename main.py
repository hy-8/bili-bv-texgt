"""
bili2text-new 主程序

B站视频下载与文案提取工具

用法:
    # 激活虚拟环境后
    python main.py BV1xx411c7mD
    python main.py BV1xx411c7mD --pages 1,3
    python main.py BV1xx411c7mD --model medium
    python main.py --info BV1xx411c7mD
"""

import argparse
import json
import os
import sys
import time

from config import get_config, reset_config


def check_ffmpeg():
    """检查 ffmpeg 是否可用"""
    try:
        from audio_processor import _find_ffmpeg
        ffmpeg = _find_ffmpeg()
        print(f"[环境] ffmpeg: {ffmpeg}")
        return True
    except FileNotFoundError as e:
        print(f"[错误] {e}")
        return False


def cmd_info(args):
    """查询视频信息"""
    from downloader import get_video_info

    info = get_video_info(args.bv)
    print(f"\n{'='*50}")
    print(f"  标题: {info['title']}")
    print(f"  UP主: {info['uploader']}")
    print(f"  时长: {info['duration']:.0f} 秒 ({info['duration']/60:.1f} 分钟)")
    print(f"  分P数: {info['pages']}")
    if info['description']:
        desc = info['description'][:200]
        print(f"  简介: {desc}{'...' if len(info['description']) > 200 else ''}")
    print(f"{'='*50}")


def cmd_download(args):
    """仅下载视频"""
    from downloader import download_video, download_all_pages

    if args.page:
        # 下载指定分P
        for p in args.page:
            download_video(args.bv, page=p)
    else:
        download_all_pages(args.bv)


def cmd_transcribe(args):
    """仅转录音频（从已有的视频目录）"""
    from audio_processor import process_audio
    from transcriber import load_model, transcribe_and_save

    config = get_config()
    video_dir = args.transcribe

    if not os.path.isdir(video_dir):
        print(f"[错误] 目录不存在: {video_dir}")
        sys.exit(1)

    model_name = args.model or config.get("WHISPER_MODEL", "medium")
    load_model(model_name)

    output_name = os.path.basename(video_dir)
    slice_dir = process_audio(video_dir, output_name)

    prompt = args.prompt or "以下是普通话的句子。"
    output_path = transcribe_and_save(slice_dir, output_name, prompt=prompt)
    print(f"\n[完成] 文案保存到: {output_path}")


def cmd_subtitle(args):
    """直接获取视频字幕（不下载视频）"""
    from subtitle_fetcher import fetch_subtitles, save_subtitles

    bv = _normalize_bv(args.bv)
    print(f"[字幕] 正在获取 {bv} 的字幕...")

    try:
        sub_data = fetch_subtitles(bv)
    except Exception as e:
        print(f"[错误] 获取字幕失败: {e}")
        sys.exit(1)

    if not sub_data["has_subtitle"]:
        print("[提示] 该视频没有字幕，需要下载视频进行语音识别")
        print("       请去掉 --subtitle 参数重新运行")
        sys.exit(1)

    output_path = save_subtitles(sub_data, bv)
    print(f"\n{'='*50}")
    print(f"文案已保存到: {output_path}")

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
        if content.strip():
            print(f"\n--- 文案预览 ---")
            print(content[:500])
            if len(content) > 500:
                print("...(更多内容请查看文件)")
    print(f"{'='*50}")


def cmd_full(args):
    """完整流程：下载 → 提取音频 → 转录"""
    from downloader import download_video, download_all_pages, get_video_info
    from audio_processor import process_audio
    from transcriber import load_model, transcribe_and_save
    from subtitle_fetcher import fetch_subtitles, save_subtitles

    config = get_config()

    # 1. 获取视频信息
    print("\n[步骤 1/4] 获取视频信息...")
    info = get_video_info(args.bv)
    print(f"  标题: {info['title']}")
    print(f"  分P数: {info['pages']}")

    # 2. 下载视频
    print(f"\n[步骤 2/4] 下载视频...")
    video_dirs = []
    try:
        if args.page:
            for p in args.page:
                path = download_video(args.bv, page=p)
                video_dirs.append(path)
        else:
            video_dirs = download_all_pages(args.bv)
    except Exception as e:
        error_msg = str(e)
        print(f"\n[错误] 下载失败: {error_msg}")

        # 尝试字幕兜底
        print(f"\n[字幕] 正在检查视频字幕...")
        try:
            sub_data = fetch_subtitles(args.bv)
            if sub_data["has_subtitle"]:
                print(f"[字幕] 发现字幕！直接获取文案...")
                bv_clean = _normalize_bv(args.bv)
                output_path = save_subtitles(sub_data, bv_clean)
                print(f"\n{'='*50}")
                print(f"文案已保存到: {output_path}")
                print(f"{'='*50}")
                return
        except Exception:
            pass

        print(f"\n[提示] 该视频需要登录才能下载，且无可用字幕。")
        print(f"  请导出 Cookie 后重试（参见 README）")
        sys.exit(1)

    # 3. 加载 Whisper 模型
    print(f"\n[步骤 3/4] 加载语音识别模型...")
    model_name = args.model or config.get("WHISPER_MODEL", "medium")
    load_model(model_name)

    # 4. 处理每个视频
    print(f"\n[步骤 4/4] 提取音频并转录...")
    prompt = args.prompt or f"以下是普通话的句子。这是一个关于{info['title']}的视频。"
    results = []

    for idx, video_dir in enumerate(video_dirs):
        bv = _normalize_bv(args.bv)
        output_name = f"{bv}" + (f"_P{idx+1}" if len(video_dirs) > 1 else "")

        print(f"\n--- 处理 {idx+1}/{len(video_dirs)}: {output_name} ---")

        slice_dir = process_audio(video_dir, output_name)
        output_path = transcribe_and_save(slice_dir, output_name, prompt=prompt)
        results.append(output_path)

    print(f"\n{'='*50}")
    print(f"全部完成！共生成 {len(results)} 个文案文件：")
    for path in results:
        print(f"  → {path}")
    print(f"{'='*50}")


def _normalize_bv(bv_input: str) -> str:
    import re
    bv_input = bv_input.strip()
    pattern = r"(BV[A-Za-z0-9]+)"
    match = re.search(pattern, bv_input)
    if match:
        return match.group(1)
    if not bv_input.upper().startswith("BV"):
        return "BV" + bv_input
    return bv_input


def parse_pages(pages_str: str) -> list:
    """解析分P参数，如 '1,3,5' 或 '1-3'"""
    pages = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start), int(end) + 1))
        else:
            pages.append(int(part))
    return pages


def main():
    parser = argparse.ArgumentParser(
        description="bili2text-new - B站视频下载与文案提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py BV1xx411c7mD              # 完整流程
  python main.py BV1xx411c7mD --page 1     # 只下载第1P
  python main.py BV1xx411c7mD --page 1-3   # 下载第1到3P
  python main.py BV1xx411c7mD --model medium  # 使用medium模型
  python main.py --info BV1xx411c7mD       # 查看视频信息
  python main.py --subtitle BV1xx411c7mD   # 直接获取字幕（不下载视频）
  python main.py --download BV1xx411c7mD   # 仅下载视频
  python main.py --transcribe ./downloads/video/BVxxx  # 仅转录
        """,
    )

    parser.add_argument("bv", nargs="?", help="BV号或B站视频链接")
    parser.add_argument("--info", action="store_true", help="仅查看视频信息")
    parser.add_argument("--download", action="store_true", help="仅下载视频（不转录）")
    parser.add_argument("--transcribe", metavar="VIDEO_DIR", help="仅转录指定目录的视频")
    parser.add_argument("--subtitle", action="store_true", help="直接获取视频字幕（不下载视频）")
    parser.add_argument("--page", type=str, help="指定下载的分P，如 '1' 或 '1,3' 或 '1-3'")
    parser.add_argument("--model", type=str, help="Whisper 模型大小 (tiny/small/medium/large)")
    parser.add_argument("--prompt", type=str, help="Whisper 转录提示词")
    parser.add_argument("--check", action="store_true", help="检查环境依赖")

    args = parser.parse_args()

    # 环境检查
    if args.check:
        print("[环境检查]")
        print(f"  Python: {sys.version}")
        ffmpeg_ok = check_ffmpeg()
        print(f"  ffmpeg: {'OK' if ffmpeg_ok else 'NOT FOUND'}")
        try:
            import faster_whisper
            print(f"  faster-whisper: OK ({faster_whisper.__version__})")
        except ImportError:
            print("  faster-whisper: NOT FOUND")
        try:
            import yt_dlp
            print(f"  yt-dlp: OK ({yt_dlp.version.__version__})")
        except ImportError:
            print("  yt-dlp: NOT FOUND")
        return

    # 查看信息
    if args.info:
        if not args.bv:
            print("[错误] 请提供BV号")
            sys.exit(1)
        cmd_info(args)
        return

    # 仅下载
    if args.download:
        if not args.bv:
            print("[错误] 请提供BV号")
            sys.exit(1)
        if args.page:
            args.page = parse_pages(args.page)
        cmd_download(args)
        return

    # 仅转录
    if args.transcribe:
        cmd_transcribe(args)
        return

    # 直接获取字幕
    if args.subtitle:
        if not args.bv:
            print("[错误] 请提供BV号")
            sys.exit(1)
        cmd_subtitle(args)
        return

    # 完整流程
    if not args.bv:
        # 交互模式
        interactive_mode()
        return

    if args.page:
        args.page = parse_pages(args.page)
    cmd_full(args)


def interactive_mode():
    """交互式模式（支持连续处理多个BV号）"""
    print("=" * 50)
    print("  bili2text-new - B站视频下载与文案提取")
    print("  输入 q 退出")
    print("=" * 50)

    # 检查 ffmpeg
    if not check_ffmpeg():
        print("\n请先安装 ffmpeg 后再运行！")
        sys.exit(1)

    # 预加载依赖
    from downloader import get_video_info, download_video, download_all_pages
    from subtitle_fetcher import fetch_subtitles, save_subtitles
    from audio_processor import process_audio
    from transcriber import load_model, transcribe_and_save

    config = get_config()
    cached_model = None  # 缓存已加载的模型名，避免重复加载

    while True:
        bv = input("\n请输入BV号或B站视频链接（输入 q 退出）: ").strip()
        if not bv:
            print("[错误] BV号不能为空")
            continue
        if bv.lower() == "q":
            print("再见！")
            break

        # 查看信息
        try:
            info = get_video_info(bv)
        except Exception as e:
            print(f"[错误] 获取视频信息失败: {e}")
            continue

        print(f"\n视频信息:")
        print(f"  标题: {info['title']}")
        print(f"  UP主: {info['uploader']}")
        print(f"  时长: {info['duration']:.0f} 秒")
        print(f"  分P数: {info['pages']}")

        # 先检查是否有字幕可以获取
        print(f"\n[检查] 正在检查视频字幕...")
        try:
            sub_data = fetch_subtitles(bv)
        except Exception as e:
            print(f"  [字幕] 检查失败: {e}")
            sub_data = {"has_subtitle": False, "subtitles": {}, "pages": []}

        if sub_data["has_subtitle"]:
            print(f"  [字幕] 发现字幕！可以直接获取视频文案（无需下载视频）")

            choice = input(f"\n选择获取方式:\n  1. 直接获取字幕文案（快速，不需要下载视频）\n  2. 下载视频 + 语音识别（更准确，耗时较长）\n请选择 (1/2，回车=1): ").strip()
            if choice != "2":
                # 直接保存字幕
                bv_clean = _normalize_bv(bv)
                output_path = save_subtitles(sub_data, bv_clean)

                print(f"\n{'='*50}")
                print(f"文案已保存到: {output_path}")

                # 预览
                with open(output_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    preview = content[:500]
                    print(f"\n--- 文案预览 ---")
                    print(preview)
                    if len(content) > 500:
                        print("...(更多内容请查看文件)")
                print(f"{'='*50}")
                continue

        # 没有字幕或用户选择下载视频
        if not sub_data["has_subtitle"]:
            print(f"  [字幕] 该视频没有字幕，需要下载视频进行语音识别")

        # 选择分P
        pages = None
        if info['pages'] > 1:
            page_input = input(f"\n下载哪些分P？(回车=全部, 或输入如 1,3 或 1-3): ").strip()
            if page_input:
                pages = parse_pages(page_input)

        # 选择模型
        model_input = input("\nWhisper 模型 (tiny/small/medium/large，回车=medium): ").strip()
        model = model_input if model_input else "medium"

        # 开始处理
        print(f"\n{'='*50}")
        print("开始处理...")
        print(f"{'='*50}")

        # 下载
        print("\n[步骤 1/3] 下载视频...")
        try:
            if pages:
                video_dirs = []
                for p in pages:
                    path = download_video(bv, page=p)
                    video_dirs.append(path)
            else:
                video_dirs = download_all_pages(bv)
        except Exception as e:
            error_msg = str(e)
            print(f"\n[错误] 下载失败: {error_msg}")

            # 下载失败，如果有字幕就兜底
            if sub_data["has_subtitle"]:
                print(f"\n[提示] 视频下载需要登录，但该视频有字幕，可以直接获取文案！")
                use_sub = input("是否直接获取字幕文案？(y/n，回车=y): ").strip().lower()
                if use_sub != "n":
                    bv_clean = _normalize_bv(bv)
                    output_path = save_subtitles(sub_data, bv_clean)
                    print(f"\n{'='*50}")
                    print(f"文案已保存到: {output_path}")
                    with open(output_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            print(f"\n--- 文案预览 ---")
                            print(content[:500])
                            if len(content) > 500:
                                print("...(更多内容请查看文件)")
                    print(f"{'='*50}")
                    continue

            # 没有字幕，提示用户获取 Cookie
            print(f"\n{'='*50}")
            print("[提示] 该视频需要登录才能下载，解决方法：")
            print("  1. 导出浏览器Cookie到 cookies.txt（推荐）")
            print("     - 安装Chrome插件 'Get cookies.txt LOCALLY'")
            print("     - 打开 bilibili.com 登录后导出cookies")
            print("     - 保存为 cookies.txt 到项目目录")
            print("  2. 在 config.env 中填写 BILIBILI_COOKIE")
            print(f"{'='*50}")
            continue

        # 加载模型（相同模型只加载一次）
        print("\n[步骤 2/3] 加载模型...")
        if cached_model != model:
            load_model(model)
            cached_model = model
        else:
            print(f"  模型 {model} 已加载，跳过重复加载")

        # 转录
        print("\n[步骤 3/3] 提取音频并转录...")
        bv_clean = _normalize_bv(bv)
        prompt = f"以下是普通话的句子。这是一个关于{info['title']}的视频。"
        results = []

        for idx, video_dir in enumerate(video_dirs):
            output_name = f"{bv_clean}" + (f"_P{idx+1}" if len(video_dirs) > 1 else "")
            print(f"\n--- 处理 {idx+1}/{len(video_dirs)}: {output_name} ---")

            slice_dir = process_audio(video_dir, output_name)
            output_path = transcribe_and_save(slice_dir, output_name, prompt=prompt)
            results.append(output_path)

        print(f"\n{'='*50}")
        print(f"全部完成！共生成 {len(results)} 个文案文件：")
        for path in results:
            print(f"  → {path}")

        # 显示文案内容预览
        if results:
            print(f"\n--- 文案预览 ---")
            with open(results[0], "r", encoding="utf-8") as f:
                content = f.read()
                preview = content[:500]
                print(preview)
                if len(content) > 500:
                    print("...(更多内容请查看文件)")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()

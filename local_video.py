"""
本地视频处理模块 - 输入本地视频文件，提取文案并翻译

流程: 提取音频 → 分割 → 语音识别 → 语言检测 → 翻译(如需) → 保存 → 清理

用法:
    from local_video import process_local_video
    process_local_video("C:/videos/my_video.mp4")
"""

import os
import shutil

from config import get_config
from audio_processor import process_audio
from transcriber import load_model, transcribe_directory
from translator import detect_language, translate_to_chinese


def process_local_video(
    video_path: str,
    model_name: str = None,
    language: str = None,
) -> str:
    """
    处理本地视频文件，提取文案并翻译（如需）

    Args:
        video_path: 本地视频文件路径
        model_name: Whisper 模型名称，默认从配置读取
        language: 语言提示 (None=自动检测, "zh"/"ja"/"en")

    Returns:
        输出文本文件路径，失败返回 None
    """
    config = get_config()

    # 1. 验证输入
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    file_size = os.path.getsize(video_path) / (1024 * 1024)
    print(f"\n[本地视频] {video_name}")
    print(f"[本地视频] 路径: {video_path}")
    print(f"[本地视频] 大小: {file_size:.1f} MB")

    # 收集需要清理的临时文件
    temp_paths = []

    try:
        # 2. 提取音频 + 分割（复用 audio_processor 公共路径）
        print(f"\n[步骤 1/3] 提取音频并分割...")
        slice_dir = process_audio(video_path, video_name)
        temp_paths.append(slice_dir)

        # process_audio 还会在 AUDIO_DIR 生成 .mp3 文件
        mp3_path = os.path.join(config["AUDIO_DIR"], f"{video_name}.mp3")
        if os.path.isfile(mp3_path):
            temp_paths.append(mp3_path)

        # 3. 加载模型并转录
        print(f"\n[步骤 2/3] 语音识别...")
        if model_name is None:
            model_name = config.get("WHISPER_MODEL", "medium")
        load_model(model_name)

        lang_prompts = {
            "zh": "以下是普通话的句子。",
            "ja": "以下は日本語の文章です。",
            "en": "The following is an English sentence.",
        }
        prompt = lang_prompts.get(language, "以下是普通话的句子。")

        full_text = transcribe_directory(
            slice_dir, language=language, prompt=prompt
        )

        if not full_text.strip():
            print("[警告] 未识别到任何文字")
            return None

        char_count = len(full_text)
        print(f"  识别到 {char_count} 个字符")
        preview = full_text[:150].replace("\n", " ")
        print(f"  预览: {preview}...")

        # 4. 语言检测与翻译
        print(f"\n[步骤 3/3] 语言检测与翻译...")

        if language in ("ja", "en"):
            detected_lang = language
            print(f"  语言: {detected_lang}（用户指定）")
        else:
            detected_lang = detect_language(full_text)
            print(f"  检测结果: {detected_lang}")

        output_dir = config["OUTPUT_DIR"]
        os.makedirs(output_dir, exist_ok=True)

        if detected_lang in ("ja", "en"):
            print(f"  正在翻译为中文...")
            translated = translate_to_chinese(full_text, detected_lang)

            original_path = os.path.join(output_dir, f"{video_name}_原文.txt")
            with open(original_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            print(f"  原文已保存: {original_path}")

            output_path = os.path.join(output_dir, f"{video_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(translated)
            print(f"  译文已保存: {output_path}")
        else:
            output_path = os.path.join(output_dir, f"{video_name}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            print(f"  文案已保存: {output_path}")

        return output_path

    finally:
        # 5. 清理临时文件（分段音频、提取的 mp3），不碰原视频
        print(f"\n[清理] 删除临时文件...")
        for path in temp_paths:
            if os.path.isfile(path):
                os.remove(path)
                print(f"  删除: {os.path.basename(path)}")
            elif os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                print(f"  删除: {os.path.basename(path)}")
        print(f"[清理] 完成")


if __name__ == "__main__":
    path = input("输入本地视频路径: ")
    result = process_local_video(path)
    if result:
        print(f"\n完成！输出: {result}")

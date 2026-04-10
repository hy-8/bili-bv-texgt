"""
语音转文字模块 - 使用 faster-whisper

支持:
- 多种模型大小
- CPU / CUDA 自动切换
- 中文优化提示
- 批量转录
"""

import os
from config import get_config

_model = None
_loaded_model_name = None


def _get_device() -> str:
    """自动检测最佳设备"""
    config = get_config()
    device = config.get("WHISPER_DEVICE", "auto")

    if device == "auto":
        # 优先用 ctranslate2 检测 CUDA（faster-whisper 自带，无需 PyTorch）
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda"
        except Exception:
            pass
        # 备选：PyTorch
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    return device


def _get_compute_type(device: str) -> str:
    """根据设备选择计算类型"""
    config = get_config()
    compute_type = config.get("WHISPER_COMPUTE_TYPE", "auto")

    if compute_type == "auto":
        return "float16" if device == "cuda" else "int8"

    return compute_type


def load_model(model_name: str = None) -> None:
    """
    加载 faster-whisper 模型

    Args:
        model_name: 模型名称，默认从配置读取
    """
    global _model, _loaded_model_name

    config = get_config()
    if model_name is None:
        model_name = config.get("WHISPER_MODEL", "small")

    if _model is not None and _loaded_model_name == model_name:
        print(f"[Whisper] 模型已加载: {model_name}")
        return

    device = _get_device()
    compute_type = _get_compute_type(device)

    print(f"[Whisper] 正在加载模型: {model_name}")
    print(f"[Whisper] 设备: {device}, 计算类型: {compute_type}")

    from faster_whisper import WhisperModel

    _model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )
    _loaded_model_name = model_name
    print(f"[Whisper] 模型加载完成")


def transcribe_file(audio_path: str, language: str = None, prompt: str = None) -> str:
    """
    转录单个音频文件

    Args:
        audio_path: 音频文件路径
        language: 语言代码 (None=自动检测, "zh"=中文, "en"=英文)
        prompt: 初始提示词

    Returns:
        转录文本
    """
    if _model is None:
        load_model()

    # 根据语言设置默认提示词
    if prompt is None:
        if language == "zh":
            prompt = "以下是普通话的句子。"
        elif language == "en":
            prompt = "The following is an English sentence."
        else:
            prompt = "以下是普通话的句子。"

    transcribe_opts = {
        "initial_prompt": prompt,
        "vad_filter": False,       # 切片音频不需要 VAD，已经分割过了
    }

    # 只在明确指定语言时传入 language，否则让模型自动检测
    if language is not None:
        transcribe_opts["language"] = language

    segments, info = _model.transcribe(audio_path, **transcribe_opts)

    text_parts = []
    for segment in segments:
        text_parts.append(segment.text)

    return "".join(text_parts)


def transcribe_directory(slice_dir: str, language: str = None, prompt: str = None) -> str:
    """
    转录目录下的所有音频文件（按文件名排序）

    Args:
        slice_dir: 音频切片目录
        language: 语言代码
        prompt: 初始提示词

    Returns:
        完整转录文本
    """
    if not os.path.isdir(slice_dir):
        raise FileNotFoundError(f"音频目录不存在: {slice_dir}")

    # 获取所有音频文件并按数字排序
    audio_files = []
    for f in os.listdir(slice_dir):
        if f.lower().endswith((".mp3", ".wav", ".m4a", ".flac")):
            audio_files.append(f)

    # 按文件名中的数字排序
    def sort_key(name):
        base = os.path.splitext(name)[0]
        try:
            return int(base)
        except ValueError:
            return base

    audio_files.sort(key=sort_key)

    if not audio_files:
        raise FileNotFoundError(f"未找到音频文件: {slice_dir}")

    print(f"[转录] 共 {len(audio_files)} 个音频片段待转录")

    full_text = []
    for idx, filename in enumerate(audio_files, start=1):
        filepath = os.path.join(slice_dir, filename)
        print(f"[转录] {idx}/{len(audio_files)}: {filename}")

        text = transcribe_file(filepath, language=language, prompt=prompt)
        if text.strip():
            full_text.append(text.strip())
            # 实时显示转录结果
            print(f"  → {text.strip()[:80]}...")

    return "\n".join(full_text)


def transcribe_and_save(
    slice_dir: str,
    output_name: str,
    language: str = None,
    prompt: str = None,
) -> str:
    """
    转录音频并保存为文本文件

    Args:
        slice_dir: 音频切片目录
        output_name: 输出文件名（不含扩展名）
        language: 语言代码
        prompt: 初始提示词

    Returns:
        输出文本文件路径
    """
    config = get_config()
    output_dir = config["OUTPUT_DIR"]
    os.makedirs(output_dir, exist_ok=True)

    text = transcribe_directory(slice_dir, language=language, prompt=prompt)

    output_path = os.path.join(output_dir, f"{output_name}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"[转录] 文案已保存到: {output_path}")
    return output_path


if __name__ == "__main__":
    # 测试
    model_name = input("模型名称 (small/medium/large): ") or "small"
    load_model(model_name)
    audio = input("音频文件路径: ")
    text = transcribe_file(audio)
    print(f"转录结果:\n{text}")

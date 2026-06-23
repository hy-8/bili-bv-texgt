"""
语音转文字模块 - 使用 faster-whisper

支持:
- 多种模型大小
- CPU / CUDA 自动切换
- 中文优化提示
- 批量转录
"""

import os
import sys
from config import get_config

_model = None
_loaded_model_name = None


def _setup_cuda_path():
    """将 pip 安装的 NVIDIA CUDA 库路径添加到 DLL 搜索路径"""
    try:
        nvidia_base = os.path.join(
            sys.prefix, "Lib", "site-packages", "nvidia"
        )
        if not os.path.isdir(nvidia_base):
            return
        for root, dirs, files in os.walk(nvidia_base):
            if "bin" in root:
                try:
                    os.add_dll_directory(root)
                except Exception:
                    pass
                os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


# 启动时自动配置 CUDA 路径
_setup_cuda_path()

# 禁用 Windows symlinks 警告
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


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

    # 模型缓存目录：优先用配置的 MODEL_DIR，不存在则用项目目录下的 models/
    model_dir = config.get("MODEL_DIR", "models")
    if not os.path.isabs(model_dir):
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_dir)
    os.makedirs(model_dir, exist_ok=True)

    # 检查模型是否已缓存，未缓存时提示下载
    model_repo = f"Systran/faster-whisper-{model_name}"
    snapshot_dir = os.path.join(model_dir, "models--Systran--faster-whisper-" + model_name, "snapshots")
    model_cached = False
    if os.path.isdir(snapshot_dir):
        for sub in os.listdir(snapshot_dir):
            if os.path.isfile(os.path.join(snapshot_dir, sub, "model.bin")):
                model_cached = True
                break

    if not model_cached:
        size_map = {"tiny": "~75MB", "small": "~500MB", "medium": "~1.5GB", "large": "~3GB"}
        est_size = size_map.get(model_name, "~1GB+")
        print(f"[Whisper] 模型未缓存，需要从 HuggingFace 下载 (预计 {est_size})")
        print(f"[Whisper] 下载中，请耐心等待... (首次下载较慢，后续会使用缓存)")

    try:
        _model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=model_dir,
        )
    except RuntimeError as e:
        if device == "cuda" and ("cublas" in str(e).lower() or "cuda" in str(e).lower() or "dll" in str(e).lower()):
            print(f"[Whisper] CUDA 加载失败: {e}")
            print(f"[Whisper] 自动回退到 CPU 模式 (速度较慢但可正常工作)")
            compute_type = "int8"
            _model = WhisperModel(
                model_name,
                device="cpu",
                compute_type=compute_type,
                download_root=model_dir,
            )
        else:
            raise
    _loaded_model_name = model_name
    print(f"[Whisper] 模型加载完成 (缓存: {model_dir})")


def _ensure_decodable_audio(audio_path: str) -> None:
    """Fail early when a slice has no usable audio stream."""
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
    if os.path.getsize(audio_path) <= 0:
        raise RuntimeError(f"Audio file is empty: {audio_path}")

    try:
        import av

        container = av.open(audio_path)
        try:
            if not list(container.streams.audio):
                raise RuntimeError(f"Audio file has no audio stream: {audio_path}")
            frames = container.decode(audio=0)
            try:
                next(frames)
            except StopIteration as exc:
                raise RuntimeError(f"Audio file has no decodable audio frames: {audio_path}") from exc
        finally:
            container.close()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Audio file is not decodable: {audio_path} ({exc})") from exc


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
    _ensure_decodable_audio(audio_path)

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

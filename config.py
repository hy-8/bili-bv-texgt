"""
bili2text-new - B站视频下载与文案提取工具

根据BV号下载B站视频，支持分段下载，提取音频并转写为文字。
"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 默认目录配置
DEFAULT_CONFIG = {
    "VIDEO_DIR": os.path.join(BASE_DIR, "downloads", "video"),
    "AUDIO_DIR": os.path.join(BASE_DIR, "downloads", "audio"),
    "OUTPUT_DIR": os.path.join(BASE_DIR, "outputs"),
    "TEMP_DIR": os.path.join(BASE_DIR, "downloads", "temp"),
    "WHISPER_MODEL": "small",
    "WHISPER_DEVICE": "auto",
    "WHISPER_COMPUTE_TYPE": "auto",
    "SLICE_LENGTH": "45",
    "BILIBILI_COOKIE": "",
}

_config = None


def _parse_env_file(filepath: str) -> dict:
    """解析 .env 格式的配置文件"""
    config = {}
    if not os.path.exists(filepath):
        return config
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # 移除引号
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                config[key] = value
    return config


def get_config() -> dict:
    """获取合并后的配置（默认 + config.env）"""
    global _config
    if _config is not None:
        return _config

    _config = dict(DEFAULT_CONFIG)
    env_path = os.path.join(BASE_DIR, "config.env")
    file_config = _parse_env_file(env_path)
    _config.update(file_config)

    # 确保目录存在
    for key in ("VIDEO_DIR", "AUDIO_DIR", "OUTPUT_DIR", "TEMP_DIR"):
        os.makedirs(_config[key], exist_ok=True)

    # 类型转换
    _config["SLICE_LENGTH"] = int(_config.get("SLICE_LENGTH", 45))

    return _config


def reset_config():
    """重置配置缓存（测试用）"""
    global _config
    _config = None

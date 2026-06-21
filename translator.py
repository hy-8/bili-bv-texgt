"""
翻译模块 - 使用 DeepSeek API 进行语言检测和中译

支持:
- 自动检测日语/英语/中文
- 日译中 / 英译中
- 长文本自动分段翻译
"""

import json
import urllib.request
import urllib.error
from config import get_config

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


def _get_api_key() -> str:
    """获取 DeepSeek API Key"""
    config = get_config()
    return config.get("DEEPSEEK_API_KEY", "")


def _call_deepseek(messages: list, max_tokens: int = 4096) -> str:
    """调用 DeepSeek Chat API"""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 config.env 中设置")

    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        DEEPSEEK_API_URL, data=payload, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"DeepSeek API 请求失败 (HTTP {e.code}): {body}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"DeepSeek API 连接失败: {e.reason}") from e

    return data["choices"][0]["message"]["content"]


def detect_language(text: str) -> str:
    """
    检测文本的主要语言

    Args:
        text: 待检测文本

    Returns:
        'zh' | 'ja' | 'en' | 'other'
    """
    if not text.strip():
        return "other"

    # 取前 800 字符作为样本
    sample = text[:800]

    messages = [
        {
            "role": "system",
            "content": (
                "You are a language detection tool. "
                "Reply with ONLY one word: chinese, japanese, english, or other."
            ),
        },
        {"role": "user", "content": f"Detect the language:\n\n{sample}"},
    ]

    try:
        result = _call_deepseek(messages, max_tokens=20)
        result = result.strip().lower()
    except Exception as e:
        print(f"  [语言检测] 失败: {e}，默认按 other 处理")
        return "other"

    if "chinese" in result or "中文" in result:
        return "zh"
    elif "japanese" in result or "日语" in result or "日文" in result:
        return "ja"
    elif "english" in result or "英文" in result:
        return "en"
    else:
        return "other"


def translate_to_chinese(text: str, source_lang: str = None) -> str:
    """
    将文本翻译为中文（长文本自动分段）

    Args:
        text: 待翻译文本
        source_lang: 源语言代码 ('ja' | 'en')

    Returns:
        中文译文
    """
    if not text.strip():
        return text

    lang_name = {"ja": "Japanese", "en": "English"}.get(source_lang, "the text")

    # 分段处理长文本
    chunks = _split_text(text, chunk_size=2000)

    if len(chunks) == 1:
        return _translate_chunk(chunks[0], lang_name)

    print(f"  [翻译] 文本共 {len(text)} 字符，分 {len(chunks)} 段翻译")
    translated_chunks = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"  [翻译] 第 {i}/{len(chunks)} 段...")
        try:
            translated = _translate_chunk(chunk, lang_name)
            translated_chunks.append(translated)
        except Exception as e:
            print(f"  [翻译] 第 {i} 段失败: {e}")
            translated_chunks.append(f"[翻译失败] {chunk[:100]}...")

    return "\n".join(translated_chunks)


def _split_text(text: str, chunk_size: int = 2000) -> list:
    """将文本按段落分割成不超过 chunk_size 字符的块"""
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        # 单个段落超长，强制按字符分割
        if para_len > chunk_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            for i in range(0, para_len, chunk_size):
                chunks.append(para[i:i + chunk_size])
            continue

        if current_len + para_len > chunk_size and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_len = 0

        current_chunk.append(para)
        current_len += para_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def _translate_chunk(text: str, lang_name: str) -> str:
    """翻译单个文本块"""
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a professional translator. Translate the following {lang_name} "
                "text to Simplified Chinese. Only output the Chinese translation, nothing else. "
                "Preserve the original meaning, tone, and paragraph structure."
            ),
        },
        {"role": "user", "content": text},
    ]

    # 输出 token 数估算：中文约为输入字符数的 1.5 倍
    out_tokens = min(max(len(text) * 2, 512), 8192)
    return _call_deepseek(messages, max_tokens=out_tokens)


if __name__ == "__main__":
    # 简单测试
    test_text = input("输入待检测/翻译的文本: ")
    lang = detect_language(test_text)
    print(f"检测语言: {lang}")
    if lang in ("ja", "en"):
        result = translate_to_chinese(test_text, lang)
        print(f"翻译结果:\n{result}")

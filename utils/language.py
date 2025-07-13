from langdetect import detect, LangDetectException

def detect_language(text):
    try:
        lang = detect(text)
        if lang == "ko":
            return "ko"
        elif lang == "en":
            return "en"
        else:
            return lang  # 필요한 경우 "ja", "zh" 등 반환
    except LangDetectException:
        return "unknown"

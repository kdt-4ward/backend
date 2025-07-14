from langdetect import detect, LangDetectException

def detect_language(text):
    try:
        lang = detect(text)
        if lang == "ko":
            return "ko"
        elif lang == "en":
            return "en"
        else:
            return "en"  # default "en"
    except LangDetectException:
        return "en"

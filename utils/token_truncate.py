import tiktoken
import logging

logger = logging.getLogger(__name__)

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def truncate_by_token(
    text: str,
    max_tokens: int = 4000,
    model: str = "gpt-4o",
    postfix: str = "\n...(이하 생략)",
    log_prefix: str = None
):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    token_count = len(tokens)
    if token_count <= max_tokens:
        return text, token_count
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoding.decode(truncated_tokens)
    # 로그
    if log_prefix:
        logger.warning(f"[{log_prefix}] {token_count} → {max_tokens} 토큰으로 잘림")
    return truncated_text + postfix, token_count

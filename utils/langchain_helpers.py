from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.dependencies import get_langchain_llm
import json
import logging
from typing import Dict, Any
from utils.token_truncate import truncate_by_token

logger = logging.getLogger(__name__)

async def run_langchain_prompt(prompt_template: str, input_vars: dict, expected_json_key: str = None,
                               max_tokens=4000, model="gpt-4o",postfix: str = "\n...(이하 생략)", log_prefix: str = None) -> Dict[str, Any]:
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | get_langchain_llm() | StrOutputParser()
    safe_input_vars = {
        k: truncate_by_token(str(v), max_tokens, model, postfix=postfix, log_prefix=log_prefix)
        for k, v in input_vars.items()
    }
    try:
        result = await chain.ainvoke(safe_input_vars)
        # JSON 파싱 및 키 체크
        data = json.loads(result)
        if expected_json_key:
            return {"success": True, "result": data.get(expected_json_key, data)}
        return {"success": True, "result": data}
    except Exception as e:
        logger.error(f"[run_langchain_prompt] 에러: {e}, 입력: {safe_input_vars}")
        return {"success": False, "error": str(e), "raw": result if 'result' in locals() else None}

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from core.dependencies import get_langchain_llm
import json
import logging
from typing import Dict, Any
from utils.token_truncate import truncate_by_token

logger = logging.getLogger(__name__)

async def run_langchain_prompt(prompt_template: str, input_vars: dict, expected_json_key: str = None,
                               max_tokens=4000, model="gpt-4o",postfix: str = "\n...(이하 생략)", log_prefix: str = None) -> Dict[str, Any]:
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | get_langchain_llm() | JsonOutputParser()
    safe_input_vars = {
        k: truncate_by_token(str(v), max_tokens, model, postfix=postfix, log_prefix=log_prefix)[0]
        for k, v in input_vars.items()
    }
    try:
        logger.info(f"[run_langchain_prompt][{log_prefix}] input_vars: {safe_input_vars}")
        result = await chain.ainvoke(safe_input_vars)
        logger.info(f"[run_langchain_prompt][{log_prefix}] result: {result}")

        # 예: run_langchain_prompt 결과에서 꺼내기
        if isinstance(result, str):
            data = json.loads(result)
        elif isinstance(result, dict):
            data = result
        else:
            raise ValueError("알 수 없는 결과 타입")
        if expected_json_key:
            return {"success": True, "result": data.get(expected_json_key, data)}
        return {"success": True, "result": data}
    except Exception as e:
        logger.error(f"[run_langchain_prompt] 에러: {e}, 입력: {safe_input_vars}")
        return {"success": False, "error": str(e), "raw": result if 'result' in locals() else None}

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from core.dependencies import get_langchain_llm
import json
import logging
from typing import Dict, Any
from utils.token_truncate import truncate_by_token

logger = logging.getLogger(__name__)

async def run_langchain_prompt(
    prompt_template: str,
    input_vars: dict,
    expected_json_key: str = None,
    max_tokens=4000,
    model="gpt-4o",
    postfix: str = "\n...(이하 생략)",
    log_prefix: str = None
) -> Dict[str, Any]:
    """
    Langchain 프롬프트 실행 및 결과 JSON 파싱 유틸.
    - input_vars의 각 값이 dict면 JSON 문자열로 변환, 아니면 토큰 기준 truncate.
    - 결과가 str이면 JSON 파싱, dict면 그대로 사용.
    - expected_json_key가 있으면 해당 키만 반환.
    - 에러 발생 시 상세 로그와 함께 실패 반환.
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    # get_langchain_llm은 async 함수이므로, await로 호출해서 인스턴스를 받아야 합니다.
    llm = await get_langchain_llm()
    chain = prompt | llm | JsonOutputParser()

    safe_input_vars = {}
    for k, v in input_vars.items():
        # dict, list 등은 JSON 문자열로 변환
        if isinstance(v, (dict, list)):
            try:
                safe_input_vars[k] = truncate_by_token(
                    json.dumps(v, ensure_ascii=False),
                    max_tokens,
                    model,
                    postfix=postfix,
                    log_prefix=log_prefix
                )[0]
            except Exception as e:
                logger.warning(f"[run_langchain_prompt][{log_prefix}] {k} JSON 변환 실패: {e}")
                safe_input_vars[k] = str(v)
        else:
            # 문자열 등은 그대로 truncate
            safe_input_vars[k] = truncate_by_token(
                str(v),
                max_tokens,
                model,
                postfix=postfix,
                log_prefix=log_prefix
            )[0]

    logger.info(f"[run_langchain_prompt][{log_prefix}] input_vars: {safe_input_vars}")

    result = None
    try:
        result = await chain.ainvoke(safe_input_vars)
        logger.info(f"[run_langchain_prompt][{log_prefix}] result: {result}")

        # 결과 파싱
        if isinstance(result, str):
            try:
                data = json.loads(result)
            except Exception as e:
                logger.error(f"[run_langchain_prompt][{log_prefix}] JSON 파싱 실패: {e}, result: {result}")
                return {"success": False, "error": f"JSON 파싱 실패: {e}", "raw": result}
        elif isinstance(result, dict):
            data = result
        else:
            logger.error(f"[run_langchain_prompt][{log_prefix}] 알 수 없는 결과 타입: {type(result)}")
            return {"success": False, "error": f"알 수 없는 결과 타입: {type(result)}", "raw": result}

        # expected_json_key가 있으면 해당 키만 반환
        if expected_json_key:
            if expected_json_key in data:
                return {"success": True, "result": data[expected_json_key]}
            else:
                logger.warning(f"[run_langchain_prompt][{log_prefix}] expected_json_key '{expected_json_key}' 없음. 전체 반환")
                return {"success": True, "result": data}
        return {"success": True, "result": data}
    except Exception as e:
        logger.error(f"[run_langchain_prompt][{log_prefix}] 에러: {e}, 입력: {safe_input_vars}, raw: {result}")
        return {"success": False, "error": str(e), "raw": result}

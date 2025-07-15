from tenacity import retry, stop_after_attempt, wait_fixed
from core.dependencies import (
    get_openai_client,
    get_langchain_chain,
)
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Optional
from openai import BadRequestError
from utils.log_utils import get_logger
import json

logger = get_logger(__name__)

# 1. 일반 OpenAI 스트리밍 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_stream_async(
    history: List[dict],
    functions: Optional[list] = None,
    function_call: str = "auto"
):
    client = await get_openai_client()
    params = {
        "model": "gpt-4o",
        "messages": history,
        "stream": True
    }
    if functions:
        params["functions"] = functions
        params["function_call"] = function_call

    return await client.chat.completions.create(**params)

# 2. 일반 OpenAI 완료형 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_completion(history: list, functions=None, function_call="auto"):
    client = await get_openai_client()
    params = {
        "model": "gpt-4o",
        "messages": history,
        "stream": False
    }
    if functions:
        params["functions"] = functions
        params["function_call"] = function_call
    response = await client.chat.completions.create(**params)
    return response.choices[0].message.content, response

# 3. Langchain 기반 LLM 호출 (비동기)
async def call_langchain_chat(prompt: str, system_prompt: str = None) -> str:
    chain = get_langchain_chain()

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = await chain.ainvoke(messages)
    return response.content

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def openai_completion_with_function_call(
    history,
    functions,
    function_map,
    bot=None,
    max_func_calls=5
):
    client = await get_openai_client()
    params = {
        "model": "gpt-4o", # 실시간 응답 속도를 위해 mini 사용
        "messages": filter_for_openai(history),
        "stream": False,
        "functions": functions,
        "function_call": "auto"
    }

    call_count = 0
    while call_count < max_func_calls:
        print(f"[openai_completion_with_function_call] call_count={call_count} | params={params}")
        try:
            response = await client.chat.completions.create(**params)
        except BadRequestError as e:
            print(e)
        
        if not response.choices:
            raise ValueError("GPT 응답에 choices가 없습니다.")
        msg = getattr(response.choices[0], "message", None)
        if msg is None:
            raise AttributeError("choices[0]에 message가 없습니다.")

        # 1. function_call 여부 판단
        function_call = getattr(msg, "function_call", None)
        if function_call:
            call_count += 1
            func_name = getattr(function_call, "name", None)
            arguments = getattr(function_call, "arguments", None)
            if func_name is None or arguments is None:
                raise ValueError("function_call object is missing 'name' or 'arguments'")

            if not arguments or arguments.strip() == "":
                args = {}
            else:
                try:
                    args = json.loads(arguments)
                except Exception as e:
                    logger.warning(f"[WARN] arguments json decode error: {arguments} | {e}")
                    args = {}

            if "query" not in args:
                logger.warning(f"[function_call] 'query' 인자가 없음 → 사용자 입력으로 대체")
                args["query"] = history[-1]["content"]

            # 실제 function 실행
            result = await function_map[func_name](**args)
            # history에 function 결과 append
            if bot is not None:
                function_msg_id = bot.save_to_db(bot.user_id, "function", json.dumps({"name": func_name, "result": result}, ensure_ascii=False))
            else:
                function_msg_id = history[-1]["id"] + 1
            
            history.append({
                "role": "function",
                "name": func_name,
                "content": json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result,
                "id":function_msg_id
            })

            if bot is not None:
                bot.save_history(history)
            # function-call 후 루프 재시작
            params["messages"] = filter_for_openai(history)
            continue  # 다시 반복문 진입

        # 2. function_call이 아니라면 assistant 답변 반환
        if hasattr(msg, "content"):
            return msg.content  # (필요시, return msg.content, response)
        else:
            # content가 없을 때(이론상 거의 없음)
            return ""

    # 함수 호출 최대치 초과
    raise RuntimeError("Function-call 반복 한도를 초과했습니다.")

# services/openai_client.py
from typing import AsyncGenerator
from openai.types.chat import ChatCompletionChunk

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def openai_stream_with_function_call(
    history: list,
    functions: list,
    function_map: dict,
    bot=None,
    max_func_calls=3
) -> AsyncGenerator[str, None]:
    """
    function_call + streaming 가능한 GPT 응답 생성기
    """
    client = await get_openai_client()
    current_history = filter_for_openai(history)

    call_count = 0
    while call_count < max_func_calls:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=current_history,
            stream=True,
            functions=functions,
            function_call="auto"
        )

        collected = ""
        func_call_detected = False
        arguments_collected = ""
        function_name = None
        async for chunk in response:
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            # ✅ function_call 감지
            if delta.function_call:
                func_call_detected = True
                if delta.function_call.name:
                    function_name = delta.function_call.name
                if delta.function_call.arguments:
                    arguments_collected += delta.function_call.arguments
                continue  # 여기서 break 하면 안 됨 ❗

            if delta.content:
                collected += delta.content
                yield delta.content  # 즉시 응답 반환

        if func_call_detected:
            call_count += 1
            try:
                args = json.loads(arguments_collected) if arguments_collected.strip() else {}
                logger.info(f"[function_call] arguments raw: {arguments_collected}")
            except Exception as e:
                logger.warning(f"[WARN] function_call arguments 파싱 실패: {arguments_collected} | {e}")
                args = {}

            if "query" not in args:
                logger.warning(f"[function_call] 'query' 인자가 없음 → 사용자 입력으로 대체")
                args["query"] = history[-1]["content"]
            # 🔧 function 실행
            result = await function_map[function_name](**args)
            function_msg_id = bot.save_to_db(bot.user_id, "function", json.dumps(result, ensure_ascii=False)) if bot else len(history)

            history.append({
                "role": "function",
                "name": function_name,
                "content": json.dumps(result, ensure_ascii=False),
                "id": function_msg_id
            })
            current_history = filter_for_openai(history)
            if bot:
                bot.save_history(history)
            continue  # GPT 재호출

        # function_call 없이 정상 종료 → 저장
        if bot:
            assistant_msg_id = bot.save_to_db(bot.user_id, "assistant", collected)
            history.append({"role": "assistant", "content": collected, "id": assistant_msg_id})
            bot.save_history(history)

        break  # 종료

    if call_count >= max_func_calls:
        raise RuntimeError("Function-call 반복 한도를 초과했습니다.")


@retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
async def get_openai_embedding(text: str):
    # OpenAI text-embedding-3-small 추천 (짧은 텍스트)
    client = await get_openai_client()
    resp = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return resp.data[0].embedding

def filter_for_openai(history: list) -> list:
    """
    OpenAI API에 전달할 메시지 리스트로 변환 (id 등 불필요 필드 제거)
    """
    # OpenAI API docs: role, content, name, function_call 등만 허용
    allowed_keys = {"role", "content", "name", "function_call"}
    openai_inputs = [
        {k: v for k, v in msg.items() if k in allowed_keys}
        for msg in history
    ]
    for msg in openai_inputs:
        if msg["role"] == "function" and "name" not in msg:
            content = json.loads(msg['content'])
            msg['name'] = content['name']
            msg['content'] = content['result']
        if msg['role'] == "summary":
            msg['role'] = "function"
            msg["name"] = "chat_summarizer"
        assert msg.get("role") in ("system", "user", "assistant", "function"), msg
        assert isinstance(msg.get("content", ""), str), msg
    return openai_inputs
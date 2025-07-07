from tenacity import retry, stop_after_attempt, wait_fixed
from core.dependencies import (
    get_openai_client,
    get_langchain_chain,
)
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Optional

import json

# 1. 일반 OpenAI 스트리밍 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_stream_async(
    history: List[dict],
    functions: Optional[list] = None,
    function_call: str = "auto"
):
    client = get_openai_client()
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
    client = get_openai_client()
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
async def openai_stream_with_function_call(history, functions, function_map, bot=None):
    client = get_openai_client()
    params = {
        "model": "gpt-4o",
        "messages": history,
        "stream": True,
        "functions": functions,
        "function_call": "auto"
    }
    max_func_calls = 5
    call_count = 0
    while call_count < max_func_calls:

        # 1. 스트리밍 응답 시작
        response = await client.chat.completions.create(**params)
        function_call_triggered  = False

        # 2. 첫번째 청크에서 function-call 여부 확인
        async for chunk in response:
            # OpenAI function-call 응답은 'choices[0].delta.function_call'에 나타남
            delta = chunk.choices[0].delta
            function_call = getattr(delta, "function_call", None) # or (delta.get("function_call") if isinstance(delta, dict) else None)
            if not function_call and isinstance(delta, dict):
                function_call = delta.get("function_call")
            if function_call and not function_call_triggered:
                call_count += 1
                function_call_triggered = True
                # Function-call 발생!
                if isinstance(function_call, dict):
                    func_name = function_call.get("name")
                    arguments = function_call.get("arguments")
                else:
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
                        # 필요시 로깅
                        print(f"[WARN] arguments json decode error: {arguments} | {e}")
                        args = {}
                if "query" not in args:
                    # 함수가 정상 실행되게 기본값 추가(혹은 에러 메시지 리턴)
                    print(f"[WARN] function_call arguments 누락: {args}")
                    args["query"] = ""  # 또는 적당한 기본값
                    
                # 3. 실제 function 실행
                result = await function_map[func_name](**args)
                # 4. history에 function 결과 append
                history.append({
                    "role": "function",
                    "name": func_name,
                    "content": json.dumps(result, ensure_ascii=False) if result is not None else ""
                })
                if bot is not None:
                    bot.save_history(history)
                    # user_id를 호출자(user/user_id)로, couple_id는 bot.couple_id로 저장
                    bot.save_to_db(bot.user_id, "function", json.dumps({"name": func_name, "result": result}, ensure_ascii=False))
                # function-call 발생했으니 루프 상위로 올라가서 재시작
                params["messages"] = history
            else:
                # 일반 답변 청크라면 바로 yield (스트리밍)
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
        else:
            return

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def openai_completion_with_function_call(
    history,
    functions,
    function_map,
    bot=None,
    max_func_calls=5
):
    client = get_openai_client()
    params = {
        "model": "gpt-4o-mini", # 실시간 응답 속도를 위해 mini 사용
        "messages": filter_for_openai(history),
        "stream": False,
        "functions": functions,
        "function_call": "auto"
    }

    call_count = 0
    while call_count < max_func_calls:
        print(f"[openai_completion_with_function_call] call_count={call_count} | params={params}")

        response = await client.chat.completions.create(**params)
        msg = response.choices[0].message

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
                    print(f"[WARN] arguments json decode error: {arguments} | {e}")
                    args = {}

            if "query" not in args:
                print(f"[WARN] function_call arguments 누락: {args}")
                args["query"] = ""

            # 실제 function 실행
            result = await function_map[func_name](**args)
            # history에 function 결과 append
            function_msg_id = None
            if bot is not None:
                function_msg_id = bot.save_to_db(bot.user_id, "function", json.dumps({"name": func_name, "result": result}, ensure_ascii=False))
            
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

@retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
async def get_openai_embedding(text: str):
    # OpenAI text-embedding-3-small 추천 (짧은 텍스트)
    client = get_openai_client()
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
        if msg['role'] == "summary":
            msg['role'] = "function"
            msg["name"] = "chat_summarizer"
    return openai_inputs
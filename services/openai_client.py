from tenacity import retry, stop_after_attempt, wait_fixed
from core.dependencies import (
    get_openai_client,
    get_langchain_chain,
)
from langchain_core.messages import HumanMessage, SystemMessage

# 1. 일반 OpenAI 스트리밍 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_stream_async(history: list):
    client = get_openai_client()
    return await client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        stream=True
    )
 
# 2. 일반 OpenAI 완료형 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_completion(history: list):
    client = get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        stream=False
    )
    return response.choices[0].message.content

# 3. Langchain 기반 LLM 호출 (비동기)
async def call_langchain_chat(prompt: str, system_prompt: str = None) -> str:
    chain = get_langchain_chain()

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = await chain.ainvoke(messages)
    return response.content

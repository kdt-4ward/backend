from tenacity import retry, stop_after_attempt, wait_fixed
from config import client
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from core.settings import settings
##############TODO: 수정 중 ####################

# output parser
parser = StrOutputParser()

# llm
chat_llm_async: BaseChatModel = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    streaming=False,
    verbose=True,
    max_tokens=1024,
    api_key=settings.openai_api_key
)

# prompt
system_template = '너는 {story}에 나오는 {character_a}의 역할을 맡고 있어. 그 캐릭터처럼 사용자와 대화해줘'
human_template = '안녕하세요, 저는 {character_b}입니다. 오늘 시간 괜찮으시면 {activity} 전에 눈 좀 더 만들어주세요.'

prompt_template = ChatPromptTemplate([
    ('system', system_template),
    ('user', human_template)
])


chain = prompt_template | chat_llm_async | parser

##############TODO: 수정 중 ####################


# 1. 일반 OpenAI 스트리밍 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_stream_async(history: list):
    return await client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        stream=True
    )

# 2. 일반 OpenAI 완료형 호출
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def call_openai_completion(history: list):
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        stream=False
    )
    return response.choices[0].message.content


# 3. Langchain 기반 LLM 호출 (비동기)
async def call_langchain_chat(prompt: str, system_prompt: str = None) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = await chain.ainvoke(messages)
    return response.content
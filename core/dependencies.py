from core.connection_manager import ConnectionManager
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.settings import settings
from openai import AsyncOpenAI
from core.settings import settings
from db.db import get_session

# DB session
def get_db_session():
    return get_session()


# 싱글 인스턴스 유지
_connection_manager = ConnectionManager()
def get_connection_manager() -> ConnectionManager:
    return _connection_manager


async def get_openai_client() -> AsyncOpenAI:
    # api_key = get_user_api_key(user_id)
    return AsyncOpenAI(api_key=await settings.get_next_api_key())


# 2. Langchain LLM
async def get_langchain_llm() -> BaseChatModel:
    _langchain_llm: BaseChatModel = ChatOpenAI(
        model="gpt-4o",
        temperature=0.7,
        streaming=False,
        verbose=True,
        max_tokens=4096,
        api_key=await settings.get_next_api_key()
    )
    return _langchain_llm


def get_langchain_chain(couple_id: str):
    persona = "대화를 요약하고 분석하는" # get_persona_from_db(couple_id)
    prompt = ChatPromptTemplate([
        ("system", f"너는 {persona} 역할을 맡고 있어."),
        ("user", "{input}")
    ])
    return prompt | get_langchain_llm() | StrOutputParser()
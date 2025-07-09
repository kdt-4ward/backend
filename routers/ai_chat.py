import asyncio
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from tenacity import RetryError
from typing import AsyncGenerator

from models.schema import ChatRequest, BotConfigRequest
from config import router, semaphore
from core.bot import PersonaChatBot
from services.rag_search import search_past_chats, process_incremental_faiss_embedding
from services.openai_client import openai_completion_with_function_call
from core.dependencies import get_connection_manager
from services.tasks_celery import run_check_and_summarize, run_embedding

# TODO: 배포시 제거
from core.utils import ensure_couple_mapping

logger = logging.getLogger(__name__)

@router.post("/chat/completion")
async def chat_with_persona(req: ChatRequest):
    ensure_couple_mapping(req.user_id, "테스트파트너", req.couple_id)  # 필요시 주석 처리

    logger.info(f"[chat_with_persona] 요청: user_id={req.user_id}, couple_id={req.couple_id}")
    async with semaphore:
        bot = PersonaChatBot(user_id=req.user_id)

        functions = [
            {
                "name": "search_past_chats",
                "description": (
                    "질문과 관련된 실제 과거 대화 내용(채팅 메시지)을 검색하여, "
                    "정확한 근거가 필요하거나, 이전의 구체적인 사건, 날짜, 표현 등을 사용자가 물었을 때 반드시 사용해야 합니다. "
                    "검색 결과가 없으면 찾을 수 없다고 안내하세요."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "검색하고 싶은 키워드, 질문, 또는 자연어 문장. "
                                "예: '작년 여름 여행', '우리가 마지막으로 싸운 이유', '상대방이 서운했던 순간'"
                            )
                        },
                        "top_k": {
                            "type": "integer",
                            "default": 3,
                            "description": (
                                "관련성이 높은 결과(대화 chunk) 최대 개수. 필요시 늘릴 수 있음."
                            )
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

        function_map = {
            "search_past_chats": lambda query, top_k=3: search_past_chats(
                query=query,
                top_k=top_k,
                user_id=req.user_id,
                couple_id=bot.couple_id
            )
        }

        user_msg_id = bot.save_to_db(req.user_id, "user", req.message)
        history = bot.get_history()
        history.append({"role": "user", "content": req.message, "id": user_msg_id})
        bot.save_history(history)

        try:
            logger.info(f"[chat_with_persona] OpenAI 호출 시작: user_id={req.user_id}, history_len={len(history)}")
            response = await openai_completion_with_function_call(
                history,
                functions=functions,
                function_map=function_map,
                bot=bot
            )
            logger.info(f"[chat_with_persona] OpenAI 응답 성공: user_id={req.user_id}")
        except RetryError as e:
            logger.error(f"[chat_with_persona] GPT 응답 실패! user_id={req.user_id} | error={e}")
            return JSONResponse(content={"error": "GPT 응답 실패"}, status_code=500)
        except Exception as e:
            logger.error(f"[chat_with_persona] 예상치 못한 에러! user_id={req.user_id} | error={e}")
            return JSONResponse(content={"error": "알 수 없는 에러"}, status_code=500)

        # assistant 응답 저장
        assistant_msg_id = bot.save_to_db(req.user_id, "assistant", response)
        history.append({"role": "assistant", "content": response, "id": assistant_msg_id})
        bot.save_history(history)

        # celery 사용 : 메인 프로세스 부하 줄여주기 (비동기 분산 처리)
        # run_check_and_summarize.delay(req.user_id)
        # run_embedding.delay(req.user_id)

        asyncio.create_task(bot.check_and_summarize_if_needed())
        asyncio.create_task(process_incremental_faiss_embedding(req.user_id))
        logger.info(f"[chat_with_persona] 응답 완료: user_id={req.user_id}, msg_id={assistant_msg_id}")
        return PlainTextResponse(response)

@router.post("/chat/reset")
async def reset_ai_chat_session(req: ChatRequest):
    logger.info(f"[reset_ai_chat_session] user_id={req.user_id}")
    bot = PersonaChatBot(user_id=req.user_id)
    bot.reset()
    return {"message": f"{req.user_id} 님의 AI 세션이 초기화되었습니다."}

@router.post("/chat/configure")
async def set_ai_bot_config(req: BotConfigRequest):
    logger.info(f"[set_ai_bot_config] user_id={req.user_id}, persona_name={req.persona_name}")
    partner_id = get_connection_manager().get_partner(req.user_id)
    bot = PersonaChatBot(req.user_id)
    bot.set_persona_name(req.persona_name)

    bot = PersonaChatBot(partner_id)
    bot.set_persona_name(req.persona_name)

    logger.info(f"[set_ai_bot_config] 챗봇 이름 저장 완료: user_id={req.user_id}, partner_id={partner_id}, persona_name={req.persona_name}")
    return {"message": "챗봇 설정이 저장되었습니다."}

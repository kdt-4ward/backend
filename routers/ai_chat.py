import asyncio
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

# TODO: 배포시 제거
from core.utils import ensure_couple_mapping

@router.post("/chat/completion")
async def chat_with_persona(req: ChatRequest):
    # TODO: test용 dummy 파트너 배포시 제거
    # ensure_couple_mapping(req.user_id, "테스트파트너", req.couple_id)  # 필요시 주석 처리
    
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

        function_map = {"search_past_chats": lambda query, top_k=3: search_past_chats(
                                                                query=query,
                                                                top_k=top_k,
                                                                user_id=req.user_id,
                                                                couple_id=bot.couple_id
                                                            )}

        user_msg_id = bot.save_to_db(req.user_id, "user", req.message)
        history = bot.get_history()
        history.append({"role": "user", "content": req.message, "id": user_msg_id})
        bot.save_history(history)

        try:
            response = await openai_completion_with_function_call(
                history,
                functions=functions,
                function_map=function_map,
                bot=bot
            )
        except RetryError as e:
            print("============ERROR========\n", e)
            return JSONResponse(content={"error": "GPT 응답 실패"}, status_code=500)

        # assistant 응답 저장
        assistant_msg_id = bot.save_to_db(req.user_id, "assistant", response)
        history.append({"role": "assistant", "content": response, "id": assistant_msg_id})
        bot.save_history(history)
        asyncio.create_task(bot.check_and_summarize_if_needed())
        asyncio.create_task(process_incremental_faiss_embedding(req.user_id))
        return PlainTextResponse(response)


@router.post("/chat/stream")
async def stream_chat_with_persona(req: ChatRequest):
    # TODO: test용 dummy 파트너 배포시 제거
    ensure_couple_mapping(req.user_id, "테스트파트너", req.couple_id)
    async def event_generator() -> AsyncGenerator[str, None]:
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


            function_map = {"search_past_chats": lambda query, top_k=3: search_past_chats(
                                                                                            query=query,
                                                                                            top_k=top_k,
                                                                                            user_id=req.user_id,
                                                                                            couple_id=bot.couple_id
                                                                                        )}

            user_msg_id = bot.save_to_db(req.user_id, "user", req.message)
            history = bot.get_history()
            history.append({"role": "user", "content": req.message, "id": user_msg_id})
            bot.save_history(history)

            try:
                response = await openai_completion_with_function_call(history,
                                                            functions=functions,
                                                            function_map=function_map,
                                                            bot=bot)
        
            except RetryError:
                yield "[ERROR] GPT 응답 실패\n"
                return

            full_reply = response

            yield full_reply
            # 어시스턴트 응답 저장
            assistant_msg_id = bot.save_to_db(req.user_id, "assistant", full_reply)
            history.append({"role": "assistant", "content": full_reply, "id": assistant_msg_id})
            bot.save_history(history)
            asyncio.create_task(bot.check_and_summarize_if_needed())

    return StreamingResponse(event_generator(), media_type="text/plain")

@router.post("/chat/reset")
async def reset_ai_chat_session(req: ChatRequest):
    bot = PersonaChatBot(user_id=req.user_id)
    bot.reset()
    return {"message": f"{req.user_id} 님의 AI 세션이 초기화되었습니다."}

@router.post("/chat/configure")
async def set_ai_bot_config(req: BotConfigRequest):
    # 함께 키우는 반려펫이기 때문에 이름 같이 변경
    partner_id = get_connection_manager().get_partner(req.user_id)
    bot = PersonaChatBot(req.user_id)
    bot.set_persona_name(req.persona_name)

    bot = PersonaChatBot(partner_id)
    bot.set_persona_name(req.persona_name)

    return {"message": "챗봇 설정이 저장되었습니다."}

import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
from tenacity import RetryError
from typing import AsyncGenerator, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from db.db_tables import AIMessage
from db.db import get_session

from models.schema import ChatRequest, BotConfigRequest
from core.cocurrency import semaphore

from core.bot import PersonaChatBot
from services.rag_search import process_incremental_faiss_embedding
from services.openai_client import openai_completion_with_function_call, openai_stream_with_function_call
from core.dependencies import get_connection_manager
from services.tasks_celery import run_check_and_summarize, run_embedding
from utils.language import detect_language
from utils.aichat_helpers import build_function_map, build_functions
# TODO: 배포시 제거
from core.utils import ensure_couple_mapping
from utils.log_utils import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/completion")
async def chat_with_persona(req: ChatRequest):
    ensure_couple_mapping(req.user_id, "테스트파트너", req.couple_id)  # 필요시 주석 처리

    logger.info(f"[chat_with_persona] 요청: user_id={req.user_id}, couple_id={req.couple_id}")
    async with semaphore:
        lang = detect_language(req.message)
        bot = PersonaChatBot(user_id=req.user_id, lang=lang)
        
        functions = build_functions()
        function_map = build_function_map()

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

@router.post("/stream", response_class=StreamingResponse)
async def chat_with_persona_streaming(req: ChatRequest):
    ensure_couple_mapping(req.user_id, "테스트파트너", req.couple_id)  # 필요시 제거 가능

    logger.info(f"[chat_with_persona] 요청: user_id={req.user_id}, couple_id={req.couple_id}")
    async with semaphore:
        lang = detect_language(req.message)
        bot = PersonaChatBot(user_id=req.user_id, lang=lang)

        functions = build_functions()
        function_map = build_function_map(req.user_id, bot.couple_id)

        user_msg_id = bot.save_to_db(req.user_id, "user", req.message)
        history = bot.get_history()
        history.append({"role": "user", "content": req.message, "id": user_msg_id})
        bot.save_history(history)

        async def stream_response():
            collected = ""  # 🔥 조립용 변수
            try:
                logger.info(f"[chat_with_persona] GPT 스트리밍 호출 시작: user_id={req.user_id}, history_len={len(history)}")
                async for chunk in openai_stream_with_function_call(
                    history=history,
                    functions=functions,
                    function_map=function_map,
                    bot=bot
                ):
                    collected += chunk
                    yield chunk
                
                logger.info(f"[chat_with_persona] GPT 스트리밍 완료: user_id={req.user_id}")

                # 후작업 비동기
                asyncio.create_task(bot.check_and_summarize_if_needed())
                asyncio.create_task(process_incremental_faiss_embedding(req.user_id))
            except RetryError as e:
                logger.error(f"[chat_with_persona] GPT 응답 실패! user_id={req.user_id} | error={e}")
                yield "[ERROR] GPT 응답 실패"
            except Exception as e:
                logger.exception(f"[chat_with_persona] 알 수 없는 에러! user_id={req.user_id}")
                yield "[ERROR] 서버 내부 오류"

        return StreamingResponse(stream_response(), media_type="text/plain")


@router.get("/history/{user_id}/recent")
async def get_recent_ai_chat_history(
    user_id: str,
    end_date: Optional[str] = None,
    limit: Optional[int] = Query(20, description="최대 조회 개수", ge=1, le=500),
    db: Session = Depends(get_session)
):
    """사용자의 최근 AI 채팅 히스토리 조회"""
    try:
        logger.info(f"[get_recent_ai_chat_history] 요청: user_id={user_id}")
        
        # 최근 N일 계산
        end_date = end_date or datetime.now()
        
        # 메시지 조회
        messages = db.query(AIMessage).filter(
            AIMessage.user_id == user_id,
            AIMessage.created_at <= end_date
        ).order_by(AIMessage.created_at.desc()).limit(limit).all()
        
        # role이 'assistant' 또는 'user'인 메시지만 반환
        filtered_messages = [
            msg for msg in reversed(messages)
            if msg.role in ("assistant", "user")
        ]

        response_data = {
            "success": True,
            "data": {
                "user_id": user_id,
                "total_messages": len(filtered_messages),
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "couple_id": msg.couple_id
                    }
                    for msg in filtered_messages  # 시간순으로 정렬
                ]
            }
        }
        
        logger.info(f"[get_recent_ai_chat_history] 조회 완료: user_id={user_id}, message_count={len(filtered_messages)}")
        return response_data
        
    except Exception as e:
        logger.error(f"[get_recent_ai_chat_history] 조회 실패: user_id={user_id}, error={e}")
        raise HTTPException(status_code=500, detail=f"최근 AI 채팅 히스토리 조회 실패: {str(e)}")


@router.post("/reset")
async def reset_ai_chat_session(req: ChatRequest):
    logger.info(f"[reset_ai_chat_session] user_id={req.user_id}")
    bot = PersonaChatBot(user_id=req.user_id)
    bot.reset()
    return {"message": f"{req.user_id} 님의 AI 세션이 초기화되었습니다."}

@router.post("/configure")
async def set_ai_bot_config(req: BotConfigRequest):
    logger.info(f"[set_ai_bot_config] user_id={req.user_id}, persona_name={req.persona_name}")
    partner_id = get_connection_manager().get_partner(req.user_id)
    bot = PersonaChatBot(req.user_id)
    bot.set_persona_name(req.persona_name)

    bot = PersonaChatBot(partner_id)
    bot.set_persona_name(req.persona_name)

    logger.info(f"[set_ai_bot_config] 챗봇 이름 저장 완료: user_id={req.user_id}, partner_id={partner_id}, persona_name={req.persona_name}")
    return {"message": "챗봇 설정이 저장되었습니다."}

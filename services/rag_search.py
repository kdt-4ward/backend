from core.bot import PersonaChatBot
from services.openai_client import get_openai_embedding
from core.dependencies import get_db_session
from db.db_tables import AIMessage
from core.redis_v2.redis import RedisFaissChunkCache
import faiss
import numpy as np
from typing import List, Dict, Optional, Tuple
from db.db import get_session
from db.db_tables import AIMessage, ChunkMetadata
import json
from datetime import datetime
from utils.log_utils import get_logger
from services.rag_service import RAGService
from services.faiss_search_service import FAISSSearchService
from services.optimized_faiss_search_service import OptimizedFAISSSearchService

logger = get_logger(__name__)


def build_multi_turn_chunks(messages, turns_per_chunk=4):
    """
    messages: [{"role": "user"/"assistant", "content": ..., "created_at": ..., "id": ...}, ...]
    turns_per_chunk: 한 chunk에 들어갈 user-assistant 턴 개수
    return: [chunk_dict, ...]
    """
    n = len(messages)
    i = 0
    result = []
    while i < n:
        chunk_lines = []
        msg_ids = []
        start_time, end_time = None, None
        turn_count = 0
        # 한 chunk에 최대 N턴씩 담기
        while turn_count < turns_per_chunk and i < n:
            # user 메시지
            if messages[i]["role"] == "user":
                if start_time is None:
                    start_time = messages[i]["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                chunk_lines.append(f'user: {messages[i]["content"]}')
                msg_ids.append(messages[i].get("id"))
                i += 1
                # 다음이 assistant면 같이 묶기
                if i < n and messages[i]["role"] == "assistant":
                    chunk_lines.append(f'assistant: {messages[i]["content"]}')
                    msg_ids.append(messages[i].get("id"))
                    end_time = messages[i]["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    i += 1
                else:
                    # 짝이 없으면 끝
                    end_time = start_time
                turn_count += 1
            else:
                # user로 시작하지 않는 경우 skip (이론상 거의 없음)
                i += 1
        if chunk_lines and len(msg_ids) >= 8:
            chunk_text = f'[{start_time} ~ {end_time}]\n' + "\n".join(chunk_lines)
            result.append({
                "text": chunk_text,
                "start_time": start_time,
                "end_time": end_time,
                "msg_ids": msg_ids
            })
    return result

# 2. chunk 생성 + embedding + 인덱스 관리 통합
async def process_and_build_faiss_index(user_id, messages, turns_per_chunk=4):
    # chunk 생성 (4턴 단위)
    chunks = build_multi_turn_chunks(messages, turns_per_chunk)
    # embedding & faiss 인덱스 생성
    embeddings = []
    for idx, chunk in enumerate(chunks):
        emb = await get_openai_embedding(chunk["text"])
        embeddings.append(emb)
        # DB에 embed_index 기록
        for msg_id in chunk["msg_ids"]:
            with get_db_session() as db:
                msg = db.query(AIMessage).filter_by(id=msg_id, user_id=user_id).first()
                if msg:
                    msg.embed_index = idx
                    db.commit()
    embeddings_np = np.array(embeddings).astype("float32")
    if not embeddings_np.size > 0:
        return None, None, []
    index = faiss.IndexFlatL2(embeddings_np.shape[1])
    index.add(embeddings_np)
    # 캐싱
    RedisFaissChunkCache.save(user_id, chunks, embeddings_np)
    return index, embeddings_np, chunks

async def process_incremental_faiss_embedding(user_id, turns_per_chunk=4):
    """증분 임베딩 처리 (효율적인 방식)"""
    try:
        rag_service = RAGService(turns_per_chunk)
        chunks = await rag_service.build_chunks_and_embeddings(user_id)
        
        if chunks:
            logger.info(f"✅ {len(chunks)}개의 새로운 chunk 처리 완료")
        else:
            logger.info("새로운 chunk가 없습니다.")
            
    except Exception as e:
        logger.error(f"증분 임베딩 처리 실패: {e}")

async def rebuild_user_chunks(user_id, turns_per_chunk=4):
    """사용자의 모든 chunk 재구성"""
    try:
        rag_service = RAGService(turns_per_chunk)
        chunks = await rag_service.rebuild_all_chunks(user_id)
        
        if chunks:
            logger.info(f"✅ {len(chunks)}개의 chunk 재구성 완료")
        else:
            logger.info("재구성할 chunk가 없습니다.")
            
    except Exception as e:
        logger.error(f"chunk 재구성 실패: {e}")

# 3. 검색시: 캐시/DB에서 인덱스/embedding 활용 (최적화된 버전)
async def search_past_chats(query, top_k=3, user_id=None, couple_id=None, turns_per_chunk=4, threshold=0.3):
    """과거 대화 검색 (최적화된 FAISS 기반)"""
    try:
        search_service = OptimizedFAISSSearchService(similarity_threshold=threshold)
        results = await search_service.search_similar_chunks_optimized(user_id, query, top_k)
        
        if not results:
            return "관련있는 대화 기록이 없습니다."
        
        # 결과 텍스트 조합
        response_text = "\n\n".join([r["text"] for r in results])
        return response_text
        
    except Exception as e:
        logger.error(f"FAISS search failed: {e}")
        return "검색 중 오류가 발생했습니다."

async def search_past_chats_with_time_filter(query, user_id, start_date=None, end_date=None, top_k=3, threshold=0.7):
    """시간 필터를 적용한 과거 대화 검색 (최적화된 FAISS 기반)"""
    try:
        search_service = OptimizedFAISSSearchService(similarity_threshold=threshold)
        results = await search_service.search_with_time_filter_optimized(
            user_id, query, start_date, end_date, top_k
        )
        
        if not results:
            return "해당 기간에 관련있는 대화 기록이 없습니다."
        
        response_text = "\n\n".join([r["text"] for r in results])
        return response_text
        
    except Exception as e:
        logger.error(f"최적화된 시간 필터 FAISS search failed: {e}")
        return "검색 중 오류가 발생했습니다."

async def search_past_chats_by_keywords(keywords, user_id, top_k=3, threshold=0.7):
    """키워드 기반 과거 대화 검색 (FAISS 기반)"""
    try:
        search_service = FAISSSearchService(similarity_threshold=threshold)
        results = await search_service.search_by_keywords_with_faiss(user_id, keywords, top_k)
        
        if not results:
            return "해당 키워드와 관련있는 대화 기록이 없습니다."
        
        response_text = "\n\n".join([r["text"] for r in results])
        return response_text
        
    except Exception as e:
        logger.error(f"Keyword search with FAISS failed: {e}")
        return "검색 중 오류가 발생했습니다."

# 새로운 함수: 캐시 관리
async def rebuild_user_cache(user_id: str):
    """사용자의 FAISS 캐시 재구성"""
    try:
        search_service = OptimizedFAISSSearchService()
        await search_service._rebuild_cache_from_db(user_id)
        logger.info(f"✅ 사용자 {user_id}의 캐시 재구성 완료")
    except Exception as e:
        logger.error(f"❌ 캐시 재구성 실패: {e}")

async def clear_user_cache(user_id: str):
    """사용자의 FAISS 캐시 삭제"""
    try:
        from services.optimized_faiss_search_service import OptimizedFAISSCache
        OptimizedFAISSCache.clear_cache(user_id)
        logger.info(f"✅ 사용자 {user_id}의 캐시 삭제 완료")
    except Exception as e:
        logger.error(f"❌ 캐시 삭제 실패: {e}")

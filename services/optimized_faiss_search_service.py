import faiss
import numpy as np
import json
import pickle
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from utils.log_utils import get_logger
from services.openai_client import get_openai_embedding
from core.redis_v2.redis import redis_client, redis_bin_client
from db.db import get_session
from db.db_tables import ChunkMetadata, AIMessage

logger = get_logger(__name__)

class OptimizedFAISSCache:
    """FAISS 인덱스와 chunk 텍스트를 Redis에 캐싱하는 클래스"""
    
    INDEX_PREFIX = "chatbot:faiss:index"
    CHUNK_TEXT_PREFIX = "chatbot:faiss:chunk_text"
    META_PREFIX = "chatbot:faiss:meta"
    
    @classmethod
    def _index_key(cls, user_id: str) -> str:
        return f"{cls.INDEX_PREFIX}:{user_id}"
    
    @classmethod
    def _chunk_text_key(cls, user_id: str) -> str:
        return f"{cls.CHUNK_TEXT_PREFIX}:{user_id}"
    
    @classmethod
    def _meta_key(cls, user_id: str) -> str:
        return f"{cls.META_PREFIX}:{user_id}"
    
    @classmethod
    def save_faiss_index(cls, user_id: str, index: faiss.Index, chunks: List[Dict], 
                        chunk_texts: List[str], metadata: Dict):
        """FAISS 인덱스와 관련 데이터를 Redis에 저장 (안전한 버전)"""
        try:
            # 1. FAISS 인덱스를 pickle로 직렬화 (가장 안전한 방법)
            index_bytes = pickle.dumps(index)
            
            # 2. Redis에 저장
            redis_bin_client.set(cls._index_key(user_id), index_bytes)
            redis_client.set(cls._chunk_text_key(user_id), json.dumps(chunk_texts))
            redis_client.set(cls._meta_key(user_id), json.dumps(metadata))
            
            logger.info(f"✅ FAISS 인덱스 캐시 저장 완료: user_id={user_id}, chunks={len(chunks)}")
            
        except Exception as e:
            logger.error(f"❌ FAISS 인덱스 캐시 저장 실패: {e}")
            logger.error(f"index_bytes 타입: {type(index_bytes) if 'index_bytes' in locals() else 'undefined'}")

    @classmethod
    def load_faiss_index(cls, user_id: str) -> Tuple[Optional[faiss.Index], Optional[List[str]], Optional[Dict]]:
        """Redis에서 FAISS 인덱스와 관련 데이터 로드 (안전한 버전)"""
        try:
            # 1. 인덱스 로드
            index_bytes = redis_bin_client.get(cls._index_key(user_id))
            if not index_bytes:
                logger.debug(f"캐시된 인덱스가 없습니다: user_id={user_id}")
                return None, None, None
            
            # 2. pickle로 역직렬화 (가장 안전한 방법)
            try:
                index = pickle.loads(index_bytes)
                logger.debug(f"인덱스 로드 성공: user_id={user_id}, 타입={type(index)}")
            except Exception as pickle_error:
                logger.error(f"pickle 역직렬화 실패: {pickle_error}")
                return None, None, None
            
            # 3. 나머지 데이터 로드
            try:
                chunk_texts_raw = redis_client.get(cls._chunk_text_key(user_id))
                chunk_texts = json.loads(chunk_texts_raw) if chunk_texts_raw else []
                
                meta_raw = redis_client.get(cls._meta_key(user_id))
                metadata = json.loads(meta_raw) if meta_raw else {}
                
                logger.info(f"✅ FAISS 인덱스 캐시 로드 완료: user_id={user_id}")
                return index, chunk_texts, metadata
                
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON 파싱 실패: {json_error}")
                return None, None, None
            
        except Exception as e:
            logger.error(f"❌ FAISS 인덱스 캐시 로드 실패: {e}")
            return None, None, None
    
    @classmethod
    def clear_cache(cls, user_id: str):
        """사용자의 캐시 삭제 (안전한 버전)"""
        try:
            # 기존 캐시 삭제
            redis_bin_client.delete(cls._index_key(user_id))
            redis_client.delete(cls._chunk_text_key(user_id))
            redis_client.delete(cls._meta_key(user_id))
            
            logger.info(f"✅ FAISS 캐시 삭제 완료: user_id={user_id}")
            
        except Exception as e:
            logger.error(f"❌ FAISS 캐시 삭제 실패: {e}")

    @classmethod
    def clear_all_cache(cls):
        """모든 FAISS 캐시 삭제 (개발/테스트용)"""
        try:
            # 패턴으로 모든 관련 키 삭제
            pattern = f"{cls.INDEX_PREFIX}:*"
            keys = redis_bin_client.keys(pattern)
            if keys:
                redis_bin_client.delete(*keys)
            
            pattern = f"{cls.CHUNK_TEXT_PREFIX}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
            
            pattern = f"{cls.META_PREFIX}:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
            
            logger.info("✅ 모든 FAISS 캐시 삭제 완료")
            
        except Exception as e:
            logger.error(f"❌ 전체 캐시 삭제 실패: {e}")

class OptimizedFAISSSearchService:
    """성능 최적화된 FAISS 검색 서비스"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = 1536
    
    async def search_similar_chunks_optimized(self, user_id: str, query: str, top_k: int = 3) -> List[Dict]:
        """최적화된 유사 chunk 검색 (캐시 우선)"""
        try:
            # 1. Redis 캐시에서 인덱스 로드
            index, chunk_texts, metadata = OptimizedFAISSCache.load_faiss_index(user_id)
            
            if index is None:
                # 캐시가 없으면 DB에서 재구성
                logger.info(f"캐시가 없어서 DB에서 재구성: user_id={user_id}")
                await self._rebuild_cache_from_db(user_id)
                index, chunk_texts, metadata = OptimizedFAISSCache.load_faiss_index(user_id)
                
                if index is None:
                    return []
            
            # 2. 쿼리 embedding 생성
            query_embedding = await get_openai_embedding(query)
            query_emb_np = np.array([query_embedding]).astype("float32")
            
            # 3. FAISS 검색 수행
            D, I = index.search(query_emb_np, min(top_k, index.ntotal))
            
            # 4. 결과 처리
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < len(chunk_texts):
                    # 코사인 유사도 계산
                    similarity = dist / np.linalg.norm(query_emb_np)
                    
                    if similarity >= self.similarity_threshold:
                        results.append({
                            "text": chunk_texts[idx],
                            "similarity": float(similarity),
                            "distance": float(dist),
                            "chunk_id": idx
                        })
            
            logger.info(f"✅ 최적화된 검색 완료: {len(results)}개 결과, 쿼리='{query[:30]}...'")
            return results
            
        except Exception as e:
            logger.error(f"❌ 최적화된 검색 실패: {e}")
            return []
    
    async def _rebuild_cache_from_db(self, user_id: str):
        """DB에서 캐시 재구성 (안전한 버전)"""
        session = get_session()
        
        try:
            # DB에서 chunk metadata 가져오기
            chunks = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.chunk_id)
                .all()
            )
            
            if not chunks:
                logger.info(f"사용자 {user_id}의 chunk가 없습니다.")
                return
            
            # embedding과 텍스트 준비
            embeddings = []
            chunk_texts = []
            metadata = {
                "total_chunks": len(chunks),
                "last_updated": datetime.now().isoformat(),
                "chunk_ids": []
            }
            
            for chunk in chunks:
                try:
                    # embedding 로드
                    embedding = json.loads(chunk.embedding)
                    embeddings.append(embedding)
                    
                    # chunk 텍스트 재구성
                    chunk_text = self._reconstruct_chunk_text(session, chunk)
                    chunk_texts.append(chunk_text)
                    
                    metadata["chunk_ids"].append(chunk.chunk_id)
                    
                except Exception as chunk_error:
                    logger.error(f"chunk {chunk.chunk_id} 처리 실패: {chunk_error}")
                    continue
            
            if not embeddings:
                logger.warning(f"처리할 수 있는 embedding이 없습니다: user_id={user_id}")
                return
            
            # FAISS 인덱스 생성
            try:
                embeddings_np = np.array(embeddings).astype("float32")
                index = faiss.IndexFlatIP(embeddings_np.shape[1])
                index.add(embeddings_np)
                
                # 캐시에 저장
                OptimizedFAISSCache.save_faiss_index(user_id, index, chunks, chunk_texts, metadata)
                
                logger.info(f"✅ 캐시 재구성 완료: user_id={user_id}, chunks={len(chunks)}")
                
            except Exception as index_error:
                logger.error(f"FAISS 인덱스 생성 실패: {index_error}")
                
        except Exception as e:
            logger.error(f"❌ 캐시 재구성 실패: {e}")
        finally:
            session.close()
    
    def _reconstruct_chunk_text(self, session, chunk: ChunkMetadata) -> str:
        """chunk metadata에서 실제 텍스트 재구성"""
        try:
            messages = (
                session.query(AIMessage)
                .filter(
                    AIMessage.id >= chunk.start_msg_id,
                    AIMessage.id <= chunk.end_msg_id,
                    AIMessage.user_id == chunk.user_id
                )
                .order_by(AIMessage.created_at)
                .all()
            )
            
            if not messages:
                return ""
            
            chunk_text = f'[{chunk.start_time.strftime("%Y-%m-%d %H:%M:%S")} ~ {chunk.end_time.strftime("%Y-%m-%d %H:%M:%S")}]\n'
            chunk_text += "\n".join([f'{msg.role}: {msg.content}' for msg in messages])
            
            return chunk_text
            
        except Exception as e:
            logger.error(f"텍스트 재구성 실패: {e}")
            return ""
    
    async def update_cache_incrementally(self, user_id: str, new_chunks: List[Dict]):
        """새로운 chunk가 추가될 때 캐시 증분 업데이트"""
        try:
            # 기존 캐시 로드
            index, chunk_texts, metadata = OptimizedFAISSCache.load_faiss_index(user_id)
            
            if index is None:
                # 캐시가 없으면 전체 재구성
                await self._rebuild_cache_from_db(user_id)
                return
            
            # 새로운 chunk들의 embedding 생성
            new_embeddings = []
            new_chunk_texts = []
            
            for chunk_data in new_chunks:
                embedding = await get_openai_embedding(chunk_data["text"])
                new_embeddings.append(embedding)
                new_chunk_texts.append(chunk_data["text"])
            
            # 기존 인덱스에 새로운 embedding 추가
            new_embeddings_np = np.array(new_embeddings).astype("float32")
            index.add(new_embeddings_np)
            
            # chunk 텍스트와 메타데이터 업데이트
            updated_chunk_texts = chunk_texts + new_chunk_texts
            metadata["total_chunks"] += len(new_chunks)
            metadata["last_updated"] = datetime.now().isoformat()
            
            # 캐시 업데이트
            OptimizedFAISSCache.save_faiss_index(user_id, index, [], updated_chunk_texts, metadata)
            
            logger.info(f"✅ 캐시 증분 업데이트 완료: user_id={user_id}, new_chunks={len(new_chunks)}")
            
        except Exception as e:
            logger.error(f"❌ 캐시 증분 업데이트 실패: {e}")
    
    async def search_with_time_filter_optimized(self, user_id: str, query: str, 
                                              start_date: Optional[datetime] = None,
                                              end_date: Optional[datetime] = None,
                                              top_k: int = 3) -> List[Dict]:
        """시간 필터를 적용한 최적화된 검색"""
        # 시간 필터는 DB 쿼리가 필요하므로 기존 방식 사용
        # 하지만 결과는 캐시된 텍스트 사용
        session = get_session()
        
        try:
            # 시간 필터로 chunk ID 찾기
            query_filter = session.query(ChunkMetadata).filter_by(user_id=user_id)
            
            if start_date:
                query_filter = query_filter.filter(ChunkMetadata.start_time >= start_date)
            if end_date:
                query_filter = query_filter.filter(ChunkMetadata.end_time <= end_date)
            
            filtered_chunks = query_filter.order_by(ChunkMetadata.chunk_id).all()
            
            if not filtered_chunks:
                return []
            
            # 캐시에서 전체 인덱스 로드
            index, chunk_texts, metadata = OptimizedFAISSCache.load_faiss_index(user_id)
            
            if index is None:
                await self._rebuild_cache_from_db(user_id)
                index, chunk_texts, metadata = OptimizedFAISSCache.load_faiss_index(user_id)
                
                if index is None:
                    return []
            
            # 필터링된 chunk들의 embedding만으로 서브인덱스 생성
            filtered_embeddings = []
            filtered_texts = []
            chunk_id_to_idx = {chunk.chunk_id: idx for idx, chunk in enumerate(filtered_chunks)}
            
            for chunk in filtered_chunks:
                embedding = json.loads(chunk.embedding)
                filtered_embeddings.append(embedding)
                filtered_texts.append(chunk_texts[chunk_id_to_idx[chunk.chunk_id]])
            
            # 서브인덱스로 검색
            filtered_embeddings_np = np.array(filtered_embeddings).astype("float32")
            sub_index = faiss.IndexFlatIP(filtered_embeddings_np.shape[1])
            sub_index.add(filtered_embeddings_np)
            
            # 쿼리 검색
            query_embedding = await get_openai_embedding(query)
            query_emb_np = np.array([query_embedding]).astype("float32")
            
            D, I = sub_index.search(query_emb_np, min(top_k, len(filtered_chunks)))
            
            # 결과 처리
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < len(filtered_texts):
                    similarity = dist / np.linalg.norm(query_emb_np)
                    
                    if similarity >= self.similarity_threshold:
                        results.append({
                            "text": filtered_texts[idx],
                            "similarity": float(similarity),
                            "distance": float(dist),
                            "chunk_id": filtered_chunks[idx].chunk_id
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"시간 필터 검색 실패: {e}")
            return []
        finally:
            session.close() 
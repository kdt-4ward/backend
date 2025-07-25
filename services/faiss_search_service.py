from typing import List, Dict, Optional, Tuple
from db.db import get_session
from db.db_tables import ChunkMetadata, AIMessage
from services.openai_client import get_openai_embedding
import numpy as np
import json
from datetime import datetime
import faiss
from utils.log_utils import get_logger

logger = get_logger(__name__)

class FAISSSearchService:
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = 1536  # OpenAI embedding-3-small 차원
    
    async def search_similar_chunks(self, user_id: str, query: str, top_k: int = 3) -> List[Dict]:
        """FAISS를 사용한 유사한 chunk 검색"""
        session = get_session()
        
        try:
            # 모든 chunk metadata 가져오기
            chunks = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.chunk_id)
                .all()
            )
            
            if not chunks:
                logger.info(f"No chunks found for user {user_id}")
                return []
            
            logger.info(f"Searching through {len(chunks)} chunks for user {user_id}")
            
            # FAISS 인덱스 생성
            embeddings = []
            for chunk in chunks:
                embedding = json.loads(chunk.embedding)
                embeddings.append(embedding)
            
            embeddings_np = np.array(embeddings).astype("float32")
            
            # FAISS IndexFlatIP 사용 (코사인 유사도 기반)
            index = faiss.IndexFlatIP(embeddings_np.shape[1])
            index.add(embeddings_np)
            
            # 쿼리 embedding 생성
            query_embedding = await get_openai_embedding(query)
            query_emb_np = np.array([query_embedding]).astype("float32")
            
            # FAISS에서 검색
            D, I = index.search(query_emb_np, min(top_k, len(chunks)))
            
            # 결과 처리
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < len(chunks):
                    chunk = chunks[idx]
                    
                    # 코사인 유사도 계산
                    similarity = dist / np.linalg.norm(query_emb_np) / np.linalg.norm(embeddings_np[idx])
                    
                    if similarity >= self.similarity_threshold:
                        chunk_text = self._reconstruct_chunk_text(session, chunk)
                        results.append({
                            "text": chunk_text,
                            "similarity": similarity,
                            "distance": float(dist),
                            "start_time": chunk.start_time,
                            "end_time": chunk.end_time,
                            "chunk_id": chunk.chunk_id,
                            "start_msg_id": chunk.start_msg_id,
                            "end_msg_id": chunk.end_msg_id
                        })
            
            logger.info(f"Found {len(results)} relevant chunks for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed for user {user_id}: {e}")
            return []
        finally:
            session.close()
    
    async def search_with_time_filter(self, user_id: str, query: str, 
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    top_k: int = 3) -> List[Dict]:
        """시간 필터를 적용한 FAISS 검색"""
        session = get_session()
        
        try:
            # 시간 필터 적용하여 chunk 가져오기
            query_filter = session.query(ChunkMetadata).filter_by(user_id=user_id)
            
            if start_date:
                query_filter = query_filter.filter(ChunkMetadata.start_time >= start_date)
            if end_date:
                query_filter = query_filter.filter(ChunkMetadata.end_time <= end_date)
            
            chunks = query_filter.order_by(ChunkMetadata.chunk_id).all()
            
            if not chunks:
                logger.info(f"No chunks found for user {user_id} with time filter")
                return []
            
            # FAISS 인덱스 생성
            embeddings = []
            for chunk in chunks:
                embedding = json.loads(chunk.embedding)
                embeddings.append(embedding)
            
            embeddings_np = np.array(embeddings).astype("float32")
            
            # FAISS IndexFlatIP 사용 (코사인 유사도 기반)
            index = faiss.IndexFlatIP(embeddings_np.shape[1])
            index.add(embeddings_np)
            
            # 쿼리 embedding 생성
            query_embedding = await get_openai_embedding(query)
            query_emb_np = np.array([query_embedding]).astype("float32")
            
            # FAISS에서 검색
            D, I = index.search(query_emb_np, min(top_k, len(chunks)))
            
            # 결과 처리
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < len(chunks):
                    chunk = chunks[idx]
                    
                    # 코사인 유사도 계산
                    similarity = dist / np.linalg.norm(query_emb_np) / np.linalg.norm(embeddings_np[idx])
                    
                    if similarity >= self.similarity_threshold:
                        chunk_text = self._reconstruct_chunk_text(session, chunk)
                        results.append({
                            "text": chunk_text,
                            "similarity": similarity,
                            "distance": float(dist),
                            "start_time": chunk.start_time,
                            "end_time": chunk.end_time,
                            "chunk_id": chunk.chunk_id
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Time-filtered FAISS search failed: {e}")
            return []
        finally:
            session.close()
    
    async def search_by_keywords_with_faiss(self, user_id: str, keywords: List[str], 
                                          top_k: int = 3) -> List[Dict]:
        """키워드 기반 검색 + FAISS 유사도 정렬"""
        session = get_session()
        
        try:
            # 키워드로 텍스트 검색
            keyword_chunks = set()
            for keyword in keywords:
                # 메시지 내용에서 키워드 검색
                messages = (
                    session.query(AIMessage)
                    .filter(
                        AIMessage.user_id == user_id,
                        AIMessage.content.contains(keyword)
                    )
                    .all()
                )
                
                for msg in messages:
                    # 해당 메시지가 포함된 chunk 찾기
                    chunk = (
                        session.query(ChunkMetadata)
                        .filter(
                            ChunkMetadata.user_id == user_id,
                            ChunkMetadata.start_msg_id <= msg.id,
                            ChunkMetadata.end_msg_id >= msg.id
                        )
                        .first()
                    )
                    
                    if chunk:
                        keyword_chunks.add(chunk.chunk_id)
            
            if not keyword_chunks:
                return []
            
            # 키워드로 찾은 chunk들의 embedding으로 FAISS 검색
            keyword_chunk_metadatas = (
                session.query(ChunkMetadata)
                .filter(
                    ChunkMetadata.user_id == user_id,
                    ChunkMetadata.chunk_id.in_(keyword_chunks)
                )
                .all()
            )
            
            if not keyword_chunk_metadatas:
                return []
            
            # FAISS 인덱스 생성
            embeddings = []
            for chunk in keyword_chunk_metadatas:
                embedding = json.loads(chunk.embedding)
                embeddings.append(embedding)
            
            embeddings_np = np.array(embeddings).astype("float32")
            
            # FAISS IndexFlatIP 사용 (코사인 유사도 기반)
            index = faiss.IndexFlatIP(embeddings_np.shape[1])
            index.add(embeddings_np)
            
            # 키워드들을 하나의 쿼리로 결합
            combined_query = " ".join(keywords)
            query_embedding = await get_openai_embedding(combined_query)
            query_emb_np = np.array([query_embedding]).astype("float32")
            
            # FAISS에서 검색
            D, I = index.search(query_emb_np, min(top_k, len(keyword_chunk_metadatas)))
            
            # 결과 처리
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < len(keyword_chunk_metadatas):
                    chunk = keyword_chunk_metadatas[idx]
                    
                    # 코사인 유사도 계산
                    similarity = dist / np.linalg.norm(query_emb_np) / np.linalg.norm(embeddings_np[idx])
                    
                    if similarity >= self.similarity_threshold:
                        chunk_text = self._reconstruct_chunk_text(session, chunk)
                        results.append({
                            "text": chunk_text,
                            "similarity": similarity,
                            "distance": float(dist),
                            "start_time": chunk.start_time,
                            "end_time": chunk.end_time,
                            "chunk_id": chunk.chunk_id,
                            "matched_keywords": keywords
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search with FAISS failed: {e}")
            return []
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
                logger.warning(f"No messages found for chunk {chunk.chunk_id}")
                return ""
            
            chunk_text = f'[{chunk.start_time.strftime("%Y-%m-%d %H:%M:%S")} ~ {chunk.end_time.strftime("%Y-%m-%d %H:%M:%S")}]\n'
            chunk_text += "\n".join([f'{msg.role}: {msg.content}' for msg in messages])
            
            return chunk_text
            
        except Exception as e:
            logger.error(f"Failed to reconstruct chunk text: {e}")
            return ""
    
    def get_chunk_statistics(self, user_id: str) -> Dict:
        """사용자의 chunk 통계 정보"""
        session = get_session()
        
        try:
            # 전체 chunk 개수
            total_chunks = session.query(ChunkMetadata).filter_by(user_id=user_id).count()
            
            if total_chunks == 0:
                return {
                    "total_chunks": 0,
                    "date_range": None,
                    "avg_messages_per_chunk": 0
                }
            
            # 시간 범위
            first_chunk = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.start_time)
                .first()
            )
            
            last_chunk = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.end_time.desc())
                .first()
            )
            
            # 평균 메시지 수 계산
            total_messages = 0
            for chunk in session.query(ChunkMetadata).filter_by(user_id=user_id).all():
                msg_count = (
                    session.query(AIMessage)
                    .filter(
                        AIMessage.id >= chunk.start_msg_id,
                        AIMessage.id <= chunk.end_msg_id,
                        AIMessage.user_id == user_id
                    )
                    .count()
                )
                total_messages += msg_count
            
            avg_messages_per_chunk = total_messages / total_chunks if total_chunks > 0 else 0
            
            return {
                "total_chunks": total_chunks,
                "date_range": {
                    "start": first_chunk.start_time if first_chunk else None,
                    "end": last_chunk.end_time if last_chunk else None
                },
                "avg_messages_per_chunk": round(avg_messages_per_chunk, 2),
                "total_messages": total_messages
            }
            
        except Exception as e:
            logger.error(f"Failed to get chunk statistics: {e}")
            return {}
        finally:
            session.close()
    
    async def build_faiss_index_for_user(self, user_id: str) -> Optional[faiss.Index]:
        """사용자별 FAISS 인덱스 생성 (캐싱용)"""
        session = get_session()
        
        try:
            chunks = (
                session.query(ChunkMetadata)
                .filter_by(user_id=user_id)
                .order_by(ChunkMetadata.chunk_id)
                .all()
            )
            
            if not chunks:
                return None
            
            # embedding 배열 생성
            embeddings = []
            for chunk in chunks:
                embedding = json.loads(chunk.embedding)
                embeddings.append(embedding)
            
            embeddings_np = np.array(embeddings).astype("float32")
            
            # FAISS 인덱스 생성
            index = faiss.IndexFlatIP(embeddings_np.shape[1])
            index.add(embeddings_np)
            
            logger.info(f"Built FAISS index for user {user_id} with {len(chunks)} chunks")
            return index
            
        except Exception as e:
            logger.error(f"Failed to build FAISS index for user {user_id}: {e}")
            return None
        finally:
            session.close() 
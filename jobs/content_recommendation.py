import logging
import requests
import random
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from core.dependencies import get_db_session
from db.db_tables import User, Couple, EmotionLog, Post
from core.settings import settings
from utils.language import detect_language
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

def safe_params(params: dict) -> dict:
    """aiohttp용 안전한 파라미터 변환"""
    safe_params = {}
    for key, value in params.items():
        if isinstance(value, bool):
            safe_params[key] = str(value).lower()
        elif isinstance(value, (int, float)):
            safe_params[key] = str(value)
        else:
            safe_params[key] = value
    return safe_params

class TMDBService:
    """TMDB API를 사용한 영화 추천 서비스"""
    
    def __init__(self):
        self.api_key = settings.tmdb_api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.language = "ko-KR"
    
    async def search_movies(self, query: str, page: int = 1) -> List[Dict]:
        """영화 검색"""
        try:
            url = f"{self.base_url}/search/movie"
            params = safe_params({
                'api_key': self.api_key,
                'language': self.language,
                'query': query,
                'page': page,
                'include_adult': False
            })
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('results', [])
        except Exception as e:
            logger.error(f"TMDB 영화 검색 오류: {e}")
            return []
    
    async def get_popular_movies(self, genre_id: Optional[int] = None) -> List[Dict]:
        """인기 영화 목록 (비동기로 변경)"""
        try:
            if genre_id:
                url = f"{self.base_url}/discover/movie"
                params = {
                    'api_key': self.api_key,
                    'language': self.language,
                    'with_genres': genre_id,
                    'sort_by': 'popularity.desc',
                    'page': 1
                }
            else:
                url = f"{self.base_url}/movie/popular"
                params = {
                    'api_key': self.api_key,
                    'language': self.language,
                    'page': 1
                }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('results', [])
        except Exception as e:
            logger.error(f"TMDB 인기 영화 조회 오류: {e}")
            return []


class YouTubeService:
    """YouTube API를 사용한 노래 추천 서비스"""
    
    def __init__(self):
        self.api_key = settings.youtube_api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    async def search_music(self, query: str, max_results: int = 10) -> List[Dict]:
        """음악 검색"""
        try:
            url = f"{self.base_url}/search"
            params = {
                'key': self.api_key,
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'videoCategoryId': '10',  # 음악 카테고리
                'maxResults': str(max_results),  # int -> string으로 변경
                'relevanceLanguage': 'ko'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data.get('items', [])
        except Exception as e:
            logger.error(f"YouTube 음악 검색 오류: {e}")
            return []

# 영화 정보 강화 함수
async def enhance_movie_info(movie_title: str, movie_reason: str) -> Dict[str, Any]:
    """TMDB API를 통해 영화 정보 강화"""
    tmdb_service = TMDBService()
    try:
        movie_search_results = await tmdb_service.search_movies(movie_title)
        movie_info = None
        if movie_search_results:
            # 제목이 가장 유사한 영화 선택
            for movie in movie_search_results:
                if movie.get('original_title', '').lower() in movie_title.lower() or \
                   movie_title.lower() in movie.get('original_title', '').lower():
                    movie_info = {
                        "title": movie.get('original_title', movie_title),
                        "overview": movie.get('overview', ''),
                        "poster_path": movie.get('poster_path'),
                        "release_date": movie.get('release_date'),
                        "vote_average": movie.get('vote_average'),
                        "tmdb_id": movie.get('id'),
                        "poster_url": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None
                    }
                    break
            
            # 정확히 일치하는 영화가 없으면 첫 번째 결과 사용
            if not movie_info and movie_search_results:
                movie = movie_search_results[0]
                movie_info = {
                    "title": movie.get('original_title', movie_title),
                    "overview": movie.get('overview', ''),
                    "poster_path": movie.get('poster_path'),
                    "release_date": movie.get('release_date'),
                    "vote_average": movie.get('vote_average'),
                    "tmdb_id": movie.get('id'),
                    "poster_url": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None
                }

        # TMDB에서 찾지 못한 경우 기본 정보만 제공
        if not movie_info:
            movie_info = {
                "title": movie_title,
                "overview": "상세 정보를 찾을 수 없습니다.",
                "poster_url": None,
                "tmdb_id": None
            }
        if movie_info.get('overview') and detect_language(movie_info['overview']) != 'ko':
            movie_info['overview'] = await translate_to_korean(movie_info['overview'])

        return {
            "title": movie_title,
            "reason": movie_reason,
            "tmdb_info": movie_info
        }
        
    except Exception as e:
        logger.error(f"TMDB 영화 정보 조회 실패: {e}")
        return {
            "title": movie_title,
            "reason": movie_reason,
            "tmdb_info": {
                "title": movie_title,
                "overview": "상세 정보를 찾을 수 없습니다.",
                "poster_url": None,
                "tmdb_id": None
            }
        }

async def translate_to_korean(text: str) -> str:
    """OpenAI를 사용한 영어-한국어 번역 (선택사항)"""
    try:
        from services.openai_client import call_openai_completion
        prompt = f"다음 텍스트를 한국어로 번역해주세요. 영화 개요입니다: \n{text}"
        response = await call_openai_completion([
            {"role": "system", "content": "당신은 전문 번역가입니다. 자연스러운 한국어로 번역해주세요."},
            {"role": "user", "content": prompt}])
        return response[0]
    except Exception as e:
        logger.error(f"번역 실패: {e}")
        return None

# 노래 정보 강화 함수
async def enhance_song_info(song_title: str, song_reason: str) -> Dict[str, Any]:
    """YouTube API를 통해 노래 정보 강화"""
    youtube_service = YouTubeService()
    try:
        print("===============================")
        print(song_title)
        print(song_reason)
        print("===============================")
        song_search_results = await youtube_service.search_music(song_title, max_results=5)
        song_info = None
        print("===============================")
        print(song_search_results)
        print("===============================")
        if song_search_results:
            # 제목이 가장 유사한 노래 선택
            for song in song_search_results:
                snippet = song.get('snippet', {})
                title = snippet.get('title', '').lower()
                if song_title.lower() in title or title in song_title.lower():
                    song_info = {
                        "title": snippet.get('title', song_title),
                        "channel_title": snippet.get('channelTitle', ''),
                        "published_at": snippet.get('publishedAt'),
                        "description": snippet.get('description', ''),
                        "thumbnail_url": snippet.get('thumbnails', {}).get('medium', {}).get('url'),
                        "video_id": song.get('id', {}).get('videoId'),
                        "youtube_url": f"https://www.youtube.com/watch?v={song.get('id', {}).get('videoId')}"
                    }
                    break
            
            # 정확히 일치하는 노래가 없으면 첫 번째 결과 사용
            if not song_info and song_search_results:
                song = song_search_results[0]
                snippet = song.get('snippet', {})
                song_info = {
                    "title": snippet.get('title', song_title),
                    "channel_title": snippet.get('channelTitle', ''),
                    "published_at": snippet.get('publishedAt'),
                    "description": snippet.get('description', ''),
                    "thumbnail_url": snippet.get('thumbnails', {}).get('medium', {}).get('url'),
                    "video_id": song.get('id', {}).get('videoId'),
                    "youtube_url": f"https://www.youtube.com/watch?v={song.get('id', {}).get('videoId')}"
                }
        
        # YouTube에서 찾지 못한 경우 기본 정보만 제공
        if not song_info:
            song_info = {
                "title": song_title,
                "description": "상세 정보를 찾을 수 없습니다.",
                "youtube_url": None,
                "video_id": None
            }
        
        return {
            "title": song_title,
            "reason": song_reason,
            "youtube_info": song_info
        }
        
    except Exception as e:
        logger.error(f"YouTube 노래 정보 조회 실패: {e}")
        return {
            "title": song_title,
            "reason": song_reason,
            "youtube_info": {
                "title": song_title,
                "description": "상세 정보를 찾을 수 없습니다.",
                "youtube_url": None,
                "video_id": None
            }
        }

# class CoupleContentRecommender:
#     """커플을 위한 맞춤형 콘텐츠 추천 시스템"""
    
#     def __init__(self):
#         self.tmdb_service = TMDBService()
#         self.youtube_service = YouTubeService()
        
#         # 감정별 검색 키워드
#         self.emotion_keywords = {
#             "happy": {
#                 "movies": ["행복한 영화", "코미디", "뮤지컬", "가족 영화"],
#                 "songs": ["행복한 노래", "기분 좋은 음악", "댄스 음악", "팝송"]
#             },
#             "romantic": {
#                 "movies": ["로맨스 영화", "사랑 영화", "로맨틱 코미디"],
#                 "songs": ["로맨틱 노래", "사랑 노래", "발라드", "로맨틱 팝"]
#             },
#             "sad": {
#                 "movies": ["드라마", "감동 영화", "치유 영화"],
#                 "songs": ["감성 노래", "치유 음악", "발라드", "잔잔한 음악"]
#             },
#             "excited": {
#                 "movies": ["액션 영화", "어드벤처", "스릴러"],
#                 "songs": ["신나는 노래", "댄스 음악", "힙합", "일렉트로닉"]
#             },
#             "calm": {
#                 "movies": ["평온한 영화", "자연 다큐멘터리", "명상 영화"],
#                 "songs": ["잔잔한 음악", "명상 음악", "클래식", "어쿠스틱"]
#             }
#         }
        
#         # 관계 상황별 검색 키워드
#         self.relationship_keywords = {
#             "new_couple": {
#                 "movies": ["첫사랑 영화", "로맨스", "달콤한 영화"],
#                 "songs": ["첫사랑 노래", "로맨틱 팝", "달콤한 음악"]
#             },
#             "long_term": {
#                 "movies": ["장기 연애 영화", "결혼 영화", "가족 영화"],
#                 "songs": ["장기 연애 노래", "결혼 노래", "가족 음악"]
#             },
#             "struggling": {
#                 "movies": ["치유 영화", "화해 영화", "성장 영화"],
#                 "songs": ["치유 음악", "위로 노래", "희망 노래"]
#             }
#         }
    
#     def analyze_couple_situation(self, db: Session, couple_id: int) -> Dict:
#         """커플의 현재 상황을 분석합니다."""
#         try:
#             # 커플 정보 조회
#             couple = db.query(Couple).filter(Couple.couple_id == couple_id).first()
#             if not couple:
#                 return {"error": "커플을 찾을 수 없습니다."}
            
#             # 최근 감정 로그 분석 (최근 7일)
#             recent_emotions = db.query(EmotionLog).filter(
#                 EmotionLog.user_id.in_([couple.user1_id, couple.user2_id]),
#                 EmotionLog.recorded_at >= datetime.now() - timedelta(days=7)
#             ).all()
            
#             # 최근 포스트 분석
#             recent_posts = db.query(Post).filter(
#                 Post.user_id.in_([couple.user1_id, couple.user2_id]),
#                 Post.recorded_at >= datetime.now() - timedelta(days=7)
#             ).all()
            
#             # 관계 기간 계산
#             relationship_duration = (datetime.now() - couple.created_at).days
            
#             # 감정 분석
#             emotion_counts = {}
#             for emotion in recent_emotions:
#                 emotion_type = emotion.emotion
#                 emotion_counts[emotion_type] = emotion_counts.get(emotion_type, 0) + 1
            
#             # 주요 감정 결정
#             dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "calm"
            
#             # 관계 상황 판단
#             if relationship_duration < 30:
#                 relationship_status = "new_couple"
#             elif relationship_duration > 365:
#                 relationship_status = "long_term"
#             else:
#                 # 감정 기반으로 판단
#                 negative_emotions = sum(emotion_counts.get(emotion, 0) for emotion in ["sad", "angry", "anxious"])
#                 positive_emotions = sum(emotion_counts.get(emotion, 0) for emotion in ["happy", "romantic", "excited"])
                
#                 if negative_emotions > positive_emotions:
#                     relationship_status = "struggling"
#                 else:
#                     relationship_status = "long_term"
            
#             return {
#                 "couple_id": couple_id,
#                 "relationship_duration_days": relationship_duration,
#                 "dominant_emotion": dominant_emotion,
#                 "relationship_status": relationship_status,
#                 "recent_emotions": emotion_counts,
#                 "post_count": len(recent_posts)
#             }
            
#         except Exception as e:
#             logger.error(f"커플 상황 분석 중 오류: {e}")
#             return {"error": f"분석 중 오류가 발생했습니다: {str(e)}"}
    
#     def get_movie_recommendations(self, emotion: str, relationship_status: str, count: int = 5) -> List[Dict]:
#         """영화 추천"""
#         try:
#             recommendations = []
            
#             # 감정 기반 영화 추천
#             if emotion in self.emotion_keywords:
#                 for keyword in self.emotion_keywords[emotion]["movies"]:
#                     movies = self.tmdb_service.search_movies(keyword)
#                     if movies:
#                         # 한국어 영화 우선 선택
#                         korean_movies = [m for m in movies if m.get('original_language') == 'ko']
#                         if korean_movies:
#                             recommendations.extend(korean_movies[:2])
#                         else:
#                             recommendations.extend(movies[:2])
            
#             # 관계 상황 기반 영화 추천
#             if relationship_status in self.relationship_keywords:
#                 for keyword in self.relationship_keywords[relationship_status]["movies"]:
#                     movies = self.tmdb_service.search_movies(keyword)
#                     if movies:
#                         recommendations.extend(movies[:2])
            
#             # 중복 제거 및 정렬
#             unique_movies = []
#             seen_ids = set()
#             for movie in recommendations:
#                 if movie['id'] not in seen_ids:
#                     seen_ids.add(movie['id'])
#                     unique_movies.append(movie)
            
#             # 인기도 순으로 정렬
#             unique_movies.sort(key=lambda x: x.get('popularity', 0), reverse=True)
            
#             return unique_movies[:count]
            
#         except Exception as e:
#             logger.error(f"영화 추천 생성 중 오류: {e}")
#             return []
    
#     def get_song_recommendations(self, emotion: str, relationship_status: str, count: int = 5) -> List[Dict]:
#         """노래 추천"""
#         try:
#             recommendations = []
            
#             # 감정 기반 노래 추천
#             if emotion in self.emotion_keywords:
#                 for keyword in self.emotion_keywords[emotion]["songs"]:
#                     songs = self.youtube_service.search_music(keyword, max_results=3)
#                     if songs:
#                         recommendations.extend(songs)
            
#             # 관계 상황 기반 노래 추천
#             if relationship_status in self.relationship_keywords:
#                 for keyword in self.relationship_keywords[relationship_status]["songs"]:
#                     songs = self.youtube_service.search_music(keyword, max_results=3)
#                     if songs:
#                         recommendations.extend(songs)
            
#             # 중복 제거
#             unique_songs = []
#             seen_ids = set()
#             for song in recommendations:
#                 if song['id']['videoId'] not in seen_ids:
#                     seen_ids.add(song['id']['videoId'])
#                     unique_songs.append(song)
            
#             return unique_songs[:count]
            
#         except Exception as e:
#             logger.error(f"노래 추천 생성 중 오류: {e}")
#             return []
    
#     def get_recommendations(self, db: Session, couple_id: int, content_type: str = "both") -> Dict:
#         """커플을 위한 맞춤형 콘텐츠 추천을 제공합니다."""
#         try:
#             # 커플 상황 분석
#             situation = self.analyze_couple_situation(db, couple_id)
#             if "error" in situation:
#                 return situation
            
#             dominant_emotion = situation["dominant_emotion"]
#             relationship_status = situation["relationship_status"]
            
#             recommendations = {
#                 "couple_id": couple_id,
#                 "analysis": situation,
#                 "recommendations": {}
#             }
            
#             # 영화 추천
#             if content_type in ["movies", "both"]:
#                 movies = self.get_movie_recommendations(dominant_emotion, relationship_status)
#                 recommendations["recommendations"]["movies"] = movies
            
#             # 노래 추천
#             if content_type in ["songs", "both"]:
#                 songs = self.get_song_recommendations(dominant_emotion, relationship_status)
#                 recommendations["recommendations"]["songs"] = songs
            
#             # 특별한 상황별 활동 추천
#             special_recommendations = self._get_special_recommendations(situation)
#             if special_recommendations:
#                 recommendations["recommendations"]["activities"] = special_recommendations
            
#             return recommendations
            
#         except Exception as e:
#             logger.error(f"추천 생성 중 오류: {e}")
#             return {"error": f"추천 생성 중 오류가 발생했습니다: {str(e)}"}
    
#     def _get_special_recommendations(self, situation: Dict) -> Optional[List[str]]:
#         """특별한 상황에 따른 활동 추천을 제공합니다."""
#         activities = []
        
#         # 새로운 커플인 경우
#         if situation["relationship_status"] == "new_couple":
#             activities = [
#                 "함께 요리하기",
#                 "산책하며 대화하기",
#                 "사진 찍기",
#                 "게임하기",
#                 "영화 보기"
#             ]
        
#         # 오래된 커플인 경우
#         elif situation["relationship_status"] == "long_term":
#             activities = [
#                 "새로운 취미 시작하기",
#                 "여행 계획 세우기",
#                 "함께 운동하기",
#                 "책 읽고 토론하기",
#                 "DIY 프로젝트"
#             ]
        
#         # 어려운 시기인 경우
#         elif situation["relationship_status"] == "struggling":
#             activities = [
#                 "마음 열고 대화하기",
#                 "상담사와 상담하기",
#                 "함께 명상하기",
#                 "감사 일기 쓰기",
#                 "서로의 공간 존중하기"
#             ]
        
#         return activities if activities else None
    
#     def get_daily_recommendation(self, db: Session, couple_id: int) -> Dict:
#         """일일 추천을 제공합니다."""
#         try:
#             # 기본 추천 가져오기
#             recommendations = self.get_recommendations(db, couple_id)
#             if "error" in recommendations:
#                 return recommendations
            
#             # 오늘의 특별 추천 추가
#             today = datetime.now().strftime("%Y-%m-%d")
#             daily_tip = self._get_daily_tip(recommendations["analysis"])
            
#             recommendations["daily"] = {
#                 "date": today,
#                 "tip": daily_tip,
#                 "activity_suggestion": self._get_activity_suggestion(recommendations["analysis"])
#             }
            
#             return recommendations
            
#         except Exception as e:
#             logger.error(f"일일 추천 생성 중 오류: {e}")
#             return {"error": f"일일 추천 생성 중 오류가 발생했습니다: {str(e)}"}
    
#     def _get_daily_tip(self, analysis: Dict) -> str:
#         """분석 결과에 따른 일일 팁을 제공합니다."""
#         emotion = analysis["dominant_emotion"]
        
#         tips = {
#             "happy": "오늘의 행복한 기분을 파트너와 함께 나누어보세요!",
#             "romantic": "로맨틱한 분위기를 더욱 깊게 만들어보세요.",
#             "sad": "서로의 감정을 이해하고 위로해주세요.",
#             "excited": "흥미진진한 에너지를 함께 활용해보세요!",
#             "calm": "평온한 시간을 함께 보내며 깊은 대화를 나누어보세요."
#         }
        
#         return tips.get(emotion, "오늘도 서로를 사랑하며 함께해주세요!")
    
#     def _get_activity_suggestion(self, analysis: Dict) -> str:
#         """분석 결과에 따른 활동 제안을 제공합니다."""
#         emotion = analysis["dominant_emotion"]
        
#         activities = {
#             "happy": "함께 춤추거나 노래를 불러보세요!",
#             "romantic": "캔들라이트 디너나 마사지를 해보세요.",
#             "sad": "따뜻한 차를 마시며 대화해보세요.",
#             "excited": "새로운 활동이나 스포츠를 함께 해보세요!",
#             "calm": "함께 요가나 명상을 해보세요."
#         }
        
#         return activities.get(emotion, "서로의 취향에 맞는 활동을 찾아보세요!")


# # 전역 인스턴스 생성
# couple_recommender = CoupleContentRecommender()


# def get_couple_recommendations(couple_id: int, content_type: str = "both") -> Dict:
#     """커플 추천 API용 함수"""
#     db = get_db_session()
#     try:
#         return couple_recommender.get_recommendations(db, couple_id, content_type)
#     finally:
#         db.close()


# def get_daily_couple_recommendation(couple_id: int) -> Dict:
#     """일일 커플 추천 API용 함수"""
#     db = get_db_session()
#     try:
#         return couple_recommender.get_daily_recommendation(db, couple_id)
#     finally:
#         db.close()


# def analyze_couple_situation(couple_id: int) -> Dict:
#     """커플 상황 분석 API용 함수"""
#     db = get_db_session()
#     try:
#         return couple_recommender.analyze_couple_situation(db, couple_id)
#     finally:
#         db.close()

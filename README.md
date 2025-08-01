# LuvTune Backend

FastAPI 기반의 커플 소통 분석 및 추천 시스템 백엔드

## 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 값들을 설정
```

### 2. 실행

#### 개발 환경
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Docker 환경
```bash
docker-compose up -d
```

## 📋 필수 환경 변수

`.env` 파일에 다음 변수들을 설정해야 합니다:

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Database
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_ENDPOINT=your_db_endpoint
DB_PORT=3306
DB_NAME=your_db_name

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_SECONDS=3600
REFRESH_TOKEN_EXPIRE_SECONDS=86400

# External APIs
TMDB_API_KEY=your_tmdb_api_key
YOUTUBE_API_KEY=your_youtube_api_key

# AWS S3
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_ACCESS_KEY=your_s3_secret_key
S3_REGION=your_s3_region
S3_BUCKET_NAME=your_s3_bucket

# Extra Settings
SUM_TURN_THRESHOLD=1~4
SUM_REMAINING_SIZE=0~3 # SUM_TURN_THRESHOLD 보다 낮아야 합니다.
SUM_TRIGGER_TOKENS=2000
FAISS_TURNS_PER_CHUNK=10
FAISS_OVERLAP_TURNS=2
FAISS_THRESHOLD=0.8
```

# 로컬에서 디렉터리 연결하여 사용함
# AWS s3 연동 시 필요없는 코드
import boto3
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import os
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("BUCKET_NAME")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

@router.post("/upload/image/")
async def upload_image(file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1]
    filename = f"{uuid4()}.{ext}"

    # S3 업로드
    s3.upload_fileobj(
        file.file,
        BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": file.content_type}  # 공개 읽기 권한
    )

    image_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"
    return JSONResponse(content={"image_url": image_url})






















# 로컬 디렉토리 테스트 용
# UPLOAD_DIR = "./uploads"
# os.makedirs(UPLOAD_DIR, exist_ok=True)  # 폴더 없으면 자동 생성

# @router.post("/upload/image/")
# async def upload_image(file: UploadFile = File(...)):
#     ext = file.filename.split('.')[-1]
#     filename = f"{uuid4()}.{ext}"
#     file_path = os.path.join(UPLOAD_DIR, filename)

#     with open(file_path, "wb") as f:
#         content = await file.read()
#         f.write(content)
        
#     # 나중에 localhost 로 변경
#     image_url = f"http://192.168.0.217:8000/uploads/{filename}"
#     return JSONResponse(content={"image_url": image_url})

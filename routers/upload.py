# 로컬에서 디렉터리 연결하여 사용함
# AWS s3 연동 시 필요없는 코드

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import os
from uuid import uuid4

router = APIRouter()

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # 폴더 없으면 자동 생성

@router.post("/upload/image/")
async def upload_image(file: UploadFile = File(...)):
    ext = file.filename.split('.')[-1]
    filename = f"{uuid4()}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # 나중에 localhost 로 변경
    image_url = f"http://192.168.0.217:8000/uploads/{filename}"
    return JSONResponse(content={"image_url": image_url})

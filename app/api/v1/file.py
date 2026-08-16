from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import os
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/files", tags=["文件管理"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload/pdf", summary="上传PDF文件")
def upload_pdf(
        file: UploadFile = File(..., description="PDF文件"),
        current_user: User = Depends(get_current_user)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持上传PDF文件")

    filename = f"{current_user.id}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return {
        "filename": filename,
        "file_size": os.path.getsize(file_path),
        "save_path": str(file_path)
    }
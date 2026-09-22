from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.config import get_settings
from app.core.response import success
from app.db.database import get_db
from app.models.user import User
from app.models.document import Document
from app.services.document_parser import parse_document
from app.utils.text_splitter import split_text_with_overlap
from app.utils.llm_client import llm_client
from app.utils.vector_store import vector_store


import logging


logger = logging.getLogger("file-api")



router = APIRouter(prefix="/files", tags=["文件管理"])

settings = get_settings()
UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload", summary="上传文档并解析存库")
def upload_document(
        file: UploadFile = File(..., description="支持 pdf 、docx 格式，单文件最大10MB"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1、读取上传文件的字节内容
    file_bytes = file.file.read()

    # 2、调用解析服务自动提取文本
    doc_type, content = parse_document(file_bytes, file.filename)

    # 3、解析结果 + 文档信息存入数据库
    db_doc = Document(
        filename=file.filename,
        content=content,
        file_type=doc_type,
        user_id=current_user.id,
        file_size=len(file_bytes)
    )
    db.add(db_doc)
    try:
        # 先 flush 获取文档ID，但不提交事务；向量失败时数据库记录会自动回滚
        db.flush()
        db.refresh(db_doc)

        # ========== 自动分块+向量化+向量入库 ==========
        # 1. 文本分块
        chunks = split_text_with_overlap(db_doc.content, chunk_size=500, chunk_overlap=100)

        # 2. 批量生成向量
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = llm_client.get_embeddings(chunk_texts)

        # 3. 构造分块ID与元数据
        chunk_ids = [f"doc_{db_doc.id}_chunk_{i:04d}" for i in range(len(chunks))]
        metadatas = [
            {
                "document_id": db_doc.id,
                "document_title": db_doc.filename,
                "user_id": current_user.id,
                "chunk_index": i,
                **chunk["metadata"]
            }
            for i, chunk in enumerate(chunks)
        ]

        # 4. 批量存入向量库
        vector_store.add_documents_with_embeddings(
            collection_name="documents",
            ids=chunk_ids,
            documents=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        # 5. 向量和数据库都成功后统一提交事务
        db.commit()
        db.refresh(db_doc)
    except Exception as e:
        db.rollback()
        # 向量可能已部分写入，执行一次幂等清理，避免留下孤立分块
        if db_doc.id is not None:
            try:
                vector_store.delete_by_metadata({
                    "document_id": db_doc.id,
                    "user_id": current_user.id
                })
            except Exception as cleanup_error:
                logger.warning(
                    f"[文档上传] 向量清理失败，document_id={db_doc.id}, error={str(cleanup_error)}"
                )

        logger.error(f"[文档上传失败] filename={file.filename}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="文档上传失败，请稍后重试") from e

    # 4、返回结果
    return {
        "id": db_doc.id,
        "title": db_doc.filename,
        "doc_type": db_doc.file_type,
        "content_length": len(db_doc.content),
        "file_size":db_doc.file_size,
        "create_time": db_doc.create_time,
        "message": "上传并解析成功"
    }

@router.get("", summary="获取当前用户的文档列表")
def get_my_documents(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 查询当前用户的所有文档，按创建时间倒序（最新的在前面）
    doc_list = db.query(Document).filter(
        Document.user_id == current_user.id
    ).order_by(Document.create_time.desc()).all()

    # 组装返回数据，不返回content长文本
    result = []
    for doc in doc_list:
        result.append({
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "file_size": doc.file_size,
            "content_length": len(doc.content),
            "create_time": doc.create_time
        })
    return {
        "total": len(result),
        "list": result,
        "message": "查询成功"
    }


@router.delete("/{doc_id}", summary="删除指定文档（仅本人可删除）")
def delete_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1、校验文档归属
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在或无权限访问")

    try:
        # 2、先删除 ChromaDB 向量分块（可重建索引优先删）
        # 按 document_id + user_id 双条件删除，避免跨用户误删
        vector_store.delete_by_metadata({
            "document_id": doc_id,
            "user_id": current_user.id
        })
        logger.info(f"[文档删除] 向量分块已删除，document_id={doc_id}, user_id={current_user.id}")

        # 3、再删除 MySQL 业务记录
        db.delete(doc)
        db.commit()
        logger.info(f"[文档删除] 数据库记录已删除，document_id={doc_id}")

        return success(message="删除成功")
    except Exception as e:
        db.rollback()
        logger.error(f"[文档删除失败] document_id={doc_id}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败，请稍后重试") from e


@router.get("/test-error")
def test_error():
    """测试全局异常处理器是否生效"""
    raise RuntimeError("这是测试业务异常")

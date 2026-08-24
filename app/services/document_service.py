from sqlalchemy.orm import Session
from app.models.document import Document
from app.utils.text_splitter import split_text_with_overlap
from app.utils.llm_client import llm_client
from app.utils.vector_store import vector_store


def get_user_all_documents_content(db: Session, user_id: int) -> str:
    """
    读取指定用户所有已上传文档的纯文本内容，拼接为完整参考上下文
    :param db: 数据库会话对象
    :param user_id: 用户ID
    :return: 所有文档内容拼接后的字符串，无文档时返回空字符串
    """
    # 查询当前用户的所有文档
    documents = db.query(Document).filter(Document.user_id == user_id).all()

    if not documents:
        return ""

    content_parts = []
    for doc in documents:
        # 字段名和模型保持一致：filename 是文件名，content 是解析后的文本
        content_parts.append(f"文档《{doc.filename}》:\n{doc.content}")

    # 用空行分隔不同文档
    return "\n\n".join(content_parts)
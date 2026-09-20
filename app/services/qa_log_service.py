import logging
import re
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.qa_log import QALog

logger = logging.getLogger("qa-log-service")

EMAIL_PATTERN = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|authorization|access[_-]?token|password)\s*[:=]\s*([^\s,;]+)"
)


def _sanitize_text(value: Optional[str], max_length: int) -> Optional[str]:
    """对日志文本做基础脱敏和长度截断，避免邮箱、密钥等信息直接落库"""
    if value is None:
        return None

    text = str(value)
    text = EMAIL_PATTERN.sub(
        lambda match: f"{match.group(1)[:2]}***@{match.group(2)}",
        text
    )
    text = SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=***", text)
    return text[:max_length]


def create_qa_log(
    user_id: int,
    question: str,
    answer_summary: str,
    latency_ms: int,
    hit_knowledge: bool,
    status: str = "success",
    error_msg: Optional[str] = None
) -> bool:
    """
    创建一条问答日志
    :param user_id: 用户ID
    :param question: 用户问题（自动截断脱敏）
    :param answer_summary: 回答摘要（不保存完整回答）
    :param latency_ms: 总耗时，单位毫秒
    :param hit_knowledge: 是否命中知识库
    :param status: 状态 success / failed
    :param error_msg: 失败时的错误信息
    :return: 是否写入成功，失败只打日志不抛出异常
    """
    db = SessionLocal()
    try:
        # 基础脱敏与截断：避免过长内容和敏感信息入库
        clean_question = _sanitize_text(question, 500) or ""
        clean_summary = _sanitize_text(answer_summary, 300) or ""
        clean_error = _sanitize_text(error_msg, 200)

        log = QALog(
            user_id=user_id,
            question=clean_question,
            answer_summary=clean_summary,
            latency_ms=latency_ms,
            hit_knowledge=hit_knowledge,
            status=status,
            error_msg=clean_error
        )
        db.add(log)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"[问答日志写入失败] user_id={user_id}, error={str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


def list_qa_logs_admin(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    keyword: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Tuple[int, List[dict]]:
    """
    管理员分页查询问答日志
    :param page: 页码，从1开始
    :param page_size: 每页条数
    :param user_id: 按用户筛选，可选
    :param keyword: 问题关键词模糊匹配，可选
    :param start_time: 开始时间，可选
    :param end_time: 结束时间，可选
    :return: (总数, 日志列表)
    """
    query = db.query(QALog)

    # 动态拼接过滤条件
    if user_id:
        query = query.filter(QALog.user_id == user_id)
    if keyword:
        query = query.filter(QALog.question.like(f"%{keyword}%"))
    if start_time:
        query = query.filter(QALog.create_time >= start_time)
    if end_time:
        query = query.filter(QALog.create_time <= end_time)

    # 统计总数
    total = query.count()
    # 分页 + 按创建时间倒序
    offset = (page - 1) * page_size
    logs = query.order_by(QALog.create_time.desc()).offset(offset).limit(page_size).all()

    # 组装返回结果，统一脱敏，兼容历史日志
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "question": _sanitize_text(log.question, 500),
            "answer_summary": _sanitize_text(log.answer_summary, 300),
            "latency_ms": log.latency_ms,
            "hit_knowledge": log.hit_knowledge,
            "status": log.status,
            "error_msg": _sanitize_text(log.error_msg, 200),
            "create_time": log.create_time
        })
    return total, result








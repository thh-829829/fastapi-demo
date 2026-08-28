import logging

logger = logging.getLogger("text-splitter")


def split_text_with_overlap(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100 ,
    doc_id: str = "unknown"
) -> list:
    """
    带重叠窗口的文本分块，同时返回分块元数据
    :param text: 待切割的原始长文本
    :param chunk_size: 单个分块的最大字符数，默认500字符
    :param chunk_overlap: 相邻分块的重叠字符数，默认100
    :param doc_id: 所属文档ID，用于溯源
    :return: 分块列表，每个元素为字典，包含 text 和 metadata
    """
    try:
        logger.info(f"[文本分块] 开始分块，doc_id={doc_id}，文本长度：{len(text)}，chunk_size={chunk_size}，overlap={chunk_overlap}")

        # 去除首位空白
        text = text.strip()
        if not text:
            logger.warning(f"[文本分块] 输入文本为空，doc_id={doc_id}")
            return []

        # 边界校验，重叠长度不能大于块大小
        if chunk_overlap >= chunk_size:
            logger.error(f"[文本分块] 参数错误：重叠长度({chunk_overlap}) >= 分块大小({chunk_size})")
            raise RuntimeError("分块参数错误：重叠长度不能大于等于分块大小")

        chunks = []
        start = 0
        text_length = len(text)
        chunk_index = 0

        # 循环切割，直到处理完所有文本
        while start < text_length:
            # 计算当前块的结束位置
            end = start + chunk_size
            if end > text_length:
                end = text_length

            # 截取当前块文本
            chunk_text = text[start:end]

            # 组装分块数据，携带元信息
            chunk_data = {
                "text": chunk_text,
                "metadata": {
                    "doc_id": doc_id,
                    "chunk_index": chunk_index,
                    "start_pos": start,
                    "end_pos": end,
                    "char_length": len(chunk_text)
                }
            }
            chunks.append(chunk_data)

            # 移动起始位置，减去重叠长度
            start = end - chunk_overlap
            chunk_index += 1

            # 处理最后一块，避免重复截取
            if end >= text_length:
                break

        logger.info(f"[文本分块] 分块完成，doc_id={doc_id}，共生成 {len(chunks)} 个分块")
        return chunks

    except RuntimeError:
        # 已经是业务异常，直接抛出
        raise
    except Exception as e:
        logger.error(f"[文本分块] 分块处理失败，doc_id={doc_id}，错误：{str(e)}", exc_info=True)
        raise RuntimeError("文本分块处理失败") from e

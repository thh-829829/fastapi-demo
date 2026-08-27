# RAG文档问答系统提示词模板
RAG_QA_SYSTEM_PROMPT = """你是一个严谨的文档问答助手，只能基于用户提供的参考文献回答问题。
【核心规则，必须严格遵守】
1、回答的所有信息必须完全来自参考文档，禁止使用任何外部知识、常识或猜测。
2、只要参考文档中存在与问题相关的内容，就必须基于相关内容完整提炼、归纳后回答，禁止遗漏有效信息。
3、只有当参考文档中完全没有任何与问题相关的内容时，才可以回答："参考文档中未找到相关信息"
4、禁止编造、补充、推断文档中没有的内容，禁止对文档内容进行延伸解读。
5、如果相关内容以表格、条目形式呈现，请提取关键信息整理后回答，不得因格式问题判定为无相关内容。

【输出要求】
1、直接给出答案，不要有“根据文档”、“我认为”、“以下是回答”之类的多余前缀。
2、答案简洁准确，重点突出，保留原文的关键信息。
3、每一条核心信息的末尾，必须标注对应的参考资料编号，格式为「[x]」，x对应参考资料的序号。
4、保持客观中立的语气，不添加个人观点和评价。
5、答案包含2个及以上要点时，必须使用数字序号分点列出，每个要点单独一行。

【参考文档】
{document_content}
"""


# 用户问题模板
RAG_QA_USER_TEMPLATE = """用户问题：{question}
请根据参考文档回答上述问题。"""


def build_rag_qa_prompt(document_content: str, question: str) -> list:
    """
    构建RAG问答的对话消息列表，区分系统提示和用户问题
    :param document_content: 参考文档全文
    :param question: 用户问题
    :return: 符合OpenAI格式的消息列表
    """
    system_prompt = RAG_QA_SYSTEM_PROMPT.format(document_content=document_content)
    user_prompt = RAG_QA_USER_TEMPLATE.format(question=question)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]















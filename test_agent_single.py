import json
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.services import task_service

# 工具定义（与大模型侧严格一致）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "查询当前用户的所有任务列表，可按状态筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "任务状态筛选，可选值：pending（待完成）、completed（已完成），不传则返回全部",
                        "enum": ["pending", "completed"]
                    }
                },
                "required": []
            }
        }
    }
]


def execute_tool(tool_name: str, arguments: dict, user_id: int):
    """执行工具调用，返回格式化的结果字符串"""
    db = next(get_db())
    try:
        if tool_name == "list_tasks":
            status = arguments.get("status")
            # 调用现有任务服务查询数据
            tasks = task_service.get_task_list(db, user_id=user_id)
            # 序列化为大模型易读的文本格式
            result = []
            for task in tasks:
                status_text = "已完成" if task.is_completed else "待完成"
                result.append(f"ID:{task.id} | 内容：{task.content} | 优先级：{task.priority} | 状态：{status_text}")
            return "\n".join(result) if result else "当前暂无任务"
        else:
            return f"错误：未找到工具 {tool_name}"
    finally:
        db.close()


def agent_run(user_input: str, user_id: int = 1):
    """单轮Agent完整执行入口"""
    messages = [{"role": "user", "content": user_input}]

    # 第1步：大模型思考，判断是否需要调用工具
    response_msg = llm_client.chat_with_tools(messages, TOOLS)

    # 无需调用工具则直接返回回答
    if not response_msg.tool_calls:
        return response_msg.content

    # 第2步：执行工具调用并回传结果
    messages.append(response_msg)
    for tool_call in response_msg.tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"[Agent] 自动调用工具：{tool_name}，参数：{arguments}")

        tool_result = execute_tool(tool_name, arguments, user_id)
        print(f"[Agent] 工具执行结果：\n{tool_result}\n")

        # 按OpenAI标准格式追加工具结果消息
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": tool_result
        })

    # 第3步：大模型基于工具结果生成自然语言回答
    final_answer = llm_client.chat_with_messages(messages)
    return final_answer


if __name__ == "__main__":
    user_query = "帮我查一下我有哪些待完成的任务"
    print(f"用户提问：{user_query}\n")
    answer = agent_run(user_query, user_id=1)
    print("=== Agent最终回答 ===")
    print(answer)

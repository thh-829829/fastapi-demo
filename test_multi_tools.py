import json
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.services import task_service, goal_service
from app.schemas.task import TaskCreate, TaskUpdate
from app.models.user import User  # 导入User模型，注册users表元数据

# ========== 工具定义集（严格遵循OpenAI Function Calling标准） ==========
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "查询当前用户的所有任务列表",
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
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "创建一条新的学习任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "任务的具体内容"
                    },
                    "priority": {
                        "type": "string",
                        "description": "任务优先级，可选值：high（高）、medium（中）、low（低），默认medium",
                        "enum": ["high", "medium", "low"]
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_status",
            "description": "更新指定任务的完成状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "要更新的任务ID"
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "是否完成，true为已完成，false为待完成"
                    }
                },
                "required": ["task_id", "is_completed"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_goals",
            "description": "查询当前用户的所有学习目标列表",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ========== 工具执行器 ==========
def execute_tool(tool_name: str, arguments: dict, user_id: int):
    """根据工具名调度执行对应业务逻辑，返回格式化结果字符串"""
    db = next(get_db())
    try:
        if tool_name == "list_tasks":
            tasks = task_service.get_task_list(db, user_id=user_id)
            result = []
            for task in tasks:
                status_text = "已完成" if task.is_completed else "待完成"
                result.append(f"ID:{task.id} | 内容：{task.content} | 优先级：{task.priority} | 状态：{status_text}")
            return "\n".join(result) if result else "当前暂无任务"

        elif tool_name == "create_task":
            content = arguments.get("content")
            priority = arguments.get("priority", "medium")
            # 构造Pydantic入参模型，调用任务创建服务
            task_in = TaskCreate(content=content, priority=priority)
            new_task = task_service.create_task(db, task_in=task_in, user_id=user_id, )
            return f"任务创建成功，ID：{new_task.id}，内容：{new_task.content}，优先级：{new_task.priority}"

        elif tool_name == "update_task_status":
            task_id = arguments.get("task_id")
            is_completed = arguments.get("is_completed")
            # 构造Pydantic入参模型，调用任务更新服务
            task_in = TaskUpdate(is_completed=is_completed)
            updated_task = task_service.update_task(db, task_id=task_id, task_in=task_in, user_id=user_id)
            status_text = "已完成" if is_completed else "待完成"
            return f"任务{task_id}状态更新成功，当前状态：{status_text}"

        elif tool_name == "list_goals":
            goals = goal_service.get_goal_list(db, user_id=user_id)
            result = []
            for goal in goals:
                result.append(f"ID:{goal.id} | 标题：{goal.title} | 描述：{goal.description} | 状态：{goal.status}")
            return "\n".join(result) if result else "当前暂无学习目标"

        else:
            return f"错误：未找到工具 {tool_name}"
    finally:
        db.close()


# ========== Agent核心调度循环 ==========
def agent_run(user_input: str, user_id: int = 1):
    messages = [{"role": "user", "content": user_input}]

    # 第1步：大模型意图识别，自动选择工具
    response_msg = llm_client.chat_with_tools(messages, TOOLS)

    # 无需调用工具则直接返回
    if not response_msg.tool_calls:
        return response_msg.content

    # 第2步：执行所有工具调用并回传结果
    messages.append(response_msg)
    for tool_call in response_msg.tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"[Agent] 自动调用工具：{tool_name}，参数：{arguments}")

        tool_result = execute_tool(tool_name, arguments, user_id)
        print(f"[Agent] 工具执行结果：\n{tool_result}\n")

        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": tool_result
        })

    # 第3步：基于工具结果生成自然语言回答
    final_answer = llm_client.chat_with_messages(messages)
    return final_answer


# ========== 多场景测试 ==========
if __name__ == "__main__":
    # 可依次注释测试不同场景
    test_queries = [
        "帮我查一下我有哪些任务",
        "帮我创建一个任务，内容是学习多工具Agent开发，优先级高",
        "把ID为1的任务标记为已完成",
        "帮我看看我有哪些学习目标"
    ]

    for i, query in enumerate(test_queries[3:4]):  # 默认先测第一个，可修改索引测试其他
        print(f"\n{'=' * 50}")
        print(f"用户提问：{query}")
        print('=' * 50)
        answer = agent_run(query, user_id=1)
        print("=== Agent最终回答 ===")
        print(answer)

import json
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.services import task_service, goal_service
from app.schemas.task import TaskCreate, TaskUpdate
from app.models.user import User

# ========== 工具定义 ==========
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
                        "description": "任务状态筛选，可选值：pending、completed，不传则返回全部",
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
                    "content": {"type": "string", "description": "任务的具体内容"},
                    "priority": {
                        "type": "string",
                        "description": "任务优先级，可选值：high、medium、low，默认medium",
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
                    "task_id": {"type": "integer", "description": "要更新的任务ID"},
                    "is_completed": {"type": "boolean", "description": "是否完成，true为已完成，false为待完成"}
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
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

# ========== 工具执行器 ==========
def execute_tool(tool_name: str, arguments: dict, user_id: int):
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
            task_in = TaskCreate(content=content, priority=priority)
            new_task = task_service.create_task(db, task_in=task_in, user_id=user_id)
            return f"任务创建成功，ID：{new_task.id}，内容：{new_task.content}，优先级：{new_task.priority}"

        elif tool_name == "update_task_status":
            task_id = arguments.get("task_id")
            is_completed = arguments.get("is_completed")
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

# ========== 最简Agent核心循环 ==========
def agent_run(user_input: str, user_id: int = 1, max_steps: int = 5):
    # 初始化对话上下文，包含系统提示
    messages = [
        {
            "role": "system",
            "content": "你是一个智能学习助手，可以调用工具帮用户管理任务和目标。"
                       "如果需要调用工具，请使用function call格式；如果可以直接回答，就直接给出最终回答。"
                       "调用工具后，你会收到工具执行结果，请根据结果继续处理或给出最终答案。"
        },
        {"role": "user", "content": user_input}
    ]

    step = 0
    while step < max_steps:
        step += 1
        print(f"\n--- 第{step}步：思考 ---")

        # 第1步：思考 - 让LLM判断下一步做什么
        response = llm_client.chat_with_tools(messages, TOOLS)

        # 第2步：判断是否需要调用工具
        if not response.tool_calls:
            # 不需要工具，直接返回最终回答
            print("--- 最终回答 ---")
            return response.content

        # 第3步：行动 - 执行所有工具调用
        print(f"--- 第{step}步：行动 ---")
        messages.append(response)  # 把助手的工具调用请求加入上下文

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"调用工具：{tool_name}，参数：{arguments}")

            # 第4步：观察 - 获取工具执行结果
            tool_result = execute_tool(tool_name, arguments, user_id)
            print(f"工具结果：{tool_result}")

            # 把观察结果加入上下文，供下一轮思考使用
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": tool_result
            })

    return "执行步数超限，未能完成任务"

# ========== 测试 ==========
if __name__ == "__main__":
    print("=" * 50)
    user_query = "帮我创建一个任务，内容是学习Agent核心原理，优先级中等"
    print(f"用户提问：{user_query}")
    print("=" * 50)

    answer = agent_run(user_query, user_id=1)
    print(answer)

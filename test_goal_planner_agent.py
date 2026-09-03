import json
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.services import task_service, goal_service
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.goal import GoalCreate
from app.models.user import User

# ========== 工具定义 ==========
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "创建一个新的学习总目标，返回目标ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "目标的简短标题"},
                    "description": {"type": "string", "description": "目标的详细描述"}
                },
                "required": ["title", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "创建一条学习任务，可关联到指定的目标ID下",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "任务的具体内容"},
                    "priority": {
                        "type": "string",
                        "description": "任务优先级，可选值：high、medium、low，默认medium",
                        "enum": ["high", "medium", "low"]
                    },
                    "goal_id": {"type": "integer", "description": "所属的目标ID，可选"}
                },
                "required": ["content"]
            }
        }
    },
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
        if tool_name == "create_goal":
            title = arguments.get("title")
            description = arguments.get("description", "")
            goal_in = GoalCreate(title=title, description=description)
            new_goal = goal_service.create_goal(db, goal_in=goal_in, user_id=user_id)
            return f"目标创建成功，ID：{new_goal.id}，标题：{new_goal.title}"

        elif tool_name == "create_task":
            content = arguments.get("content")
            priority = arguments.get("priority", "medium")
            goal_id = arguments.get("goal_id")
            task_in = TaskCreate(content=content, priority=priority, goal_id=goal_id)
            new_task = task_service.create_task(db, task_in=task_in, user_id=user_id)
            return f"任务创建成功，ID：{new_task.id}，内容：{new_task.content}，所属目标ID：{goal_id}"

        elif tool_name == "list_tasks":
            tasks = task_service.get_task_list(db, user_id=user_id)
            result = []
            for task in tasks:
                status_text = "已完成" if task.is_completed else "待完成"
                result.append(f"ID:{task.id} | 内容：{task.content} | 优先级：{task.priority} | 状态：{status_text}")
            return "\n".join(result) if result else "当前暂无任务"

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

# ========== Agent核心循环 ==========
def agent_run(user_input: str, user_id: int = 1, max_steps: int = 10):
    messages = [
        {
            "role": "system",
            "content": "你是专业的学习规划师，擅长将用户的学习目标拆解为可执行的阶段任务。\n"
                       "执行规则：\n"
                       "1. 先分析用户的学习目标，拆解为1个总目标和3-5个分阶段任务\n"
                       "2. 先调用create_goal创建总目标，拿到目标ID\n"
                       "3. 再依次调用create_task创建每个阶段任务，关联到刚才的目标ID下\n"
                       "4. 全部创建完成后，给用户输出完整的规划总结\n"
                       "5. 任务优先级：基础入门类为high，进阶实践类为medium"
        },
        {"role": "user", "content": user_input}
    ]

    step = 0
    while step < max_steps:
        step += 1
        print(f"\n--- 第{step}步：思考 ---")

        response = llm_client.chat_with_tools(messages, TOOLS)

        if not response.tool_calls:
            print("--- 最终回答 ---")
            return response.content

        print(f"--- 第{step}步：行动 ---")
        messages.append(response)

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"调用工具：{tool_name}，参数：{arguments}")

            tool_result = execute_tool(tool_name, arguments, user_id)
            print(f"工具结果：{tool_result}")

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
    user_query = "我想在两周内学会Python基础编程"
    print(f"用户提问：{user_query}")
    print("=" * 50)

    answer = agent_run(user_query, user_id=1)
    print(answer)

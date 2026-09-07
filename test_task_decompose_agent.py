import json
from datetime import datetime, timedelta
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.db.database import Base, engine
from app.services import task_service, goal_service
from app.schemas.task import TaskCreate
from app.schemas.goal import GoalCreate
from app.models import user, goal, task, document


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
                    "goal_id": {"type": "integer", "description": "所属的目标ID，可选"},
                    "deadline": {"type": "string", "description": "截止日期，格式YYYY-MM-DD，可选"}
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
            deadline_str = arguments.get("deadline")
            deadline = None
            if deadline_str:
                try:
                    deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                except:
                    pass
            task_in = TaskCreate(content=content, priority=priority, goal_id=goal_id, deadline=deadline)
            new_task = task_service.create_task(db, task_in=task_in, user_id=user_id)
            return f"任务创建成功，ID：{new_task.id}，内容：{content[:30]}...，优先级：{priority}，截止：{deadline_str}"

        elif tool_name == "list_tasks":
            tasks = task_service.get_task_list(db, user_id=user_id)
            result = []
            for task in tasks:
                status_text = "已完成" if task.is_completed else "待完成"
                result.append(f"ID:{task.id} | 内容：{task.content} | 优先级：{task.priority} | 状态：{status_text}")
            return "\n".join(result) if result else "当前暂无任务"

        else:
            return f"错误：未找到工具 {tool_name}"
    finally:
        db.close()

# ========== Agent核心循环 ==========
def agent_run(user_input: str, user_id: int = 1, max_steps: int = 20):
    today = datetime.now().date()
    messages = [
        {
            "role": "system",
            "content": f"你是专业的任务拆解专家，擅长将大的学习目标拆解为层级化的可执行任务。\n"
                       f"今天日期：{today.strftime('%Y-%m-%d')}\n"
                       "执行规则：\n"
                       "1. 先分析用户的学习目标和总周期，拆解为2-4个学习阶段\n"
                       "2. 每个阶段拆解为3-5个具体子任务，层层递进\n"
                       "3. 先调用create_goal创建总目标，拿到目标ID\n"
                       "4. 再依次调用create_task创建所有子任务，全部关联到该目标ID下\n"
                       "5. 优先级规则：基础核心阶段为high，进阶提升阶段为medium，复盘收尾阶段为low\n"
                       "6. 截止时间：按阶段平均分配总周期，每个阶段的任务统一使用该阶段的截止日期，格式YYYY-MM-DD\n"
                       "7. 全部任务创建完成后，给用户输出结构化的拆解总结，分阶段展示任务"
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
    # 确保所有数据表已创建
    Base.metadata.create_all(bind=engine)

    print("=" * 50)
    user_query = "我想在2周内系统学习FastAPI后端开发"
    print(f"用户提问：{user_query}")
    print("=" * 50)

    answer = agent_run(user_query, user_id=1)
    print(answer)





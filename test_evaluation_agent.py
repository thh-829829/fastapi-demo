import json
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.services import task_service, goal_service
from app.schemas.task import TaskCreate, TaskUpdate
from app.utils.agent_context import AgentContextManager

from sqlalchemy import text


# ========== 工具定义（复用现有标准工具） ==========
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
    }
]


# ========== 工具执行器（复用现有逻辑） ==========
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
        elif tool_name == "update_task_status":
            task_id = arguments.get("task_id")
            is_completed = arguments.get("is_completed")
            # 原生SQL更新，避开ORM外键映射问题
            sql = "UPDATE tasks SET is_completed = :is_completed WHERE id = :task_id AND user_id = :user_id"
            db.execute(text(sql), {"is_completed": is_completed, "task_id": task_id, "user_id": user_id})
            db.commit()
            status_text = "已完成" if is_completed else "待完成"
            return f"任务{task_id}状态更新成功，当前状态：{status_text}"
        else:
            return f"错误：未找到工具 {tool_name}"
    finally:
        db.close()


# ========== 学习评价Agent核心循环 ==========
def evaluation_agent_run(user_input: str, user_id: int = 1, session_id: str = "eval_default", max_steps: int = 5):
    # 1. 初始化上下文管理器
    ctx = AgentContextManager(session_id=session_id, ttl=1800)

    # 2. 新会话自动初始化系统提示
    if ctx.message_count() == 0:
        system_prompt = """# 角色定位
你是一位专业的学习进度管理师与学习顾问，专注于帮助用户管理学习任务、跟踪完成进度、给出针对性的学习评价与行动建议。你严谨务实，所有结论基于真实任务数据，输出结构化、可落地。

# 核心能力
1. 任务状态更新：识别用户的任务完成汇报，自动调用工具更新对应任务的完成状态
2. 任务数据查询：调用工具获取用户全量任务列表，掌握整体进度
3. 学习评价生成：基于真实任务数据，从进度、节奏、优先级等维度给出专业评价
4. 行动建议输出：结合当前任务情况，给出具体可执行的下一步学习建议
5. 多轮对话交互：结合历史对话上下文，支持用户追问、补充需求、细化建议

# 标准执行流程（严格按顺序执行）
## 第一步：意图识别
分析用户输入，判断属于以下哪种场景：
- 场景A：用户明确汇报「某ID的任务已完成/未完成」→ 进入「先更新、后查询、再评价」流程
- 场景B：用户请求「查看进度/评价学习情况/总结任务」→ 进入「直接查询、再评价」流程
- 场景C：用户表述模糊（如只说“我完成了”未指定任务ID）→ 主动追问具体任务ID，不猜测、不编造

## 第二步：数据操作（必须调用工具，禁止编造数据）
1. 场景A：先调用 update_task_status 工具更新对应任务状态，成功后再调用 list_tasks 获取最新全量任务列表
2. 场景B：直接调用 list_tasks 获取全量任务列表
3. 所有工具执行结果必须完整纳入对话上下文，作为评价的唯一数据依据

## 第三步：生成结构化评价
基于真实任务数据，按固定结构输出评价，禁止脱离数据泛泛而谈。

# 输出结构规范（严格遵循）
✅ 状态确认
（先回应用户的操作，明确说明任务状态已更新 / 已获取最新任务数据）

📊 整体进度概览
- 总任务数：X 个
- 已完成：X 个
- 待完成：X 个
- 完成率：XX%

👍 完成反馈与评价
（肯定用户的执行成果，结合任务优先级、数量给出正面激励；如果有逾期或高优先级任务未完成，客观指出问题）

💡 优化与调整建议
（给出1-2条具体、可落地的建议，例如优先级调整、时间分配、任务拆分方向等，针对当前任务情况定制，不套用空话）

🎯 下一步优先行动
（推荐1个最优先的待办任务，明确说明推荐理由，例如「优先级最高」「临近截止」「是后续任务的基础」等）

# 对话与上下文规则
1. 参考完整历史对话，用户之前提到过的信息不要重复询问
2. 用户追问细节时，结合历史任务数据展开回答，不偏离当前学习主题
3. 多轮对话中保持人设一致，评价口径前后统一

# 边界约束
1. 所有任务数据必须来自工具调用，绝对禁止编造任务ID、内容、状态
2. 只围绕学习任务管理与学习建议展开，不回答无关问题
3. 工具调用失败时，友好告知用户原因，不要输出技术报错信息
4. 评价客观中立，既肯定成果也不回避问题，但整体语气积极鼓励"""
        ctx.init_session(system_prompt)

    # 3. 追加当前用户输入
    ctx.add_user_message(user_input)

    step = 0
    while step < max_steps:
        step += 1
        print(f"\n--- 第{step}步：思考 ---")

        # 4. 从Redis获取完整历史上下文
        messages = ctx.get_messages()

        # 调用大模型判断
        response = llm_client.chat_with_tools(messages, TOOLS)

        # 5. 判断是否需要调用工具
        if not response.tool_calls:
            # 不需要工具，输出最终评价
            ctx.add_assistant_message(content=response.content)
            print("--- 最终评价 ---")
            return response.content

        # 6. 执行工具调用
        print(f"--- 第{step}步：行动 ---")
        ctx.add_assistant_message(
            content=response.content,
            tool_calls=[
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in response.tool_calls
            ]
        )

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"调用工具：{tool_name}，参数：{arguments}")

            tool_result = execute_tool(tool_name, arguments, user_id)
            print(f"工具结果：{tool_result}")

            ctx.add_tool_message(
                tool_call_id=tool_call.id,
                name=tool_name,
                content=tool_result
            )

    return "执行步数超限，未能完成评价"


# ========== 多场景测试 ==========
if __name__ == "__main__":
    TEST_SESSION = "test_evaluation_agent_001"

    # 清空历史会话，确保干净环境
    AgentContextManager(session_id=TEST_SESSION).clear()
    print("已清空历史会话，开始全新测试\n")

    print("=" * 60)
    print("【场景1：汇报任务完成 → 自动更新+生成评价】")
    print("=" * 60)
    # 提示：请替换为你数据库中真实存在的待完成任务ID
    user_input1 = "我完成了ID为4的任务"
    print(f"用户输入：{user_input1}")
    result1 = evaluation_agent_run(user_input1, user_id=1, session_id=TEST_SESSION)
    print(result1)

    print("\n" + "=" * 60)
    print("【场景2：直接查询进度 → 生成整体评价】")
    print("=" * 60)
    user_input2 = "帮我看一下现在整体学习进度怎么样，给个评价"
    print(f"用户输入：{user_input2}")
    result2 = evaluation_agent_run(user_input2, user_id=1, session_id=TEST_SESSION)
    print(result2)

    print("\n" + "=" * 60)
    print("【场景3：多轮追问 → 结合上下文细化建议】")
    print("=" * 60)
    user_input3 = "针对下一步的优先任务，给我点具体的学习方法建议"
    print(f"用户输入：{user_input3}")
    result3 = evaluation_agent_run(user_input3, user_id=1, session_id=TEST_SESSION)
    print(result3)

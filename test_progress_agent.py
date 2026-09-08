import json
from app.utils.llm_client import llm_client
from app.db.database import get_db
from app.services import task_service
from app.utils.agent_context import AgentContextManager
from sqlalchemy import text

# ========== 工具定义（复用list_tasks标准工具） ==========
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
    }
]


# ========== 工具执行器 ==========
def execute_tool(tool_name: str, arguments: dict, user_id: int):
    db = next(get_db())
    try:
        if tool_name == "list_tasks":
            status_filter = arguments.get("status")
            tasks = task_service.get_task_list(db, user_id=user_id)

            # 状态过滤
            if status_filter == "completed":
                tasks = [t for t in tasks if t.is_completed]
            elif status_filter == "pending":
                tasks = [t for t in tasks if not t.is_completed]

            result = []
            for task in tasks:
                status_text = "已完成" if task.is_completed else "待完成"
                result.append(f"ID:{task.id} | 内容：{task.content} | 优先级：{task.priority} | 状态：{status_text}")
            return "\n".join(result) if result else "当前暂无任务"
        else:
            return f"错误：未找到工具 {tool_name}"
    finally:
        db.close()


# ========== 进度统计Agent核心循环 ==========
def progress_agent_run(user_input: str, user_id: int = 1, session_id: str = "progress_default", max_steps: int = 5):
    # 1. 初始化上下文管理器
    ctx = AgentContextManager(session_id=session_id, ttl=1800)

    # 2. 新会话自动初始化系统提示
    if ctx.message_count() == 0:
        system_prompt = """# 角色定位
你是一位专业的学习项目进度管理师，专注于学习任务的多维度统计分析、风险识别预警和全局进度优化。你严谨细致，所有结论严格基于真实任务数据，输出结构化、数据化、可落地。

# 核心能力
1. 全量任务查询：调用工具获取用户所有任务数据，作为统计分析的唯一依据
2. 多维度进度统计：从整体、优先级两个维度计算完成率，精准呈现各层级进度
3. 风险识别预警：识别待完成的高优先级任务，判定风险等级，说明潜在影响
4. 全局优化建议：结合进度情况和风险点，给出优先级调整、时间分配、节奏规划的系统性建议
5. 多轮对话交互：支持用户按维度筛选查询、追问细节，结合历史上下文回答

# 标准执行流程
1. 接收用户进度查询请求后，**必须先调用 list_tasks 工具**获取全量任务列表
2. 基于真实任务数据进行统计计算，禁止编造任何任务数量、状态、内容
3. 按照固定结构输出结构化进度报告，模块顺序不可调整
4. 用户后续追问时，优先复用已获取的任务数据分析回答；仅当用户明确要求刷新数据时，才重新调用工具
5. 所有交互完整纳入对话上下文，保持口径一致

# 输出规范（严格遵循）
## 📊 全局进度总览
- 总任务数：X 个
- 已完成：X 个
- 待完成：X 个
- 整体完成率：XX%

## 📈 分维度进度拆解
### 【高优先级任务】
- 总数：X 个，已完成：X 个，待完成：X 个，完成率：XX%
- 状态评估：进度正常 / 略有滞后 / 严重滞后
  （判定标准：完成率≥80%为正常，50%-79%为略有滞后，<50%为严重滞后）

### 【中优先级任务】
- 总数：X 个，已完成：X 个，待完成：X 个，完成率：XX%
- 状态评估：进度正常 / 略有滞后
  （判定标准：完成率≥70%为正常，<70%为略有滞后）

## ⚠️ 风险预警提醒
按风险等级从高到低列出核心待办任务，最多展示5条，每条格式：
• 【风险等级】任务ID：任务内容（优先级）
- 影响说明：简述该任务延误的具体影响

风险等级判定规则：
- 高风险：高优先级 + 待完成
- 中风险：中优先级 + 待完成
- 无风险：已完成任务不列入

## 💡 全局优化建议
给出3条具体、可落地的建议，分别对应以下方向：
1. 优先级调整建议：针对风险任务，明确优先级调整或处理顺序建议
2. 时间分配建议：针对当前进度，给出每日/阶段时间投入的分配方案
3. 学习节奏建议：结合任务难度和进度，给出推进节奏与阶段目标建议

# 边界约束
1. 数据真实性：所有统计数据必须来自工具调用结果，绝对禁止编造任务信息
2. 风险客观性：风险判定严格按规则执行，不夸大焦虑也不忽视隐患
3. 建议落地性：每条建议都有明确的行动指向，不使用空泛套话
4. 语气正向性：客观指出问题的同时，整体保持鼓励、建设性的语气
5. 范围边界：只围绕学习任务进度展开，不回答无关问题"""
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
            # 不需要工具，输出最终报告
            ctx.add_assistant_message(content=response.content)
            print("--- 最终进度报告 ---")
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
            print(f"工具结果：{tool_result[:150]}...")

            ctx.add_tool_message(
                tool_call_id=tool_call.id,
                name=tool_name,
                content=tool_result
            )

    return "执行步数超限，未能完成统计"


# ========== 多场景测试 ==========
if __name__ == "__main__":
    TEST_SESSION = "test_progress_agent_001"

    # 清空历史会话，确保干净环境
    AgentContextManager(session_id=TEST_SESSION).clear()
    print("已清空历史会话，开始全新测试\n")

    print("=" * 60)
    print("【场景1：全局进度查询 → 多维度统计+风险预警】")
    print("=" * 60)
    user_input1 = "帮我统计一下整体学习进度，做个全面的进度分析"
    print(f"用户输入：{user_input1}")
    result1 = progress_agent_run(user_input1, user_id=1, session_id=TEST_SESSION)
    print(result1)

    print("\n" + "=" * 60)
    print("【场景2：多轮追问 → 聚焦高风险任务详情】")
    print("=" * 60)
    user_input2 = "重点说一下高风险的任务，给我排个处理顺序"
    print(f"用户输入：{user_input2}")
    result2 = progress_agent_run(user_input2, user_id=1, session_id=TEST_SESSION)
    print(result2)

    print("\n" + "=" * 60)
    print("【场景3：维度筛选 → 只看待完成任务】")
    print("=" * 60)
    user_input3 = "只给我列出所有待完成的任务，按优先级排序"
    print(f"用户输入：{user_input3}")
    result3 = progress_agent_run(user_input3, user_id=1, session_id=TEST_SESSION)
    print(result3)

import json
import uuid
from typing import Tuple
from sqlalchemy import text
from app.utils.llm_client import llm_client
from app.utils.agent_context import AgentContextManager
from app.db.database import get_db
from app.services import task_service

# ========== 工具定义（与测试脚本保持一致） ==========
TOOLS = [
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
                        "description": "任务ID"
                    },
                    "is_completed": {
                        "type": "boolean",
                        "description": "是否完成，True为已完成，False为待完成"
                    }
                },
                "required": ["task_id", "is_completed"]
            }
        }
    },
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

# ========== 系统Prompt（复用统一管家Prompt） ==========
SYSTEM_PROMPT = """# 角色定位
你是一位专业的智能学习管家，一站式负责用户的学习任务管理、进度统计分析与学习规划制定。你能准确理解用户意图，自动调度对应能力，输出专业、结构化、可落地的结果。

# 核心能力
1. 任务完成管理：接收用户任务完成汇报，自动更新任务状态，给出针对性学习评价与下一步建议
2. 进度统计分析：多维度统计学习进度，识别风险任务，输出结构化进度报告与优化建议
3. 学习规划生成：将学习目标拆解为每日执行计划，设置里程碑，给出可落地的学习安排
4. 跨场景多轮交互：支持连续对话、跨场景追问，基于上下文连贯响应
5. 混合意图处理：支持用户同时提出多个需求，按逻辑顺序依次处理

# 意图判定与执行规则
## 1. 任务完成汇报意图
- 判定特征：用户提到「完成了/做完了/搞定了/提交」+ 任务ID或任务名称
- 执行流程：
  ① 调用 update_task_status 工具，将对应任务更新为已完成状态
  ② 调用 list_tasks 工具，获取最新的全量任务数据
  ③ 输出结构化学习评价，严格遵循四段式结构

## 2. 进度查询分析意图
- 判定特征：用户询问「进度/统计/分析/怎么样/风险/完成率/完成情况」
- 执行流程：
  ① 调用 list_tasks 工具，获取全量任务数据
  ② 按整体、优先级双维度统计计算，识别风险任务并分级
  ③ 输出结构化进度报告，严格遵循四大模块结构

## 3. 学习规划生成意图
- 判定特征：用户要求「计划/规划/拆解/安排/每天学什么/怎么学/制定学习方案」
- 执行流程：
  ① 明确用户的学习目标、周期、每日时长、侧重方向等约束条件
  ② 按照循序渐进、依赖优先、工作量均衡、学练结合、里程碑五大原则拆解任务
  ③ 输出结构化学习规划，严格遵循五大模块结构

# 分场景输出规范
## 任务完成评价输出规范
### ✅ 状态确认
明确说明哪个任务已更新为完成状态，数据来源于工具执行结果。

### 📝 完成反馈
结合任务内容，评价该任务的知识价值与掌握意义，肯定完成进度。

### 🧠 知识掌握评估
关联前置与后续任务，评估当前知识节点的掌握程度对后续学习的支撑作用。

### 🎯 下一步行动建议
给出1-2条明确的下一步任务建议，优先推荐高优先级的后续任务。

## 进度分析报告输出规范
## 📊 全局进度总览
- 总任务数：X 个
- 已完成：X 个
- 待完成：X 个
- 整体完成率：XX%

## 📈 分维度进度拆解
### 【高优先级任务】
- 总数：X 个，已完成：X 个，待完成：X 个，完成率：XX%
- 状态评估：进度正常 / 略有滞后 / 严重滞后

### 【中优先级任务】
- 总数：X 个，已完成：X 个，待完成：X 个，完成率：XX%
- 状态评估：进度正常 / 略有滞后

## ⚠️ 风险预警提醒
按风险等级从高到低列出核心待办任务，最多展示5条，标注风险等级与影响说明。

## 💡 全局优化建议
给出3条分别对应优先级调整、时间分配、学习节奏的落地建议。

## 学习规划方案输出规范
## 🎯 目标任务拆解总览
- 总目标：对应用户提出的规划目标
- 规划周期：X天
- 拆解子任务总数：X个
- 核心里程碑：X个

## 📋 分层任务拆解清单
按知识模块归类，展示子任务、预计耗时与前置依赖。

## 📅 每日执行计划
按天排布，每天包含核心学习任务、配套练习任务、当日验收标准。

## 🚩 关键里程碑节点
至少设置2个里程碑，每个有可量化的验收标准。

## 💡 执行建议
给出时间分配、学习方法、风险注意事项3条落地建议。

# 边界约束
1. 数据真实性：所有任务数据必须来自工具调用结果，绝对禁止编造任务ID、内容、状态
2. 意图准确性：意图识别不确定时优先询问用户确认，不臆断需求
3. 执行顺序性：混合意图按逻辑顺序处理，先更新后查询，先数据后规划
4. 上下文一致性：多轮对话保持口径统一，数据前后一致，不矛盾
5. 输出规范性：严格对应场景的输出结构，不随意增减模块，格式统一
6. 范围边界性：只围绕学习任务管理展开，不回答无关问题"""


class AgentService:
    """智能学习管家业务服务类"""

    def __init__(self):
        self.max_steps = 10

    def _execute_tool(self, tool_name: str, arguments: dict, user_id: int) -> str:
        """工具执行器，复用已验证的原生SQL方案"""
        db = next(get_db())
        try:
            if tool_name == "update_task_status":
                task_id = arguments.get("task_id")
                is_completed = arguments.get("is_completed")
                sql = "UPDATE tasks SET is_completed = :is_completed WHERE id = :task_id AND user_id = :user_id"
                db.execute(text(sql), {
                    "is_completed": is_completed,
                    "task_id": task_id,
                    "user_id": user_id
                })
                db.commit()
                status_text = "已完成" if is_completed else "待完成"
                return f"任务{task_id}状态更新成功，当前状态：{status_text}"

            elif tool_name == "list_tasks":
                status_filter = arguments.get("status")
                tasks = task_service.get_task_list(db, user_id=user_id)
                if status_filter == "completed":
                    tasks = [t for t in tasks if t.is_completed]
                elif status_filter == "pending":
                    tasks = [t for t in tasks if not t.is_completed]

                result = []
                for task in tasks:
                    status_text = "已完成" if task.is_completed else "待完成"
                    result.append(
                        f"ID:{task.id} | 内容：{task.content} | 优先级：{task.priority} | 状态：{status_text}"
                    )
                return "\n".join(result) if result else "当前暂无任务"
            else:
                return f"错误：未找到工具 {tool_name}"
        finally:
            db.close()

    def _detect_intent(self, reply: str) -> str:
        """简易意图识别，基于回复内容特征判断"""
        if "状态确认" in reply and "已成功更新" in reply:
            return "task_complete"
        elif "全局进度总览" in reply and "分维度进度拆解" in reply:
            return "progress_query"
        elif "目标任务拆解总览" in reply and "每日执行计划" in reply:
            return "plan_generate"
        else:
            return "unknown"

    def chat(self, user_id: int, session_id: str = None, message: str = "") -> Tuple[str, str]:
        """
        统一对话入口
        :param user_id: 用户ID
        :param session_id: 会话ID，None则自动生成
        :param message: 用户消息
        :return: (session_id, reply_content)
        """
        # 1. 会话ID处理
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

        # 2. 初始化上下文管理器
        ctx = AgentContextManager(session_id=session_id, ttl=1800)

        # 3. 新会话初始化系统提示
        if ctx.message_count() == 0:
            ctx.init_session(SYSTEM_PROMPT)

        # 4. 追加用户消息
        ctx.add_user_message(message)

        # 5. 核心推理循环
        step = 0
        while step < self.max_steps:
            step += 1
            messages = ctx.get_messages()
            response = llm_client.chat_with_tools(messages, TOOLS)

            # 无需工具调用，返回最终结果
            if not response.tool_calls:
                ctx.add_assistant_message(content=response.content)
                return session_id, response.content

            # 执行工具调用
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
                tool_result = self._execute_tool(tool_name, arguments, user_id)
                ctx.add_tool_message(
                    tool_call_id=tool_call.id,
                    name=tool_name,
                    content=tool_result
                )

        return session_id, "执行步数超限，未能完成处理"


# 单例实例
agent_service = AgentService()

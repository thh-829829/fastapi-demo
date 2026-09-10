import json
from app.utils.llm_client import llm_client
from app.utils.agent_context import AgentContextManager

# ================== 工具定义（规范Agent暂无需外部工具，后续可扩展计划保存等能力） ==========
TOOLS = []

# ================ 工具执行器（预留框架，当前无工具调用） ===========
def execute_tool(tool_name: str, arguments: dict, user_id: int):
    return f"错误：未找到工具{tool_name}"

# ================ 任务规划Agent核心循环 ==============
def plan_agent_run(user_input: str, user_id: int = 1, session_id: str = "plan_default", max_steps: int =5):
    # 1、初始化上下文管理
    ctx = AgentContextManager(session_id=session_id, ttl=1800)

    # 2、新会话自动初始化系统提示
    if ctx.message_count() == 0:
        system_prompt = """# 角色定位
你是一位专业的学习规划师，你擅长将大型学习目标拆解为结构化、可落地的每日执行计划。
你深谙学习认知规律，拆解逻辑严谨，任务排布科学，输出的计划可直接执行。

#核心能力
1、目标分层拆解：将大的学习目标拆解为知识模块，再细化为可执行的子任务，明确依赖关系
2、每日计划生成：基于拆解结果，按天排布任务，均衡分配工作量，匹配合理的学习节奏
3、里程碑设定：识别关键知识节点，设置阶段里程碑与可量化的验收标准
4、多轮调整优化：支持用户调整周期、每日时长、侧重方向，基于上下文重新生成计划
5、落地建议输出：配套给出时间分配，学习方法、风险规避等执行层面的建议

#执行流程
1、接收用户的规划目标与约束条件（周期、每日时长、侧重方向等）
2、按照循序渐进、依赖优先、工作量均衡、学练结合、里程碑5项核心原则进行任务拆解与计划排布
3、按照固定结构输出完整的结构化计划
4、用户提出调整需求时，基于原有计划上下文调整，无需从头重复拆解
5、所有交互完整纳入对话上下文，保持计划口径一致

#输出规范（严格遵循）
一、目标任务拆解总览
 - 总目标：对应用户提出的规划目标
 - 规划周期：x天
 - 拆解子任务总数：x天
 - 核心里程碑：x天
 
二、分层任务拆解清单
按知识模板归类，清晰展示每个模块的子任务、预计耗时与前置依赖
模块颗粒度适中，子任务粒度控制在1-2小时可完成的量级

三、每日执行计划
按天依次排布，每天的任务量均衡，学练结合。
每天必须包含：核心学习任务、配套练习任务、当日验收标准。
时间分配符合常规学习节奏，单日学习时长不超过4小时。

四、关键里程碑节点
至少设置2个里程碑，对应阶段核心节点。
每个里程碑必须有可量化、可验证的验收标准。

五、执行建议
给出3条不同维度的落地建议，分别对应时间分配、学习方法、风险注意事项。
建议务实具体，可直接执行，不使用空泛套话。

# 边界约束
1、拆解逻辑必须符合学习认知规律，前置知识不后置，基础内容不跳级
2、任务量与周期匹配，严禁出现单日任务过载或明显空闲的情况
3、计划必须可落地，每个任务都有明确的内容与验收标准，不写模糊表述
4、调整计划时保留原有核心框架，只做适配性修改，保持上下文一致性
5、只围绕学习规划展开，不回答无关问题"""
        ctx.init_session(system_prompt)

    # 3、追加当前用户输入
    ctx.add_user_message(user_input)

    step = 0
    while step < max_steps:
        step += 1
        print(f"\n---- 第{step}步：思考---")

        # 4、从Redis获取完整历史上下文
        messages = ctx.get_messages()

        # 调用大模型
        response = llm_client.chat_with_tools(messages, TOOLS)

        # 5、判断是否需要调用工具
        if not response.tool_calls:
            # 不需要工具，输出最终计划
            ctx.add_assistant_message(content=response.content)
            print("----- 最终规划方案 --------")
            return response.content

        # 6、执行工具调用（当前无工具，预留框架）
        print(f"--- 第{step}步：行动 ----")
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

    return "执行步数超限，未能生成规划"

# =========== 多场景测试 =========
if __name__ == "__main__":
    TEST_SESSION = "test_plan_agent_001"

    # 清空历史会话，确保干净环境
    AgentContextManager(session_id=TEST_SESSION).clear()
    print("已清空历史会话，开始全新测试\n")

    print("=" * 60)
    print("【场景1：基础规划生成 ： 5天Python基础学习计划】")
    print("=" * 60)
    user_input1 = "帮我把Python基础语法学习拆解成每日计划，按5天完成"
    print(f"用户输入：{user_input1}")
    result1 = plan_agent_run(user_input1, user_id=1, session_id=TEST_SESSION)
    print(result1)

    print("\n" + "=" * 60)
    print("【场景2：多轮调整 ： 周期调整为7天，放慢节奏】")
    print("=" * 60)
    user_input2 = "改成7天完成，节奏放慢一点，每天轻松一点"
    print(f"用户输入：{user_input2}")
    result2 = plan_agent_run(user_input2, user_id=2, session_id=TEST_SESSION)
    print(result2)


    print("\n" + "=" * 60)
    print("【场景3：深度调整 → 限制每日时长+加强练习】")
    print("=" * 60)
    user_input3 = "每天只学2小时，重点加强练习部分，多安排实操任务"
    print(f"用户输入：{user_input3}")
    result3 = plan_agent_run(user_input3, user_id=1, session_id=TEST_SESSION)
    print(result3)







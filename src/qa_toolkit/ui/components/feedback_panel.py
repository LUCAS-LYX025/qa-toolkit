import streamlit as st
import datetime
import html
import re
from qa_toolkit.config.constants import TOOL_CATEGORIES

# === 留言反馈区域 ===
class FeedbackSection:
    def __init__(self):
        self.initialize_feedback_data()

    def initialize_feedback_data(self):
        """初始化反馈数据"""
        if 'user_feedbacks' not in st.session_state:
            st.session_state.user_feedbacks = []
        if 'feedback_count' not in st.session_state:
            st.session_state.feedback_count = 0

    def render_tool_feedback_bar(self, tool_name):
        """渲染贴近当前工具的轻量反馈入口。"""
        st.markdown('<div id="tool-feedback-anchor"></div>', unsafe_allow_html=True)
        st.markdown("---")

        tool_feedback_count = len(
            [fb for fb in st.session_state.user_feedbacks if fb.get("tool_name") == tool_name]
        )
        total_feedback_count = len(st.session_state.user_feedbacks)
        tool_key = self._tool_key(tool_name)

        st.markdown(
            f"""
            <div style="
                background:
                    radial-gradient(circle at top right, rgba(250, 204, 21, 0.12), rgba(250, 204, 21, 0) 34%),
                    linear-gradient(145deg, rgba(247,249,253,0.98) 0%, rgba(238,243,250,0.98) 56%, rgba(247,239,223,0.98) 100%);
                border: 1px solid #d5dce8;
                border-radius: 20px;
                padding: 18px 20px;
                margin: 10px 0 14px 0;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,0.88),
                    0 14px 28px rgba(15, 23, 42, 0.08);
            ">
                <div style="font-size: 12px; font-weight: 700; color: #b45309; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;">
                    用户反馈
                </div>
                <div style="font-size: 18px; font-weight: 700; color: #17324a; margin-bottom: 6px;">
                    刚用完「{tool_name}」？给个快速反馈
                </div>
                <div style="font-size: 14px; color: #476179; line-height: 1.7;">
                    详细表单改成弹出式，不再占一整段页面。当前工具已收到 {tool_feedback_count} 条反馈，全站累计 {total_feedback_count} 条。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        with action_col1:
            if st.button("👍 有帮助", key=f"feedback_helpful_{tool_key}", use_container_width=True):
                self._record_quick_feedback(tool_name, reaction="有帮助")
        with action_col2:
            with st.popover("👎 没帮助", use_container_width=True):
                self._render_compact_feedback_form(
                    tool_name=tool_name,
                    default_mode="issue",
                    form_key=f"feedback_issue_{tool_key}",
                )
        with action_col3:
            with st.popover("💡 提建议", use_container_width=True):
                self._render_compact_feedback_form(
                    tool_name=tool_name,
                    default_mode="suggestion",
                    form_key=f"feedback_suggestion_{tool_key}",
                )
        with action_col4:
            with st.popover("🕘 最近反馈", use_container_width=True):
                recent_tool_feedbacks = [
                    fb for fb in reversed(st.session_state.user_feedbacks) if fb.get("tool_name") == tool_name
                ][:3]
                if recent_tool_feedbacks:
                    st.caption("只展示当前工具最近 3 条反馈。")
                    for feedback in recent_tool_feedbacks:
                        self._render_feedback_card(feedback, compact=True)
                else:
                    st.caption("当前工具还没有反馈记录。")

    def render_feedback_section(self):
        """渲染完整的留言反馈区域"""
        st.markdown("---")
        st.markdown("### 💬 用户体验反馈区")

        # 显示反馈统计
        self._render_feedback_stats()

        # 反馈提交区域
        self._render_feedback_form()

        # 显示历史反馈
        self._render_feedback_history()

        # 页脚信息
        self._render_footer()

    def _render_feedback_stats(self):
        """渲染反馈统计信息"""
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("总反馈数", len(st.session_state.user_feedbacks))
        with col_stat2:
            suggestion_count = len([fb for fb in st.session_state.user_feedbacks if fb.get('type') == '功能建议'])
            st.metric("功能建议", suggestion_count)
        with col_stat3:
            issue_count = len([fb for fb in st.session_state.user_feedbacks if fb.get('type') == '问题反馈'])
            st.metric("问题反馈", issue_count)
        with col_stat4:
            avg_rating = sum([fb.get('rating', 0) for fb in st.session_state.user_feedbacks]) / len \
                (st.session_state.user_feedbacks) if st.session_state.user_feedbacks else 0
            st.metric("平均评分", f"{avg_rating:.1f}/5")

    def _render_feedback_form(self):
        """渲染反馈提交表单"""
        with st.expander("📝 点击这里分享您的建议或需求", expanded=False):
            st.markdown("""
            <div style='
                background:
                    radial-gradient(circle at top right, rgba(250, 204, 21, 0.12), rgba(250, 204, 21, 0) 34%),
                    linear-gradient(145deg, rgba(247,249,253,0.98) 0%, rgba(238,243,250,0.98) 56%, rgba(247,239,223,0.98) 100%);
                padding: 20px;
                border-radius: 16px;
                border: 1px solid #d5dce8;
                border-left: 4px solid #f59e0b;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.88);
            '>
                <h4 style='color: #17324a; margin-top: 0;'>💡 帮助我们做得更好！</h4>
                <p style='color: #476179; margin-bottom: 15px;'>
                    您的反馈对我们非常重要！请分享：
                </p>
                <ul style='color: #476179;'>
                    <li>使用过程中遇到的任何问题</li>
                    <li>希望新增的功能或工具</li>
                    <li>界面或交互的优化建议</li>
                    <li>任何其他想法或需求</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            # 反馈表单
            with st.form(key="feedback_form"):
                col1, col2 = st.columns(2)

                with col1:
                    feedback_type = st.selectbox(
                        "反馈类型 *",
                        ["功能建议", "问题反馈", "体验优化", "新工具需求", "其他"],
                        help="请选择最符合您反馈的类别"
                    )
                    nickname = st.text_input(
                        "昵称（可选）",
                        placeholder="如何称呼您",
                        help="可以留下昵称或匿名"
                    )

                with col2:
                    urgency = st.radio(
                        "紧急程度",
                        ["一般", "重要", "紧急"],
                        horizontal=True,
                        help="请选择问题的紧急程度"
                    )
                    rating = st.slider(
                        "整体满意度 *",
                        1, 5, 4,
                        help="1分-很不满意，5分-非常满意"
                    )

                feedback_content = st.text_area(
                    "详细反馈内容 *",
                    height=150,
                    placeholder="请详细描述您的建议、遇到的问题或需求...",
                    help="请尽可能详细地描述，这将帮助我们更好地理解您的需求"
                )

                # 表单提交按钮
                submitted = st.form_submit_button("📤 提交反馈", use_container_width=True)

                if submitted:
                    self._handle_feedback_submission(feedback_type, urgency, rating, feedback_content, nickname)

    def _render_compact_feedback_form(self, tool_name, default_mode, form_key):
        mode = default_mode
        default_type = "问题反馈" if mode == "issue" else "功能建议"
        default_rating = 2 if mode == "issue" else 4
        placeholder = (
            "哪里不符合预期？最好附上操作步骤、输入示例和期望结果。"
            if mode == "issue"
            else "希望新增什么能力？用在什么场景？"
        )

        st.caption(f"当前工具: `{tool_name}`，提交时间和工具名会自动记录。")
        with st.form(key=form_key):
            col1, col2 = st.columns(2)
            with col1:
                feedback_type = st.selectbox(
                    "反馈类型",
                    ["功能建议", "问题反馈", "体验优化", "新工具需求", "其他"],
                    index=["功能建议", "问题反馈", "体验优化", "新工具需求", "其他"].index(default_type),
                    key=f"{form_key}_type",
                )
                nickname = st.text_input("昵称（可选）", placeholder="匿名也可以", key=f"{form_key}_nickname")
            with col2:
                urgency = st.radio(
                    "紧急程度",
                    ["一般", "重要", "紧急"],
                    horizontal=True,
                    key=f"{form_key}_urgency",
                )
                rating = st.slider("当前满意度", 1, 5, default_rating, key=f"{form_key}_rating")

            feedback_content = st.text_area(
                "反馈内容",
                height=140,
                placeholder=placeholder,
                key=f"{form_key}_content",
            )

            submitted = st.form_submit_button("提交反馈", use_container_width=True)

            if submitted:
                self._handle_feedback_submission(
                    feedback_type,
                    urgency,
                    rating,
                    feedback_content,
                    nickname,
                    tool_name=tool_name,
                    source="compact_popover",
                )

    def _tool_key(self, tool_name):
        return re.sub(r"\W+", "_", tool_name).strip("_").lower() or "tool"

    def _record_quick_feedback(self, tool_name, reaction):
        feedback_record = {
            'id': st.session_state.feedback_count + 1,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': "快速反馈",
            'urgency': "一般",
            'rating': 5 if reaction == "有帮助" else 2,
            'content': f"用户对「{tool_name}」给出快速反馈：{reaction}",
            'nickname': "匿名用户",
            'tool_name': tool_name,
            'source': "quick_action",
            'reaction': reaction,
        }
        st.session_state.user_feedbacks.append(feedback_record)
        st.session_state.feedback_count += 1
        st.success(f"已记录：{reaction}。后续会优先优化「{tool_name}」相关体验。")

    def _handle_feedback_submission(self, feedback_type, urgency, rating, content, nickname, tool_name=None, source="full_page"):
        """处理反馈提交"""
        if not content.strip():
            st.error("❌ 请填写反馈内容")
            return False

        if not rating:
            st.error("❌ 请选择满意度评分")
            return False

        # 创建反馈记录
        feedback_record = {
            'id': st.session_state.feedback_count + 1,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': feedback_type,
            'urgency': urgency,
            'rating': rating,
            'content': content,
            'nickname': nickname or "匿名用户",
            'tool_name': tool_name,
            'source': source,
        }

        # 添加到反馈列表
        st.session_state.user_feedbacks.append(feedback_record)
        st.session_state.feedback_count += 1

        st.success("""
        ✅ 感谢您的反馈！

        我们已经收到您的宝贵建议，这将帮助我们持续改进工具。
        """)

        # 显示反馈摘要
        st.info(f"""
        **反馈摘要：**
        - 类型：{feedback_type}
        - 工具：{tool_name or '全局反馈'}
        - 紧急程度：{urgency}
        - 满意度：{rating}/5 分
        - 内容长度：{len(content)} 字符
        - 提交时间：{feedback_record['timestamp']}
        """)
        return True

    def _render_feedback_history(self):
        """渲染历史反馈记录"""
        if not st.session_state.user_feedbacks:
            st.info("""
            📝 **还没有反馈记录**

            您将是第一个分享建议的用户！您的反馈将帮助我们一起改进这个工具集。
            """)
            return

        st.markdown("### 📋 历史反馈记录")

        # 筛选选项
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            filter_type = st.selectbox("筛选类型",
                                       ["全部"] + list(set([fb['type'] for fb in st.session_state.user_feedbacks])))
        with col_filter2:
            filter_urgency = st.selectbox("筛选紧急程度", ["全部"] + list
            (set([fb['urgency'] for fb in st.session_state.user_feedbacks])))
        with col_filter3:
            sort_order = st.selectbox("排序方式", ["最新优先", "最早优先", "评分最高", "评分最低"])

        # 获取筛选后的反馈
        filtered_feedbacks = self._get_filtered_feedbacks(filter_type, filter_urgency, sort_order)

        # 显示反馈
        for feedback in filtered_feedbacks:
            self._render_feedback_card(feedback)

    def _get_filtered_feedbacks(self, filter_type, filter_urgency, sort_order):
        """获取筛选和排序后的反馈列表"""
        filtered_feedbacks = st.session_state.user_feedbacks.copy()

        # 筛选
        if filter_type != "全部":
            filtered_feedbacks = [fb for fb in filtered_feedbacks if fb['type'] == filter_type]

        if filter_urgency != "全部":
            filtered_feedbacks = [fb for fb in filtered_feedbacks if fb['urgency'] == filter_urgency]

        # 排序
        if sort_order == "最新优先":
            filtered_feedbacks.sort(key=lambda x: x['timestamp'], reverse=True)
        elif sort_order == "最早优先":
            filtered_feedbacks.sort(key=lambda x: x['timestamp'])
        elif sort_order == "评分最高":
            filtered_feedbacks.sort(key=lambda x: x['rating'], reverse=True)
        elif sort_order == "评分最低":
            filtered_feedbacks.sort(key=lambda x: x['rating'])

        return filtered_feedbacks

    def _render_feedback_card(self, feedback, compact=False):
        """渲染单个反馈卡片"""
        # 根据紧急程度设置颜色
        urgency_color = {
            "一般": "#48bb78",
            "重要": "#ed8936",
            "紧急": "#f56565"
        }.get(feedback['urgency'], "#718096")

        # 根据评分设置星星
        stars = "⭐" * feedback['rating'] + "☆" * (5 - feedback['rating'])
        tool_badge = f" · {feedback['tool_name']}" if feedback.get("tool_name") else ""
        content = feedback['content']
        if compact and len(content) > 120:
            content = content[:117] + "..."
        nickname = html.escape(str(feedback['nickname']))
        meta_text = html.escape(f"{feedback['type']}{tool_badge} · {feedback['urgency']}")
        safe_content = html.escape(str(content))
        safe_timestamp = html.escape(str(feedback['timestamp']))

        with st.container():
            st.markdown(f"""
            <div style='
                background:
                    radial-gradient(circle at top right, rgba(250, 204, 21, 0.08), rgba(250, 204, 21, 0) 32%),
                    linear-gradient(145deg, rgba(255,255,255,0.96) 0%, rgba(247,239,223,0.76) 100%);
                padding: 15px; 
                border-radius: 16px; 
                border-left: 4px solid {urgency_color};
                margin: 10px 0;
                border: 1px solid rgba(213, 220, 232, 0.86);
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,0.86),
                    0 10px 20px rgba(15, 23, 42, 0.08);
            '>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                    <div>
                        <strong>{nickname}</strong>
                        <span style='color: {urgency_color}; font-size: 0.9em; margin-left: 10px;'>
                            {meta_text}
                        </span>
                    </div>
                    <div style='color: #476179; font-size: 0.8em;'>
                        {safe_timestamp}
                    </div>
                </div>
                <div style='color: #17324a; margin-bottom: 10px;'>
                    {safe_content}
                </div>
                <div style='color: #d69e2e; font-size: 0.9em;'>
                    {stars} ({feedback['rating']}/5)
                </div>
            </div>
            """, unsafe_allow_html=True)

    def _render_footer(self):
        """渲染页脚信息"""
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🛠️ 工具总数**")
            st.markdown(f"<h3 style='text-align: center; color: #17324a;'>{len(TOOL_CATEGORIES)}</h3>",
                        unsafe_allow_html=True)
        with col2:
            st.markdown("**📈 用户反馈**")
            st.markdown(f"<h3 style='text-align: center; color: #224d79;'>{len(st.session_state.user_feedbacks)}</h3>",
                        unsafe_allow_html=True)
        with col3:
            st.markdown("**💝 感谢使用**")
            st.markdown("<h3 style='text-align: center; color: #ea580c;'>❤️</h3>", unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align: center; color: #476179; margin-top: 20px;'>
            <small>感谢您使用测试工程师常用工具集！我们会根据您的反馈持续优化和改进。</small>
        </div>
        """, unsafe_allow_html=True)

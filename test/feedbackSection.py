import streamlit as st
import datetime
from data_constants import TOOL_CATEGORIES
import sys

print(sys.path)
sys.path.append('/mount/src/test/test')
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
            <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;'>
                <h4 style='color: #2d3748; margin-top: 0;'>💡 帮助我们做得更好！</h4>
                <p style='color: #4a5568; margin-bottom: 15px;'>
                    您的反馈对我们非常重要！请分享：
                </p>
                <ul style='color: #4a5568;'>
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

    def _handle_feedback_submission(self, feedback_type, urgency, rating, content, nickname):
        """处理反馈提交"""
        if not content.strip():
            st.error("❌ 请填写反馈内容")
            return

        if not rating:
            st.error("❌ 请选择满意度评分")
            return

        # 创建反馈记录
        feedback_record = {
            'id': st.session_state.feedback_count + 1,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': feedback_type,
            'urgency': urgency,
            'rating': rating,
            'content': content,
            'nickname': nickname or "匿名用户"
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
        - 紧急程度：{urgency}
        - 满意度：{rating}/5 分
        - 内容长度：{len(content)} 字符
        - 提交时间：{feedback_record['timestamp']}
        """)

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

    def _render_feedback_card(self, feedback):
        """渲染单个反馈卡片"""
        # 根据紧急程度设置颜色
        urgency_color = {
            "一般": "#48bb78",
            "重要": "#ed8936",
            "紧急": "#f56565"
        }.get(feedback['urgency'], "#718096")

        # 根据评分设置星星
        stars = "⭐" * feedback['rating'] + "☆" * (5 - feedback['rating'])

        with st.container():
            st.markdown(f"""
            <div style='
                background: white; 
                padding: 15px; 
                border-radius: 10px; 
                border-left: 4px solid {urgency_color};
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            '>
                <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
                    <div>
                        <strong>{feedback['nickname']}</strong>
                        <span style='color: {urgency_color}; font-size: 0.9em; margin-left: 10px;'>
                            {feedback['type']} · {feedback['urgency']}
                        </span>
                    </div>
                    <div style='color: #718096; font-size: 0.8em;'>
                        {feedback['timestamp']}
                    </div>
                </div>
                <div style='color: #4a5568; margin-bottom: 10px;'>
                    {feedback['content']}
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
            st.markdown(f"<h3 style='text-align: center; color: #667eea;'>{len(TOOL_CATEGORIES)}</h3>",
                        unsafe_allow_html=True)
        with col2:
            st.markdown("**📈 用户反馈**")
            st.markdown(f"<h3 style='text-align: center; color: #48bb78;'>{len(st.session_state.user_feedbacks)}</h3>",
                        unsafe_allow_html=True)
        with col3:
            st.markdown("**💝 感谢使用**")
            st.markdown("<h3 style='text-align: center; color: #ed8936;'>❤️</h3>", unsafe_allow_html=True)

        st.markdown("""
        <div style='text-align: center; color: #718096; margin-top: 20px;'>
            <small>感谢您使用测试工程师常用工具集！我们会根据您的反馈持续优化和改进。</small>
        </div>
        """, unsafe_allow_html=True)


import streamlit as st
from PIL import Image

from qa_toolkit.paths import IMAGES_DIR


class AuthorProfile:
    def __init__(self):
        self.styles = """
        <style>
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        .author-card {
            animation: fadeInUp 0.8s ease-out;
            transition: all 0.3s ease;
        }

        .author-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15) !important;
        }

        .tech-tag {
            animation: fadeInUp 0.6s ease-out;
            transition: all 0.3s ease;
        }

        .tech-tag:hover {
            transform: scale(1.1);
        }

        .qr-card {
            animation: float 3s ease-in-out infinite;
        }

        .gradient-bg {
            background: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #f5576c);
            background-size: 400% 400%;
            animation: gradientShift 8s ease infinite;
        }

        /* 链接悬停效果 */
        .sidebar-link {
            color: #1a202c; 
            text-decoration: none; 
            font-size: 12px;
            word-break: break-all;
            font-weight: 500;
            background: rgba(255,255,255,0.8);
            padding: 8px 12px;
            border-radius: 8px;
            display: block;
            text-align: center;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.5);
            margin-bottom: 10px;
        }

        .sidebar-link:hover {
            background: rgba(255,255,255,0.9);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .sidebar-link-small {
            color: #1a202c; 
            text-decoration: none; 
            font-size: 11px;
            word-break: break-all;
            font-weight: 500;
            background: rgba(255,255,255,0.8);
            padding: 6px 10px;
            border-radius: 6px;
            display: block;
            text-align: center;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.5);
            margin-bottom: 8px;
        }

        .sidebar-link-small:hover {
            background: rgba(255,255,255,0.9);
            transform: translateY(-2px);
        }

        /* 按钮样式 */
        .wechat-btn {
            display: inline-block;
            margin-top: 8px;
            padding: 4px 10px;
            background: rgba(255,255,255,0.8);
            color: #2d3748;
            text-decoration: none;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
            border: 1px solid rgba(255,255,255,0.5);
        }

        .wechat-btn:hover {
            background: rgba(255,255,255,0.9);
        }

        /* 侧边栏隐藏按钮样式 */
        .sidebar-toggle {
            position: fixed;
            right: 20px;
            bottom: 20px;
            z-index: 1000;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .sidebar-toggle:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }

        /* 隐藏按钮的样式 */
        .sidebar-toggle.hidden {
            display: none !important;
        }
        </style>
        """

        self.author_info = {
            "name": "LUCAS 🎯",
            "title": "进击的雷神",
            "description": "CSDN博客专家 | 测试技术布道者",
            "bio": "专注AI赋能开发测试、自动化测试、性能测试等领域，分享实用的测试工具和开发经验。CSDN博客「进击的雷神」，微信公众号「进击的测试圈」，持续输出高质量技术内容。",
            "csdn_url": "https://thundergod-lyx.blog.csdn.net",
            "wechat_public": "进击的测试圈",
            "wechat_url": "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=Mzg5Mzk3MTcwOQ==&action=getalbum&album_id=3163113351812644865#wechat_redirect",
            "gitcode_url": "https://gitcode.net/LYX_WIN",
            "github_url": "https://github.com/LUCAS-LYX025",
            "skills": ["AI应用师", "接口测试", "自动化测试", "性能测试","安全测试",  "测试工具开发"]
        }

    def load_image(self, image_path):
        """加载图片，如果图片不存在则返回None"""
        try:
            full_path = IMAGES_DIR / image_path
            if full_path.exists():
                return Image.open(full_path)
            return None
        except Exception:
            return None

    def render_main_profile(self):
        """渲染底部作者介绍"""
        st.markdown("---")
        st.markdown(self.styles, unsafe_allow_html=True)

        # 作者介绍主容器 - 动态渐变背景
        st.markdown(f"""
        <div class="gradient-bg" style="
            padding: 40px; 
            border-radius: 20px; 
            color: white;
            margin: 20px 0;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.1);"></div>
            <div style="position: relative; z-index: 2;">
                <h2 style="color: white; text-align: center; margin-bottom: 15px; font-size: 32px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">🚀 作者简介</h2>
                <p style="text-align: center; color: rgba(255,255,255,0.9); font-size: 16px; margin-bottom: 0;">{self.author_info['description']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 作者信息内容 - 三列布局
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            self._render_wechat_card()

        with col2:
            self._render_author_card()

        with col3:
            self._render_csdn_card()

        st.markdown("---")

    def _render_wechat_card(self):
        """渲染微信公众号卡片"""
        st.markdown("""
        <div class="author-card qr-card" style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 25px 20px; 
            border-radius: 20px; 
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border: none;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            text-align: center;
        ">
        """, unsafe_allow_html=True)

        wechat_image = self.load_image("wechat_qrcode.jpg")
        if wechat_image:
            st.markdown("""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                margin-bottom: 20px;
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            ">
            """, unsafe_allow_html=True)
            st.image(wechat_image, width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="font-size: 48px; margin-bottom: 15px;">💬</div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="width: 100%;">
            <div style="
                font-weight: 700; 
                font-size: 18px;
                margin-bottom: 8px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            ">💬 {self.author_info['wechat_public']}</div>
            <div style="
                font-size: 14px;
                margin-bottom: 10px;
                opacity: 0.9;
            ">微信公众号</div>
            <div style="
                font-size: 12px;
                line-height: 1.4;
                opacity: 0.8;
            ">技术分享 | AI测试开发 | 实战经验</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    def _render_author_card(self):
        """渲染作者信息卡片"""
        st.markdown("""
        <div class="author-card" style="
            background: linear-gradient(135deg, #f8fafc, #e2e8f0); 
            padding: 30px; 
            border-radius: 20px; 
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
            border: none;
            height: 100%;
        ">
        """, unsafe_allow_html=True)

        # 作者标题区域
        st.markdown(f"""
        <div style="margin-bottom: 25px; text-align: center;">
            <h3 style="color: #2d3748; margin-bottom: 8px; font-size: 24px; font-weight: 700;">{self.author_info['name']}</h3>
            <div style="
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                display: inline-block;
                margin-bottom: 10px;
            ">{self.author_info['title']}</div>
            <div style="color: #718096; font-size: 15px; margin-bottom: 5px;">🧪 测试工程师 | 📝 技术博主</div>
        </div>
        """, unsafe_allow_html=True)

        # 联系信息 - 改为渐变色背景
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 15px; padding: 12px; background: linear-gradient(135deg, #f0f4ff, #e6f0ff); border-radius: 12px; border-left: 4px solid #667eea;">
            <span style="background: #667eea; padding: 8px; border-radius: 50%; font-size: 16px; color: white; margin-right: 15px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">🌐</span>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #2d3748; font-size: 15px; margin-bottom: 4px;">CSDN博客</div>
                <a href="{self.author_info['csdn_url']}" target="_blank" style="color: #667eea; text-decoration: none; font-size: 14px; font-weight: 500;">进击的雷神 - thundergod-lyx.blog.csdn.net</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 15px; padding: 12px; background: linear-gradient(135deg, #fdf2ff, #f9e6ff); border-radius: 12px; border-left: 4px solid #f093fb;">
            <span style="background: #f093fb; padding: 8px; border-radius: 50%; font-size: 16px; color: white; margin-right: 15px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">💬</span>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #2d3748; font-size: 15px; margin-bottom: 4px;">微信公众号</div>
                <div style="color: #718096; font-size: 14px; font-weight: 500;">{self.author_info['wechat_public']} - 技术分享与实战经验</div>
                <a href="{self.author_info['wechat_url']}" target="_blank" style="color: #667eea; text-decoration: none; font-size: 12px; font-weight: 500;">访问公众号文章 →</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 代码仓库信息
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 15px; padding: 12px; background: linear-gradient(135deg, #f0fff4, #e6fffa); border-radius: 12px; border-left: 4px solid #48bb78;">
            <span style="background: #48bb78; padding: 8px; border-radius: 50%; font-size: 16px; color: white; margin-right: 15px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;">💻</span>
            <div style="flex: 1;">
                <div style="font-weight: 600; color: #2d3748; font-size: 15px; margin-bottom: 4px;">代码仓库</div>
                <div style="display: flex; flex-direction: column; gap: 4px;">
                    <a href="{self.author_info['gitcode_url']}" target="_blank" style="color: #667eea; text-decoration: none; font-size: 13px; font-weight: 500;">📦 GitCode: {self.author_info['gitcode_url'].split('//')[1]}</a>
                    <a href="{self.author_info['github_url']}" target="_blank" style="color: #667eea; text-decoration: none; font-size: 13px; font-weight: 500;">🐙 GitHub: {self.author_info['github_url'].split('//')[1]}</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 技术栈
        skills_html = "".join([
            f'<span class="tech-tag" style="background: linear-gradient(135deg, {self._get_skill_color(i)}); color: {self._get_skill_text_color(i)}; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; border: 1px solid {self._get_skill_border_color(i)};">{skill}</span>'
            for i, skill in enumerate(self.author_info['skills'])
        ])

        st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <div style="font-weight: 700; color: #2d3748; margin-bottom: 12px; font-size: 16px; display: flex; align-items: center;">
                <span style="margin-right: 8px;">🛠️</span>技术专长
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                {skills_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 个人简介 - 改为渐变色背景
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f7fafc, #edf2f7); 
            padding: 20px; 
            border-radius: 15px; 
            border-left: 5px solid #667eea;
            font-size: 14px;
            color: #4a5568;
            line-height: 1.6;
            position: relative;
        ">
            <div style="font-size: 24px; position: absolute; top: 15px; right: 20px; opacity: 0.1;">🚀</div>
            <div style="font-weight: 600; color: #2d3748; margin-bottom: 8px; font-size: 15px;">关于我</div>
            {self.author_info['bio']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    def _render_csdn_card(self):
        """渲染CSDN卡片"""
        st.markdown("""
        <div class="author-card qr-card" style="
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
            padding: 25px 20px; 
            border-radius: 20px; 
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border: none;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            text-align: center;
        ">
        """, unsafe_allow_html=True)

        csdn_image = self.load_image("csdn_profile.jpg")
        if csdn_image:
            st.markdown("""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                margin-bottom: 20px;
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
            ">
            """, unsafe_allow_html=True)
            st.image(csdn_image, width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="font-size: 48px; margin-bottom: 15px;">🌐</div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="width: 100%;">
            <div style="
                font-weight: 700; 
                font-size: 18px;
                margin-bottom: 8px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
            ">🌐 {self.author_info['title']}</div>
            <div style="
                font-size: 14px;
                margin-bottom: 10px;
                opacity: 0.9;
            ">CSDN博客</div>
            <div style="
                font-size: 12px;
                line-height: 1.4;
                opacity: 0.8;
            ">技术博客 | 原创分享 | 实战教程</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    def _get_skill_color(self, index):
        """获取技能标签颜色"""
        colors = [
            "#e6fffa, #b2f5ea",
            "#fff5f5, #fed7d7",
            "#f0fff4, #c6f6d5",
            "#faf5ff, #e9d8fd",
            "#fffaf0, #feebc8"
        ]
        return colors[index % len(colors)]

    def _get_skill_text_color(self, index):
        """获取技能标签文字颜色"""
        colors = ["#234e52", "#742a2a", "#22543d", "#44337a", "#744210"]
        return colors[index % len(colors)]

    def _get_skill_border_color(self, index):
        """获取技能标签边框颜色"""
        colors = ["#b2f5ea", "#fed7d7", "#c6f6d5", "#e9d8fd", "#feebc8"]
        return colors[index % len(colors)]

    def render_sidebar_profile(self):
        """渲染侧边栏作者信息"""
        with st.sidebar:
            st.markdown("---")
            st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h4 style="
                    color: #2d3748; 
                    margin-bottom: 15px; 
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    font-weight: 700;
                    font-size: 18px;
                ">🌟 关注作者</h4>
            </div>
            """, unsafe_allow_html=True)

            self._render_sidebar_wechat_card()
            self._render_sidebar_csdn_card()
            self._render_sidebar_links()

    def render_sidebar_compact_profile(self):
        """渲染更轻量的侧边栏作者卡，避免抢占工具主流程。"""
        st.markdown(self.styles, unsafe_allow_html=True)
        with st.sidebar:
            st.markdown("---")
            st.markdown(
                f"""
                <div class="author-card" style="
                    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
                    border: 1px solid #dbe4ff;
                    border-radius: 18px;
                    padding: 16px 16px 14px 16px;
                    box-shadow: 0 10px 24px rgba(79, 70, 229, 0.10);
                    margin-bottom: 14px;
                ">
                    <div style="font-size: 12px; font-weight: 700; color: #4f46e5; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;">
                        关于作者
                    </div>
                    <div style="font-size: 18px; font-weight: 800; color: #1e293b; margin-bottom: 4px;">
                        {self.author_info['name']}
                    </div>
                    <div style="font-size: 13px; color: #475569; line-height: 1.7; margin-bottom: 10px;">
                        {self.author_info['description']}
                    </div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;">
                        {''.join(
                            f"<span style='background:#ffffff;border:1px solid #dbe4ff;border-radius:999px;padding:4px 10px;font-size:11px;color:#334155;'>{skill}</span>"
                            for skill in self.author_info['skills'][:4]
                        )}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            link_col1, link_col2 = st.columns(2)
            with link_col1:
                st.link_button("CSDN", self.author_info["csdn_url"], use_container_width=True)
            with link_col2:
                st.link_button("GitHub", self.author_info["github_url"], use_container_width=True)

            with st.expander("公众号与更多资源", expanded=False):
                st.caption("需要深入内容时再展开，默认不打断工具操作。")
                wechat_image = self.load_image("wechat_qrcode.jpg")
                if wechat_image:
                    st.image(wechat_image, width="stretch")
                st.markdown(
                    f"- 微信公众号：`{self.author_info['wechat_public']}`\n"
                    f"- GitCode：{self.author_info['gitcode_url']}\n"
                    f"- 微信文章：{self.author_info['wechat_url']}"
                )

    def _render_sidebar_wechat_card(self):
        """渲染侧边栏微信公众号卡片"""
        st.markdown("""
        <div class="author-card" style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px 15px; 
            border-radius: 15px; 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            border: none;
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.1); backdrop-filter: blur(5px);"></div>
            <div style="position: relative; z-index: 2; width: 100%;">
        """, unsafe_allow_html=True)

        wechat_image = self.load_image("wechat_qrcode.jpg")
        if wechat_image:
            st.markdown("""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                margin-bottom: 15px;
                background: rgba(255,255,255,0.9);
                padding: 12px;
                border-radius: 12px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.3);
            ">
            """, unsafe_allow_html=True)
            st.image(wechat_image, width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="font-size: 36px; margin-bottom: 12px; color: #2d3748;">💬</div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align: center; width: 100%;">
            <div style="font-size: 16px; color: #1a202c; font-weight: 700; margin-bottom: 6px;">💬 {self.author_info['wechat_public']}</div>
            <div style="font-size: 13px; color: #2d3748; margin-bottom: 8px; font-weight: 600;">微信公众号</div>
            <div style="font-size: 11px; color: #4a5568; line-height: 1.4; padding: 0 10px;">技术分享 | 测试开发 | 实战经验</div>
            <a href="{self.author_info['wechat_url']}" target="_blank" class="wechat-btn">
                访问文章
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    def _render_sidebar_csdn_card(self):
        """渲染侧边栏CSDN卡片"""
        st.markdown("""
        <div class="author-card" style="
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
            padding: 20px 15px; 
            border-radius: 15px; 
            box-shadow: 0 8px 25px rgba(245, 87, 108, 0.3);
            border: none;
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.1); backdrop-filter: blur(5px);"></div>
            <div style="position: relative; z-index: 2; width: 100%;">
        """, unsafe_allow_html=True)

        csdn_image = self.load_image("csdn_profile.jpg")
        if csdn_image:
            st.markdown("""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                margin-bottom: 15px;
                background: rgba(255,255,255,0.9);
                padding: 12px;
                border-radius: 12px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.3);
            ">
            """, unsafe_allow_html=True)
            st.image(csdn_image, width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="font-size: 36px; margin-bottom: 12px; color: #2d3748;">🌐</div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="text-align: center; width: 100%;">
            <div style="font-size: 16px; color: #1a202c; font-weight: 700; margin-bottom: 6px;">🌐 {self.author_info['title']}</div>
            <div style="font-size: 13px; color: #2d3748; margin-bottom: 8px; font-weight: 600;">CSDN博客</div>
            <div style="font-size: 11px; color: #4a5568; line-height: 1.4; padding: 0 10px;">技术博客 | 原创分享 | 实战教程</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div></div>", unsafe_allow_html=True)

    def _render_sidebar_links(self):
        """渲染侧边栏链接"""
        st.markdown(f"""
        <div class="author-card" style="
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
            padding: 20px; 
            border-radius: 15px; 
            box-shadow: 0 8px 25px rgba(79, 172, 254, 0.3);
            border: none;
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255,255,255,0.1); backdrop-filter: blur(5px);"></div>
            <div style="position: relative; z-index: 2;">
                <div style="font-size: 15px; color: #1a202c; margin-bottom: 12px; font-weight: 700; display: flex; align-items: center;">
                    <span style="margin-right: 8px;">⚡</span>快速访问
                </div>
                <div style="font-size: 13px; color: #2d3748; margin-bottom: 8px; font-weight: 600;">CSDN博客</div>
                <a href="{self.author_info['csdn_url']}" style="
                    color: #1a202c; 
                    text-decoration: none; 
                    font-size: 12px;
                    word-break: break-all;
                    font-weight: 500;
                    background: rgba(255,255,255,0.8);
                    padding: 8px 12px;
                    border-radius: 8px;
                    display: block;
                    text-align: center;
                    transition: all 0.3s ease;
                    border: 1px solid rgba(255,255,255,0.5);
                " onmouseover="this.style.background='rgba(255,255,255,0.9)'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.15)';" 
                onmouseout="this.style.background='rgba(255,255,255,0.8)'; this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                    thundergod-lyx.blog.csdn.net
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 使用示例
def main():
    # 创建作者信息实例
    author = AuthorProfile()

    # 根据需要在不同位置调用
    # 如果要在主内容区显示作者介绍，调用：
    # author.render_main_profile()

    # 如果要在侧边栏显示作者信息，调用：
    # author.render_sidebar_profile()


if __name__ == "__main__":
    main()

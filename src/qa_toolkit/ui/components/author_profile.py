import base64
import html
import io
import mimetypes

import streamlit as st
import streamlit.components.v1 as components
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
            "name": "LUCAS",
            "title": "测试开发与质量工程实践者",
            "description": "专注测试开发、AI 提效与工具落地",
            "bio": "长期聚焦 AI 赋能测试开发、自动化测试、性能测试与质量工程建设，持续沉淀可复用工具、工程化方法与一线实战经验。CSDN 博客「进击的雷神」、微信公众号「进击的测试圈」围绕测试开发提效、质量治理落地与团队协作持续更新。",
            "sidebar_tagline": "测试开发 | AI 提效 | 工程实践",
            "sidebar_story": "👇专注测试老本行，顺便卷一卷👇",
            "csdn_url": "https://thundergod-lyx.blog.csdn.net",
            "wechat_public": "进击的测试圈",
            "wechat_url": "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=Mzg5Mzk3MTcwOQ==&action=getalbum&album_id=3163113351812644865#wechat_redirect",
            "gitcode_url": "https://gitcode.net/LYX_WIN",
            "github_url": "https://github.com/LUCAS-LYX025",
            "sidebar_hero_gif_asset": "luffy_jump.gif",
            "sidebar_hero_gif_url": "https://media1.tenor.com/m/Adp4Bl8kqaAAAAAC/luffy-jump.gif",
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

    def _image_to_data_uri(self, image_path):
        """将本地图片转成 data URI，方便在 HTML 卡片中直接使用。"""
        image = self.load_image(image_path)
        if image is None:
            return ""

        export_image = image
        if image.mode not in {"RGB", "RGBA"}:
            export_image = image.convert("RGBA" if "A" in image.mode else "RGB")

        image_format = "PNG" if export_image.mode == "RGBA" else "JPEG"
        if image_format == "JPEG":
            export_image = export_image.convert("RGB")

        buffer = io.BytesIO()
        save_kwargs = {"format": image_format}
        if image_format == "JPEG":
            save_kwargs["quality"] = 92
        export_image.save(buffer, **save_kwargs)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        mime = "image/png" if image_format == "PNG" else "image/jpeg"
        return f"data:{mime};base64,{encoded}"

    def _build_avatar_placeholder_data_uri(self, label="L"):
        """构建内联 SVG 占位头像，确保无网络时也能展示。"""
        safe_label = html.escape(str(label or "L"))[:2]
        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
            <defs>
                <linearGradient id="avatarBg" x1="0%" x2="100%" y1="0%" y2="100%">
                    <stop offset="0%" stop-color="#fff7ed" />
                    <stop offset="100%" stop-color="#ffedd5" />
                </linearGradient>
            </defs>
            <rect width="320" height="320" rx="160" fill="url(#avatarBg)" />
            <text x="50%" y="54%" text-anchor="middle" font-size="132" font-weight="900"
                  font-family="Avenir Next, PingFang SC, Microsoft YaHei, sans-serif"
                  fill="#9a3412">{safe_label}</text>
        </svg>
        """.strip()
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"

    def _asset_file_to_data_uri(self, asset_name):
        """将本地静态资源转成 data URI，适合 GIF / PNG / JPG 等原始文件。"""
        if not asset_name:
            return ""

        asset_path = IMAGES_DIR / asset_name
        if not asset_path.exists() or not asset_path.is_file():
            return ""

        mime_type, _ = mimetypes.guess_type(str(asset_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
        except Exception:
            return ""

        return f"data:{mime_type};base64,{encoded}"

    def _build_sidebar_hero_visual_html(self, avatar_uri):
        """优先展示动态头像，加载失败时自动回退到本地头像。"""
        fallback_uri = avatar_uri or self._build_avatar_placeholder_data_uri(self.author_info.get("name", "L")[:1])
        local_hero_gif_uri = self._asset_file_to_data_uri(self.author_info.get("sidebar_hero_gif_asset", ""))
        hero_gif_url = local_hero_gif_uri or (self.author_info.get("sidebar_hero_gif_url") or "").strip()
        safe_fallback_uri = html.escape(fallback_uri, quote=True)
        if not hero_gif_url:
            return f'<img src="{safe_fallback_uri}" alt="作者头像" class="hero-avatar" />'

        safe_hero_gif_url = html.escape(hero_gif_url, quote=True)
        return (
            '<div class="hero-visual-stack">'
            f'<img src="{safe_fallback_uri}" alt="作者头像" class="hero-avatar hero-avatar--base" />'
            f'<img src="{safe_hero_gif_url}" alt="动态头像" class="hero-luffy hero-luffy--overlay" loading="eager" '
            f'referrerpolicy="no-referrer" '
            f'onerror="this.onerror=null;this.style.display=\'none\';" />'
            '</div>'
        )

    def _render_sidebar_compact_styles(self):
        st.markdown(
            """
            <style>
            @keyframes qaCurtainLeft {
                0% { transform: translateX(0) skewY(0deg); }
                100% { transform: translateX(-115%) skewY(-6deg); }
            }

            @keyframes qaCurtainRight {
                0% { transform: translateX(0) skewY(0deg); }
                100% { transform: translateX(115%) skewY(6deg); }
            }

            @keyframes qaCaptainPop {
                0% { opacity: 0; transform: translateY(18px) scale(0.78) rotate(-10deg); }
                65% { opacity: 1; transform: translateY(-5px) scale(1.03) rotate(3deg); }
                100% { opacity: 1; transform: translateY(0) scale(1) rotate(0deg); }
            }

            @keyframes qaGlowDrift {
                0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
                50% { transform: translate3d(6px, -10px, 0) scale(1.06); }
            }

            @keyframes qaRibbonFloat {
                0%, 100% { transform: translateX(-50%) translateY(0); }
                50% { transform: translateX(-50%) translateY(-3px); }
            }

            .qa-sidebar-author-showcase {
                position: relative;
                overflow: hidden;
                border-radius: 24px;
                padding: 18px 16px 16px;
                margin: 4px 0 14px;
                background:
                    radial-gradient(circle at 18% 18%, rgba(250, 204, 21, 0.26), transparent 30%),
                    radial-gradient(circle at 82% 14%, rgba(45, 212, 191, 0.18), transparent 24%),
                    linear-gradient(160deg, #071427 0%, #13294b 48%, #09111f 100%);
                border: 1px solid rgba(250, 204, 21, 0.20);
                box-shadow: 0 18px 34px rgba(7, 20, 39, 0.34);
            }

            .qa-sidebar-author-showcase::before {
                content: "";
                position: absolute;
                inset: 10px;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.10);
                pointer-events: none;
            }

            .qa-sidebar-author-glow {
                position: absolute;
                inset: auto auto 18px 20px;
                width: 92px;
                height: 92px;
                border-radius: 999px;
                background: radial-gradient(circle, rgba(250, 204, 21, 0.34), rgba(250, 204, 21, 0));
                filter: blur(6px);
                animation: qaGlowDrift 4.2s ease-in-out infinite;
            }

            .qa-sidebar-author-curtain {
                position: absolute;
                top: -10%;
                bottom: -10%;
                width: 54%;
                z-index: 2;
                background: linear-gradient(180deg, #fb923c 0%, #ea580c 42%, #7c2d12 100%);
                box-shadow: inset -10px 0 18px rgba(124, 45, 18, 0.34);
            }

            .qa-sidebar-author-curtain::after {
                content: "";
                position: absolute;
                inset: 0;
                background: repeating-linear-gradient(
                    90deg,
                    rgba(255, 255, 255, 0.14) 0,
                    rgba(255, 255, 255, 0.14) 6px,
                    transparent 6px,
                    transparent 18px
                );
                opacity: 0.36;
            }

            .qa-sidebar-author-curtain--left {
                left: -5%;
                border-radius: 20px 0 0 20px;
                animation: qaCurtainLeft 1.2s cubic-bezier(0.66, 0, 0.2, 1) forwards;
            }

            .qa-sidebar-author-curtain--right {
                right: -5%;
                border-radius: 0 20px 20px 0;
                box-shadow: inset 10px 0 18px rgba(124, 45, 18, 0.34);
                animation: qaCurtainRight 1.2s cubic-bezier(0.66, 0, 0.2, 1) forwards;
            }

            .qa-sidebar-author-stage-copy {
                position: relative;
                z-index: 1;
                text-align: center;
                margin-bottom: 10px;
            }

            .qa-sidebar-author-kicker {
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.16em;
                color: rgba(250, 204, 21, 0.92);
                font-weight: 800;
                margin-bottom: 6px;
            }

            .qa-sidebar-author-stage-title {
                color: #f8fafc;
                font-size: 22px;
                line-height: 1.1;
                font-weight: 900;
                margin-bottom: 6px;
            }

            .qa-sidebar-author-stage-subtitle {
                color: rgba(226, 232, 240, 0.88);
                font-size: 12px;
                line-height: 1.6;
            }

            .qa-sidebar-author-avatar-shell {
                position: relative;
                z-index: 3;
                width: 92px;
                height: 92px;
                margin: 0 auto 14px;
                padding: 3px;
                border-radius: 999px;
                background: linear-gradient(135deg, #facc15 0%, #fb7185 100%);
                box-shadow: 0 18px 28px rgba(15, 23, 42, 0.26);
                animation: qaCaptainPop 1.12s 0.4s both;
            }

            .qa-sidebar-author-avatar {
                width: 100%;
                height: 100%;
                display: block;
                object-fit: cover;
                border-radius: 999px;
                border: 2px solid rgba(255, 255, 255, 0.72);
                background: #ffffff;
            }

            .qa-sidebar-author-avatar-fallback {
                width: 100%;
                height: 100%;
                border-radius: 999px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
                color: #9a3412;
                font-size: 28px;
                font-weight: 900;
                border: 2px solid rgba(255, 255, 255, 0.72);
            }

            .qa-sidebar-author-ribbon {
                position: absolute;
                left: 50%;
                bottom: -10px;
                transform: translateX(-50%);
                white-space: nowrap;
                background: rgba(8, 15, 29, 0.88);
                border: 1px solid rgba(250, 204, 21, 0.28);
                color: #fef3c7;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 0.04em;
                animation: qaRibbonFloat 3.4s ease-in-out infinite;
            }

            .qa-sidebar-author-copy {
                position: relative;
                z-index: 1;
                text-align: center;
            }

            .qa-sidebar-author-name {
                color: #f8fafc;
                font-size: 19px;
                font-weight: 900;
                margin-bottom: 4px;
            }

            .qa-sidebar-author-title {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                padding: 6px 12px;
                border-radius: 999px;
                background: linear-gradient(135deg, rgba(250, 204, 21, 0.16), rgba(248, 113, 113, 0.18));
                color: #fde68a;
                font-size: 11px;
                font-weight: 800;
                margin-bottom: 10px;
                border: 1px solid rgba(250, 204, 21, 0.20);
            }

            .qa-sidebar-author-description {
                color: rgba(226, 232, 240, 0.90);
                font-size: 12px;
                line-height: 1.75;
                margin-bottom: 12px;
            }

            .qa-sidebar-author-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 7px;
                justify-content: center;
            }

            .qa-sidebar-author-chip {
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.14);
                color: #e2e8f0;
                border-radius: 999px;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: 700;
                backdrop-filter: blur(8px);
            }

            .qa-sidebar-author-card-stack {
                display: grid;
                gap: 10px;
                margin-bottom: 12px;
            }

            .qa-sidebar-author-link-card {
                position: relative;
                display: flex;
                align-items: flex-start;
                gap: 12px;
                padding: 13px 14px;
                border-radius: 18px;
                text-decoration: none;
                color: #e2e8f0 !important;
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.90), rgba(30, 41, 59, 0.94));
                border: 1px solid rgba(148, 163, 184, 0.18);
                box-shadow: 0 12px 22px rgba(15, 23, 42, 0.18);
                overflow: hidden;
                transition: transform 0.24s ease, box-shadow 0.24s ease, border-color 0.24s ease;
            }

            .qa-sidebar-author-link-card::before {
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(135deg, var(--card-glow), transparent 55%);
                opacity: 0.95;
                pointer-events: none;
            }

            .qa-sidebar-author-link-card::after {
                content: "";
                position: absolute;
                top: 12px;
                bottom: 12px;
                left: 0;
                width: 4px;
                border-radius: 999px;
                background: var(--card-accent);
                box-shadow: 0 0 18px var(--card-glow);
            }

            .qa-sidebar-author-link-card:hover {
                transform: translateY(-3px) scale(1.01);
                border-color: rgba(250, 204, 21, 0.28);
                box-shadow: 0 18px 28px rgba(15, 23, 42, 0.26);
            }

            .qa-sidebar-author-link-icon {
                position: relative;
                z-index: 1;
                width: 42px;
                height: 42px;
                border-radius: 14px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                font-weight: 900;
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.12);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
                flex: 0 0 auto;
            }

            .qa-sidebar-author-link-body {
                position: relative;
                z-index: 1;
                min-width: 0;
                flex: 1;
            }

            .qa-sidebar-author-link-title {
                color: #f8fafc;
                font-size: 14px;
                font-weight: 800;
                margin-bottom: 4px;
            }

            .qa-sidebar-author-link-meta {
                color: rgba(226, 232, 240, 0.76);
                font-size: 11px;
                line-height: 1.6;
                margin-bottom: 8px;
            }

            .qa-sidebar-author-link-cta {
                color: var(--card-accent);
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.03em;
            }

            .qa-sidebar-author-drawer-note {
                color: #64748b;
                font-size: 12px;
                line-height: 1.7;
                margin-bottom: 10px;
            }

            .qa-sidebar-author-mini-grid {
                display: grid;
                gap: 8px;
                margin-top: 10px;
            }

            .qa-sidebar-author-mini-card {
                display: block;
                text-decoration: none;
                color: #0f172a !important;
                border-radius: 14px;
                padding: 11px 12px;
                background: linear-gradient(135deg, #fff7ed 0%, #fffbeb 100%);
                border: 1px solid rgba(251, 146, 60, 0.18);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }

            .qa-sidebar-author-mini-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 18px rgba(249, 115, 22, 0.12);
            }

            .qa-sidebar-author-mini-card strong {
                display: block;
                font-size: 12px;
                margin-bottom: 3px;
            }

            .qa-sidebar-author-mini-card span {
                display: block;
                font-size: 11px;
                color: #475569;
                line-height: 1.5;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def _build_sidebar_compact_showcase_html(self):
        avatar_uri = self._image_to_data_uri("csdn_profile.jpg")
        avatar_markup = (
            f'<img src="{avatar_uri}" alt="作者头像" class="qa-sidebar-author-avatar" />'
            if avatar_uri
            else '<div class="qa-sidebar-author-avatar-fallback">L</div>'
        )
        chips_html = "".join(
            f'<span class="qa-sidebar-author-chip">{skill}</span>'
            for skill in self.author_info["skills"][:4]
        )

        return f"""
        <div class="qa-sidebar-author-showcase">
            <div class="qa-sidebar-author-glow"></div>
            <div class="qa-sidebar-author-curtain qa-sidebar-author-curtain--left"></div>
            <div class="qa-sidebar-author-curtain qa-sidebar-author-curtain--right"></div>
            <div class="qa-sidebar-author-stage-copy">
                <div class="qa-sidebar-author-kicker">Author Deck</div>
                <div class="qa-sidebar-author-stage-title">开门见山</div>
                <div class="qa-sidebar-author-stage-subtitle">侧边栏改成了更像舞台入口的作者名片，信息更直给，交互更轻。</div>
            </div>
            <div class="qa-sidebar-author-avatar-shell">
                {avatar_markup}
                <div class="qa-sidebar-author-ribbon">冒险模式开启</div>
            </div>
            <div class="qa-sidebar-author-copy">
                <div class="qa-sidebar-author-name">{self.author_info['name']}</div>
                <div class="qa-sidebar-author-title">航海风技术卡片 · {self.author_info['title']}</div>
                <div class="qa-sidebar-author-description">{self.author_info['description']}</div>
                <div class="qa-sidebar-author-chip-row">{chips_html}</div>
            </div>
        </div>
        """

    def _build_sidebar_compact_link_cards_html(self):
        cards = [
            {
                "title": "CSDN 专栏",
                "meta": "工具拆解、AI 测试开发、实战教程",
                "cta": "点击进入专栏",
                "icon": "📚",
                "href": self.author_info["csdn_url"],
                "accent": "#fb7185",
                "glow": "rgba(251, 113, 133, 0.22)",
            },
            {
                "title": "GitHub 仓库",
                "meta": "开源项目、更新记录、Issue 协作",
                "cta": "查看仓库动态",
                "icon": "⚙",
                "href": self.author_info["github_url"],
                "accent": "#38bdf8",
                "glow": "rgba(56, 189, 248, 0.20)",
            },
            {
                "title": "GitCode 镜像",
                "meta": "国内访问更顺手，适合快速拉代码",
                "cta": "打开国内镜像",
                "icon": "🧩",
                "href": self.author_info["gitcode_url"],
                "accent": "#f97316",
                "glow": "rgba(249, 115, 22, 0.22)",
            },
            {
                "title": "公众号专栏",
                "meta": "精选合集、工具复盘、测试方法论",
                "cta": "点击查看文章集",
                "icon": "📡",
                "href": self.author_info["wechat_url"],
                "accent": "#2dd4bf",
                "glow": "rgba(45, 212, 191, 0.22)",
            },
        ]

        cards_html = "".join(
            f"""
            <a class="qa-sidebar-author-link-card"
               href="{card['href']}"
               target="_blank"
               rel="noopener noreferrer"
               style="--card-accent: {card['accent']}; --card-glow: {card['glow']};">
                <div class="qa-sidebar-author-link-icon">{card['icon']}</div>
                <div class="qa-sidebar-author-link-body">
                    <div class="qa-sidebar-author-link-title">{card['title']}</div>
                    <div class="qa-sidebar-author-link-meta">{card['meta']}</div>
                    <div class="qa-sidebar-author-link-cta">{card['cta']} →</div>
                </div>
            </a>
            """
            for card in cards
        )
        return f'<div class="qa-sidebar-author-card-stack">{cards_html}</div>'

    def _build_sidebar_compact_component_html(self):
        avatar_uri = self._image_to_data_uri("csdn_profile.jpg")
        hero_visual_html = self._build_sidebar_hero_visual_html(avatar_uri)
        logo_uris = {
            "CSDN 专栏": self._image_to_data_uri("brand_csdn.ico"),
            "GitHub 仓库": self._image_to_data_uri("brand_github.png"),
            "GitCode 镜像": self._image_to_data_uri("brand_gitcode.png"),
        }

        cards = [
            {
                "title": "CSDN 专栏",
                "desc": "文章与实践总结。",
                "cta": "阅读文章",
                "href": self.author_info["csdn_url"],
                "accent": "#fb7185",
                "glow": "rgba(251, 113, 133, 0.24)",
            },
            {
                "title": "GitHub 仓库",
                "desc": "源码、迭代与协作记录。",
                "cta": "查看源码",
                "href": self.author_info["github_url"],
                "accent": "#38bdf8",
                "glow": "rgba(56, 189, 248, 0.24)",
            },
            {
                "title": "GitCode 镜像",
                "desc": "国内访问更稳的镜像仓库。",
                "cta": "访问镜像",
                "href": self.author_info["gitcode_url"],
                "accent": "#f97316",
                "glow": "rgba(249, 115, 22, 0.24)",
            },
        ]
        cards_html = "".join(
            f"""
            <a class="deck-card" href="{card['href']}" target="_blank" rel="noopener noreferrer"
               style="--accent:{card['accent']};--glow:{card['glow']};">
                <div class="deck-card__icon">
                    <img src="{logo_uris.get(card['title'], '')}" alt="{card['title']} 图标" class="deck-card__logo" />
                </div>
                <div class="deck-card__body">
                    <div class="deck-card__title">{card['title']}</div>
                    <div class="deck-card__desc">{card['desc']}</div>
                    <div class="deck-card__cta">{card['cta']} →</div>
                </div>
            </a>
            """
            for card in cards
        )

        skill_html = "".join(
            f'<span class="skill-chip">{skill}</span>'
            for skill in self.author_info["skills"][:4]
        )

        return f"""
        <!doctype html>
        <html lang="zh-CN">
        <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            * {{ box-sizing: border-box; }}
            html, body {{
                width: 100%;
                max-width: 100%;
                overflow-x: hidden;
            }}
            body {{
                margin: 0;
                font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
                background: transparent;
                color: #e2e8f0;
            }}
            @keyframes curtainLeft {{
                0% {{ transform: translateX(0) skewY(0deg); }}
                100% {{ transform: translateX(-118%) skewY(-7deg); }}
            }}
            @keyframes curtainRight {{
                0% {{ transform: translateX(0) skewY(0deg); }}
                100% {{ transform: translateX(118%) skewY(7deg); }}
            }}
            @keyframes captainPop {{
                0% {{ opacity: 0; transform: translateY(18px) scale(.76) rotate(-11deg); }}
                65% {{ opacity: 1; transform: translateY(-4px) scale(1.04) rotate(2deg); }}
                100% {{ opacity: 1; transform: translateY(0) scale(1) rotate(0deg); }}
            }}
            @keyframes glowDrift {{
                0%, 100% {{ transform: translate3d(0,0,0) scale(1); }}
                50% {{ transform: translate3d(7px,-10px,0) scale(1.05); }}
            }}
            @keyframes ribbonFloat {{
                0%, 100% {{ transform: translateX(-50%) translateY(0); }}
                50% {{ transform: translateX(-50%) translateY(-3px); }}
            }}
            @keyframes heroFloat {{
                0%, 100% {{ transform: translateY(0px); }}
                50% {{ transform: translateY(-5px); }}
            }}
            .author-deck {{
                position: relative;
                overflow: hidden;
                width: 100%;
                border-radius: 26px;
                padding: 18px 16px 16px;
                background:
                    radial-gradient(circle at 16% 15%, rgba(250, 204, 21, .26), transparent 28%),
                    radial-gradient(circle at 84% 14%, rgba(45, 212, 191, .18), transparent 22%),
                    linear-gradient(160deg, #071427 0%, #13294b 48%, #09111f 100%);
                border: 1px solid rgba(250, 204, 21, .18);
                box-shadow: 0 18px 36px rgba(7, 20, 39, .34);
            }}
            .author-deck::before {{
                content: "";
                position: absolute;
                inset: 10px;
                border: 1px solid rgba(255,255,255,.10);
                border-radius: 22px;
                pointer-events: none;
            }}
            .glow {{
                position: absolute;
                left: 20px;
                bottom: 18px;
                width: 94px;
                height: 94px;
                border-radius: 999px;
                background: radial-gradient(circle, rgba(250, 204, 21, .34), rgba(250, 204, 21, 0));
                filter: blur(8px);
                animation: glowDrift 4.2s ease-in-out infinite;
            }}
            .curtain {{
                position: absolute;
                top: -8%;
                bottom: -8%;
                width: 54%;
                z-index: 2;
                background: linear-gradient(180deg, #fb923c 0%, #ea580c 44%, #7c2d12 100%);
            }}
            .curtain::after {{
                content: "";
                position: absolute;
                inset: 0;
                background: repeating-linear-gradient(
                    90deg,
                    rgba(255,255,255,.14) 0,
                    rgba(255,255,255,.14) 6px,
                    transparent 6px,
                    transparent 18px
                );
                opacity: .36;
            }}
            .curtain--left {{
                left: -6%;
                border-radius: 22px 0 0 22px;
                box-shadow: inset -12px 0 20px rgba(124,45,18,.30);
                animation: curtainLeft 1.16s cubic-bezier(.66,0,.2,1) forwards;
            }}
            .curtain--right {{
                right: -6%;
                border-radius: 0 22px 22px 0;
                box-shadow: inset 12px 0 20px rgba(124,45,18,.30);
                animation: curtainRight 1.16s cubic-bezier(.66,0,.2,1) forwards;
            }}
            .deck-copy {{
                position: relative;
                z-index: 1;
                text-align: center;
                margin-bottom: 12px;
            }}
            .deck-kicker {{
                font-size: 11px;
                letter-spacing: .22em;
                text-transform: uppercase;
                color: rgba(250, 204, 21, .94);
                font-weight: 800;
                margin-bottom: 6px;
            }}
            .deck-title {{
                font-size: 22px;
                font-weight: 900;
                line-height: 1.1;
                color: #f8fafc;
                margin-bottom: 8px;
            }}
            .deck-subtitle {{
                font-size: 12px;
                line-height: 1.75;
                color: rgba(226, 232, 240, .84);
                max-width: 250px;
                margin: 0 auto;
            }}
            .hero-shell {{
                position: relative;
                z-index: 3;
                width: 126px;
                height: 126px;
                margin: 0 auto 28px;
                padding: 3px;
                border-radius: 999px;
                background: linear-gradient(135deg, #facc15 0%, #fb7185 100%);
                box-shadow: 0 18px 28px rgba(15, 23, 42, .26);
                animation: captainPop 1.08s .35s both, heroFloat 4.6s 1.2s ease-in-out infinite;
                overflow: visible;
            }}
            .hero-visual-stack {{
                position: relative;
                width: 100%;
                height: 100%;
                border-radius: 999px;
                overflow: hidden;
            }}
            .hero-avatar {{
                position: absolute;
                inset: 0;
                width: 100%;
                height: 100%;
                border-radius: 999px;
                object-fit: cover;
                display: block;
                border: 2px solid rgba(255,255,255,.72);
                background: #fff;
            }}
            .hero-avatar-fallback {{
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 30px;
                font-weight: 900;
                color: #9a3412;
                background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
            }}
            .hero-luffy {{
                position: absolute;
                inset: 0;
                width: 100%;
                height: 100%;
                border-radius: 999px;
                object-fit: cover;
                display: block;
                border: 2px solid rgba(255,255,255,.72);
                background: radial-gradient(circle at 50% 40%, #fff7ed 0%, #ffedd5 58%, #fdba74 100%);
                box-shadow: inset 0 0 18px rgba(255,255,255,.18);
            }}
            .hero-avatar--base {{
                z-index: 1;
            }}
            .hero-luffy--overlay {{
                z-index: 2;
            }}
            .hero-ribbon {{
                position: absolute;
                left: 50%;
                bottom: -10px;
                z-index: 4;
                transform: translateX(-50%);
                white-space: nowrap;
                padding: 4px 10px;
                border-radius: 999px;
                background: rgba(8, 15, 29, .88);
                border: 1px solid rgba(250, 204, 21, .28);
                color: #fef3c7;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: .04em;
                animation: ribbonFloat 3.4s ease-in-out infinite;
            }}
            .identity {{
                position: relative;
                z-index: 1;
                text-align: center;
            }}
            .identity-name {{
                font-size: 20px;
                font-weight: 900;
                color: #f8fafc;
                margin-bottom: 4px;
            }}
            .identity-summary {{
                font-size: 11px;
                line-height: 1.7;
                color: rgba(191, 219, 254, .84);
                max-width: 250px;
                margin: 0 auto 8px;
            }}
            .identity-role {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                padding: 6px 12px;
                border-radius: 999px;
                background: linear-gradient(135deg, rgba(250, 204, 21, .16), rgba(248, 113, 113, .18));
                color: #fde68a;
                font-size: 11px;
                font-weight: 800;
                border: 1px solid rgba(250, 204, 21, .18);
                margin-bottom: 10px;
            }}
            .identity-text {{
                font-size: 12px;
                line-height: 1.82;
                color: rgba(226, 232, 240, .9);
                margin: 0 auto 12px;
                max-width: 252px;
            }}
            .skill-row {{
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 7px;
                margin-bottom: 14px;
            }}
            .skill-chip {{
                padding: 5px 10px;
                border-radius: 999px;
                font-size: 10px;
                font-weight: 700;
                color: #e2e8f0;
                background: rgba(255,255,255,.10);
                border: 1px solid rgba(255,255,255,.14);
                backdrop-filter: blur(8px);
            }}
            .cards {{
                display: grid;
                gap: 8px;
            }}
            .deck-card {{
                position: relative;
                display: flex;
                align-items: flex-start;
                gap: 12px;
                text-decoration: none;
                color: inherit;
                padding: 12px 13px;
                border-radius: 18px;
                background: linear-gradient(135deg, rgba(15, 23, 42, .92), rgba(30, 41, 59, .96));
                border: 1px solid rgba(148, 163, 184, .18);
                box-shadow: 0 12px 22px rgba(15, 23, 42, .18);
                overflow: hidden;
                transition: transform .24s ease, box-shadow .24s ease, border-color .24s ease, background .24s ease;
            }}
            .deck-card::before {{
                content: "";
                position: absolute;
                inset: 0;
                background: linear-gradient(135deg, var(--glow), transparent 56%);
                opacity: .86;
            }}
            .deck-card::after {{
                content: "";
                position: absolute;
                top: 12px;
                bottom: 12px;
                left: 0;
                width: 4px;
                border-radius: 999px;
                background: var(--accent);
                box-shadow: 0 0 18px var(--glow);
            }}
            .deck-card:hover {{
                transform: translateY(-4px) scale(1.012);
                box-shadow: 0 20px 30px rgba(15, 23, 42, .28);
                border-color: rgba(250, 204, 21, .30);
                background: linear-gradient(135deg, rgba(15, 23, 42, .96), rgba(37, 49, 71, .98));
            }}
            .deck-card__icon {{
                position: relative;
                z-index: 1;
                width: 46px;
                height: 46px;
                flex: 0 0 auto;
                border-radius: 16px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: rgba(255,255,255,.10);
                border: 1px solid rgba(255,255,255,.12);
                padding: 8px;
                transition: transform .24s ease, background .24s ease, border-color .24s ease;
            }}
            .deck-card__logo {{
                width: 100%;
                height: 100%;
                object-fit: contain;
                display: block;
                filter: drop-shadow(0 2px 8px rgba(15, 23, 42, .24));
            }}
            .deck-card:hover .deck-card__icon {{
                transform: translateY(-2px) scale(1.05);
                background: rgba(255,255,255,.14);
                border-color: rgba(255,255,255,.20);
            }}
            .deck-card__body {{
                position: relative;
                z-index: 1;
                flex: 1 1 auto;
                min-width: 0;
            }}
            .deck-card__title {{
                font-size: 14px;
                font-weight: 800;
                color: #f8fafc;
                margin-bottom: 4px;
            }}
            .deck-card__desc {{
                font-size: 10.5px;
                line-height: 1.55;
                color: rgba(226, 232, 240, .78);
                margin-bottom: 7px;
            }}
            .deck-card__cta {{
                font-size: 11px;
                font-weight: 800;
                color: var(--accent);
                transition: transform .24s ease, letter-spacing .24s ease;
            }}
            .deck-card:hover .deck-card__cta {{
                transform: translateX(2px);
                letter-spacing: .02em;
            }}
            @media (max-width: 640px) {{
                .author-deck {{
                    border-radius: 22px;
                    padding: 16px 12px 12px;
                }}
                .author-deck::before {{
                    inset: 8px;
                    border-radius: 18px;
                }}
                .deck-title {{
                    font-size: 20px;
                }}
                .deck-subtitle,
                .identity-summary,
                .identity-text {{
                    max-width: none;
                }}
                .hero-shell {{
                    width: 106px;
                    height: 106px;
                    margin-bottom: 24px;
                }}
                .hero-ribbon {{
                    bottom: -8px;
                    padding: 4px 9px;
                    font-size: 9px;
                }}
                .identity-name {{
                    font-size: 18px;
                }}
                .identity-role {{
                    padding: 5px 10px;
                    font-size: 10px;
                    margin-bottom: 8px;
                }}
                .identity-text {{
                    line-height: 1.72;
                    margin-bottom: 10px;
                }}
                .skill-row {{
                    gap: 6px;
                    margin-bottom: 12px;
                }}
                .deck-card {{
                    gap: 10px;
                    padding: 10px 11px;
                    border-radius: 16px;
                }}
                .deck-card__icon {{
                    width: 40px;
                    height: 40px;
                    border-radius: 14px;
                    padding: 7px;
                }}
                .deck-card__title {{
                    font-size: 13px;
                }}
                .deck-card__desc {{
                    font-size: 10px;
                    margin-bottom: 5px;
                }}
            }}
            @media (max-width: 420px) {{
                .author-deck {{
                    padding: 14px 10px 10px;
                }}
                .deck-subtitle {{
                    font-size: 11px;
                    line-height: 1.6;
                }}
                .hero-shell {{
                    width: 96px;
                    height: 96px;
                    margin-bottom: 20px;
                }}
                .identity-summary {{
                    font-size: 10.5px;
                }}
                .identity-text {{
                    font-size: 11px;
                }}
                .skill-chip {{
                    padding: 4px 8px;
                    font-size: 9.5px;
                }}
            }}
        </style>
        </head>
        <body>
            <div class="author-deck">
                <div class="glow"></div>
                <div class="curtain curtain--left"></div>
                <div class="curtain curtain--right"></div>
                <div class="deck-copy">
                    <div class="deck-kicker">AUTHOR LINKS</div>
                    <div class="deck-title">作者入口</div>
                    <div class="deck-subtitle">文章、源码与镜像入口，直接点开就能看。</div>
                </div>
                <div class="hero-shell">
                    {hero_visual_html}
                    <div class="hero-ribbon">技术布道者</div>
                </div>
                <div class="identity">
                    <div class="identity-name">{self.author_info['name']}</div>
                    <div class="identity-summary">{self.author_info['description']}</div>
                    <div class="identity-role">{self.author_info['sidebar_tagline']}</div>
                    <div class="identity-text">
                        {self.author_info['sidebar_story']}
                    </div>
                    <div class="skill-row">{skill_html}</div>
                </div>
                <div class="cards">
                    {cards_html}
                </div>
            </div>
            <script>
                (function() {{
                    var scheduled = false;

                    function updateFrameHeight() {{
                        scheduled = false;
                        var bodyHeight = document.body ? document.body.scrollHeight : 0;
                        var docHeight = document.documentElement ? document.documentElement.scrollHeight : 0;
                        var nextHeight = Math.max(bodyHeight, docHeight) + 8;
                        if (!nextHeight) {{
                            return;
                        }}

                        if (window.frameElement) {{
                            window.frameElement.style.height = nextHeight + "px";
                        }}

                        try {{
                            window.parent.postMessage(
                                {{
                                    isStreamlitMessage: true,
                                    type: "streamlit:setFrameHeight",
                                    height: nextHeight,
                                }},
                                "*"
                            );
                        }} catch (error) {{
                            // Ignore parent messaging failures and keep the local iframe resize fallback.
                        }}
                    }}

                    function scheduleHeightUpdate() {{
                        if (scheduled) {{
                            return;
                        }}
                        scheduled = true;
                        window.requestAnimationFrame(updateFrameHeight);
                    }}

                    window.addEventListener("load", scheduleHeightUpdate);
                    window.addEventListener("resize", scheduleHeightUpdate);

                    if (document.fonts && document.fonts.ready) {{
                        document.fonts.ready.then(scheduleHeightUpdate).catch(function() {{}});
                    }}

                    Array.prototype.forEach.call(document.images || [], function(image) {{
                        if (!image.complete) {{
                            image.addEventListener("load", scheduleHeightUpdate);
                            image.addEventListener("error", scheduleHeightUpdate);
                        }}
                    }});

                    if (window.ResizeObserver) {{
                        var resizeObserver = new ResizeObserver(scheduleHeightUpdate);
                        resizeObserver.observe(document.documentElement);
                        if (document.body) {{
                            resizeObserver.observe(document.body);
                        }}
                    }}

                    scheduleHeightUpdate();
                    window.setTimeout(scheduleHeightUpdate, 180);
                    window.setTimeout(scheduleHeightUpdate, 640);
                }})();
            </script>
        </body>
        </html>
        """

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
            components.html(self._build_sidebar_compact_component_html(), height=760, scrolling=False)

            with st.expander("扫码名片 / 更多资源", expanded=False):
                wechat_image = self.load_image("wechat_qrcode.jpg")
                if wechat_image:
                    st.image(wechat_image, width="stretch")
                st.caption(f"公众号：{self.author_info['wechat_public']}")
                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    st.link_button("公众号合集", self.author_info["wechat_url"], use_container_width=True)
                with action_col2:
                    st.link_button("CSDN主页", self.author_info["csdn_url"], use_container_width=True)

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

from __future__ import annotations


TOOL_ICON_SVG_BODIES = {
    "数据生成工具": '<circle cx="10" cy="12" r="3"></circle><circle cx="22" cy="10" r="3"></circle><circle cx="19.5" cy="22" r="3"></circle><path d="M12.8 11.3 19 10.6"></path><path d="M11.8 14.4 17.6 19.8"></path><path d="M21.3 13 20.2 19"></path>',
    "测试用例生成器": '<rect x="9" y="8" width="14" height="18" rx="3"></rect><path d="M13 8h6a2 2 0 0 0-2-2h-2a2 2 0 0 0-2 2Z"></path><path d="m12.4 15.2 1.8 1.8 3.3-3.3"></path><path d="M16 21h4.5"></path><path d="M16 24h4.5"></path>',
    "禅道绩效统计": '<path d="M10 24v-7"></path><path d="M16 24V13"></path><path d="M22 24V9"></path><path d="m9 11 5 3 4-5 5 2"></path>',
    "日志分析工具": '<path d="M11 7h8l4 4v12a3 3 0 0 1-3 3H11a3 3 0 0 1-3-3V10a3 3 0 0 1 3-3Z"></path><path d="M19 7v4h4"></path><path d="M12 16h8"></path><path d="M12 20h8"></path><path d="M12 24h5"></path>',
    "BI数据分析工具": '<path d="M16 8a8 8 0 1 0 8 8h-8Z"></path><path d="M18 8a8 8 0 0 1 8 8h-8Z"></path>',
    "文本对比工具": '<rect x="8" y="9" width="6" height="14" rx="1.5"></rect><rect x="18" y="9" width="6" height="14" rx="1.5"></rect><path d="M15 13h2"></path><path d="m15 13-1.8 1.8"></path><path d="M17 19h2"></path><path d="m19 17 1.8 1.8"></path>',
    "字数统计工具": '<path d="M10 10h12"></path><path d="M9 16h14"></path><path d="M12 22h8"></path><path d="M14 8v16"></path><path d="M20 8v16"></path>',
    "正则测试工具": '<path d="M12 10 8 16l4 6"></path><path d="M20 10 24 16l-4 6"></path><path d="M16 12v8"></path><path d="M13.2 15.5h5.6"></path><path d="M14.2 19h3.6"></path>',
    "加密/解密工具": '<path d="M16 6 24 9v6c0 5-3.4 9.6-8 11-4.6-1.4-8-6-8-11V9l8-3Z"></path><rect x="13" y="14" width="6" height="6" rx="1.4"></rect><path d="M14.5 14v-1a1.5 1.5 0 0 1 3 0v1"></path>',
    "JSON处理工具": '<path d="M13 8c-2 0-3 1.2-3 3v2c0 1.5-.8 2.4-2.2 3 1.4.6 2.2 1.5 2.2 3v2c0 1.8 1 3 3 3"></path><path d="M19 8c2 0 3 1.2 3 3v2c0 1.5.8 2.4 2.2 3-1.4.6-2.2 1.5-2.2 3v2c0 1.8-1 3-3 3"></path><circle cx="16" cy="16" r="1.2" fill="currentColor" stroke="none"></circle>',
    "时间处理工具": '<circle cx="16" cy="16" r="9"></circle><path d="M16 11v5l3.5 2.2"></path>',
    "图片处理工具": '<rect x="8" y="8" width="16" height="16" rx="3"></rect><circle cx="13" cy="13" r="1.5"></circle><path d="m10 21 4-4 3 3 5-5 2 2"></path>',
    "IP/域名查询工具": '<circle cx="16" cy="16" r="9"></circle><path d="M7 16h18"></path><path d="M16 7c3 2.4 4.8 5.6 4.8 9S19 22.6 16 25"></path><path d="M16 7c-3 2.4-4.8 5.6-4.8 9S13 22.6 16 25"></path>',
    "接口性能测试": '<path d="M9 22a7 7 0 1 1 14 0"></path><path d="M16 16l4.5-4.5"></path><path d="M12 22h8"></path>',
    "接口安全测试": '<path d="M16 6 24 9v6c0 5-3.4 9.6-8 11-4.6-1.4-8-6-8-11V9l8-3Z"></path><path d="m12.6 16.2 2.4 2.4 4.8-4.8"></path>',
    "接口研发辅助": '<path d="M12 10 8 16l4 6"></path><path d="M20 10 24 16l-4 6"></path><path d="m18.5 9-5 14"></path>',
    "接口自动化测试": '<rect x="8" y="9" width="16" height="14" rx="3"></rect><path d="M11 13h4"></path><path d="M11 17h6"></path><path d="m18 14 4 2-4 2Z"></path>',
}


def build_tool_icon_badge(tool_name: str, accent_color: str, variant: str = "card") -> str:
    """生成统一的 SVG 工具图标徽章。"""
    svg_body = TOOL_ICON_SVG_BODIES.get(
        tool_name,
        '<rect x="9" y="9" width="14" height="14" rx="3"></rect><path d="M13 16h6"></path><path d="M16 13v6"></path>',
    )
    class_name = "tool-picker-banner-icon" if variant == "banner" else "tool-picker-icon-badge"
    icon_size = 52 if variant == "banner" else 54
    return (
        f'<span class="{class_name}" style="--tool-icon-accent: {accent_color}; --tool-icon-size: {icon_size}px;">'
        f'<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.85" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{svg_body}</svg>'
        f"</span>"
    )

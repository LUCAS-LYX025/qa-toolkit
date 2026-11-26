"""按国家/地区推断界面语言，并提供浏览器侧的自动定位脚本。

服务端只保留纯函数，方便测试；浏览器侧通过轻量组件读取本机 IP 归属国家
（只取国家码，不读取或保存 IP），优先级低于用户手动选择的 ``lang`` 参数。
"""

from __future__ import annotations

import json
import threading
from typing import Callable, Dict, Optional

from qa_toolkit.core.i18n import DEFAULT_LOCALE, normalize_locale

_COUNTRY_LOCALES: Dict[str, str] = {
    # 中文
    "CN": DEFAULT_LOCALE,
    "SG": DEFAULT_LOCALE,
    "TW": "zh-TW",
    "HK": "zh-TW",
    "MO": "zh-TW",
    # 韩语
    "KR": "ko-KR",
    # 英语
    "US": "en-US",
    "CA": "en-US",
    "GB": "en-US",
    "IE": "en-US",
    "AU": "en-US",
    "NZ": "en-US",
    "IN": "en-US",
    "PH": "en-US",
    "SG": DEFAULT_LOCALE,
    "ZA": "en-US",
    "NG": "en-US",
    "KE": "en-US",
    "DE": "en-US",
    "FR": "en-US",
    "ES": "en-US",
    "IT": "en-US",
    "NL": "en-US",
    "SE": "en-US",
    "NO": "en-US",
    "DK": "en-US",
    "FI": "en-US",
    "PL": "en-US",
    "BR": "en-US",
    "MX": "en-US",
    "AR": "en-US",
    "CL": "en-US",
    "CO": "en-US",
    "JP": "en-US",
    "RU": "en-US",
    "TR": "en-US",
    "AE": "en-US",
    "SA": "en-US",
    "IL": "en-US",
}
_LOCK = threading.RLock()
IP_SERVICE_URL = "https://ipapi.co/json/"


def register_country_locale(country_code: str, locale: str, replace: bool = False) -> None:
    """扩展国家到语言的映射；默认拒绝覆盖已有映射。"""
    code = normalize_locale(locale)
    if code is None:
        raise ValueError(f"unsupported locale: {locale}")
    country = str(country_code).strip().upper()
    with _LOCK:
        if country in _COUNTRY_LOCALES and not replace:
            raise ValueError(f"country mapping already registered: {country}")
        _COUNTRY_LOCALES[country] = code


def get_country_locale_map() -> Dict[str, str]:
    with _LOCK:
        return dict(_COUNTRY_LOCALES)


def locale_from_country(country_code: object) -> Optional[str]:
    """国家码（ISO 3166-1 alpha-2）→ 已注册语言，未知返回 None。"""
    if not country_code:
        return None
    country = str(country_code).strip().upper()
    with _LOCK:
        locale = _COUNTRY_LOCALES.get(country)
    return normalize_locale(locale)


def detect_locale_from_ip(
    ip_address: str,
    *,
    http_get: Optional[Callable[[str, int], str]] = None,
    timeout: int = 2,
) -> Optional[str]:
    """服务端按 IP 查询国家码（可注入 http_get 用于单测）。

    默认不直接发起外部请求：Streamlit 服务端通常只能看到代理 IP，
    实际用户侧的自动定位由 :func:`build_browser_locale_bootstrap` 完成。
    """
    if not ip_address:
        return None
    if http_get is None:
        return None
    import urllib.request

    url = f"https://ipapi.co/{ip_address}/json/"
    try:
        if http_get is urllib.request.urlopen:
            with http_get(url, timeout=timeout) as response:  # type: ignore[attr-defined]
                payload = json.loads(response.read().decode("utf-8"))
        else:
            payload = json.loads(http_get(url, timeout))
    except Exception:
        return None
    return locale_from_country(payload.get("country_code") or payload.get("country"))


def _json_for_js(value: object) -> str:
    """避免 JSON 中出现可闭合 script 标签的字符。"""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def build_browser_locale_bootstrap(locale: str, *, query_key: str = "lang") -> str:
    """生成首访自动定位脚本：本地偏好 > 浏览器语言 > IP 国家码。

    只在 URL 没有显式 ``lang`` 参数时由主入口渲染；探测尝试在
    sessionStorage 中去重，失败不会造成无限刷新。
    """
    country_map = _json_for_js(get_country_locale_map())
    fallback_locale = _json_for_js(locale)
    query_key_js = _json_for_js(query_key)
    return f"""
<script>
(function() {{
    try {{
        const key = {query_key_js};
        const probeKey = 'qa_toolkit_locale_probe';
        const preferenceKey = 'qa_toolkit_locale';
        const countryMap = {country_map};
        const fallback = {fallback_locale};
        const host = window.parent || window;
        const current = new URL(host.location.href);
        if (current.searchParams.get(key)) {{
            return;
        }}
        const saved = host.localStorage.getItem(preferenceKey);
        if (saved && countryMap && Object.values(countryMap).includes(saved)) {{
            current.searchParams.set(key, saved);
            host.location.assign(current.toString());
            return;
        }}
        if (host.sessionStorage.getItem(probeKey)) {{
            return;
        }}
        host.sessionStorage.setItem(probeKey, '1');

        const apply = (next) => {{
            if (!next || next === fallback) {{
                return;
            }}
            host.localStorage.setItem(preferenceKey, next);
            const target = new URL(host.location.href);
            target.searchParams.set(key, next);
            host.location.assign(target.toString());
        }};

        const fromNavigator = () => {{
            const value = (host.navigator.language || '').toLowerCase();
            if (value.startsWith('ko')) {{
                return 'ko-KR';
            }}
            if (value.startsWith('zh')) {{
                return value.includes('-hant') || value.includes('hk') || value.includes('tw') || value.includes('mo')
                    ? 'zh-TW' : 'zh-CN';
            }}
            if (value.startsWith('en')) {{
                return 'en-US';
            }}
            return null;
        }};

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 2600);
        fetch({_json_for_js(IP_SERVICE_URL)}, {{ signal: controller.signal, credentials: 'omit' }})
            .then((response) => response.ok ? response.json() : null)
            .then((data) => {{
                clearTimeout(timer);
                const country = data && (data.country_code || data.country);
                apply((country && countryMap[String(country).toUpperCase()]) || fromNavigator());
            }})
            .catch(() => {{
                clearTimeout(timer);
                apply(fromNavigator());
            }});
    }} catch (error) {{
        // 自动定位失败时保留默认语言，不阻断页面渲染。
    }}
}})();
</script>
"""


def build_locale_persistence_script(locale: str) -> str:
    """用户手动切换语言后写入本地偏好，下次访问可直接恢复。"""
    value = _json_for_js(locale)
    return f"""
<script>
(function() {{
    try {{
        const host = window.parent || window;
        host.localStorage.setItem('qa_toolkit_locale', {value});
        host.sessionStorage.setItem('qa_toolkit_locale_probe', '1');
    }} catch (error) {{}}
}})();
</script>
"""

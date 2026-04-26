import base64
import io
import plistlib
import threading
import warnings
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL*")

try:
    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.application_security_tool import ApplicationSecurityTool


APK_MANIFEST_B64 = (
    "AwAIAJAGAAABABwAhAMAABsAAAAAAAAAAAAAAIgAAAAAAAAAAAAAABoAAAA0AAAAUgAAAHYAAACQAAAAngAAAKwAAAC4AAAAxgAAANgAAAAwAQAANAEAAEYBAAB6AQAArgEAAMIBAADgAQAA6AEAAPABAAAOAgAAIgIAADwCAABSAgAAbgIAAJICAAC4AgAACwB2AGUAcgBzAGkAbwBuAEMAbwBkAGUAAAALAHYAZQByAHMAaQBvAG4ATgBhAG0AZQAAAA0AbQBpAG4AUwBkAGsAVgBlAHIAcwBpAG8AbgAAABAAdABhAHIAZwBlAHQAUwBkAGsAVgBlAHIAcwBpAG8AbgAAAAsAYQBsAGwAbwB3AEIAYQBjAGsAdQBwAAAABQBsAGEAYgBlAGwAAAAFAHQAaABlAG0AZQAAAAQAbgBhAG0AZQAAAAUAdgBhAGwAdQBlAAAABwBhAG4AZAByAG8AaQBkAAAAKgBoAHQAdABwADoALwAvAHMAYwBoAGUAbQBhAHMALgBhAG4AZAByAG8AaQBkAC4AYwBvAG0ALwBhAHAAawAvAHIAZQBzAC8AYQBuAGQAcgBvAGkAZAAAAAAAAAAHAHAAYQBjAGsAYQBnAGUAAAAYAHAAbABhAHQAZgBvAHIAbQBCAHUAaQBsAGQAVgBlAHIAcwBpAG8AbgBDAG8AZABlAAAAGABwAGwAYQB0AGYAbwByAG0AQgB1AGkAbABkAFYAZQByAHMAaQBvAG4ATgBhAG0AZQAAAAgAbQBhAG4AaQBmAGUAcwB0AAAADQBqAHUAcwB0AC4AdAByAHUAcwB0AC4AbQBlAAAAAgAuADIAAAACADIAMgAAAA0ANQAuADEALgAxAC0AMQA4ADEAOQA3ADIANwAAAAgAdQBzAGUAcwAtAHMAZABrAAAACwBhAHAAcABsAGkAYwBhAHQAaQBvAG4AAAAJAG0AZQB0AGEALQBkAGEAdABhAAAADAB4AHAAbwBzAGUAZABtAG8AZAB1AGwAZQAAABAAeABwAG8AcwBlAGQAbQBpAG4AdgBlAHIAcwBpAG8AbgAAABEAeABwAG8AcwBlAGQAZABlAHMAYwByAGkAcAB0AGkAbwBuAAAAIABLAGkAbABsAHMAIABTAFMATAAgAGMAZQByAHQAaQBmAGkAYwBhAHQAZQAgAHYAYQBsAGkAZABhAHQAaQBvAG4AAACAAQgALAAAABsCAQEcAgEBDAIBAXACAQGAAgEBAQABAQAAAQEDAAEBJAABAQABEAAYAAAAAgAAAP////8JAAAACgAAAAIBEACIAAAAAgAAAP//////////DwAAABQAFAAFAAAAAAAAAAoAAAAAAAAA/////wgAABACAAAACgAAAAEAAAARAAAACAAAAxEAAAD/////DAAAABAAAAAIAAADEAAAAP////8NAAAAEgAAAAgAABAWAAAA/////w4AAAATAAAACAAAAxMAAAACARAATAAAAAcAAAD//////////xQAAAAUABQAAgAAAAAAAAAKAAAAAgAAAP////8IAAAQEAAAAAoAAAADAAAA/////wgAABAWAAAAAwEQABgAAAAJAAAA//////////8UAAAAAgEQAGAAAAALAAAA//////////8VAAAAFAAUAAMAAAAAAAAACgAAAAYAAAD/////CAAAAQAABH8KAAAABQAAAP////8IAAABAQADfwoAAAAEAAAA/////wgAABL/////AgEQAEwAAAAPAAAA//////////8WAAAAFAAUAAIAAAAAAAAACgAAAAcAAAAXAAAACAAAAxcAAAAKAAAACAAAAP////8IAAAS/////wMBEAAYAAAAEQAAAP//////////FgAAAAIBEABMAAAAEgAAAP//////////FgAAABQAFAACAAAAAAAAAAoAAAAHAAAAGAAAAAgAAAMYAAAACgAAAAgAAAD/////CAAAEB4AAAADARAAGAAAABQAAAD//////////xYAAAACARAATAAAABUAAAD//////////xYAAAAUABQAAgAAAAAAAAAKAAAABwAAABkAAAAIAAADGQAAAAoAAAAIAAAAGgAAAAgAAAMaAAAAAwEQABgAAAAXAAAA//////////8WAAAAAwEQABgAAAAYAAAA//////////8VAAAAAwEQABgAAAAaAAAA//////////8PAAAAAQEQABgAAAAaAAAA/////wkAAAAKAAAA"
)


def _build_apk_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("AndroidManifest.xml", base64.b64decode(APK_MANIFEST_B64))
        archive.writestr(
            "classes.dex",
            b"http://test.internal api_key=abcd1234567890 xposed Hooking SSL certificate validation 10.2.3.4",
        )
    return buffer.getvalue()


def _build_ipa_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        plist = {
            "CFBundleDisplayName": "Demo",
            "CFBundleIdentifier": "com.demo.app",
            "CFBundleShortVersionString": "1.2.3",
            "CFBundleVersion": "12",
            "MinimumOSVersion": "14.0",
            "CFBundleExecutable": "Demo",
            "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
            "NSCameraUsageDescription": "need camera",
            "UIFileSharingEnabled": True,
            "CFBundleURLTypes": [{"CFBundleURLSchemes": ["demoapp"]}],
        }
        archive.writestr("Payload/Demo.app/Info.plist", plistlib.dumps(plist))
        archive.writestr(
            "Payload/Demo.app/Demo",
            b"https://api.example.com http://test.internal demoapp://open api_key=abcd1234567890 10.2.3.4",
        )
    return buffer.getvalue()


def _build_appx_bytes() -> bytes:
    manifest = """<?xml version="1.0" encoding="utf-8"?>
    <Package
        xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
        xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
        xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities">
      <Identity Name="Demo.WinApp" Publisher="CN=Demo" Version="1.0.0.0" ProcessorArchitecture="x64" />
      <Properties>
        <DisplayName>Demo Win</DisplayName>
        <PublisherDisplayName>Demo Corp</PublisherDisplayName>
      </Properties>
      <Applications>
        <Application Id="App" Executable="Demo.exe" EntryPoint="Demo.App">
          <uap:VisualElements DisplayName="Demo Win" />
          <Extensions>
            <uap:Extension Category="windows.protocol">
              <uap:Protocol Name="demoapp" />
            </uap:Extension>
            <uap:Extension Category="windows.appService">
              <uap:AppService Name="demo.service" />
            </uap:Extension>
          </Extensions>
        </Application>
      </Applications>
      <Capabilities>
        <Capability Name="internetClientServer" />
        <rescap:Capability Name="runFullTrust" />
      </Capabilities>
    </Package>
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("AppxManifest.xml", manifest)
        archive.writestr(
            "Demo.exe",
            b"http://demo.internal api_key=abcd1234567890 10.2.3.4 ssl bypass",
        )
    return buffer.getvalue()


class _TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Set-Cookie", "sessionid=abc123; Path=/")
            self.end_headers()
            self.wfile.write(
                b"""
                <html>
                  <head><title>Demo Home</title></head>
                  <body>
                    <a href="/login">Login</a>
                    <a href="/upload">Upload</a>
                  </body>
                </html>
                """
            )
            return
        if self.path == "/login":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"""
                <html>
                  <head><title>Login</title></head>
                  <body>
                    <form method="post" action="/auth">
                      <input name="username" />
                      <input name="password" type="password" />
                    </form>
                  </body>
                </html>
                """
            )
            return
        if self.path == "/upload":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"""
                <html>
                  <body>
                    <form method="post" action="/files">
                      <input name="file" type="file" />
                    </form>
                  </body>
                </html>
                """
            )
            return
        if self.path == "/robots.txt":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"User-agent: *\nDisallow: /admin\n")
            return
        if self.path == "/.git/HEAD":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ref: refs/heads/main\n")
            return
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"not found")

    def log_message(self, format, *args):  # noqa: A003
        return


def _start_server():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
    except PermissionError as exc:
        pytest.skip(f"当前执行环境不允许绑定本地端口: {exc}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class _MockResponse:
    def __init__(self, json_data=None, content=b"", status_code=200, text=""):
        self._json_data = json_data
        self.content = content
        self.status_code = status_code
        self.text = text or (json_data if isinstance(json_data, str) else "")

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.text or f"HTTP {self.status_code}", response=self)


def test_scan_apk_manifest_parses_binary_manifest():
    report = ApplicationSecurityTool().scan_mobile_package("sample.apk", _build_apk_bytes(), custom_keywords=["xposed"])

    assert report["overview"]["identifier"] == "just.trust.me"
    assert report["overview"]["min_sdk"] == "16"
    assert any(item["Title"] == "Manifest 启用了 allowBackup" for item in report["findings"])
    assert any(item["Value"] == "http://test.internal" for item in report["external_urls"])
    assert any(item["Keyword"] == "xposed" for item in report["keyword_hits"])
    assert any(item["Value"] == "10.2.3.4" for item in report["ip_hits"])


def test_scan_ipa_detects_ats_http_and_secret():
    report = ApplicationSecurityTool().scan_mobile_package("sample.ipa", _build_ipa_bytes(), custom_keywords=["api_key"])

    assert report["overview"]["identifier"] == "com.demo.app"
    assert any(item["Title"] == "ATS 允许任意明文或弱校验流量" for item in report["findings"])
    assert any(item["Value"] == "http://test.internal" for item in report["external_urls"])
    assert any(item["Type"] == "Credential Assignment" for item in report["secret_hits"])
    assert any(item["Keyword"] == "api_key" for item in report["keyword_hits"])


def test_scan_appx_detects_capabilities_protocol_and_http():
    report = ApplicationSecurityTool().scan_mobile_package("sample.appx", _build_appx_bytes(), custom_keywords=["ssl"])

    titles = {item["Title"] for item in report["findings"]}
    assert report["platform"] == "windows"
    assert report["overview"]["identifier"] == "Demo.WinApp"
    assert "APPX 声明高风险能力" in titles
    assert "APPX 声明自定义协议" in titles
    assert any(item["Value"] == "http://demo.internal" for item in report["external_urls"])
    assert any(item["Keyword"] == "ssl" for item in report["keyword_hits"])


def test_scan_web_target_detects_http_form_and_git_exposure():
    server = _start_server()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        report = ApplicationSecurityTool().scan_web_target(
            base_url,
            timeout_seconds=3,
            verify_ssl=False,
            max_pages=4,
            include_common_paths=True,
        )
    finally:
        server.shutdown()
        server.server_close()

    titles = {item["Title"] for item in report["findings"]}
    assert "站点使用明文 HTTP" in titles
    assert ".git 目录暴露" in titles
    assert any(item["Title"] == "POST 表单未发现显式 CSRF 令牌线索" for item in report["findings"])
    assert report["crawl"]["forms_found"] >= 1
    assert "/admin" in report["robots_paths"]


def test_run_mobsf_static_analysis_uses_official_endpoints():
    tool = ApplicationSecurityTool()
    called_urls = []

    def fake_request(method, url, headers=None, data=None, files=None, timeout=None, verify=None):
        called_urls.append((method, url, data))
        assert headers["X-Mobsf-Api-Key"] == "secret-key"
        if url.endswith("/api/v1/upload"):
            assert "file" in files
            assert files["file"] == ("sample.apk", b"binary", "application/vnd.android.package-archive")
            return _MockResponse(json_data={"hash": "abcd1234", "file_name": "sample.apk", "scan_type": "apk"})
        if url.endswith("/api/v1/scan"):
            assert data == {"hash": "abcd1234"}
            return _MockResponse(json_data={"hash": "abcd1234", "scan_type": "apk", "status": "ok"})
        if url.endswith("/api/v1/report_json"):
            return _MockResponse(json_data={
                "app_name": "Sample App",
                "package_name": "demo.app",
                "scan_type": "apk",
                "permissions": {"camera": "dangerous"},
                "urls": ["http://demo.internal"],
                "manifest_analysis": [{"rule": "allowBackup", "severity": "warning"}],
            })
        if url.endswith("/api/v1/scorecard"):
            return _MockResponse(json_data={"security_score": 88, "high": 0, "medium": 1})
        if url.endswith("/api/v1/download_pdf"):
            return _MockResponse(content=b"%PDF-1.4")
        raise AssertionError(f"unexpected url: {url}")

    with patch("qa_toolkit.core.application_security_tool.requests.request", side_effect=fake_request):
        bundle = tool.run_mobsf_static_analysis(
            base_url="127.0.0.1:8000",
            api_key="secret-key",
            file_name="sample.apk",
            file_bytes=b"binary",
            timeout_seconds=30,
            verify_ssl=False,
            include_pdf=True,
        )

    assert bundle["hash"] == "abcd1234"
    assert bundle["summary"]["scan_type"] == "apk"
    assert bundle["summary"]["has_pdf"] is True
    assert bundle["json_report"]["app_name"] == "Sample App"
    assert bundle["review_bundle"]["summary"]["issue_count"] >= 2
    assert bundle["review_bundle"]["summary"]["regression_case_count"] >= 1
    assert len(called_urls) == 5


def test_mobsf_upload_file_rejects_unsupported_extension_early():
    tool = ApplicationSecurityTool()

    try:
        tool.mobsf_upload_file(
            base_url="127.0.0.1:8000",
            api_key="secret-key",
            file_name="sample.exe",
            file_bytes=b"binary",
            verify_ssl=False,
        )
    except ValueError as exc:
        assert "暂不支持当前文件类型" in str(exc)
    else:
        raise AssertionError("expected ValueError for unsupported extension")


def test_build_mobsf_review_bundle_generates_issue_register_and_regression_suite():
    tool = ApplicationSecurityTool()
    report_json = {
        "app_name": "Demo App",
        "scan_type": "apk",
        "permissions": {"camera": "dangerous", "location": "dangerous"},
        "urls": ["http://demo.internal", "https://api.example.com"],
        "certificate_analysis": {"issues": ["pinning missing"]},
        "manifest_analysis": {"android:allowBackup": True, "exported_activity": "true"},
        "code_analysis": {"hardcoded": ["api_key=abcd123456"]},
    }
    scorecard = {"security_score": 62}

    review = tool.build_mobsf_review_bundle(
        report_json=report_json,
        scorecard=scorecard,
        file_hash="hash-demo",
        scan_type="apk",
        app_name="Demo App",
    )

    titles = {item["Title"] for item in review["issue_register"]}
    scenarios = {item["Scenario"] for item in review["regression_suite"]}

    assert review["summary"]["issue_count"] >= 4
    assert review["summary"]["security_score"] == 62
    assert "权限 / Capability 复核" in titles
    assert "发现明文传输或网络配置风险线索" in titles
    assert "Scorecard 分数回归" in scenarios
    assert "MobSF 结果二次整理" in review["markdown"]


def test_mobsf_dynamic_report_helpers_use_official_parameters():
    tool = ApplicationSecurityTool()
    called_urls = []

    def fake_request(method, url, headers=None, data=None, files=None, timeout=None, verify=None):
        called_urls.append((method, url, data))
        assert headers["X-Mobsf-Api-Key"] == "secret-key"
        if url.endswith("/api/v1/dynamic/get_apps"):
            return _MockResponse(json_data={"apps": [{"hash": "android-hash", "package": "demo.app"}]})
        if url.endswith("/api/v1/dynamic/start_analysis"):
            assert data == {"hash": "android-hash"}
            return _MockResponse(json_data={"status": "ok", "hash": "android-hash"})
        if url.endswith("/api/v1/dynamic/stop_analysis"):
            assert data == {"hash": "android-hash"}
            return _MockResponse(json_data={"status": "ok", "hash": "android-hash", "report": "collecting"})
        if url.endswith("/api/v1/dynamic/report_json"):
            assert data == {"hash": "android-hash"}
            return _MockResponse(json_data={"package_name": "demo.app", "api_monitor": ["token"], "tls_tests": ["http://demo.internal"]})
        if url.endswith("/api/v1/dynamic/ios_report_json"):
            assert data == {"instance_id": "instance-1", "bundle_id": "com.demo.ios"}
            return _MockResponse(json_data={"bundle_id": "com.demo.ios", "network_capture": ["http://ios.internal"]})
        if url.endswith("/api/v1/ios/device_report_json"):
            assert data == {"device_id": "device-1", "bundle_id": "com.demo.ios"}
            return _MockResponse(json_data={"bundle_id": "com.demo.ios", "frida_logs": ["api_key=abcd123456"]})
        raise AssertionError(f"unexpected url: {url}")

    with patch("qa_toolkit.core.application_security_tool.requests.request", side_effect=fake_request):
        android_apps = tool.mobsf_get_android_dynamic_apps("127.0.0.1:8000", "secret-key", verify_ssl=False)
        android_start = tool.mobsf_start_android_dynamic_analysis("127.0.0.1:8000", "secret-key", "android-hash", verify_ssl=False)
        android_stop = tool.mobsf_stop_android_dynamic_analysis("127.0.0.1:8000", "secret-key", "android-hash", verify_ssl=False)
        android_report = tool.mobsf_get_android_dynamic_report("127.0.0.1:8000", "secret-key", "android-hash", verify_ssl=False)
        ios_report = tool.mobsf_get_ios_dynamic_report("127.0.0.1:8000", "secret-key", "instance-1", "com.demo.ios", verify_ssl=False)
        ios_device_report = tool.mobsf_get_ios_device_dynamic_report("127.0.0.1:8000", "secret-key", "device-1", "com.demo.ios", verify_ssl=False)

    assert android_apps["apps"][0]["hash"] == "android-hash"
    assert android_start["status"] == "ok"
    assert android_stop["status"] == "ok"
    assert android_report["package_name"] == "demo.app"
    assert ios_report["bundle_id"] == "com.demo.ios"
    assert ios_device_report["bundle_id"] == "com.demo.ios"
    assert len(called_urls) == 6


def test_is_mobsf_dynamic_report_unavailable_error_matches_official_message():
    tool = ApplicationSecurityTool()

    assert tool.is_mobsf_dynamic_report_unavailable_error(
        "MobSF 请求失败: POST /api/v1/dynamic/report_json Dynamic Analysis report is not available for this app. Perform Dynamic Analysis and generate the report."
    )
    assert tool.is_mobsf_dynamic_report_unavailable_error("dynamic report is not available")
    assert tool.is_mobsf_dynamic_report_unavailable_error("other error") is False


def test_is_mobsf_android_dynamic_analysis_failed_error_matches_common_message():
    tool = ApplicationSecurityTool()

    assert tool.is_mobsf_android_dynamic_analysis_failed_error(
        "MobSF 请求失败: POST /api/v1/dynamic/start_analysis Dynamic Analysis Failed."
    )
    assert tool.is_mobsf_android_dynamic_analysis_failed_error("failed to start dynamic analysis")
    assert tool.is_mobsf_android_dynamic_analysis_failed_error("other error") is False


def test_build_mobsf_dynamic_bundle_adds_runtime_metadata():
    tool = ApplicationSecurityTool()
    report_json = {
        "package_name": "demo.app",
        "api_monitor": {"calls": ["Authorization: Bearer demo-token"]},
        "tls_tests": ["http://demo.internal"],
        "frida_logs": ["ssl pinning bypass"],
    }

    bundle = tool.build_mobsf_dynamic_bundle(
        report_json=report_json,
        platform="android",
        analysis_mode="android_dynamic",
        identifier="android-hash",
        runtime_target="android-hash",
        app_name="Demo App",
    )

    assert bundle["summary"]["platform"] == "android"
    assert bundle["summary"]["analysis_mode"] == "android_dynamic"
    assert bundle["summary"]["identifier"] == "android-hash"
    assert bundle["review_bundle"]["summary"]["runtime_target"] == "android-hash"
    assert bundle["review_bundle"]["summary"]["issue_count"] >= 2
    assert "分析模式: android_dynamic" in bundle["review_bundle"]["markdown"]


def test_build_mobsf_static_bundle_from_hash_collects_report_scorecard_and_pdf():
    tool = ApplicationSecurityTool()
    called_urls = []

    def fake_request(method, url, headers=None, data=None, files=None, timeout=None, verify=None):
        called_urls.append((method, url, data))
        if url.endswith("/api/v1/report_json"):
            assert data == {"hash": "abcd1234"}
            return _MockResponse(json_data={"app_name": "Demo App", "scan_type": "apk", "permissions": {"camera": "dangerous"}})
        if url.endswith("/api/v1/scorecard"):
            assert data == {"hash": "abcd1234"}
            return _MockResponse(json_data={"security_score": 78})
        if url.endswith("/api/v1/download_pdf"):
            assert data == {"hash": "abcd1234"}
            return _MockResponse(content=b"%PDF-1.4")
        raise AssertionError(f"unexpected url: {url}")

    with patch("qa_toolkit.core.application_security_tool.requests.request", side_effect=fake_request):
        bundle = tool.build_mobsf_static_bundle_from_hash(
            base_url="127.0.0.1:8000",
            api_key="secret-key",
            file_hash="abcd1234",
            verify_ssl=False,
            include_pdf=True,
        )

    assert bundle["hash"] == "abcd1234"
    assert bundle["summary"]["scan_type"] == "apk"
    assert bundle["summary"]["has_pdf"] is True
    assert bundle["review_bundle"]["summary"]["analysis_mode"] == "static"
    assert len(called_urls) == 3


def test_resolve_mobsf_profile_prefers_env_then_local_then_defaults():
    tool = ApplicationSecurityTool()
    profile = tool.resolve_mobsf_profile(
        env={
            "MOBSF_BASE_URL": "http://env-mobsf:8000",
            "MOBSF_API_KEY": "env-key",
            "MOBSF_TIMEOUT": "45",
            "MOBSF_VERIFY_SSL": "false",
            "MOBSF_INCLUDE_PDF": "true",
        },
        secrets={
            "base_url": "https://secrets-mobsf.example.com",
            "api_key": "secrets-key",
            "timeout_seconds": 90,
            "verify_ssl": True,
            "include_pdf": False,
        },
        local_profile={
            "base_url": "http://local-mobsf:8000",
            "api_key": "local-key",
            "timeout_seconds": 30,
            "verify_ssl": True,
            "include_pdf": False,
        },
    )

    assert profile["base_url"] == "http://env-mobsf:8000"
    assert profile["api_key"] == "env-key"
    assert profile["timeout_seconds"] == 45.0
    assert profile["verify_ssl"] is False
    assert profile["include_pdf"] is True
    assert profile["ready"] is True
    assert "环境变量" in profile["source"]

    secrets_only = tool.resolve_mobsf_profile(
        env={},
        secrets={
            "base_url": "https://secrets-mobsf.example.com",
            "api_key": "secrets-key",
            "timeout_seconds": 90,
            "verify_ssl": True,
            "include_pdf": True,
        },
        local_profile={
            "base_url": "http://local-mobsf:8000",
            "api_key": "local-key",
            "timeout_seconds": 30,
            "verify_ssl": False,
            "include_pdf": False,
        },
    )
    assert secrets_only["base_url"] == "https://secrets-mobsf.example.com"
    assert secrets_only["api_key"] == "secrets-key"
    assert secrets_only["timeout_seconds"] == 90.0
    assert secrets_only["verify_ssl"] is True
    assert secrets_only["include_pdf"] is True
    assert secrets_only["source"] == "Streamlit Secrets"

    local_only = tool.resolve_mobsf_profile(
        env={},
        local_profile={
            "base_url": "http://local-mobsf:8000",
            "api_key": "local-key",
            "timeout_seconds": 30,
            "verify_ssl": False,
        },
    )
    assert local_only["base_url"] == "http://local-mobsf:8000"
    assert local_only["api_key"] == "local-key"
    assert local_only["timeout_seconds"] == 30.0
    assert local_only["verify_ssl"] is False
    assert local_only["source"] == "本地配置"


def test_normalize_mobsf_base_url_keeps_proxy_prefix_and_strips_api_suffix():
    tool = ApplicationSecurityTool()

    assert tool._normalize_mobsf_base_url("https://demo.local/mobsf") == "https://demo.local/mobsf"
    assert tool._normalize_mobsf_base_url("https://demo.local/mobsf/api/v1") == "https://demo.local/mobsf"
    assert tool._normalize_mobsf_base_url("demo.local/mobsf/api/v1/scans") == "http://demo.local/mobsf"


def test_mobsf_check_connection_reports_success_and_scan_count():
    tool = ApplicationSecurityTool()

    def fake_request(method, url, headers=None, data=None, files=None, timeout=None, verify=None):
        assert method == "GET"
        assert url.endswith("/api/v1/scans")
        assert headers["X-Mobsf-Api-Key"] == "secret-key"
        return _MockResponse(json_data=[
            {"MD5": "abcd1234", "FILE_NAME": "demo.apk", "SCAN_TYPE": "apk"},
            {"bundle_id": "com.demo.ios", "instance_id": "instance-1"},
        ])

    with patch("qa_toolkit.core.application_security_tool.requests.request", side_effect=fake_request):
        result = tool.mobsf_check_connection("127.0.0.1:8000", "secret-key", verify_ssl=False)

    assert result["success"] is True
    assert result["authenticated"] is True
    assert result["status_code"] == 200
    assert result["recent_scan_count"] >= 2


def test_mobsf_check_connection_reports_auth_failure():
    tool = ApplicationSecurityTool()

    def fake_request(method, url, headers=None, data=None, files=None, timeout=None, verify=None):
        return _MockResponse(json_data={"error": "Forbidden"}, status_code=403, text="Forbidden")

    with patch("qa_toolkit.core.application_security_tool.requests.request", side_effect=fake_request):
        result = tool.mobsf_check_connection("127.0.0.1:8000", "bad-key", verify_ssl=False)

    assert result["success"] is False
    assert result["reachable"] is True
    assert result["authenticated"] is False
    assert result["status_code"] == 403
    assert "API Key" in result["message"]


def test_mobsf_extract_reference_candidates_supports_nested_recent_and_search_payloads():
    tool = ApplicationSecurityTool()
    payload = {
        "items": [
            {"MD5": "abcd1234", "FILE_NAME": "demo.apk", "SCAN_TYPE": "apk", "package_name": "demo.app"},
            {"report": {"bundle_id": "com.demo.ios", "instance_id": "instance-1", "device_id": "device-1"}},
        ]
    }

    candidates = tool.mobsf_extract_reference_candidates(payload, source_name="搜索结果")

    assert any(item["Hash"] == "abcd1234" for item in candidates)
    assert any(item["Bundle ID"] == "com.demo.ios" for item in candidates)
    assert any(item["Instance ID"] == "instance-1" for item in candidates)
    assert any(item["Device ID"] == "device-1" for item in candidates)

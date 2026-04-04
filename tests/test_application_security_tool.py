import base64
import io
import plistlib
import threading
import warnings
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL*")

try:
    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

import sys

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
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


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

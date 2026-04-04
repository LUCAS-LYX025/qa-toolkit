from typing import Any, Dict, List

from qa_toolkit.core.api_test_core import InterfaceAutoTestCore


class EnhancedTestRunner:
    """增强测试执行器"""

    def __init__(self):
        self.core = InterfaceAutoTestCore()

    def run_tests_with_details(self, framework: str, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行测试并返回真实结果"""
        results = self.core.run_tests(framework)

        if results.get("test_details"):
            return results

        if interfaces:
            fallback_details = self._build_fallback_details(interfaces, results)
            results["test_details"] = fallback_details
            results["total"] = len(fallback_details)
            results["passed"] = sum(1 for item in fallback_details if item.get("status") == "passed")
            results["failed"] = sum(1 for item in fallback_details if item.get("status") == "failed")
            results["errors"] = sum(1 for item in fallback_details if item.get("status") == "error")
            results["success"] = results["failed"] == 0 and results["errors"] == 0

        return results

    def _build_fallback_details(
        self,
        interfaces: List[Dict[str, Any]],
        results: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """当结构化日志缺失时构建兜底详情"""
        error_message = results.get("error_message") or results.get("output") or "未获取到测试详情"
        details = []
        for interface in interfaces:
            details.append(
                {
                    "name": interface.get("name", "未命名接口"),
                    "method": interface.get("method", "GET"),
                    "path": interface.get("path", ""),
                    "status": "error",
                    "status_code": 0,
                    "response_time": 0.0,
                    "headers": interface.get("headers", {}),
                    "parameters": interface.get("parameters"),
                    "response_body": "",
                    "error": error_message,
                    "assertions": [],
                }
            )
        return details

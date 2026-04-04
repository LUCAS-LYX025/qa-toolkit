import json
import re
import time
import requests
from typing import List, Dict


class TestCaseGenerator:
    """
    测试用例生成器 - 统一封装多个AI平台的测试用例生成API
    """

    def __init__(self):
        self.supported_platforms = {
            "ali": "阿里通义千问",
            "openai": "OpenAI GPT",
            "baidu": "百度文心一言",
            "spark": "讯飞星火",
            "glm": "智谱ChatGLM"
        }

        self.case_styles = {
            "标准格式": "使用标准测试用例格式，包含清晰的步骤和预期结果",
            "详细步骤": "提供非常详细的测试步骤，每个步骤都要具体明确",
            "简洁格式": "使用简洁的格式，重点描述关键测试点",
            "BDD格式(Given-When-Then)": "使用Given-When-Then格式编写测试场景"
        }

        self.languages = ["中文", "英文", "中英混合"]

    def generate_testcases(self,
                           requirement: str,
                           platform: str,
                           api_config: Dict,
                           id_prefix: str = "TC",
                           case_style: str = "标准格式",
                           language: str = "中文") -> List[Dict]:
        """
        生成测试用例的主方法

        Args:
            requirement: 需求描述
            platform: AI平台，支持 ali/openai/baidu/spark/glm
            api_config: API配置参数
            id_prefix: 用例ID前缀
            case_style: 用例风格
            language: 输出语言

        Returns:
            List[Dict]: 测试用例列表
        """
        if platform not in self.supported_platforms:
            raise ValueError(f"不支持的平台: {platform}，支持的平台: {list(self.supported_platforms.keys())}")

        if case_style not in self.case_styles:
            raise ValueError(f"不支持的用例风格: {case_style}，支持的风格: {list(self.case_styles.keys())}")

        if language not in self.languages:
            raise ValueError(f"不支持的语言: {language}，支持的语言: {self.languages}")

        platform_methods = {
            "ali": self._call_ali_api,
            "openai": self._call_openai_api,
            "baidu": self._call_baidu_api,
            "spark": self._call_spark_api,
            "glm": self._call_glm_api
        }

        return platform_methods[platform](requirement, api_config, id_prefix, case_style, language)

    def _call_ali_api(self, requirement: str, api_config: Dict, id_prefix: str,
                      case_style: str, language: str) -> List[Dict]:
        """调用阿里通义千问API"""
        headers = {
            "Authorization": f"Bearer {api_config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = self._build_prompt(requirement, id_prefix, case_style, language)

        payload = {
            "model": "qwen-turbo",
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"result_format": "text"}
        }

        try:
            response = requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            if "output" in response_data and "text" in response_data["output"]:
                result_text = response_data["output"]["text"]
                return self._parse_testcases(result_text, id_prefix, language)
            else:
                raise Exception("API响应格式错误")

        except Exception as e:
            raise Exception(f"阿里通义千问API调用失败: {str(e)}")

    def _call_openai_api(self, requirement: str, api_config: Dict, id_prefix: str,
                         case_style: str, language: str) -> List[Dict]:
        """调用OpenAI GPT API"""
        headers = {
            "Authorization": f"Bearer {api_config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = self._build_prompt(requirement, id_prefix, case_style, language, "openai")

        payload = {
            "model": api_config.get('model_version', 'gpt-3.5-turbo'),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            if "choices" in response_data and len(response_data["choices"]) > 0:
                result_text = response_data["choices"][0]["message"]["content"]
                return self._parse_testcases(result_text, id_prefix, language)
            else:
                raise Exception("API响应格式错误")

        except Exception as e:
            raise Exception(f"OpenAI API调用失败: {str(e)}")

    def _call_baidu_api(self, requirement: str, api_config: Dict, id_prefix: str,
                        case_style: str, language: str) -> List[Dict]:
        """调用百度文心一言API"""

        # 获取access_token
        def get_access_token(api_key, secret_key):
            url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
            response = requests.post(url)
            return response.json().get("access_token")

        access_token = get_access_token(api_config['api_key'], api_config['secret_key'])

        headers = {"Content-Type": "application/json"}
        prompt = self._build_prompt(requirement, id_prefix, case_style, language)

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            response = requests.post(
                f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            response_data = response.json()

            if "result" in response_data:
                result_text = response_data["result"]
                return self._parse_testcases(result_text, id_prefix, language)
            else:
                raise Exception("API响应格式错误")

        except Exception as e:
            raise Exception(f"百度文心一言API调用失败: {str(e)}")

    def _call_spark_api(self, requirement: str, api_config: Dict, id_prefix: str,
                        case_style: str, language: str) -> List[Dict]:
        """调用讯飞星火API（使用OpenAI兼容接口）"""
        try:
            from openai import OpenAI

            # 获取配置参数
            api_key = api_config.get('api_key', '')
            api_base = api_config.get('api_base', 'http://maas-api.cn-huabei-1.xf-yun.com/v1')
            model_id = api_config.get('model_id', '')

            if not api_key:
                raise ValueError("讯飞星火API Key不能为空")

            # 创建OpenAI客户端
            client = OpenAI(api_key=api_key, base_url=api_base)

            # 构建提示词
            prompt = self._build_prompt(requirement, id_prefix, case_style, language)

            # 构建消息
            messages = [
                {"role": "user", "content": prompt}
            ]

            # 调用API - 简化参数，移除不支持的extra_body
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                stream=False,
                temperature=0.3,
                max_tokens=4096
                # 移除 extra_headers 和 extra_body 参数
            )

            # 提取响应内容
            if response.choices and response.choices[0].message.content:
                result_text = response.choices[0].message.content
                return self._parse_testcases(result_text, id_prefix, language)
            else:
                raise Exception("API响应格式错误，未找到有效内容")

        except ImportError:
            raise Exception("请安装openai库: pip install openai")
        except Exception as e:
            raise Exception(f"讯飞星火API调用失败: {str(e)}")

    def _call_glm_api(self, requirement: str, api_config: Dict, id_prefix: str,
                      case_style: str, language: str) -> List[Dict]:
        """调用智谱ChatGLM API（简化实现）"""
        # 这里可以根据智谱AI的实际API进行调整
        return self._call_openai_api(requirement, api_config, id_prefix, case_style, language)

    def _build_prompt(self, requirement: str, id_prefix: str, case_style: str,
                      language: str, platform: str = "default") -> str:
        """构建提示词"""

        # 统一的风格指令定义
        style_instructions = {
            "标准格式": {
                "中文": "使用标准测试用例格式，包含清晰的步骤和预期结果",
                "英文": "Use standard test case format with clear steps and expected results"
            },
            "详细步骤": {
                "中文": "提供非常详细的测试步骤，每个步骤都要具体明确，包含具体的操作细节和输入数据",
                "英文": "Provide very detailed test steps, each step should be specific and clear with concrete operation details and input data"
            },
            "简洁格式": {
                "中文": "使用简洁的格式，重点描述关键测试点，省略不必要的细节",
                "英文": "Use concise format, focus on key test points, omit unnecessary details"
            },
            "BDD格式(Given-When-Then)": {
                "中文": "使用Given-When-Then格式编写测试场景，明确给定条件、执行动作和预期结果",
                "英文": "Write test scenarios using Given-When-Then format, clearly specifying given conditions, when actions, and then expected results"
            }
        }

        # 语言指令
        language_instructions = {
            "中文": "所有内容请使用中文，包括用例名称、步骤描述和预期结果",
            "英文": "All content should be in English, including case names, step descriptions and expected results"
        }

        # 根据语言选择提示词模板
        if language == "英文":
            prompt = f"""You are a senior software testing expert. Please generate test cases based on the following requirements:

    Requirement Description:
    {requirement}

    Please generate comprehensive and accurate test cases, {style_instructions[case_style]['英文']}.

    Each test case should contain the following fields:
    - Case ID: Format as {id_prefix}001, {id_prefix}002, etc.
    - Case Name: Clearly describe the test scenario
    - Precondition: Conditions that need to be met before test execution
    - Test Steps: Detailed test operation steps
    - Expected Result: Expected output or behavior
    - Priority: High, Medium, Low

    {language_instructions['英文']}

    Please ensure the test cases:
    1. Cover all major functional points
    2. Include normal and abnormal scenarios  
    3. Consider boundary conditions and error handling
    4. Set reasonable priorities
    5. Follow the {case_style} style consistently

    Please return in strict JSON array format, ensure the JSON format is correct."""

        else:
            prompt = f"""你是一位资深软件测试专家，请基于以下需求生成测试用例：

    需求描述：
    {requirement}

    请生成全面、精准的测试用例，{style_instructions[case_style]['中文']}。

    每个测试用例包含以下字段：
    - 用例ID：格式为{id_prefix}001, {id_prefix}002等
    - 用例名称：清晰描述测试场景
    - 前置条件：执行测试前需要满足的条件
    - 测试步骤：详细的测试操作步骤
    - 预期结果：期望的输出或行为
    - 优先级：高、中、低

    {language_instructions['中文']}

    请确保测试用例：
    1. 覆盖所有主要功能点
    2. 包含正常和异常场景
    3. 考虑边界条件和错误处理
    4. 优先级设置合理
    5. 严格遵循{case_style}的风格要求

    请以严格的JSON数组格式返回，确保JSON格式正确。"""

        return prompt
    def _get_language_instruction(self, language: str) -> str:
        """获取语言指令"""
        instructions = {
            "中文": "所有内容请使用中文",
            "英文": "All content should be in English",
            "中英混合": "用例名称和描述使用中文，技术术语可保留英文"
        }
        return instructions.get(language, "所有内容请使用中文")

    def _parse_testcases(self, result_text: str, id_prefix: str, language: str) -> List[Dict]:
        """从API返回的文本中解析测试用例"""
        try:
            # 尝试直接解析JSON
            json_pattern = r'\[\s*\{.*\}\s*\]'
            match = re.search(json_pattern, result_text, re.DOTALL)
            if match:
                json_str = match.group()
                test_cases = json.loads(json_str)
            else:
                # 如果没有找到JSON数组，尝试其他格式
                raise Exception("无法从响应中解析出JSON数据")

            # 标准化测试用例格式
            standardized_cases = []
            for i, test_case in enumerate(test_cases):
                if language == "英文":
                    # 英文输出使用英文字段名
                    standardized_case = {
                        "Case ID": test_case.get("Case ID", test_case.get("用例ID", f"{id_prefix}{i + 1:03d}")),
                        "Case Name": test_case.get("Case Name",
                                                   test_case.get("用例名称", test_case.get("用例标题", f"Test Case {i + 1}"))),
                        "Precondition": test_case.get("Precondition", test_case.get("前置条件", test_case.get("前提条件", ""))),
                        "Test Steps": test_case.get("Test Steps", test_case.get("测试步骤", test_case.get("步骤", ""))),
                        "Expected Result": test_case.get("Expected Result",
                                                         test_case.get("预期结果", test_case.get("期望结果", ""))),
                        "Priority": test_case.get("Priority", test_case.get("优先级", test_case.get("优先级别", "Medium")))
                    }
                else:
                    # 中文输出使用中文字段名
                    standardized_case = {
                        "用例ID": test_case.get("用例ID", test_case.get("Case ID", f"{id_prefix}{i + 1:03d}")),
                        "用例名称": test_case.get("用例名称",
                                              test_case.get("Case Name", test_case.get("用例标题", f"测试用例{i + 1}"))),
                        "前置条件": test_case.get("前置条件", test_case.get("Precondition", test_case.get("前提条件", ""))),
                        "测试步骤": test_case.get("测试步骤", test_case.get("Test Steps", test_case.get("步骤", ""))),
                        "预期结果": test_case.get("预期结果", test_case.get("Expected Result", test_case.get("期望结果", ""))),
                        "优先级": test_case.get("优先级", test_case.get("Priority", test_case.get("优先级别", "中")))
                    }
                standardized_cases.append(standardized_case)

            return standardized_cases

        except Exception as e:
            raise Exception(f"解析测试用例失败: {str(e)}")

    def generate_markdown_report(self, test_cases: List[Dict], requirement: str,
                                 title: str = "测试用例文档") -> str:
        """生成Markdown格式的测试用例文档"""

        md_content = f"""# {title}

## 需求描述
{requirement}

## 测试用例汇总

| 用例ID | 用例名称 | 优先级 | 前置条件 | 测试步骤 | 预期结果 |
|--------|----------|--------|----------|----------|----------|
"""

        for case in test_cases:
            # 对长文本进行截断处理
            precondition = str(case['前置条件'])[:50] + "..." if len(str(case['前置条件'])) > 50 else case['前置条件']
            steps = str(case['测试步骤'])[:80] + "..." if len(str(case['测试步骤'])) > 80 else case['测试步骤']
            expected = str(case['预期结果'])[:80] + "..." if len(str(case['预期结果'])) > 80 else case['预期结果']

            md_content += f"| {case['用例ID']} | {case['用例名称']} | {case['优先级']} | {precondition} | {steps} | {expected} |\n"

        md_content += f"\n## 统计信息\n- 总用例数: {len(test_cases)}\n- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"

        return md_content

    def get_supported_platforms(self) -> Dict[str, str]:
        """获取支持的平台列表"""
        return self.supported_platforms

    def get_case_styles(self) -> Dict[str, str]:
        """获取支持的用例风格"""
        return self.case_styles

    def get_languages(self) -> List[str]:
        """获取支持的语言"""
        return ["中文", "英文"]


# 使用示例
def example_usage():
    """使用示例"""
    generator = TestCaseGenerator()

    # 示例需求
    requirement = "用户登录功能，需要验证用户名密码，支持记住登录状态"

    # API配置
    ali_config = {"api_key": "your_ali_api_key"}
    openai_config = {"api_key": "your_openai_key", "model_version": "gpt-3.5-turbo"}
    baidu_config = {"api_key": "your_baidu_key", "secret_key": "your_baidu_secret"}

    try:
        # 使用阿里通义千问生成测试用例
        test_cases = generator.generate_testcases(
            requirement=requirement,
            platform="ali",
            api_config=ali_config,
            id_prefix="LOGIN",
            case_style="标准格式",
            language="中文"
        )

        # 生成Markdown报告
        markdown_report = generator.generate_markdown_report(test_cases, requirement)
        print(markdown_report)

        # 保存到文件
        with open("test_cases.md", "w", encoding="utf-8") as f:
            f.write(markdown_report)

        print(f"成功生成 {len(test_cases)} 个测试用例")

    except Exception as e:
        print(f"生成测试用例失败: {e}")


if __name__ == "__main__":
    example_usage()
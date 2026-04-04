import json
import platform
import re
import shutil
import subprocess
import tempfile
import time
from io import BytesIO
from pathlib import Path
import requests
from typing import Any, Dict, List, Optional

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from qa_toolkit.paths import BIN_DIR


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
        self.coverage_focus_options = {
            "核心功能": "覆盖主流程和核心业务动作",
            "异常处理": "覆盖失败提示、异常分支和恢复逻辑",
            "边界值": "覆盖长度、范围、数量、格式等边界条件",
            "权限角色": "覆盖不同角色、权限和数据隔离场景",
            "状态流转": "覆盖状态变化、重复操作和幂等性",
            "数据校验": "覆盖必填、格式、唯一性和数据一致性",
            "兼容性与易用性": "覆盖设备、浏览器、交互易用性和提示文案",
            "性能与稳定性": "覆盖响应时延、并发、重试和稳定性"
        }
        self.ocr_languages = {
            "中英混合": "chi_sim+eng",
            "中文优先": "chi_sim",
            "英文优先": "eng"
        }
        self.ocr_preprocess_modes = ["增强文本", "高对比度", "黑白文档", "原图"]
        self.pytesseract = None
        self.ocr_available = False
        self.tesseract_cmd = ""
        self.ocr_backend = ""
        self._configure_ocr()

    def _resolve_tesseract_command(self) -> str:
        """优先选择系统 tesseract，其次才尝试项目内置二进制。"""
        system_tesseract = shutil.which("tesseract")
        if system_tesseract:
            return system_tesseract

        for common_path in ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"]:
            if Path(common_path).exists():
                return common_path

        embedded_tesseract = BIN_DIR / "tesseract"
        if not embedded_tesseract.exists():
            return ""

        # 当前仓库内置的是 macOS x86_64 版本，在 Apple Silicon 上不可直接使用。
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            return ""

        return str(embedded_tesseract)

    def _configure_ocr(self):
        """初始化 OCR 环境。"""
        self.tesseract_cmd = self._resolve_tesseract_command()
        try:
            import pytesseract

            self.pytesseract = pytesseract
            if self.tesseract_cmd:
                self.pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
                self.ocr_available = True
                self.ocr_backend = "pytesseract"
            else:
                self.ocr_available = False
                self.ocr_backend = ""
        except Exception:
            self.pytesseract = None
            if self.tesseract_cmd:
                self.ocr_available = True
                self.ocr_backend = "tesseract-cli"
            else:
                self.ocr_available = False
                self.ocr_backend = ""

    def generate_testcases(self,
                           requirement: str,
                           platform: str,
                           api_config: Dict,
                           id_prefix: str = "TC",
                           case_style: str = "标准格式",
                           language: str = "中文",
                           target_case_count: int = 12,
                           coverage_focus: Optional[List[str]] = None) -> List[Dict]:
        """
        生成测试用例的主方法

        Args:
            requirement: 需求描述
            platform: AI平台，支持 ali/openai/baidu/spark/glm
            api_config: API配置参数
            id_prefix: 用例ID前缀
            case_style: 用例风格
            language: 输出语言
            target_case_count: 期望生成的用例数量
            coverage_focus: 重点覆盖维度

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

        return platform_methods[platform](
            requirement,
            api_config,
            id_prefix,
            case_style,
            language,
            max(1, target_case_count),
            coverage_focus or []
        )

    def _call_ali_api(self, requirement: str, api_config: Dict, id_prefix: str,
                      case_style: str, language: str, target_case_count: int,
                      coverage_focus: List[str]) -> List[Dict]:
        """调用阿里通义千问API"""
        headers = {
            "Authorization": f"Bearer {api_config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = self._build_prompt(
            requirement,
            id_prefix,
            case_style,
            language,
            target_case_count=target_case_count,
            coverage_focus=coverage_focus
        )

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
                         case_style: str, language: str, target_case_count: int,
                         coverage_focus: List[str]) -> List[Dict]:
        """调用OpenAI GPT API"""
        headers = {
            "Authorization": f"Bearer {api_config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = self._build_prompt(
            requirement,
            id_prefix,
            case_style,
            language,
            "openai",
            target_case_count=target_case_count,
            coverage_focus=coverage_focus
        )

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
                        case_style: str, language: str, target_case_count: int,
                        coverage_focus: List[str]) -> List[Dict]:
        """调用百度文心一言API"""

        # 获取access_token
        def get_access_token(api_key, secret_key):
            url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
            response = requests.post(url)
            return response.json().get("access_token")

        access_token = get_access_token(api_config['api_key'], api_config['secret_key'])

        headers = {"Content-Type": "application/json"}
        prompt = self._build_prompt(
            requirement,
            id_prefix,
            case_style,
            language,
            target_case_count=target_case_count,
            coverage_focus=coverage_focus
        )

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
                        case_style: str, language: str, target_case_count: int,
                        coverage_focus: List[str]) -> List[Dict]:
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
            prompt = self._build_prompt(
                requirement,
                id_prefix,
                case_style,
                language,
                target_case_count=target_case_count,
                coverage_focus=coverage_focus
            )

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
                      case_style: str, language: str, target_case_count: int,
                      coverage_focus: List[str]) -> List[Dict]:
        """调用智谱ChatGLM API（简化实现）"""
        # 这里可以根据智谱AI的实际API进行调整
        return self._call_openai_api(
            requirement,
            api_config,
            id_prefix,
            case_style,
            language,
            target_case_count,
            coverage_focus
        )

    def _build_prompt(self, requirement: str, id_prefix: str, case_style: str,
                      language: str, platform: str = "default",
                      target_case_count: int = 12,
                      coverage_focus: Optional[List[str]] = None) -> str:
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
            "英文": "All content should be in English, including case names, step descriptions and expected results",
            "中英混合": "用例名称和说明主要使用中文，必要的技术术语、字段名和按钮名可保留英文"
        }
        focus_items = coverage_focus or ["核心功能", "异常处理", "边界值", "数据校验"]
        focus_text_cn = "\n".join(f"- {item}: {self.coverage_focus_options.get(item, '')}" for item in focus_items)
        focus_text_en = "\n".join(f"- {item}" for item in focus_items)
        target_case_count = max(1, target_case_count)

        # 根据语言选择提示词模板
        if language == "英文":
            prompt = f"""You are a senior software testing expert. Please generate test cases based on the following requirements:

    Requirement Description:
    {requirement}

    Please generate comprehensive and accurate test cases, {style_instructions[case_style]['英文']}.
    Target case count: around {target_case_count}.

    Please prioritize the following coverage dimensions:
    {focus_text_en}

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
    6. If requirements are incomplete, infer carefully and reflect assumptions in preconditions
    7. Return only a valid JSON array without markdown fences

    Output schema example:
    [
      {{
        "Case ID": "{id_prefix}001",
        "Case Name": "User logs in with valid credentials",
        "Precondition": "Login page is available",
        "Test Steps": "1. Enter username\\n2. Enter password\\n3. Click Login",
        "Expected Result": "Login succeeds and user enters dashboard",
        "Priority": "High",
        "Test Type": "Functional"
      }}
    ]"""

        else:
            prompt = f"""你是一位资深软件测试专家，请基于以下需求生成测试用例：

    需求描述：
    {requirement}

    请生成全面、精准的测试用例，{style_instructions[case_style]['中文']}。
    目标用例数量：约{target_case_count}条，可按风险和场景适当增减。

    请优先覆盖以下维度：
    {focus_text_cn}

    每个测试用例包含以下字段：
    - 用例ID：格式为{id_prefix}001, {id_prefix}002等
    - 用例名称：清晰描述测试场景
    - 前置条件：执行测试前需要满足的条件
    - 测试步骤：详细的测试操作步骤
    - 预期结果：期望的输出或行为
    - 优先级：高、中、低
    - 测试类型：如功能、异常、边界、权限、流程等，可选但建议返回

    {language_instructions.get(language, language_instructions['中文'])}

    请确保测试用例：
    1. 覆盖所有主要功能点
    2. 包含正常和异常场景
    3. 考虑边界条件和错误处理
    4. 优先级设置合理
    5. 严格遵循{case_style}的风格要求
    6. 若需求存在不明确之处，请基于合理假设补全，并在前置条件中体现假设
    7. 只返回合法 JSON 数组，不要附带 ```json 代码块或额外解释

    输出格式示例：
    [
      {{
        "用例ID": "{id_prefix}001",
        "用例名称": "用户使用正确账号密码登录",
        "前置条件": "系统已发布登录功能，测试账号状态正常",
        "测试步骤": "1. 打开登录页\\n2. 输入正确用户名\\n3. 输入正确密码\\n4. 点击登录",
        "预期结果": "登录成功并进入首页",
        "优先级": "高",
        "测试类型": "功能"
      }}
    ]"""

        return prompt

    def _get_language_instruction(self, language: str) -> str:
        """获取语言指令"""
        instructions = {
            "中文": "所有内容请使用中文",
            "英文": "All content should be in English",
            "中英混合": "用例名称和描述使用中文，技术术语可保留英文"
        }
        return instructions.get(language, "所有内容请使用中文")

    def _prepare_image_for_ocr(self, image: Image.Image, preprocess_mode: str) -> Image.Image:
        """对图片做简单预处理，提升 OCR 识别率。"""
        processed = image.convert("RGB")
        if preprocess_mode == "原图":
            return processed

        gray = ImageOps.grayscale(processed)
        gray = ImageOps.autocontrast(gray)

        if preprocess_mode == "增强文本":
            gray = ImageEnhance.Contrast(gray).enhance(1.8)
            return gray.filter(ImageFilter.SHARPEN)
        if preprocess_mode == "高对比度":
            gray = ImageEnhance.Contrast(gray).enhance(2.5)
            gray = gray.filter(ImageFilter.MedianFilter(size=3))
            return gray
        if preprocess_mode == "黑白文档":
            bw = gray.point(lambda x: 255 if x > 180 else 0, mode="1")
            return bw.convert("L")
        return gray

    def extract_text_from_image(self, image_bytes: bytes, lang: str = "chi_sim+eng",
                                preprocess_mode: str = "增强文本") -> str:
        """从图片中提取需求文本。"""
        if not self.ocr_available or not self.tesseract_cmd:
            raise RuntimeError("OCR 功能不可用，请检查 pytesseract 或 tesseract 环境。")

        try:
            with Image.open(BytesIO(image_bytes)) as image:
                processed_image = self._prepare_image_for_ocr(image, preprocess_mode)
                if self.pytesseract is not None and self.ocr_backend == "pytesseract":
                    try:
                        raw_text = self.pytesseract.image_to_string(
                            processed_image,
                            lang=lang,
                            config="--psm 6"
                        )
                    except Exception:
                        raw_text = self.pytesseract.image_to_string(
                            processed_image,
                            config="--psm 6"
                        )
                else:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        input_path = Path(tmp_dir) / "ocr_input.png"
                        output_base = Path(tmp_dir) / "ocr_output"
                        processed_image.save(input_path)

                        command = [
                            self.tesseract_cmd,
                            str(input_path),
                            str(output_base),
                            "-l",
                            lang,
                            "--psm",
                            "6",
                            "txt",
                        ]
                        result = subprocess.run(
                            command,
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if result.returncode != 0:
                            fallback_command = [
                                self.tesseract_cmd,
                                str(input_path),
                                str(output_base),
                                "--psm",
                                "6",
                                "txt",
                            ]
                            fallback_result = subprocess.run(
                                fallback_command,
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            if fallback_result.returncode != 0:
                                stderr = fallback_result.stderr or result.stderr or "未知错误"
                                raise RuntimeError(stderr.strip())

                        raw_text = (output_base.with_suffix(".txt")).read_text(encoding="utf-8", errors="ignore")
            cleaned_text = self.clean_requirement_text(raw_text)
            if not cleaned_text:
                raise RuntimeError("未识别到有效文字，请尝试更清晰的截图或更换预处理模式。")
            return cleaned_text
        except Exception as e:
            raise RuntimeError(f"图片 OCR 识别失败: {str(e)}")

    def clean_requirement_text(self, requirement: str) -> str:
        """清洗需求文本，适配 OCR 或复制粘贴内容。"""
        text = str(requirement or "").replace("\r\n", "\n").replace("\r", "\n").replace("\u3000", " ")
        cleaned_lines = []
        blank_pending = False

        for raw_line in text.split("\n"):
            line = re.sub(r"[ \t]+", " ", raw_line).strip()
            if not line:
                if cleaned_lines and not blank_pending:
                    cleaned_lines.append("")
                    blank_pending = True
                continue
            cleaned_lines.append(line)
            blank_pending = False

        return "\n".join(cleaned_lines).strip()

    def compose_requirement_context(self, requirement: str, ocr_text: str = "",
                                    module_name: str = "", business_rules: str = "",
                                    acceptance_criteria: str = "", out_of_scope: str = "",
                                    additional_notes: str = "") -> str:
        """将手工输入、OCR 内容和结构化补充拼成更适合生成的需求上下文。"""
        sections = []
        primary_requirement = self.clean_requirement_text(requirement)
        if primary_requirement:
            sections.append(f"需求原文:\n{primary_requirement}")

        if module_name.strip():
            sections.append(f"所属模块/页面:\n{self.clean_requirement_text(module_name)}")

        if ocr_text.strip():
            sections.append(f"图片识别补充需求:\n{self.clean_requirement_text(ocr_text)}")

        if business_rules.strip():
            sections.append(f"业务规则/字段约束:\n{self.clean_requirement_text(business_rules)}")

        if acceptance_criteria.strip():
            sections.append(f"验收标准/关键成功条件:\n{self.clean_requirement_text(acceptance_criteria)}")

        if out_of_scope.strip():
            sections.append(f"本次不覆盖范围:\n{self.clean_requirement_text(out_of_scope)}")

        if additional_notes.strip():
            sections.append(f"补充说明:\n{self.clean_requirement_text(additional_notes)}")

        return "\n\n".join(sections).strip()

    def _suggest_coverage_focus(self, requirement: str) -> List[str]:
        """基于关键词给出推荐覆盖维度。"""
        text = requirement.lower()
        suggestions = ["核心功能", "异常处理"]

        keyword_mapping = {
            "边界值": ["长度", "范围", "数量", "最大", "最小", "字符", "格式", "size", "limit"],
            "权限角色": ["权限", "角色", "管理员", "访客", "审核", "登录态", "身份"],
            "状态流转": ["状态", "流程", "审批", "回调", "取消", "支付", "订单", "重试"],
            "数据校验": ["必填", "校验", "唯一", "重复", "邮箱", "手机号", "身份证", "上传"],
            "兼容性与易用性": ["页面", "浏览器", "app", "小程序", "按钮", "提示", "兼容"],
            "性能与稳定性": ["性能", "并发", "耗时", "超时", "稳定", "批量", "大数据量"]
        }

        for focus, keywords in keyword_mapping.items():
            if any(keyword in text for keyword in keywords):
                suggestions.append(focus)

        deduplicated = []
        for item in suggestions:
            if item not in deduplicated:
                deduplicated.append(item)
        return deduplicated[:5]

    def analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """对当前需求做本地梳理，给出功能点、测试关注点和待确认项。"""
        cleaned = self.clean_requirement_text(requirement)
        if not cleaned:
            return {
                "summary": "",
                "feature_points": [],
                "business_rules": [],
                "roles": [],
                "suggested_focus": [],
                "unclear_points": ["当前没有可分析的需求文本"],
                "complexity": "低",
                "line_count": 0,
            }

        lines = [line for line in cleaned.splitlines() if line.strip()]
        sentences = [item.strip() for item in re.split(r"[。！？!?]\s*|\n", cleaned) if item.strip()]
        feature_keywords = ["支持", "需要", "允许", "可以", "应", "必须", "展示", "校验", "上传", "导出", "登录", "支付", "搜索", "审批"]
        rule_keywords = ["必填", "唯一", "长度", "范围", "格式", "状态", "权限", "金额", "次数", "大小", "类型", "限制"]
        role_keywords = ["用户", "管理员", "访客", "运营", "审核", "商家", "客服", "测试人员", "开发人员"]

        feature_points = []
        for line in lines:
            if re.match(r"^[-*•\d一二三四五六七八九十]", line) or any(keyword in line for keyword in feature_keywords):
                feature_points.append(line)
        if not feature_points:
            feature_points = sentences[:5]

        business_rules = [line for line in lines if any(keyword in line for keyword in rule_keywords)]
        roles = []
        for role in role_keywords:
            if role in cleaned and role not in roles:
                roles.append(role)

        unclear_points = []
        if not roles:
            unclear_points.append("未明确用户角色或参与方")
        if not any(keyword in cleaned for keyword in ["失败", "异常", "错误", "拒绝", "提示", "超时"]):
            unclear_points.append("未明确异常流程、失败提示或错误处理")
        if not any(keyword in cleaned for keyword in rule_keywords):
            unclear_points.append("未明确字段校验、边界值或业务约束")
        if not any(keyword in cleaned for keyword in ["状态", "流程", "完成后", "提交后", "回调", "审批"]):
            unclear_points.append("未明确状态流转、前后置动作或处理时机")

        complexity_score = len(feature_points) + len(business_rules) + len(roles)
        if complexity_score >= 10:
            complexity = "高"
        elif complexity_score >= 5:
            complexity = "中"
        else:
            complexity = "低"

        summary = sentences[0] if sentences else cleaned[:120]

        return {
            "summary": summary,
            "feature_points": feature_points[:8],
            "business_rules": business_rules[:6],
            "roles": roles,
            "suggested_focus": self._suggest_coverage_focus(cleaned),
            "unclear_points": unclear_points,
            "complexity": complexity,
            "line_count": len(lines),
        }

    def normalize_case_record(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """将中英文用例字段归一化为便于展示和导出的统一结构。"""
        priority_value = str(case.get("优先级", case.get("Priority", case.get("优先级别", "中")))).strip()
        priority_mapping = {
            "High": "高",
            "Medium": "中",
            "Low": "低",
            "高": "高",
            "中": "中",
            "低": "低",
        }
        return {
            "用例ID": case.get("用例ID", case.get("Case ID", "")),
            "用例名称": case.get("用例名称", case.get("Case Name", case.get("用例标题", ""))),
            "前置条件": case.get("前置条件", case.get("Precondition", case.get("前提条件", ""))),
            "测试步骤": case.get("测试步骤", case.get("Test Steps", case.get("步骤", ""))),
            "预期结果": case.get("预期结果", case.get("Expected Result", case.get("期望结果", ""))),
            "优先级": priority_mapping.get(priority_value, priority_value or "中"),
            "测试类型": case.get("测试类型", case.get("Test Type", case.get("Type", ""))),
            "备注": case.get("备注", case.get("Notes", case.get("说明", ""))),
        }

    def normalize_cases_for_display(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量归一化测试用例。"""
        return [self.normalize_case_record(case) for case in test_cases]

    def _parse_testcases(self, result_text: str, id_prefix: str, language: str) -> List[Dict]:
        """从API返回的文本中解析测试用例"""
        try:
            cleaned_text = result_text.strip()
            cleaned_text = re.sub(r"^```json\s*", "", cleaned_text, flags=re.IGNORECASE)
            cleaned_text = re.sub(r"^```\s*", "", cleaned_text)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            candidates = [cleaned_text]
            json_pattern = r'\[\s*\{.*\}\s*\]'
            match = re.search(json_pattern, cleaned_text, re.DOTALL)
            if match:
                candidates.insert(0, match.group())

            test_cases = None
            parse_error = None
            for candidate in candidates:
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        for key in ["test_cases", "cases", "data", "items", "用例列表"]:
                            if isinstance(parsed.get(key), list):
                                test_cases = parsed[key]
                                break
                    elif isinstance(parsed, list):
                        test_cases = parsed
                    if isinstance(test_cases, list):
                        break
                except Exception as e:
                    parse_error = e

            if not isinstance(test_cases, list):
                raise Exception(f"无法从响应中解析出JSON数据: {parse_error or '未找到数组结构'}")

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
                        "Priority": test_case.get("Priority", test_case.get("优先级", test_case.get("优先级别", "Medium"))),
                        "Test Type": test_case.get("Test Type", test_case.get("测试类型", test_case.get("Type", ""))),
                        "Notes": test_case.get("Notes", test_case.get("备注", test_case.get("说明", "")))
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
                        "优先级": test_case.get("优先级", test_case.get("Priority", test_case.get("优先级别", "中"))),
                        "测试类型": test_case.get("测试类型", test_case.get("Test Type", test_case.get("Type", ""))),
                        "备注": test_case.get("备注", test_case.get("Notes", test_case.get("说明", "")))
                    }
                standardized_cases.append(standardized_case)

            return standardized_cases

        except Exception as e:
            raise Exception(f"解析测试用例失败: {str(e)}")

    def generate_markdown_report(self, test_cases: List[Dict], requirement: str,
                                 title: str = "测试用例文档") -> str:
        """生成Markdown格式的测试用例文档"""
        normalized_cases = self.normalize_cases_for_display(test_cases)
        cleaned_requirement = self.clean_requirement_text(requirement)

        md_content = f"""# {title}

## 需求描述
{cleaned_requirement}

## 测试用例汇总

| 用例ID | 用例名称 | 优先级 | 测试类型 | 前置条件 | 测试步骤 | 预期结果 |
|--------|----------|--------|----------|----------|----------|----------|
"""

        for case in normalized_cases:
            # 对长文本进行截断处理
            precondition = str(case['前置条件'])[:50] + "..." if len(str(case['前置条件'])) > 50 else case['前置条件']
            steps = str(case['测试步骤'])[:80] + "..." if len(str(case['测试步骤'])) > 80 else case['测试步骤']
            expected = str(case['预期结果'])[:80] + "..." if len(str(case['预期结果'])) > 80 else case['预期结果']
            case_type = case.get("测试类型", "")

            md_content += f"| {case['用例ID']} | {case['用例名称']} | {case['优先级']} | {case_type} | {precondition} | {steps} | {expected} |\n"

        md_content += f"\n## 统计信息\n- 总用例数: {len(normalized_cases)}\n- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"

        return md_content

    def get_supported_platforms(self) -> Dict[str, str]:
        """获取支持的平台列表"""
        return self.supported_platforms

    def get_case_styles(self) -> Dict[str, str]:
        """获取支持的用例风格"""
        return self.case_styles

    def get_languages(self) -> List[str]:
        """获取支持的语言"""
        return self.languages

    def get_coverage_focus_options(self) -> Dict[str, str]:
        """获取覆盖维度选项。"""
        return self.coverage_focus_options

    def get_ocr_language_options(self) -> Dict[str, str]:
        """获取 OCR 语言选项。"""
        return self.ocr_languages

    def get_ocr_preprocess_modes(self) -> List[str]:
        """获取 OCR 预处理模式。"""
        return self.ocr_preprocess_modes

    def is_ocr_available(self) -> bool:
        """OCR 是否可用。"""
        return self.ocr_available

    def get_ocr_status(self) -> Dict[str, str]:
        """返回 OCR 运行状态。"""
        if self.ocr_available:
            cmd_label = Path(self.tesseract_cmd).name if self.tesseract_cmd else "system"
            backend_label = self.ocr_backend or "ocr"
            return {"status": "available", "message": f"OCR 已就绪，后端: {backend_label}，当前 tesseract: {cmd_label}"}
        return {"status": "unavailable", "message": "OCR 不可用，请确认系统已安装可运行的 tesseract，或安装 pytesseract 作为 Python 封装"}


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

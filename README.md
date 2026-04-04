# QA Toolkit

面向测试工程师的综合工具平台，提供数据生成、文本处理、接口自动化、接口安全、接口性能、应用安全扫描、BI 分析、禅道统计导出等能力。项目已按源码、资源、示例、运行工作区和测试分层整理，便于继续维护和扩展。

## 项目定位

- 主应用：基于 Streamlit 的测试工程工具平台。
- 核心能力：接口自动化、接口性能、接口安全、移动应用/站点安全扫描。
- 支撑模块：常量配置、文档说明、报告生成、第三方集成、工具类。

## 目录结构

```text
.
├── assets/                     # 项目静态资源
│   ├── bin/                    # 内置可执行资源
│   ├── fonts/                  # 字体资源
│   └── images/                 # 图片资源
├── examples/                   # 示例输入与历史样例
│   ├── api_cases/
│   ├── interface_documents/
│   └── screenshots/
├── src/
│   └── qa_toolkit/             # 主源码包
│       ├── config/             # 常量与配置
│       ├── core/               # 核心测试能力
│       ├── integrations/       # 外部系统集成
│       ├── reporting/          # 报告与执行封装
│       ├── support/            # 文档与辅助说明
│       ├── tools/              # 通用测试工具
│       ├── ui/                 # Streamlit 页面与组件
│       ├── utils/              # 基础工具类
│       ├── paths.py            # 路径常量
│       └── streamlit_app.py    # 主应用入口模块
├── tests/                      # 自动化测试
├── workspace/                  # 运行期工作区
│   ├── api_cases/              # 生成的接口用例脚本
│   ├── reports/                # 生成的报告
│   └── uploads/                # 上传后的临时文件
├── requirements.txt
└── streamlit_app.py            # 主应用启动入口
```

## 命名与分层规范

- 统一采用英文 `snake_case` 文件名，避免 `test/` 同时承载源码和测试数据。
- 业务源码统一收敛到 `src/qa_toolkit/`，避免根目录散落脚本。
- 静态资源放到 `assets/`，示例文件放到 `examples/`，运行产物放到 `workspace/`。
- `core/` 放核心测试执行能力，`ui/` 放页面与组件，`tools/` 放用户侧工具类，`utils/` 放底层通用能力。

## 主要模块

- `src/qa_toolkit/streamlit_app.py`：主 Streamlit 工具平台。
- `src/qa_toolkit/core/api_test_core.py`：接口文档解析、用例生成、执行与报告基础能力。
- `src/qa_toolkit/core/api_performance_tool.py`：接口性能测试能力。
- `src/qa_toolkit/core/api_security_tool.py`：接口安全测试能力。
- `src/qa_toolkit/core/application_security_tool.py`：APK/IPA/Web 目标安全扫描。
- `src/qa_toolkit/reporting/report_generator.py`：HTML 报告生成。
- `src/qa_toolkit/integrations/zentao_exporter.py`：禅道统计导出。

## 快速开始

### 1. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 启动主工具平台

```bash
streamlit run streamlit_app.py
```

### 3. 运行测试

```bash
pytest tests/test_application_security_tool.py
```

## 工作区说明

- `workspace/uploads/`：页面上传文件的暂存目录。
- `workspace/api_cases/`：接口自动化生成的脚本与清单目录。
- `workspace/reports/`：测试执行后生成的报告目录。

这些目录默认保留结构，不提交运行产物。

## 示例资源

- `examples/interface_documents/`：接口文档模板与示例输入。
- `examples/api_cases/`：接口测试清单与示例执行脚本。
- `examples/screenshots/`：历史输出截图样例。

## 后续建议

- 可以继续把 `src/qa_toolkit/streamlit_app.py` 中的大型页面逻辑拆分到更多 `ui/pages/` 模块。
- 可以补充 `pyproject.toml`、格式化工具和导入排序规则，进一步统一工程规范。
- 可以逐步为 `core/` 与 `tools/` 增加更多单元测试，降低后续重构成本。

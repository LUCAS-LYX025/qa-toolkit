# QA Toolkit

> 17 个测试工程师高频工具，一个本地入口。不用再为了造一条测试数据去开三个网页。

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.50-FF4B4B?logo=streamlit&logoColor=white">
  <img alt="tools" src="https://img.shields.io/badge/tools-17-4CAF50">
  <img alt="tests" src="https://img.shields.io/badge/tests-31%20files-blue">
</p>

![QA Toolkit 首页](assets/images/screenshots/01_home.png)

---

## 这东西是给谁用的

写测试的人每天都在重复做几件事：造数据、写用例、对接口文档、看日志、整理报告。这些活单看都不难，但每个都要切换工具、拼命令、手动整理格式，一天下来真正花在「判断」上的时间没多少。

QA Toolkit 把这些活收进一个 Streamlit 应用里。启动一次，左边选工具，右边干活，结果直接下载成 CSV / Excel / JSON / HTML。

具体一点，它覆盖这些场景：

- 联调前要一批格式正确的用户、订单、地址数据
- 拿到需求文档或原型截图，要先出一版用例初稿
- 接口文档换了版本，想知道到底改了哪几个字段
- 想按接口文档直接跑一轮基础回归，而不是手写脚本
- 上线前想做安全基线自查，但不知道从哪下手
- 几十万行日志里要找出异常和状态码分布

## 工具一览

按使用场景分五组，共 17 个。

### 测试设计

| 工具 | 什么时候会用到 | 输出 |
| --- | --- | --- |
| 🧬 数据生成工具 | 联调造数、表单校验、边界值设计。支持 Faker 真实感数据、基础随机值、业务场景数据集、边界值/异常值 | 文本、CSV、JSON |
| 📑 测试用例生成器 | 拿到需求文本或截图，要一版用例初稿。四种模型可选，支持 OCR 识别截图、需求分析助手 | Excel、CSV、Markdown、JSON |
| 📈 禅道绩效统计 | 月底统计测试/开发的缺陷处理时效、超时响应率 | Excel、CSV |

### 接口相关

| 工具 | 什么时候会用到 | 输出 |
| --- | --- | --- |
| 🔧 接口研发辅助 | 文档要标准化、两个版本要对比、联调前要 Mock 和调试代码、要生成断言模板 | JSON、Markdown、Mock 脚本、代码片段 |
| 🤖 接口自动化测试 | 按接口文档直接生成脚本并执行，支持 pytest / unittest / requests 三种模式 | 测试脚本 + HTML 报告 |
| 🚀 接口性能测试 | 轻量压测。Thread Group、多接口顺序执行、CSV 参数化、事务链路聚合 | HTML、JSON、CSV 报告 |
| 🛡️ 接口安全测试 | 上线前安全基线。API 基线检查、APK/IPA/APPX 静态扫描、MobSF 集成、Web 站点扫描、Nuclei 模板导出 | Markdown、JSON、CSV、PDF |

### 日志与数据

| 工具 | 什么时候会用到 | 输出 |
| --- | --- | --- |
| 📜 日志分析工具 | 日志级别统计、过滤搜索、状态码/IP/接口分布、异常洞察 | 统计表、CSV |
| 🧩 JSON 处理工具 | 格式化、校验、两个 JSON 对比、JSONPath 取值 | JSON、文本 |
| 📊 BI 数据分析工具 | 数据分析类测试的图表辅助 | 图表 |

### 文本与内容

| 工具 | 什么时候会用到 | 输出 |
| --- | --- | --- |
| 🆚 文本对比工具 | 对比两版文档/配置。行级差异、词级高亮、空白规范化 | Unified Diff、对比视图 |
| 🔢 字数统计工具 | 字符/单词/段落统计、词频、重复行诊断，支持 doc/docx/log 等导入 | 多格式导出 |
| 🔣 正则测试工具 | 调表达式、看分组、生成多语言示例代码 | 匹配结果、代码片段 |

### 工程杂活

| 工具 | 什么时候会用到 | 输出 |
| --- | --- | --- |
| 🕒 时间处理工具 | 时间戳转换、区间计算、日期推算 | 时间字符串 |
| 🔐 加密/解密工具 | Base64、MD5、SHA、RSA、URL、HTML、Unicode、Hex 编解码 | 结果文本 |
| 🌐 IP/域名查询工具 | 解析 IP 归属、域名信息、URL 拆解，支持批量 | 表格 |
| 🖼️ 图片处理工具 | 格式转换、尺寸调整、裁剪、旋转、加水印 | 图片文件 |

## 界面

几个用得最多的页面：

| 数据生成 | 测试用例生成 |
| --- | --- |
| ![数据生成工具](assets/images/screenshots/02_data_generator.png) | ![测试用例生成器](assets/images/screenshots/03_test_case_generator.png) |

| 接口自动化 | 接口安全测试 |
| --- | --- |
| ![接口自动化测试](assets/images/screenshots/05_api_automation.png) | ![接口安全测试](assets/images/screenshots/07_api_security.png) |

<details>
<summary>展开看其余工具的界面截图</summary>

| | |
| --- | --- |
| ![接口研发辅助](assets/images/screenshots/04_api_dev_tools.png) | ![接口性能测试](assets/images/screenshots/06_api_performance.png) |
| ![禅道绩效统计](assets/images/screenshots/08_zentao.png) | ![文本对比](assets/images/screenshots/09_text_compare.png) |
| ![JSON 处理](assets/images/screenshots/10_json_tools.png) | ![正则测试](assets/images/screenshots/11_regex_tester.png) |
| ![日志分析](assets/images/screenshots/12_log_analysis.png) | ![字数统计](assets/images/screenshots/13_word_counter.png) |
| ![时间处理](assets/images/screenshots/14_time_processor.png) | ![IP 域名查询](assets/images/screenshots/15_ip_lookup.png) |
| ![加密解密](assets/images/screenshots/16_crypto_tools.png) | ![图片处理](assets/images/screenshots/17_image_processor.png) |
| ![BI 分析](assets/images/screenshots/18_bi_analysis.png) | ![正则字段提取](assets/images/screenshots/19_regex_field_extractor.png) |

</details>

## 快速开始

```bash
git clone https://github.com/LUCAS-LYX025/qa-toolkit.git
cd qa-toolkit

python3 -m venv .venv
source .venv/bin/activate          # Windows 用 .venv\Scripts\activate

python3 -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

浏览器会打开 `http://localhost:8501`。左边是工具切换区，默认停在首页。

**需要 OCR（识别需求截图）时**，额外装系统级 tesseract：

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

装完在页面里应该能看到「OCR 已就绪」。没装也不影响其他 16 个工具。

## 四个高频场景怎么走

### 1. 截图/需求文档 → 测试用例

打开 **测试用例生成器** → 上传原型图或需求截图，用 OCR 提取文本 → 在「结构化补充」里补业务规则、验收标准、不覆盖范围 → 看「需求分析助手」给出的覆盖维度和待确认项 → 选模型、风格、目标用例数 → 生成后筛选、导出 Excel。

> 生成结果是初稿。复杂需求建议拆成「业务规则」+「验收标准」两块喂进去，比贴一大段文本效果好得多。

### 2. 接口文档 → 自动化回归

先打开 **接口研发辅助** 做文档标准化和接口体检，顺手看一眼变更分析（如果是新版本）→ 打开 **接口自动化测试**，导入文档、填 Base URL、选脚本模式 → 生成脚本、执行、下载 HTML 报告。

> 体检这一步别跳过。文档缺字段是最常见的失败原因，提前修比跑挂了再查省事。

### 3. 上线前安全基线

打开 **接口安全测试** → 导入接口文档，确认范围 → 跑 API 基线检查 → 有移动端包就上传 APK/IPA 做静态扫描（想更完整就配 MobSF 做官方静态分析）→ 有 Web 入口补一轮站点扫描 → 导出报告和回归清单。

### 4. 联调前准备

**数据生成工具** 造一批场景数据（建议填随机种子，回归时可复现）→ **接口研发辅助** 生成 Mock 服务和调试代码 → 需要处理请求参数就用 **JSON 处理** 或 **加密/解密**。

## 关于 AI 部分

测试用例生成器支持四家模型，都需要你自己的 API Key：

- 阿里通义千问（DashScope）
- 百度文心一言
- 讯飞星火（OpenAI 兼容接口）
- 智谱 ChatGLM

想让人不填 Key 就能试用，可以配一个示范模型 Key：

```toml
# .streamlit/secrets.toml
TCG_DEMO_GLM_API_KEY = "your-demo-key"
```

配好后页面上的「免费体验示范」入口直接可用。

## 配置

敏感配置统一走 Streamlit Secrets，不进仓库：

```toml
# .streamlit/secrets.toml
TCG_DEMO_GLM_API_KEY = "replace-with-your-key"

[mobsf]
base_url = "https://your-mobsf.example.com"
api_key = "replace-with-your-mobsf-api-key"
timeout_seconds = 180
verify_ssl = true
include_pdf = false
```

模板见 `.streamlit/secrets.toml.example`。`.streamlit/secrets.toml` 已在 `.gitignore` 里，不会误提交。

## 部署到 Streamlit Community Cloud

仓库根目录已经准备好部署所需的三个文件：`streamlit_app.py`、`requirements.txt`、`packages.txt`。

| 配置项 | 值 |
| --- | --- |
| Main file path | `streamlit_app.py` |
| Python version | `3.12` |
| System dependencies | `packages.txt`（tesseract-ocr、中文语言包、poppler、libgl1） |

几个 Cloud 上的限制值得提前知道：

- Cloud 实例是临时的，`workspace/` 里的产物不会长期保存，结果请及时下载
- 没有 Docker / ADB / 模拟器，MobSF 只能用「远程服务模式」，通过 Secrets 提供地址和 Key
- 上传和消息体上限已设为 200MB（`.streamlit/config.toml`）

完整步骤、Cloud 后台填写模板和故障速查表在 [DEPLOY_STREAMLIT_COMMUNITY_CLOUD.md](DEPLOY_STREAMLIT_COMMUNITY_CLOUD.md)。

## 项目结构

```text
.
├── streamlit_app.py             # 启动入口（根目录薄壳）
├── src/qa_toolkit/
│   ├── streamlit_app.py         # 主应用逻辑
│   ├── config/                  # 工具路由、常量、图标资源
│   ├── core/                    # 接口自动化/性能/安全等核心能力
│   ├── tools/                   # 数据生成、用例生成、IP 查询等工具模块
│   ├── ui/pages/                # 每个工具一个页面模块
│   ├── integrations/            # 禅道导出与代理
│   ├── reporting/               # 报告生成、执行封装、MobSF PDF
│   └── utils/                   # 日志、时间、图片、JSON 等通用工具
├── assets/images/screenshots/   # 工具截图
├── examples/                    # 接口文档模板、示例用例、示例脚本
├── tests/                       # 31 个测试文件
├── workspace/                   # 运行期产物（uploads / reports / api_cases）
├── MANUAL.md                    # 完整操作手册（每个工具的使用细节）
├── packages.txt                 # Cloud 系统依赖
└── requirements.txt
```

## 测试

```bash
pytest                            # 跑全部
pytest tests/test_data_generator.py -v    # 跑单个模块
```

`tests/` 下 31 个文件，覆盖核心逻辑（数据生成、接口核心、安全工具、禅道导出）和页面冒烟（各工具页面能否正常渲染、工具路由是否可达）。

## 文档

| 文档 | 内容 |
| --- | --- |
| [MANUAL.md](MANUAL.md) | 完整操作手册，逐工具讲清输入、输出、注意事项和典型流程 |
| [DEPLOY_STREAMLIT_COMMUNITY_CLOUD.md](DEPLOY_STREAMLIT_COMMUNITY_CLOUD.md) | Cloud 部署步骤、后台填写模板、故障排查 |
| 本 README | 快速了解项目全貌和上手方式 |

日常使用建议直接看 MANUAL，这份 README 只负责让你在 3 分钟内知道它能干什么。

## 注意事项

- **安全测试模块是基线自查工具，不是攻击平台。** 只对已授权目标使用，别直接对着生产环境跑。自动化扫描替代不了人工安全测试。
- **AI 生成的用例需要人工复核。** 模型给的是初稿，业务规则和边界条件还是要自己过一遍。
- **Streamlit 页面里压测别一上来就开大并发。** 先用小规模确认脚本和断言正常，再放大线程数；长链路优先看事务级统计。
- **禅道绩效统计建议先在数据库备份或影子库验证**，统计口径建议结合项目背景解读。
- 仓库目前未声明开源协议，如需商用请先联系作者。

## 已知可以更好的地方

- 页面逻辑还有一部分集中在 `src/qa_toolkit/streamlit_app.py`，后续可以继续往 `ui/pages/` 拆
- `.npm-cache/` 目录曾被误提交（294 个文件），不影响运行，但会让仓库变大，后续会清理
- 部分工具的错误提示还比较粗，遇到问题欢迎提 issue 带上复现步骤

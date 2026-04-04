# QA Toolkit

面向测试工程师的综合工具平台，基于 Streamlit 构建，覆盖测试数据生成、测试用例生成、接口研发辅助、接口自动化、接口性能、接口安全、文本与图片处理、日志分析、禅道绩效统计等场景。

这个 README 不只介绍怎么启动项目，也作为项目的操作手册和使用说明。

## 如何阅读本文档

如果你是日常使用者，优先阅读下面这些部分：

- `第一部分：使用者操作手册`
- `1. 项目定位`
- `2. 适用场景`
- `3. 能力总览`
- `4. 快速开始`
- `5. 页面导航与通用使用方式`
- `6. 重点工具操作手册`
- `7. 典型工作流`

如果你是项目维护者或部署负责人，优先阅读下面这些部分：

- `第二部分：维护者指南`
- `8. 开发环境与项目结构`
- `9. 部署与运行说明`
- `10. 运行产物与示例资源`
- `11. 开发与维护建议`
- `12. 发布前检查清单`

## 第一部分：使用者操作手册

## 1. 项目定位

- 主应用：一个本地可运行、也可部署到 Streamlit Cloud 的测试工程工具平台
- 核心目标：把测试设计、联调准备、回归支持、基线检查和常用效率工具放到一个入口里
- 适用人群：测试工程师、测试开发、接口联调人员、质量负责人、部分研发同学

## 2. 适用场景

- 需要快速造测试数据，支持联调、导入、回归、边界值设计
- 需要根据需求文档、截图、原型图快速生成测试用例
- 需要对接口文档做标准化、变更分析、Mock、断言模板和调试代码生成
- 需要把接口文档转成自动化测试脚本并执行
- 需要对接口做压测、安全基线检查、移动包静态扫描或 Web 轻量扫描
- 需要处理文本、正则、JSON、时间、图片、加密、IP/域名、日志等日常测试工作

## 3. 能力总览

| 模块 | 主要用途 | 典型输出 |
|---|---|---|
| 数据生成工具 | 造随机值、结构化场景数据、边界值/异常值 | 文本、CSV、JSON |
| 测试用例生成器 | 基于需求文本或截图生成测试用例 | Excel、CSV、Markdown、JSON |
| 接口研发辅助 | 文档标准化、变更分析、Mock、断言、调试代码 | JSON、Markdown、Mock 脚本、代码片段 |
| 接口自动化测试 | 解析接口文档、生成并执行自动化测试 | 测试脚本、HTML 报告 |
| 接口性能测试 | JMeter 风格接口压测、参数化和事务链路 | HTML、JSON、CSV 报告 |
| 接口安全测试 | API 安全基线、APK/IPA/APPX 静态扫描、MobSF 静态/动态集成、Web 基线扫描 | Markdown、JSON、CSV、PDF 报告 |
| 禅道绩效统计 | 测试/开发绩效统计、超时响应分析 | Excel、CSV |
| 通用效率工具 | 文本、JSON、正则、时间、图片、加密、IP、日志、BI | 对应格式结果或下载文件 |

## 4. 快速开始

### 4.1 环境要求

- 建议 Python 3.9 及以上
- 建议使用虚拟环境
- 若需 OCR，需安装系统级 `tesseract`

### 4.2 安装 Python 依赖

```bash
python -m pip install -r requirements.txt
```

### 4.3 启动主工具平台

```bash
streamlit run streamlit_app.py
```

默认会在本机打开一个本地地址，通常是 `http://localhost:8501`。

### 4.4 运行测试

```bash
pytest tests/test_application_security_tool.py
```

如果你补充了新的单测，也可以按文件维度执行，例如：

```bash
pytest tests/test_data_generator.py
pytest tests/test_test_case_generator.py
```

## 5. 页面导航与通用使用方式

启动后，页面会展示工具切换区。推荐按下面的方式使用：

1. 先选择工具分类
2. 按页面提示输入文本、上传文件或配置参数
3. 先预览分析结果，再执行生成、扫描、导出或测试
4. 结果优先下载到本地归档，必要时保留 `workspace/` 产物

通用交互特点：

- 多数工具支持复制结果和下载文件
- 结构化结果通常支持表格预览
- 复杂工具会保留历史记录或上次生成结果
- 上传文件默认会放到 `workspace/uploads/`

## 6. 重点工具操作手册

### 6.1 数据生成工具

适用场景：

- 注册账号、员工信息、订单支付、收货地址等联调造数
- 随机字符串、密码、邮箱、手机号、身份证等单字段造数
- 表单校验、接口校验所需的边界值和异常值设计

主要功能：

- Faker 高级生成器：人物、地址、网络、公司、日期、文本等真实感数据
- 基础随机生成器：字符串、数字、密码、UUID、邮箱、电话、地址、身份证
- 测试场景造数：按业务场景生成结构化数据集
- 边界值/异常值生成器：按字段生成正常值、边界值和异常值

推荐使用流程：

1. 若只是联调单个字段，直接用基础生成器
2. 若要批量导入或联调整组数据，优先用“测试场景造数”
3. 若在做测试设计，优先用“边界值/异常值生成器”
4. 结果优先下载 CSV 或 JSON，便于复用

实用建议：

- 批次标识建议写清楚，例如 `qa0410`、`regression_v2`
- 随机种子建议在回归场景填写，这样同参数可复现同一批数据
- 结构化数据更适合接口联调、导入测试和数据准备，不建议只复制纯文本

### 6.2 测试用例生成器

适用场景：

- 根据需求文档、验收标准、原型图、聊天截图快速生成测试用例
- 为迭代回归、新功能测试、测试评审提供初版用例
- 为新人提供标准化测试用例模板

主要功能：

- 支持多模型：阿里通义千问、OpenAI、百度文心一言、讯飞星火、智谱 ChatGLM
- 支持三种需求输入方式：手动输入、图片 OCR、结构化补充
- 支持需求分析助手：自动提取功能点、业务规则、建议覆盖维度、待确认项
- 支持设置目标用例数、输出语言、测试风格和覆盖维度
- 支持结果筛选、逐条查看和多格式导出

推荐使用流程：

1. 先在“手动输入”里录入主要需求
2. 若需求来自截图或原型图，再在“图片 OCR 识别”里补充
3. 在“结构化补充”里明确模块、业务规则、验收标准和不覆盖范围
4. 看“需求分析助手”给出的建议覆盖维度和待确认项
5. 选择模型、风格、语言和目标用例数后生成
6. 先筛选查看，再导出 Excel/CSV/Markdown/JSON

使用建议：

- 复杂需求不要只贴一段大文本，最好拆出“业务规则”和“验收标准”
- OCR 更适合提取标题、规则、表单说明，不适合完全替代人工整理
- 生成结果建议作为初稿，正式评审前仍要人工补充和修正

### 6.3 接口研发辅助

适用场景：

- 新版本接口文档回归前检查
- 前后端联调前做 Mock、调试代码和接口体检
- 两份接口文档之间做变更分析

主要功能：

- 文档标准化导出
- 接口变更分析
- 回归清单生成
- 接口文档体检
- 断言模板生成
- Mock 服务生成
- 调试代码片段生成

推荐使用流程：

1. 先导入接口文档
2. 先做标准化导出和接口体检
3. 如有版本对比，再做变更分析
4. 按需要生成回归清单、断言模板、Mock 或调试代码

更适合的使用顺序：

- 接口文档很乱：先标准化
- 准备联调：先 Mock，再生成调试代码
- 准备回归：先变更分析，再看回归清单
- 准备自动化：先体检，再生成断言模板

### 6.4 接口自动化测试

适用场景：

- 根据 Excel、JSON、文本、Swagger 等接口定义快速生成自动化测试
- 快速验证接口基础可用性、状态码、返回结构和简单断言
- 沉淀基础接口回归能力

主要功能：

- 解析接口文档
- 自动生成测试脚本
- 支持 pytest / unittest / requests 脚本模式
- 执行自动化测试
- 生成 HTML 报告

推荐使用流程：

1. 导入接口文档或使用示例数据
2. 配置基础 URL、请求方式和参数格式
3. 生成自动化用例脚本
4. 执行测试
5. 下载或查看 HTML 报告

使用建议：

- 导入前先用“接口研发辅助”做一次体检，能减少坏文档带来的问题
- 基础 URL 建议优先使用测试环境或预发环境
- 如果文档不完整，先补充期望状态码和响应示例

### 6.5 接口性能测试

适用场景：

- 做轻量接口压测、基准测试、事务链路测试
- 用 CSV 参数化压测账号、Token、订单号等不同数据
- 观察吞吐量、响应时间和错误率

主要功能：

- Thread Group：并发用户、Ramp-Up、循环、时长
- HTTP Sampler：多接口顺序执行
- Assertions：状态码、响应内容、最大响应时间
- Timer：固定等待和随机抖动
- CSV 参数化
- Transaction Controller：链路级聚合
- 报告导出：HTML、JSON、CSV

推荐使用流程：

1. 导入接口定义，选择参与压测的接口
2. 设置并发、持续时间和断言
3. 如需参数化，上传 CSV
4. 如需链路统计，配置事务控制器
5. 先小规模试跑，再扩大规模

使用建议：

- 在 Streamlit 页面里执行压测时，不建议一上来就跑超大规模并发
- 先用少量并发确认脚本和断言是否正常，再扩大线程数
- 对于长链路，优先看事务级统计而不是只看单接口

### 6.6 接口安全测试

适用场景：

- 接口上线前做安全基线自查
- 对 APK/IPA/APPX 做静态安全预检
- 通过 MobSF 官方能力补强移动端静态分析、动态报告拉取与测试视角整理
- 对 Web 站点做轻量头部和暴露面扫描

主要功能：

- API 文档安全方案与基线检查
- APK / IPA / APPX 静态扫描
- MobSF 官方静态/动态集成、一次性预配置、连通性检查、结果回填、一键拉报告与二次整理
- Web 站点轻量扫描
- OWASP API Top 10 清单
- 权限矩阵
- Nuclei 模板导出
- 安全回归套件和报告

推荐使用流程：

1. 导入接口文档，确认测试范围和 Base URL
2. 做 API 基线检查
3. 如有移动端包，先上传 APK / IPA / APPX 做本地静态扫描
4. 如需更完整能力，配置 MobSF 地址和 API Key，执行官方静态分析、动态报告拉取和测试视角二次整理
5. 如有 Web 入口，补一轮站点基线扫描
6. 最后导出报告或回归清单

注意事项：

- 当前更偏向“安全基线”和“低风险检查”，不是主动攻击平台
- 适合已授权目标，不建议拿来直接打生产环境
- 自动化发现不能替代人工安全测试
- MobSF 动态分析需要其自身侧准备设备、模拟器、Frida 或 Corellium 等环境
- 部署到 Streamlit Community Cloud 时，MobSF 建议改为“远程服务模式”，通过 `st.secrets` 或环境变量提供 `base_url/api_key`
- Streamlit Community Cloud 不提供本机 Docker、ADB、Frida、Android 模拟器，因此不能在云端直接启动本地 MobSF 或 Android 动态环境

### 6.7 禅道绩效统计

适用场景：

- 按月、季度统计测试和开发的缺陷处理绩效
- 统计超时响应率和超时明细
- 生成 Excel / CSV 绩效报表

推荐使用流程：

1. 配置禅道数据库连接
2. 选择产品、时间范围、统计维度
3. 设置超时规则和排除缺陷类型
4. 生成统计报告
5. 按成员查看超时明细

使用建议：

- 建议先在数据库备份或影子环境验证
- 月度和季度是更适合的统计粒度
- 统计结果建议结合项目背景解读，不建议脱离上下文单独评价

### 6.8 通用效率工具

这些工具适合日常测试和联调工作中的高频小任务：

- 文本对比工具：对比两版文本、配置、接口返回
- 字数统计工具：统计字符、单词、段落、频率
- 正则测试工具：调试表达式、替换规则、生成语言示例
- JSON 处理工具：格式化、校验、对比、解析
- 时间处理工具：时间转换、区间计算、日期辅助
- 图片处理工具：格式转换、尺寸调整、裁剪、旋转、水印
- IP/域名查询工具：解析 IP、域名、URL、批量查询
- 加密/解密工具：Base64、MD5、SHA、RSA、URL/HTML/Unicode/Hex
- 日志分析工具：日志级别统计、模式识别、结构提取
- BI 数据分析工具：面向数据分析类测试和可视化辅助

## 7. 典型工作流

### 7.1 需求截图转测试用例

1. 打开“测试用例生成器”
2. 上传需求截图或原型图
3. 用 OCR 提取文本
4. 在结构化补充里补业务规则和验收标准
5. 看需求分析助手
6. 生成并导出测试用例

### 7.2 接口文档转自动化回归

1. 打开“接口研发辅助”
2. 先做文档标准化和接口体检
3. 必要时做版本变更分析
4. 打开“接口自动化测试”
5. 导入接口文档并生成脚本
6. 执行测试并查看 HTML 报告

### 7.3 联调前准备

1. 打开“数据生成工具”造联调数据
2. 打开“接口研发辅助”生成 Mock 和调试代码
3. 用“JSON 处理工具”或“加密/解密工具”处理请求参数

### 7.4 上线前基线检查

1. 先用“接口安全测试”做 API 基线
2. 如有 Web 入口，补 Web 扫描
3. 如有移动端安装包，做 APK / IPA 静态扫描
4. 对关键接口做轻量性能验证

## 第二部分：维护者指南

## 8. 开发环境与项目结构

```text
.
├── assets/                     # 静态资源、字体、内置工具
│   ├── bin/
│   ├── fonts/
│   └── images/
├── examples/                   # 示例输入与样例文件
│   ├── api_cases/
│   ├── interface_documents/
│   └── screenshots/
├── src/
│   └── qa_toolkit/
│       ├── config/             # 常量、配置、样例文案
│       ├── core/               # 接口自动化、性能、安全等核心能力
│       ├── integrations/       # 外部系统集成
│       ├── reporting/          # 报告生成与执行封装
│       ├── support/            # 页面内置文档说明
│       ├── tools/              # 数据生成、测试用例等工具模块
│       ├── ui/                 # 页面和组件
│       ├── utils/              # 日志、时间、图片、JSON 等通用工具
│       ├── paths.py            # 路径常量
│       └── streamlit_app.py    # 主应用入口模块
├── tests/                      # 自动化测试
├── workspace/                  # 运行期产物目录
│   ├── api_cases/
│   ├── reports/
│   └── uploads/
├── packages.txt                # Streamlit Cloud 系统依赖
├── requirements.txt            # Python 依赖
└── streamlit_app.py            # 根目录启动入口
```

## 9. 部署与运行说明

本节更适合项目维护者、部署负责人和需要排查环境问题的同学。

### 9.1 本地开发运行

- 安装 Python 依赖：`python -m pip install -r requirements.txt`
- 启动项目：`streamlit run streamlit_app.py`
- 若需 OCR，需额外安装系统级 `tesseract`

### 9.2 OCR 与 Streamlit Cloud 部署

测试用例生成器支持图片 OCR 识别需求，运行时依赖系统级 `tesseract`。

本地运行：

- 先安装 Python 依赖：`python -m pip install -r requirements.txt`
- 再安装系统级 `tesseract`
- macOS 可用 Homebrew：

```bash
brew install tesseract tesseract-lang
```

Streamlit Cloud 部署：

- 如果你只想看最短上线步骤，直接看 `DEPLOY_STREAMLIT_COMMUNITY_CLOUD.md`
- 如果你准备现在就发布，优先看其中的“上线前最后检查清单”和“Cloud 后台填写模板”
- 如果已经上线但遇到问题，直接看其中的“故障排查速查表”

- 根目录的 `packages.txt` 已声明系统依赖：
  - `tesseract-ocr`
  - `tesseract-ocr-chi-sim`
  - `poppler-utils`
  - `libgl1`
  - `libglib2.0-0`
- Streamlit Cloud 构建时会按 `packages.txt` 安装 Linux 系统依赖
- 更新依赖后建议重新部署或手动 `Reboot app`
- 根目录的 `.streamlit/config.toml` 已设置上传和消息体大小为 `200MB`
- 如需在 Cloud 中使用 MobSF，建议在应用 Secrets 中配置：

```toml
[mobsf]
base_url = "https://your-mobsf.example.com"
api_key = "replace-with-your-mobsf-api-key"
timeout_seconds = 180
verify_ssl = true
include_pdf = false
```

- 仓库提供示例文件：`.streamlit/secrets.toml.example`
- Community Cloud 中本地文件系统是临时的，`workspace/mobsf_profile.local.json` 只适合本机，不适合当长期云端配置

推荐配置：

- Repository：当前仓库
- Branch：稳定分支，如 `main`
- Main file path：`streamlit_app.py`
- Python version：`3.12`
- Python dependencies：`requirements.txt`
- System dependencies：`packages.txt`

推荐保留的根目录结构：

```text
.
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── packages.txt
├── requirements.txt
├── streamlit_app.py
├── src/
├── assets/
└── workspace/
```

### 9.3 兼容性说明

- `assets/bin/tesseract` 仅作为本地资源兜底，不应依赖它做云端跨平台部署
- Linux 部署环境会优先使用系统安装的 `tesseract`
- 如果页面提示 OCR 不可用，优先检查系统是否安装了 `tesseract`

### 9.4 常见问题排查

- 报错 `Exec format error`
  - 原因：运行了不匹配当前平台架构的 `tesseract`
  - 处理：不要依赖仓库里的 `assets/bin/tesseract`，云端通过 `packages.txt` 安装系统版

- 报错 `OCR 不可用，请确认 pytesseract 和 tesseract 已正确安装`
  - 原因：系统里没有可执行的 `tesseract`，或 Python 环境里缺少 `pytesseract`
  - 处理：先确认 `tesseract --version` 能执行；本项目即使没有 `pytesseract`，只要系统 `tesseract` 可用也能工作

- 报错 `Failed loading language 'chi_sim'`
  - 原因：缺少简体中文语言包
  - 处理：本地安装 `tesseract-lang`；云端保证 `packages.txt` 包含 `tesseract-ocr-chi-sim`

- 页面显示 OCR 可用，但识别结果为空
  - 原因：截图分辨率低、背景干扰大、对比度不足
  - 处理：优先尝试“增强文本 / 高对比度 / 黑白文档”预处理模式，并尽量上传清晰截图

- 本地正常、云端失败
  - 原因：本地依赖的是 macOS/Homebrew，云端是 Linux 系统依赖
  - 处理：检查 `packages.txt` 是否已提交、云端是否完成新一轮构建

## 10. 运行产物与示例资源

- `workspace/uploads/`：页面上传文件暂存目录
- `workspace/api_cases/`：接口自动化生成的脚本与清单
- `workspace/reports/`：测试报告、执行结果、导出文件

建议：

- 可以保留目录结构，但不要把运行产物长期提交到仓库
- 对需要归档的结果，建议导出到独立归档目录或对象存储

### 10.1 示例资源说明

- `examples/interface_documents/`：接口文档模板和示例输入
- `examples/api_cases/`：接口测试清单与示例执行脚本
- `examples/screenshots/`：历史输出或截图样例

适合的使用方式：

- 第一次接触工具时，先用示例跑通完整流程
- 确认格式后，再替换成自己的真实文档或数据

## 11. 开发与维护建议

- 页面逻辑目前仍有一部分集中在 `src/qa_toolkit/streamlit_app.py`，后续可持续拆分到 `ui/pages/`
- 新工具优先放到 `src/qa_toolkit/tools/` 或 `src/qa_toolkit/core/`，不要直接堆到根目录
- 页面新功能如果有稳定说明，建议同步写入 `src/qa_toolkit/support/documentation.py`
- 涉及核心逻辑的改动，建议补 `tests/` 下对应单测
- 运行产物统一落到 `workspace/`，避免源码目录被污染

## 12. 发布前检查清单

### 12.1 部署前自检

- 确认根目录已提交 `packages.txt`
- 确认 `requirements.txt` 已包含运行所需依赖
- 确认 `streamlit_app.py` 位于仓库根目录
- 确认 `src/`、`assets/` 已完整提交
- 本地先执行 `tesseract --version`
- 本地启动后，确认“测试用例生成器”页面提示 `OCR 已就绪`
- 本地至少做一次 OCR 冒烟
- 云端发布后，验证截图上传、OCR、需求追加、测试用例生成链路

### 12.2 发布提交清单

建议至少确认以下文件已提交：

- `streamlit_app.py`
- `requirements.txt`
- `packages.txt`
- `src/qa_toolkit/streamlit_app.py`
- `src/qa_toolkit/tools/test_case_generator.py`
- `src/qa_toolkit/tools/data_generator.py`
- `src/qa_toolkit/support/documentation.py`

如果本次改动涉及 OCR、图片处理或字体显示，再额外确认：

- `assets/bin/tesseract` 仅作为本地资源保留，不作为云端依赖
- `assets/fonts/` 下的字体资源路径没有被改坏
- 新增系统依赖是否同步到了 `packages.txt`

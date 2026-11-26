# QA Toolkit 全功能测试审计报告

对 qa-toolkit 的 15 个工具页面 + 核心模块 + 工具函数做了全面测试审计，
共记录 **100 个 issue** 并真实提交到 GitHub Issues（#1–#100）。

## 统计

| 严重程度 | 数量 |
| --- | --- |
| critical | 13 |
| high | 1 |
| major | 42 |
| medium | 15 |
| minor | 21 |
| low | 8 |

## Issue 清单

| # | GitHub | 严重程度 | 类型 | 标题 | 位置 |
| --- | --- | --- | --- | --- | --- |
| 021 | [#21](https://github.com/LUCAS-LYX025/qa-toolkit/issues/21) | critical | 代码注入/RCE | 生成脚本用 r''' 内嵌 JSON，数据中的三单引号可逃逸为任意 Python 代码 | `src/qa_toolkit/core/api_test_core.py:1288` |
| 055 | [#55](https://github.com/LUCAS-LYX025/qa-toolkit/issues/55) | critical | StreamlitAPIException | 重置视图按钮在 widget 实例化后回写 session_state key | `src/qa_toolkit/ui/pages/api_performance_page.py:677` |
| 056 | [#56](https://github.com/LUCAS-LYX025/qa-toolkit/issues/56) | critical | StreamlitAPIException | 分页导航按钮回写已实例化的页码 number_input | `src/qa_toolkit/ui/pages/api_performance_page.py:830` |
| 057 | [#57](https://github.com/LUCAS-LYX025/qa-toolkit/issues/57) | critical | StreamlitAPIException | Reset Filter 按钮回写已实例化的搜索框和复选框 | `src/qa_toolkit/ui/pages/api_performance_page.py:1448` |
| 059 | [#59](https://github.com/LUCAS-LYX025/qa-toolkit/issues/59) | critical | StreamlitAPIException | 清空安全工作台按钮覆盖已绑定的顶层 tab radio 状态 | `src/qa_toolkit/ui/pages/api_security_page.py:663` |
| 060 | [#60](https://github.com/LUCAS-LYX025/qa-toolkit/issues/60) | critical | StreamlitAPIException | 填充多角色示例按钮回写已实例化的 text_area | `src/qa_toolkit/ui/pages/api_security_page.py:831` |
| 061 | [#61](https://github.com/LUCAS-LYX025/qa-toolkit/issues/61) | critical | StreamlitAPIException | Android 动态报告拉取回写已实例化的 Hash 输入框 | `src/qa_toolkit/ui/pages/api_security_page.py:1692` |
| 076 | [#76](https://github.com/LUCAS-LYX025/qa-toolkit/issues/76) | critical | StreamlitAPIException | 点击回填清洗结果页面直接崩溃 | `src/qa_toolkit/ui/pages/word_counter_page.py:289` |
| 077 | [#77](https://github.com/LUCAS-LYX025/qa-toolkit/issues/77) | critical | StreamlitAPIException | 批量转换页填入示例数据按钮崩溃 | `src/qa_toolkit/ui/pages/time_processor_page.py:269` |
| 078 | [#78](https://github.com/LUCAS-LYX025/qa-toolkit/issues/78) | critical | StreamlitAPIException | 批量转换页清空批量输入按钮崩溃 | `src/qa_toolkit/ui/pages/time_processor_page.py:271` |
| 079 | [#79](https://github.com/LUCAS-LYX025/qa-toolkit/issues/79) | critical | StreamlitAPIException | 最近生成记录回填结果必然崩溃 | `src/qa_toolkit/ui/pages/test_case_generator_page.py:945` |
| 080 | [#80](https://github.com/LUCAS-LYX025/qa-toolkit/issues/80) | critical | KeyError | 切换目标语言后生成代码抛 KeyError | `src/qa_toolkit/ui/pages/regex_tester_page.py:673` |
| 095 | [#95](https://github.com/LUCAS-LYX025/qa-toolkit/issues/95) | critical | StreamlitAPIException | 环境配置面板保存当前按钮回写已实例化的 widget key | `src/qa_toolkit/ui/components/env_profile_panel.py:136` |
| 031 | [#31](https://github.com/LUCAS-LYX025/qa-toolkit/issues/31) | high | 依赖缺失 | 硬依赖 pytz 未在 requirements.txt 声明 | `requirements.txt:1` |
| 001 | [#1](https://github.com/LUCAS-LYX025/qa-toolkit/issues/1) | major | 参数探测 | _invoke_executor 对仅含 **kwargs 的 executor 传参错误 | `src/qa_toolkit/core/task_runner.py:222` |
| 002 | [#2](https://github.com/LUCAS-LYX025/qa-toolkit/issues/2) | major | 状态管理竞态 | cancel 后 mark_success 覆盖取消状态，任务误报成功 | `src/qa_toolkit/core/task_runner.py:176` |
| 004 | [#4](https://github.com/LUCAS-LYX025/qa-toolkit/issues/4) | major | 逻辑分支错误 | clear_active(namespace) 对具体命名空间无效 | `src/qa_toolkit/core/env_profile_manager.py:388` |
| 005 | [#5](https://github.com/LUCAS-LYX025/qa-toolkit/issues/5) | major | 数据丢失 | Fernet 密钥更换后 upsert 静默永久丢失加密凭据 | `src/qa_toolkit/core/env_profile_manager.py:350` |
| 006 | [#6](https://github.com/LUCAS-LYX025/qa-toolkit/issues/6) | major | 逻辑分支错误 | compare_interfaces 按 method+path 建索引致同名接口被静默覆盖 | `src/qa_toolkit/core/api_dev_tools.py:23` |
| 007 | [#7](https://github.com/LUCAS-LYX025/qa-toolkit/issues/7) | major | URL 处理 | _build_full_url 用 dict(parse_qsl) 丢失重复查询参数 | `src/qa_toolkit/core/api_dev_tools.py:1114` |
| 008 | [#8](https://github.com/LUCAS-LYX025/qa-toolkit/issues/8) | major | 命令注入 | _render_curl_snippet 生成的 curl 命令存在 shell 注入 | `src/qa_toolkit/core/api_dev_tools.py:1220` |
| 011 | [#11](https://github.com/LUCAS-LYX025/qa-toolkit/issues/11) | major | URL 处理 | _build_full_url 丢失重复查询参数 | `src/qa_toolkit/core/api_performance_tool.py:851` |
| 012 | [#12](https://github.com/LUCAS-LYX025/qa-toolkit/issues/12) | major | 逻辑分支错误 | _substitute_variables 单次替换依赖字典插入顺序 | `src/qa_toolkit/core/api_performance_tool.py:989` |
| 013 | [#13](https://github.com/LUCAS-LYX025/qa-toolkit/issues/13) | major | 资源耗尽 | 虚拟用户数无上限可创建十万线程致崩溃 | `src/qa_toolkit/core/api_performance_tool.py:172` |
| 014 | [#14](https://github.com/LUCAS-LYX025/qa-toolkit/issues/14) | major | 数据校验 | expected_status 裸 int() 转换非数字直接崩溃 | `src/qa_toolkit/core/api_security_tool.py:1062` |
| 015 | [#15](https://github.com/LUCAS-LYX025/qa-toolkit/issues/15) | major | 资源泄露 | run_baseline_probe 创建的 requests.Session 从未关闭 | `src/qa_toolkit/core/api_security_tool.py:338` |
| 016 | [#16](https://github.com/LUCAS-LYX025/qa-toolkit/issues/16) | major | 数据校验 | json.dumps 对不可序列化对象抛 TypeError | `src/qa_toolkit/core/api_security_tool.py:1141` |
| 017 | [#17](https://github.com/LUCAS-LYX025/qa-toolkit/issues/17) | major | URL 处理 | _build_full_url 丢失重复查询参数 | `src/qa_toolkit/core/api_security_tool.py:1085` |
| 022 | [#22](https://github.com/LUCAS-LYX025/qa-toolkit/issues/22) | major | XSS | HTML 报告未转义接口名/路径/framework | `src/qa_toolkit/core/api_test_core.py:1731` |
| 023 | [#23](https://github.com/LUCAS-LYX025/qa-toolkit/issues/23) | major | 健壮性 | subprocess.run 执行生成测试无 timeout | `src/qa_toolkit/core/api_test_core.py:1582` |
| 026 | [#26](https://github.com/LUCAS-LYX025/qa-toolkit/issues/26) | major | URL 处理 | Postman query 值未 URL 编码 | `src/qa_toolkit/core/api_test_core.py:2215` |
| 027 | [#27](https://github.com/LUCAS-LYX025/qa-toolkit/issues/27) | major | 资源泄露 | scan_web_target 的 requests.Session 从未关闭 | `src/qa_toolkit/core/application_security_tool.py:432` |
| 028 | [#28](https://github.com/LUCAS-LYX025/qa-toolkit/issues/28) | major | 正则错误 | UTF-16LE 提取正则写成 '\\x00' 永远匹配不到 NUL | `src/qa_toolkit/core/application_security_tool.py:2921` |
| 029 | [#29](https://github.com/LUCAS-LYX025/qa-toolkit/issues/29) | major | 边界条件 | _parse_axml_events 无长度校验，畸形 Manifest 触发 struct.error | `src/qa_toolkit/core/application_security_tool.py:2761` |
| 030 | [#30](https://github.com/LUCAS-LYX025/qa-toolkit/issues/30) | major | 边界条件 | _inspect_tls_certificate 非法端口抛 ValueError 致整站扫描失败 | `src/qa_toolkit/core/application_security_tool.py:3272` |
| 058 | [#58](https://github.com/LUCAS-LYX025/qa-toolkit/issues/58) | major | StreamlitAPIException | 自定义列取消全部勾选回写已实例化的 multiselect | `src/qa_toolkit/ui/pages/api_performance_page.py:674` |
| 062 | [#62](https://github.com/LUCAS-LYX025/qa-toolkit/issues/62) | major | 边界值崩溃 | 比例裁剪默认参数下 slider min==max 抛异常 | `src/qa_toolkit/ui/pages/image_processor_page.py:628` |
| 063 | [#63](https://github.com/LUCAS-LYX025/qa-toolkit/issues/63) | major | 边界值崩溃 | 自由裁剪拖动左边距到最大后右边距 slider 区间为空 | `src/qa_toolkit/ui/pages/image_processor_page.py:596` |
| 064 | [#64](https://github.com/LUCAS-LYX025/qa-toolkit/issues/64) | major | 查询结果未校验 | 环境配置 JSON 合法但非对象时 AttributeError 未捕获 | `src/qa_toolkit/ui/pages/api_automation_page.py:962` |
| 065 | [#65](https://github.com/LUCAS-LYX025/qa-toolkit/issues/65) | major | 缓存键冲突 | 上传文档缓存仅用文件名+大小判重 | `src/qa_toolkit/ui/pages/api_automation_page.py:690` |
| 066 | [#66](https://github.com/LUCAS-LYX025/qa-toolkit/issues/66) | major | 状态一致性 | 执行测试前未校验生成产物与当前接口清单一致 | `src/qa_toolkit/ui/pages/api_automation_page.py:1063` |
| 067 | [#67](https://github.com/LUCAS-LYX025/qa-toolkit/issues/67) | major | 脚本生成错误 | hash() 为负时复制按钮 JS 函数名非法 | `src/qa_toolkit/ui/pages/api_dev_tools_page.py:108` |
| 070 | [#70](https://github.com/LUCAS-LYX025/qa-toolkit/issues/70) | major | 按钮回调逻辑错误 | 鉴权头非法时 st.stop() 终止整个页面 | `src/qa_toolkit/ui/pages/api_security_page.py:898` |
| 072 | [#72](https://github.com/LUCAS-LYX025/qa-toolkit/issues/72) | major | 编码异常静默吞掉 | CSV 参数化数据用 errors=ignore 解码致非 UTF-8 内容丢失 | `src/qa_toolkit/ui/pages/api_performance_page.py:1104` |
| 075 | [#75](https://github.com/LUCAS-LYX025/qa-toolkit/issues/75) | major | 文件上传边界 | 上传文件名未净化直接拼接落盘路径 | `src/qa_toolkit/ui/pages/api_automation_page.py:694` |
| 081 | [#81](https://github.com/LUCAS-LYX025/qa-toolkit/issues/81) | major | re.error | 汇总/明细搜索框输入正则元字符导致页面崩溃 | `src/qa_toolkit/ui/pages/zentao_performance_page.py:454` |
| 082 | [#82](https://github.com/LUCAS-LYX025/qa-toolkit/issues/82) | major | None 输入异常 | 清空开始/结束日期后日期计算 Tab 崩溃 | `src/qa_toolkit/ui/pages/time_processor_page.py:350` |
| 083 | [#83](https://github.com/LUCAS-LYX025/qa-toolkit/issues/83) | major | None 输入异常 | 时间戳转换页清空日期后点击转换崩溃 | `src/qa_toolkit/ui/pages/time_processor_page.py:226` |
| 084 | [#84](https://github.com/LUCAS-LYX025/qa-toolkit/issues/84) | major | None 输入异常 | 禅道页清空日期后校验与区间统计崩溃 | `src/qa_toolkit/ui/pages/zentao_performance_page.py:269` |
| 085 | [#85](https://github.com/LUCAS-LYX025/qa-toolkit/issues/85) | major | 性能/大文件 | 文本比较大文件每次 rerun 全量 O(n^2) diff 卡死 | `src/qa_toolkit/ui/pages/text_comparison_page.py:347` |
| 086 | [#86](https://github.com/LUCAS-LYX025/qa-toolkit/issues/86) | major | ReDoS | 灾难性回溯表达式可挂死整个应用 | `src/qa_toolkit/ui/pages/regex_tester_page.py:494` |
| 087 | [#87](https://github.com/LUCAS-LYX025/qa-toolkit/issues/87) | major | 逻辑错误 | 12 位毫秒时间戳被误判为秒致转换失败 | `src/qa_toolkit/ui/pages/time_processor_page.py:115` |
| 088 | [#88](https://github.com/LUCAS-LYX025/qa-toolkit/issues/88) | major | 时区/DST | 纽约夏令时跳变时刻被 localize 成不存在的时间 | `src/qa_toolkit/ui/pages/time_processor_page.py:227` |
| 089 | [#89](https://github.com/LUCAS-LYX025/qa-toolkit/issues/89) | major | 配置类型校验 | 端口/超时环境变量非数字导致页面无法加载 | `src/qa_toolkit/ui/pages/zentao_performance_page.py:145` |
| 090 | [#90](https://github.com/LUCAS-LYX025/qa-toolkit/issues/90) | major | 资源耗尽 | 压测时间戳生成数量无上限可耗尽内存 | `src/qa_toolkit/ui/pages/time_processor_page.py:479` |
| 091 | [#91](https://github.com/LUCAS-LYX025/qa-toolkit/issues/91) | major | 日期越界 | 超大月偏移导致日期溢出崩溃 | `src/qa_toolkit/ui/pages/time_processor_page.py:386` |
| 032 | [#32](https://github.com/LUCAS-LYX025/qa-toolkit/issues/32) | medium | 注入风险 | create_copy_button 未转义 button_text 直接拼进 JS/HTML | `src/qa_toolkit/streamlit_app.py:259` |
| 033 | [#33](https://github.com/LUCAS-LYX025/qa-toolkit/issues/33) | medium | HTML 转义不一致 | 三个渲染函数未做 HTML 转义 | `src/qa_toolkit/ui/components/tool_page_shell.py:158` |
| 034 | [#34](https://github.com/LUCAS-LYX025/qa-toolkit/issues/34) | medium | 类型异常 | 测试报告 response_time 非数值导致格式化崩溃 | `src/qa_toolkit/reporting/report_generator.py:878` |
| 035 | [#35](https://github.com/LUCAS-LYX025/qa-toolkit/issues/35) | medium | 输入校验 | add_feedback 对 rating/类型字段无校验 | `src/qa_toolkit/support/feedback_store.py:50` |
| 036 | [#36](https://github.com/LUCAS-LYX025/qa-toolkit/issues/36) | medium | 静默失败 | add_watermark 无测试且异常静默吞掉 | `src/qa_toolkit/utils/image_processing.py:358` |
| 037 | [#37](https://github.com/LUCAS-LYX025/qa-toolkit/issues/37) | medium | 边界场景 | convert_to_target_filesize 未覆盖不可行/零目标体积 | `src/qa_toolkit/utils/image_processing.py:145` |
| 038 | [#38](https://github.com/LUCAS-LYX025/qa-toolkit/issues/38) | medium | 递归风险 | compare_json/count_keys/get_json_depth 无循环引用与深嵌套防护 | `src/qa_toolkit/utils/json_utils.py:52` |
| 041 | [#41](https://github.com/LUCAS-LYX025/qa-toolkit/issues/41) | medium | 边界场景 | _percentile 与 _to_int/_to_float 边界未校验 | `src/qa_toolkit/core/api_performance_tool.py:1000` |
| 042 | [#42](https://github.com/LUCAS-LYX025/qa-toolkit/issues/42) | medium | 注入防护不完整 | build_dev_query 仅测单一参数注入 | `src/qa_toolkit/integrations/zentao_exporter.py:57` |
| 043 | [#43](https://github.com/LUCAS-LYX025/qa-toolkit/issues/43) | medium | 持久化健壮性 | 未测试损坏 store_file / 缺失或非法密钥文件 | `src/qa_toolkit/core/env_profile_manager.py:100` |
| 045 | [#45](https://github.com/LUCAS-LYX025/qa-toolkit/issues/45) | medium | 边界场景 | analyze_regex 未测无效正则与灾难性回溯 | `src/qa_toolkit/utils/regex_tools.py:19` |
| 046 | [#46](https://github.com/LUCAS-LYX025/qa-toolkit/issues/46) | medium | 外部依赖 | IP 扩展查询未测网络异常/超时/空响应 | `src/qa_toolkit/tools/ip_lookup.py:187` |
| 047 | [#47](https://github.com/LUCAS-LYX025/qa-toolkit/issues/47) | medium | 输入健壮性 | scan_mobile_package 未测损坏或非压缩包文件 | `src/qa_toolkit/core/application_security_tool.py:211` |
| 048 | [#48](https://github.com/LUCAS-LYX025/qa-toolkit/issues/48) | medium | 行为测试盲区 | 查询参数与工具切换函数无行为测试 | `src/qa_toolkit/streamlit_app.py:135` |
| 051 | [#51](https://github.com/LUCAS-LYX025/qa-toolkit/issues/51) | medium | 路径健壮性 | 全局路径常量无测试且目录创建责任分散 | `src/qa_toolkit/paths.py:4` |
| 003 | [#3](https://github.com/LUCAS-LYX025/qa-toolkit/issues/3) | minor | 数据校验缺失 | list_runs 的 limit 非法输入未保护 | `src/qa_toolkit/core/task_runner.py:276` |
| 009 | [#9](https://github.com/LUCAS-LYX025/qa-toolkit/issues/9) | minor | 集合语义误用 | _describe_value_change 对字符串数组用 set 比较丢失重复/顺序信息 | `src/qa_toolkit/core/api_dev_tools.py:1049` |
| 010 | [#10](https://github.com/LUCAS-LYX025/qa-toolkit/issues/10) | minor | 编码警告 | Python 3.12+ 导入产生 SyntaxWarning invalid escape sequence | `src/qa_toolkit/core/api_dev_tools.py:615` |
| 018 | [#18](https://github.com/LUCAS-LYX025/qa-toolkit/issues/18) | minor | YAML 注入 | _yaml_quote 不转义换行与控制字符 | `src/qa_toolkit/core/api_security_tool.py:2059` |
| 019 | [#19](https://github.com/LUCAS-LYX025/qa-toolkit/issues/19) | minor | 逻辑分支错误 | 同名角色在对比矩阵中互相覆盖 | `src/qa_toolkit/core/api_security_tool.py:1468` |
| 020 | [#20](https://github.com/LUCAS-LYX025/qa-toolkit/issues/20) | minor | 边界条件 | build_scan_policy 对 scope=None 抛 AttributeError | `src/qa_toolkit/core/api_security_tool.py:590` |
| 024 | [#24](https://github.com/LUCAS-LYX025/qa-toolkit/issues/24) | minor | 异常处理 | _coerce_int 对 'inf'/'1e400' 抛 OverflowError | `src/qa_toolkit/core/api_test_core.py:2775` |
| 025 | [#25](https://github.com/LUCAS-LYX025/qa-toolkit/issues/25) | minor | 边界条件 | _looks_like_har 对 log 为非 dict 抛 AttributeError | `src/qa_toolkit/core/api_test_core.py:2705` |
| 068 | [#68](https://github.com/LUCAS-LYX025/qa-toolkit/issues/68) | minor | 状态一致性 | 切换解析来源后旧断言结果未清理 | `src/qa_toolkit/ui/pages/api_dev_tools_page.py:659` |
| 069 | [#69](https://github.com/LUCAS-LYX025/qa-toolkit/issues/69) | minor | 按钮回调逻辑错误 | 代码片段展示语言使用上次缓存值 | `src/qa_toolkit/ui/pages/api_dev_tools_page.py:862` |
| 071 | [#71](https://github.com/LUCAS-LYX025/qa-toolkit/issues/71) | minor | 按钮回调逻辑错误 | 清空工作区后 MobSF 预配置被自动重新套用 | `src/qa_toolkit/ui/pages/api_security_page.py:257` |
| 073 | [#73](https://github.com/LUCAS-LYX025/qa-toolkit/issues/73) | minor | 空输入未校验 | 批量查询输入为空仍提交并标记成功 | `src/qa_toolkit/ui/pages/ip_lookup_page.py:190` |
| 074 | [#74](https://github.com/LUCAS-LYX025/qa-toolkit/issues/74) | minor | 异常反馈缺失 | 获取公网 IP 失败时把错误文案当 IP 回填输入框 | `src/qa_toolkit/ui/pages/ip_lookup_page.py:153` |
| 092 | [#92](https://github.com/LUCAS-LYX025/qa-toolkit/issues/92) | minor | widget 状态冲突 | 日志级别 multiselect 同时用 default 和 key | `src/qa_toolkit/ui/pages/log_analysis_page.py:518` |
| 093 | [#93](https://github.com/LUCAS-LYX025/qa-toolkit/issues/93) | minor | 异常反馈缺失 | JSON 字段下拉为空时仍可添加无效过滤条件 | `src/qa_toolkit/ui/pages/log_analysis_page.py:592` |
| 094 | [#94](https://github.com/LUCAS-LYX025/qa-toolkit/issues/94) | minor | 索引越界 | _apply_favorite 直接以 index 取元素未做边界校验 | `src/qa_toolkit/ui/pages/regex_tester_page.py:187` |
| 096 | [#96](https://github.com/LUCAS-LYX025/qa-toolkit/issues/96) | minor | 索引越界 | days_in_month 对月份 13 抛 IndexError | `src/qa_toolkit/utils/datetime_tools.py:28` |
| 097 | [#97](https://github.com/LUCAS-LYX025/qa-toolkit/issues/97) | minor | 数据校验 | calculate_response_time_percentiles 数据含 None 抛 TypeError | `src/qa_toolkit/utils/datetime_tools.py:371` |
| 098 | [#98](https://github.com/LUCAS-LYX025/qa-toolkit/issues/98) | minor | 递归风险 | get_json_depth 对自引用 dict 抛 RecursionError | `src/qa_toolkit/utils/json_utils.py:149` |
| 099 | [#99](https://github.com/LUCAS-LYX025/qa-toolkit/issues/99) | minor | 边界越界 | _percentile 分位数 >100 抛 IndexError | `src/qa_toolkit/core/api_performance_tool.py:1006` |
| 100 | [#100](https://github.com/LUCAS-LYX025/qa-toolkit/issues/100) | minor | 边界错误 | get_constellation 非法日期返回错误星座 | `src/qa_toolkit/utils/datetime_tools.py:227` |
| 039 | [#39](https://github.com/LUCAS-LYX025/qa-toolkit/issues/39) | low | 索引越界 | days_in_month 与 get_constellation 缺非法入参边界 | `src/qa_toolkit/utils/datetime_tools.py:24` |
| 040 | [#40](https://github.com/LUCAS-LYX025/qa-toolkit/issues/40) | low | 边界场景 | calculate_response_time_percentiles 未测非法分位数/空值 | `src/qa_toolkit/utils/datetime_tools.py:369` |
| 044 | [#44](https://github.com/LUCAS-LYX025/qa-toolkit/issues/44) | low | 边界场景 | search_lines 正则模式与无效正则未测试 | `src/qa_toolkit/utils/log_analysis.py:103` |
| 049 | [#49](https://github.com/LUCAS-LYX025/qa-toolkit/issues/49) | low | 边界场景 | task_run_panel 记录解析用字符串分割反解 run_id | `src/qa_toolkit/ui/components/task_run_panel.py:41` |
| 050 | [#50](https://github.com/LUCAS-LYX025/qa-toolkit/issues/50) | low | 测试盲区 | 文档管理模块无测试 | `src/qa_toolkit/support/documentation.py:1311` |
| 052 | [#52](https://github.com/LUCAS-LYX025/qa-toolkit/issues/52) | low | 配置问题 | 上传与消息上限 200MB 且无其他服务端保护 | `.streamlit/config.toml:2` |
| 053 | [#53](https://github.com/LUCAS-LYX025/qa-toolkit/issues/53) | low | 测试基建 | pytest 配置极简且各测试文件重复 sys.path 注入 | `pytest.ini:1` |
| 054 | [#54](https://github.com/LUCAS-LYX025/qa-toolkit/issues/54) | low | 平台依赖 | decode_uploaded_text 的 .doc 分支依赖 macOS textutil 无跨平台兜底测试 | `src/qa_toolkit/utils/text_analysis.py:133` |

## 修复方案

按根因分组批量修复，共改动 35 个源文件 + 新增 6 个测试文件：

- **Streamlit widget 状态回写（12 条）**：新建 `session_state_bridge.py`，提供
  `make_setter` / `make_multi_setter` / `queue_widget_updates` / `pop_widget_updates`；
  按钮回写统一改为 `on_click` 回调（在 widget 实例化前执行），复杂场景用 pending 队列。
- **安全注入（RCE / XSS / shell / JS / YAML）**：生成脚本改用 `repr(json.dumps(...))`、
  HTML 统一 `html.escape`、curl 用 `shlex.quote`、JS 标识符转义、YAML 控制字符转义。
- **URL 与编码**：三个 `_build_full_url` 保留同名多值参数；Postman query 用 urlencode；
  CSV 参数化 UTF-8 严格解码 + GB18030 回退。
- **资源与稳定性**：两处 `requests.Session` 用 try/finally 关闭；subprocess 加 timeout；
  虚拟用户数、时间戳总量、月偏移、上传体积、正则回溯、大文本 diff 均加上限保护。
- **边界与类型校验**：非法日期/None、非数值输入、畸形压缩包、损坏配置、
  循环引用 JSON、非法端口等统一返回结构化错误或友好降级。
- **依赖与配置**：补 `pytz`、`reportlab` 声明；上传上限 200MB→50MB；pytest 增加 markers。

## 验证

- **pytest：223 passed**（原有 157 + 新增 66 条审计回归测试）
- **e2e：6/6 通过**（含 2 条 widget 回写 UI 回归用例）
- 全部 62 个 Python 源文件通过 `py_compile`
- 回归测试覆盖：安全注入、SQL 注入防护、核心模块边界、工具函数边界、UI 交互

---

## 日志分析工具专项审计（2026-11-23，Issues #102-#117）

以测试专家（功能正确性/边界/性能/安全）+ 产品工程师（可用性优化）双视角对日志分析工具做专项审计，实测确认 13 项缺陷、3 项产品优化，全部修复。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| ReDoS（#102） | `(a+)+$` 在 1000 字符行上即卡死 >20s（SIGALRM 超时） |
| 状态码误报（#103） | `duration=123ms` 的 123、时间戳 `.123` 均被计入状态码 |
| 级别误判（#104） | `INFO ... error count: 0` 被判为"错误" |
| IP 子串误匹配（#105） | 过滤 `10.0.0.8` 命中 `10.0.0.81` |
| 1900 时间线污染（#106） | 仅 HH:MM:SS 的行全部聚到 `1900-01-01` |
| 列错位误滤（#107） | 单元格含 ` \| ` 时 AND 模式整行被误滤 |
| GBK CSV（#109/#7） | GB18030 编码 CSV 导入直接 UnicodeDecodeError |

### 修复方案要点

- `search_lines`：编译前硬拦截嵌套量词/分支回溯模式（与 regex_tools 风险检测同源），新增 `include_total` 返回总匹配数与截断标志。
- `STATUS_CODE_REGEX`：前后边界升级为非字母/数字/点，毫秒值、追踪 ID 不再误计。
- `detect_log_level`：改按行内最早出现的级别标记判级；新增中文级别词（错误/严重/致命/警告/信息/调试）。
- `_match_ip_filter`：移除子串兜底，仅按 `ipaddress` 校验后的精确 IP/CIDR 匹配；新增 IPv6 提取。
- 时间线/时间范围：无日期时间不再产生 1900 伪日期。
- `DURATION_PATTERNS`：支持 s/秒并换算 ms。
- `detect_json_columns`：默认采样提升至 500 行。
- UI：GBK CSV 编码回退；10 万行分析上限+截断提示；搜索改为显式"执行搜索"按钮；概览页按当前范围导出日志；健康提示新增 5xx/4xx 占比结论。

### 专项验证

- 专项回归测试 `tests/test_audit_log_analysis.py`：15 passed
- 全量 pytest：240 passed
- e2e（含新增日志分析 3 用例）：9/9 passed
- 探针复测：13 项实测缺陷全部转绿

---

## 测试用例生成器专项审计（2026-11-24，Issues #119-#132）

以测试专家（功能正确性 / 边界 / 健壮性 / 超时）+ 产品工程师（可用性 / 导出一致性）双视角专项审计，实测确认 14 项问题，全部修复。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 旧优先级残留（#119） | AppTest 注入上次优先级 ['高','中']、新用例只有 '低' → `StreamlitAPIException: The default value '高' is not part of the options`，结果页整页不可用 |
| 清空优先级过滤（#120） | 多选值设为 [] 后仍展示全部 2 条用例，与用户预期相反 |
| 畸形用例数据（#121） | `[null, "x", 3, {...}]` → `'NoneType' object has no attribute 'get'`，整批生成作废 |
| 百度 token（#122） | URL 直接 f-string 拼接密钥，`requests.post(url)` 无超时；密钥含 `&` 即破坏查询串 |
| 缺 API Key（#123） | `generate_testcases(..., {})` → `KeyError: 'api_key'` |
| 目标数入参（#124/#125） | 字符串/None → TypeError；`10**9` 原样进入提示词 |
| compose None（#126） | 可选字段传 None → `AttributeError: 'NoneType' object has no attribute 'strip'` |
| Markdown 导出（#127） | 用例名 `a|b`、换行文本未转义，表格列错位 |
| 导出与筛选不一致（#128） | 过滤后仍导出全部用例 |
| OCR 超时（#129） | tesseract-cli 两次 subprocess.run 均无 timeout |

### 修复方案要点

- UI：优先级 signature 变更时重置过滤值；空优先级视为无匹配；搜索域补用例 ID / 前置条件；导出跟随当前筛选并提示条数。
- Core：新增 `_coerce_target_case_count`（钳制 [1,60]）、`_safe_text`、`_markdown_cell`；核心层统一校验必填配置；解析跳过非 dict 元素；百度 token 用 `urlencode` + 超时 + 状态检查；OCR / 讯飞客户端加超时与超大图片拦截。

### 专项验证

- 专项回归 `tests/test_audit_tcg.py`：14 passed
- 全量 pytest：254 passed
- e2e（含新增测试用例生成器 3 用例）：12/12 passed
- 三个探针复测：全部转绿

---

## BI 数据分析工具专项审计（2026-11-24，Issues #134-#151）

以测试专家（功能正确性 / 边界 / 健壮性 / 安全 / 性能）+ 产品工程师（可用性 / **拓展性**，不局限于当前业务）双视角专项审计，实测确认 18 项问题（含 4 项拓展性与产品优化），全部修复。PR #152 已合并，`fix/bi-audit` → `master`，合并提交 `a8c9b0d`。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| HTML 报告 XSS（#134） | 列名/单元格含 `<img src=x onerror=alert(1)>` → `to_html(escape=False)` 与 f-string 拼接原样写入报告，打开即触发 JS |
| 快速过滤正则崩溃（#135） | 筛选值输入 `(` → `re.error: missing ), unterminated subpattern at position 0` |
| CSV 公式注入（#136） | `=1+1`、`+SUM(A1:A2)`、`@cmd` 三处导出全部原样保留，Excel 打开可执行 |
| 重复列名崩溃（#137） | `id,id,val,val` → `int(series.notna().sum())` 抛 `TypeError: cannot convert the series to <class 'int'>`，整页不可用 |
| 数字时间漏识别（#138） | `20260401` / `20260401100000` 列被纯数字规则跳过，`datetime_columns=[]`，趋势分析不可用 |
| 通过率分母（#139） | 通过/失败/空 → `33.3%（1/3）`，空结果被计入分母，期望 `50.0%（1/2）` |
| 分号 CSV（#140） | `日期;产品;销售额` 被默认 `sep=','` 读成 1 列 2 行，`sep=None` 嗅探分支永不执行 |
| code 关键词误匹配（#141） | 无状态码列时把 `area_code` 识别为状态码，输出错误率 0% 与地区编码分布 |
| 字段搜索崩溃（#150） | 输入 `(` → 字段画像 `str.contains` 正则异常 |

### 修复方案要点

- **安全**：新增 `_html_text()` 统一转义，所有 `to_html` 改 `escape=True`，洞察卡片 / 场景标签 / 建议 / 明细表全部转义；新增 `safe_csv_bytes()`，三处 CSV 导出统一把 `= + - @` 开头的字符串降级为文本；列名重复自动规范化（含 pandas 的 `id.1` 自动改名还原）并在加载提示中说明。
- **正确性**：通过率按有效结果行计算；`_numeric_datetime_ratio()` 支持 8/14 位数字时间且排除普通 ID；CSV 用 `csv.Sniffer` 识别 `, ; \t |` 并支持界面显式指定编码/分隔符；场景列识别按注册表规则排除 `area_code` / `zip_code` 等干扰词。
- **健壮性**：字符串过滤默认字面量匹配，正则作为独立“正则匹配”操作符并对非法表达式兜底；`pivot_column_overflow()` 限制列维度唯一值 ≤50；`limit_correlation_columns()` 限制字段数 ≤20 且超过 12 列关闭文本标注；空数据集显示明确空态、不展开分析 Tab。
- **性能 / 状态一致性**：`cached_analysis_context()` 与 `cached_template_payloads()` 跨 rerun 缓存；`dataset_signature()` 加入内容 SHA-256 摘要，防止同名同大小文件复用旧过滤/校验结果。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/bi_registry.py`，把**场景识别规则、模板、图表类型、聚合函数**做成可注册扩展点：`register_scenario` / `register_template` / `register_chart` / `register_aggregator`。新增业务场景或图表只需注册，不再改 `bi_analysis.py` 的 if/elif；`reset_bi_registry()` 保证测试隔离。导出报告新增“数据源”选择（原始 / 过滤结果 / JSON 展开结果），HTML 报告补齐洞察明细表。

### 专项验证

- 专项回归 `tests/test_audit_bi.py`：18 passed（逐条对应 issue）
- 原 BI 测试：6 passed
- 全量 pytest：272 passed
- e2e（新增 `04-bi-analysis.e2e.ts`，含分号 CSV 上传、特殊字符交互、导出数据源）：4/4 passed
- GitHub：issues #134-#151 全部关闭，仓库 open issues = 0 / closed = 148

---

## 文本对比工具专项审计（2026-11-25，Issues #153-#168）

以测试专家（功能正确性 / 边界 / 健壮性 / 安全）+ 产品工程师（易用性 / **拓展性**，不局限于当前业务）双视角专项审计，实测确认 16 项问题并全部修复。PR #169 已合并，`fix/tc-audit` → `master`，合并提交 `8838d0c`。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 尾随换行误报（#153） | `compare_texts("alpha\nbeta\n", "alpha\nbeta")` → `changed=True`，凭空多出一条「删除」空行 |
| autojunk 误报（#154） | 300 行重复日志改 1 行 → 报告 150 行「修改」、行相似度 0.5，差异定位完全失真 |
| 中文词级高亮失效（#158） | `创建订单成功` vs `创建支付订单成功` → 整句 delete + insert，token 相似度 0.0 |
| Markdown 报告注入（#159） | 来源名 `[假来源](http://evil.com)`、正文 `[click](javascript:alert(1))` 原样写入报告；diff 中的 ``` 提前闭合围栏 |
| CSV 导出风险（#160） | 差异 CSV 无 BOM（Excel 中文乱码），`=HYPERLINK(...)` / `+SUM(...)` 原样保留 |
| 忽略空行行号失真（#155） | `"A\n\nX\nB"` vs `"A\nB"` 开启忽略空行后，删除行号显示为 2（源文件实际为 3） |
| Unicode 换行（#156） | `split_lines("a\u2028b\u2029c")` → 1 行，画像与差异定位错位 |
| 大小写折叠（#157） | 忽略大小写下 `Straße` vs `STRASSE` 仍判为不同 |
| 报告截断（#161） | 60 条差异只导出 50 条，无任何提示 |
| 相似度呈现（#162） | 0.9999 显示成「100.0%」却同时提示有差异；两侧全空也显示 100% |

### 修复方案要点

- **正确性**：`split_lines` 去掉仅由末尾换行产生的空行；所有 `SequenceMatcher` 走注册式 matcher，默认 `autojunk=False`，超 5000 项降级并在结果中标注 `matching_mode`；规范化阶段保留原始行号映射，差异行号始终指回源文件；统一 U+2028/U+2029/NEL 换行；`lower()` 改 `casefold()`。
- **中文体验**：默认分词器改为「中文单字 + 英文单词 + 符号/空白」，插入一个词只高亮该词，词相似度从 0.0 提升到 0.857。
- **安全与导出**：新增 `_markdown_text()` 全量转义来源名、状态、差异正文，diff 围栏内的 ``` 转义；`safe_csv_bytes()` 统一加 UTF-8 BOM 并把 `= + - @` 前缀降级为文本；报告声明「仅展示前 50 条，共 N 条」；无差异时 diff 导出为 `# 两侧文本无差异`；新增 TXT 摘要导出且所有格式由注册表生成按钮。
- **易用性**：明确区分「两侧为空 / 单侧输入 / 完全一致」；`format_similarity()` 避免 99.99% 显示成 100.0%；长行截断并显示数量提示、新增并排对照视图、首个差异跳转锚点、过滤结果计数；移除已弃用的 `use_container_width`。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/text_comparison_registry.py`，把**规范化规则、分词器、序列匹配算法、导出格式**做成可注册扩展点（`register_normalizer` / `register_tokenizer` / `register_matcher` / `register_exporter`），并内置忽略标点、忽略所有空白两条可选规则。新增业务规则或输出格式只需注册，不再改 `text_comparison.py` 的 if/elif 或页面里的按钮列表。

### 专项验证

- 专项回归 `tests/test_audit_tc.py`：16 passed（逐条对应 issue）
- 全量 pytest：288 passed
- e2e（新增 `05-text-comparison.e2e.ts`，空态 / 示例 / 扩展规则 / 动态导出）：4/4 passed
- GitHub：issues #153-#168 全部关闭，open issues = 0

---

## 字数统计工具专项审计（2026-11-25，Issues #170-#187）

以测试专家（正确性 / Unicode / 边界 / 安全）+ 产品工程师（易用性 / **拓展性**，不局限于当前业务）双视角专项审计，实测确认 18 项问题并全部修复。PR #188 已合并，`fix/wc-audit` → `master`，合并提交 `e698f20`。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| CJK 扩展区漏计（#170） | `analyze_text('𠀀𠀁𠀂')` → chinese_chars=0、latin_letters=3，生僻字/古字被误判成英文字母 |
| emoji 高估（#171） | `👍🏽👨‍👩‍👧‍👦🇨🇳` → other_chars=11，ZWJ/肤色/国旗按码点累加 |
| 全角空格漏计（#172） | `spaces=0`、`total_chars_no_spaces=5`（应为 3），中文排版全角空格被算进正文 |
| NFC/NFD 分裂（#173） | 同一 `café` 的两种 Unicode 形式 → `[('caf',1),('cafe',1)]` |
| 非 ASCII 词截断（#175） | `ÄPFEL Straße café naïve` → `['pfel','stra','caf','na','ve']`，俄语整词丢弃 |
| 零宽字符不可见（#174） | `ab\u200bcd\ufeffef` 报 8 字符，界面只见 6 个 |
| 口径误导（#176） | 中文连写 `需求说明接口文档测试总结` → 单词数=1、阅读单元=12，三套口径无说明 |
| 注入（#178/#179） | 来源名 `[假来源](javascript:alert(1))` 原样写入 Markdown；来源换行可伪造 TXT 统计行 |
| CSV 乱码（#180） | 导出无 BOM，Excel 打开中文乱码；公式前缀未降级 |

### 修复方案要点

- **Unicode 正确性**：字符分类改为注册式规则，CJK 覆盖扩展 A-G，emoji 独立成类（含 ZWJ/肤色/国旗），全角空格/NBSP 计入 spaces；默认 NFC 归一化；`casefold()` + Unicode 分词器让重音/西里尔词完整提取；零宽/BOM 单独计数并给出诊断建议。
- **口径清晰化**：区分「空格分词数 / 阅读单元 / 拉丁词数」并加可展开的口径说明；高频词与重复词统一按 `most_common` 排序；内置中英文停用词表。
- **安全与导出**：Markdown 来源/关键词转义反引号、方括号、HTML；TXT 来源/建议换行折叠成单行防伪造；CSV 加 UTF-8 BOM 并把 `= + - @` 前缀降级为文本；TXT/MD 报告同样加 BOM。
- **易用性**：新增 emoji、不可见字符、其他字符维度展示；阅读速度、长行阈值、追加停用词做成侧栏可配置项；100 万字符上限保护；统计结果按「文本+配置快照」跨 rerun 缓存。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/text_analysis_registry.py`，把**字符分类规则、分词器、停用词、阅读速度、长行阈值、Unicode 归一化方式**做成可注册配置点（`register_character_class` 支持 priority 插队、`register_tokenizer`、`configure_settings`、`configure_stopwords`）。新增业务统计维度或语言支持只需注册，不再改 `text_analysis.py` 的逐字符扫描逻辑；`reset_text_analysis_registry()` 保证测试隔离。

### 专项验证

- 专项回归 `tests/test_audit_wc.py`：18 passed（逐条对应 issue）
- 原字数统计测试：7 passed
- 全量 pytest：306 passed
- e2e（新增 `06-word-counter.e2e.ts`，空态 / 示例 / Unicode 特殊字符 / 高级配置与导出）：4/4 passed
- GitHub：issues #170-#187 全部关闭，仓库 open issues = 0 / closed = 182

---

## 正则测试工具专项审计（2026-11-25，Issues #189-#207）

以测试专家（正确性 / 安全 / 性能边界）+ 产品工程师（易用性 / **拓展性**，不局限于当前 QA 业务）双视角专项审计，实测确认 19 项问题并全部修复。PR #208 已合并，`fix/regex-audit` → `master`，合并提交 `a520dd9`。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 代码生成转义（#189/#190） | Python 生成 `pattern = r'it's\s+\d+'`；JS 生成 `/https?://qa\.example\.com/`；Java 生成 `Pattern.compile("ORD-\d+", 0)`，均无法直接编译运行 |
| Go 内联 flags（#191） | `cat|dog` + `i` → `(?i)cat|dog`，忽略大小写只作用于左分支，与页面预览结论不一致 |
| 灾难性回溯（#192） | `(a|aa)+$` 不在 5 个硬编码黑名单内；36 个 `a` + `!` 实测 3 秒不返回，可占满 Streamlit 脚本线程 |
| 危险/过期结果（#193/#194） | 危险表达式被拒后仍展示上次「匹配数 1」；改文本不重跑也继续展示旧高亮与旧明细 |
| 截断口径（#196） | 6000 条匹配只显示「匹配数 5000 / 唯一值 5000」，指标本身无截断标记 |
| CSV 公式注入（#197） | 唯一值 CSV 原样写入 `=1+1` / `@SUM(A1)`，Excel 打开即当公式执行 |
| 示例反推（#198） | `1,000` 被拆成 `1`/`000`，生成的 `\d{1,3}` 无法覆盖原例 |
| 预定义表达式（#199-#203） | `匹配整数` 不认 0/-0；`网址URL` 误命中 `foo]://`；`格式日期` 误命中 `2026x04x05`；`身份证号` 误收 `|`；`中文字符` 漏掉 CJK 扩展区 |

### 修复方案要点

- **安全与性能**：核心层统一加 `regex` 模块方法级超时（默认 2 秒）+ 10 万字符上限；超时返回可读错误并清空旧结果，页面层字符串黑名单整体移除。风险提示同步覆盖重叠分支与 `{n,}` 嵌套量词，并给出改写建议。
- **代码生成正确性**：按目标语言字面量规则转义（Python `repr`、JS/PHP/Ruby 分隔符与引号、Java/Go 双引号内部内容、C# verbatim）；Go 内联 flags 包成 `(?i)(?:pattern)`；新增「全局 / 首个匹配」选项，Python 生成 `findall`/`search`、JS 自动带/不带 `g`。
- **结果可信度**：每条结果带输入签名，表达式 / 文本 / flags / 替换 / 高亮配置任一变化即提示「结果已过期」并隐藏旧结果；截断时展示「5000+」和完整总数，唯一值明确标注基于截断样本；新增分析结果 JSON 下载便于归档复现。
- **易用性**：收藏项连同 flags、测试文本、替换模板一起保存并恢复；高亮上下文长度与窗口数可在「实用提示」里调整；CSV 下载对 `= + - @` 开头内容前置单引号降级；预定义模式与 QA 样例保留跨 Tab 回填链路。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/regex_registry.py`，把**预定义模式、QA 场景样例、代码生成语言（模板 / flags / 转义规则）、字段提取规则**做成可注册扩展点（`register_pattern_preset` / `register_sample_case` / `register_code_language` / `register_field_extractor`）。新增公司私有规则或新语言只需注册，不再改 constants.py / 页面 if-else；`reset_regex_registry()` 保证测试隔离。

### 专项验证

- 专项回归 `tests/test_audit_regex.py`：25 passed（逐条对应 issue）
- 原正则测试：10 passed
- 全量 pytest：331 passed
- e2e（新增 `07-regex-tester.e2e.ts`，入口 / 示例运行 / JSON 导出 / 代码生成 / 示例反推 / 字段提取）：4/4 passed，全套 28/28 passed
- GitHub：issues #189-#207 全部关闭，仓库 open issues = 0

---

## 加密/解密工具专项审计（2026-11-25，Issues #209-#227）

以测试专家（正确性 / 边界 / 安全 / 健壮性）+ 产品工程师（易用性 / **拓展性**，不局限于当前业务）双视角专项审计，实测确认 19 项问题并全部修复。PR #228 已合并，`fix/crypto-audit` → `master`，合并提交 `f91a5be`。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| Base64 空白与 URL-safe（#209/#210） | 标准 Base64 按每 8 字符换行后即报 `Non-base64 digit found`；`-__-LXRlc3Q=` 无法解码，JWT / query 参数场景不可用 |
| URL 加号与 Unicode（#211/#212） | `q=hello+world` 解码后仍是 `+`；“Unicode 解码”直接输入 `中文原文` 静默产出 `ä¸­æ–‡åŽŸæ–‡` 且显示成功 |
| 十六进制二进制（#213） | `bytes(range(0x80,0xa0)).hex()` 解码抛 `UnicodeDecodeError`；`hex_encode(bytes)` 变成字符串表示再编码，结果错误 |
| 编码固定 UTF-8（#214） | GBK 编码的 Base64 解码即报错；摘要只能算 UTF-8 字节哈希，无法复现老系统签名 |
| PBKDF2 无上限（#215） | `iterations=10**9` 超过 2 秒仍未返回，页面脚本线程被占用；页面控件仅设 `min_value=1` |
| 结果误导（#217/#218） | 编码 `hello` 得 `aGVsbG8=` 后把输入改成 `world`，页面仍显示旧值；输出面板在所有 Tab 之外，切到对称加解密仍看到编码结果；空输出完全不显示 |
| RSA 限制与覆盖（#219/#220） | 2048 位密钥加密 300 字节只报 `Encryption failed`；手工填入团队测试密钥后再点生成，被新密钥静默覆盖，且分享屏幕时私钥长期明文可见 |
| 默认 ECB（#221） | 页面默认模式实测为 ECB，相同明文块产生相同密文块，DES / 3DES 无弃用提示 |
| 扩展点（#224） | 编码器 / 摘要 / 对称算法清单散落在 4+ 处，新增 Base32 / SM4 / AES-GCM 要同时改核心函数与页面 selectbox；其他专项均已有注册表，唯独本工具全硬编码 |

### 修复方案要点

- **编码正确性**：Base64 解码统一清洗空白并自动兼容 URL-safe 字符集，新增“Base64 (URL-safe)”选项；URL 解码默认把 `+` 还原为空格；十六进制提供“文本 / Base64 / Hex”三种输出，`hex_encode` 直接接受 bytes；Unicode 解码遇到非转义输入明确报错并引导使用编码功能。
- **安全与稳定性**：PBKDF2 迭代次数上限 1000 万、导出长度上限 1024 字节；RSA 按公钥位数计算 OAEP-SHA256 明文上限并在超限前给出中文提示，密钥长度限定 2048–8192 位；重新生成 RSA 密钥必须先勾选覆盖确认；默认模式改为 CBC，ECB / DES / 3DES / MD5 / SHA1 全部带风险提示；私钥默认掩码显示，公钥 / 私钥可分别下载。
- **结果可信度**：每条结果与工具、算法、输入、参数组成的签名绑定，输入一变即提示“结果已过期”并隐藏旧结果；输出面板移入各自 Tab 内，跨 Tab 不再复用；空输出显示明确提示；解密失败按 Base64 / Padding / IV / 密钥长度分类给出可操作诊断。
- **易用性**：编码、摘要、HMAC 增加 UTF-8 / GBK / GB18030 / UTF-16LE 字符编码选择；PBKDF2 盐值支持 text / hex / base64 并在结果标签回显全部参数；对称加解密实时显示密钥 / IV 长度是否合法并支持一键生成随机材料；导出文件名带来源与算法，避免同名覆盖。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/crypto_registry.py`，把**编码器、摘要算法、对称算法、加密模式、字符编码**做成可注册扩展点（`register_encoder` / `register_hash` / `register_symmetric_algorithm` / `register_symmetric_mode` / `register_text_encoding`）。页面选项与核心算法清单均从注册表读取，新增国密 SM4 或 AES-GCM 只需注册，不再改页面 if-else。

### 专项验证

- 专项回归 `tests/test_audit_crypto.py`：18 passed（逐条对应 issue）
- 原加密工具测试：5 passed
- 全量 pytest：349 passed
- e2e（新增 `08-crypto-tools.e2e.ts`，入口 / 结果过期 / MD5 / CBC / RSA 上限）：4/4 passed，全套 32/32 passed
- GitHub：issues #209-#227 全部关闭，仓库 open issues = 0

---

## JSON 处理工具专项审计（2026-11-25，Issues #229-#247）

以测试专家（正确性 / 边界 / 健壮性）+ 产品工程师（易用性 / **拓展性**，不局限于当前业务）双视角专项审计，实测确认 19 项问题并全部修复。PR #248 已合并到 `master`，合并提交 `b45aeca`。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 格式化 / 清空按钮（#229） | 输入框改成 `{"a":1}` 后点击“✨ 格式化”，`session_state` 已变为带缩进文本，但 widget 仍显示旧值；清空同理，用户以为按钮失效 |
| 结果过期（#230） | 解析 `{"a":1}` 后把输入改为 `{"a":999}`，旧结果继续展示；对比和 JSONPath 同样残留；JSONPath 输入 `{bad json` 报错后仍显示上一次的 `['Author 1', 'Author 2']` |
| 递归下降重复（#231/#232） | `$..author` 在 3 本书的数据上返回 12 项（每个作者重复 4 次），`$..book[0].title` 返回 2 项，`$..*` 返回 40+ 项且包含大量重复子树 |
| 过滤器与语法（#233-#235） | `?(@.tags[0]=='a')` 返回空；`?(@.isbn)` 只对硬编码的 isbn 生效；`$['store']['book'][0]['title']` 静默返回空；`[0:3:0]` 抛 `range() arg 3 must not be zero` |
| 解析宽松性（#236/#237） | `{"a":1,"a":2}` 静默取最后一个值；`NaN`/`Infinity` 被接受并原样写出；带 BOM 的粘贴内容直接报 `Unexpected UTF-8 BOM` |
| 对比确定性（#238/#239） | 同一对象与 `{}` 对比，多次运行差异顺序由哈希随机化决定（实测 d、c、a、b）；`1` 与 `1.0` 被误报为“类型不同” |
| 深嵌套（#240） | 1200 层嵌套对象调用 `analyze_json_structure()` 抛 `RecursionError`，页面无保护；其他遍历方法已有上限，唯独结构分析遗漏 |
| 导出与错误提示（#242-#244） | JSONPath 对象结果用 Python `str` 导出，形如 `{'title': 'A'}`，不是合法 JSON；解析结果无下载按钮；错误只回显 `Expecting property name... line 1 column 10`，没有上下文与原因提示 |
| 拓展性（#246） | 约 280 行工具逻辑内嵌 `streamlit_app.py`，模式、按钮、JSONPath 规则、导出格式全部硬编码，新增扩展点要改多处 |

### 修复方案要点

- **解析与序列化**：新增 `parse_json_text()` / `serialize_json()`，默认严格拒绝 NaN/Infinity、重复键给可见告警、自动剥离 BOM、识别 JSONL 并作为数组处理；错误转成“第 N 行第 M 列 + 附近内容 + 常见原因”的中文提示；输入体积上限防止页面卡死。
- **JSONPath 重写**：实现词法分割与 token 求值，递归下降每个节点只访问一次；支持标准括号字符串索引、数组切片/负索引/多选、通配符、过滤器中的嵌套路径 `@.a.b` 与数组下标 `@.tags[0]`、任意属性存在性检查、`=~` 正则和注册函数（`length` / `keys` / `values`）；步长为 0 与未闭合括号给出明确错误。
- **对比与结构分析**：dict 按键稳定排序，差异文本可逐行 diff；JSON number 支持可配置数值等价；`compare_json_values()` 返回统计信息并在页面展示；结构分析改迭代实现并加深度/节点上限，`get_json_depth()` 明确“标量 0、空容器 1、嵌套容器逐层 +1”。
- **结果可信度**：解析、对比、查询三类结果均与输入/参数签名绑定，输入变化即提示“结果已过期”并隐藏旧结果；解析或查询失败时清空对应结果；格式化与清空通过 widget key 版本递增真正刷新输入框。
- **易用性**：三种模式均有带标签的输入框、可载入示例和 JSONPath 速查；导出格式从注册表读取，支持 JSON / JSONL / 纯文本下载；解析错误给出可定位的上下文。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/json_registry.py`，把 **JSONPath 函数、差异规则、导出格式、校验器、示例** 做成可注册扩展点；同时把 JSON 工具从 `streamlit_app.py` 迁到独立页面 `json_tools_page.py`，`tool_routes.py` 从 inline 改为 page 路由，业务方扩展无需再改主脚本。

### 专项验证

- 专项回归 `tests/test_audit_json.py`：16 passed（逐条对应 issue）
- 既有 JSON/路由回归：20 passed
- 全量 pytest：365 passed
- e2e（新增 `09-json-tools.e2e.ts`，格式化清空 / 错误定位与过期 / 稳定对比 / JSONPath 去重与失败清空）：4/4 passed，全套 36/36 passed
- GitHub：issues #229-#247 全部关闭，仓库 open issues = 0

## 时间处理工具专项审计（2026-11-25，Issues #250-#268）

### 审计范围与方式

- 对象：`src/qa_toolkit/utils/datetime_tools.py`（DateTimeUtils 全量方法）+ `src/qa_toolkit/ui/pages/time_processor_page.py`（时间戳/单位换算/日期计算/SLA/Cron/性能/时区 4 大 Tab）。
- 方式：候选问题先写成复现脚本（`.qa-audit/datetime_repro.py`）逐条实测，证伪后排除（12/13 位时间戳识别、SLA 跨天与周末跳过、毫秒往返精度等候选均被证伪），确认 19 项后提交 GitHub Issues #250-#268（另有脚本误建的重复 issue #249 已关闭）。
- 修复分支 `fix/datetime-audit`（commit `955b1a4`），PR #269 合并至 master（merge commit `a0b3801`）。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 无效时区静默（#250） | `get_timezone_conversion(..., 'Not/ARealZone')` 返回原时间 2026-04-06 09:00，无任何报错，页面把原时间当转换结果展示 |
| 夏令时歧义不一致（#251） | 纽约 2026-03-08 02:30（不存在的时刻）在时间戳页明确报错，但核心层 `localize` 默认 `is_dst=False` 静默给出标准时间结果 |
| 节假日年份缺口崩溃（#252） | `summarize_date_range(2100-01-01, 2100-01-03, country='CN')` 抛 `TypeError: Value after * must be an iterable`（holidays 库对 2100+ 年构造失败），页面实时调用无 try 保护 |
| 中国调休失真（#253） | `count_business_days(2024-02-04, 2024-02-04, country='CN')` 返回 0，但该周日是春节调休上班日；holidays 库只标记放假不标记调休上班 |
| 结果不失效（#254） | AppTest：时间戳转换/批量转换/Cron 生成结果在输入修改后全部残留旧值 |
| CSV 公式注入（#255） | 批量输入 `=1+1`，导出 CSV 第二行为 `1,=1+1,失败,...`，Excel 打开会执行公式 |
| Cron API 设计（#256） | 错误信息 `['解析错误: ...']` 与正常 `list[datetime]` 同型返回，调用方只能 `isinstance` 嗅探；croniter 缺失时同样只返回字符串 |
| 错误信息英文（#257） | 批量失败行显示 `Unknown string format: abc` 等原生异常 |
| 星期英文（#258） | `parse_datetime_input` 返回 `Monday`，多时区对照表“星期”列同样英文 |
| 边界校验（#259-#264） | 未来生日 `get_age(2030-01-01)` 返回 -4；`get_constellation(2,30)` 返回双鱼座；`add_business_days` 无上限（页面 number_input 无 max）；`duration×rps=52.5` 静默截断为 52；负响应时间参与 P95；`add_months(date(1,1,1),-1)` 抛裸 `ValueError: year 0 is out of range` |
| DataFrame 混合类型（#265） | 结果表“结果”列混合 str/int，触发 `ArrowTypeError: Expected bytes, got a 'int' object` 告警 |
| 硬编码扩展点（#266） | `TIME_UNIT_SECONDS`、`CRON_PRESETS`、13 个时区、对照表 `[UTC,北京,东京,纽约,伦敦]` 全部硬编码 |
| 时区能力薄弱（#267） | 仅 13 个常用城市，无法搜索全量或输入 IANA 名称（如 `Asia/Ho_Chi_Minh`） |
| SLA 无日历（#268） | `calculate_sla_due_date` 只跳周末，`count_business_days`/`add_business_days` 却都支持国家日历，能力不对齐 |

### 修复方案要点

- **时区转换健壮化**：无效时区抛 `ValueError`（含可用时区提示）；`localize(..., is_dst=None)` 统一处理夏令时歧义/不存在时刻，错误信息区分“不存在”与“有歧义”；多时区快照同样校验。
- **节假日缺口降级**：`_get_country_holidays_safe` 按年构造、失败年份跳过并回传 `unsupported_holiday_years`，区间统计把缺口年份视为无节假日并在页面标注“节假日数据缺口”，不再崩溃；`is_holiday` 对不支持年份返回 False 而非吞异常。
- **中国调休支持**：新增 `register_business_calendar(country, extra_workdays, extra_holidays)` 自定义覆盖表，`is_workday`/`count_business_days`/`add_business_days`/`summarize_date_range`/`calculate_sla_due_date`/`calculate_business_hours_diff` 全链路生效；SLA 增加可选 `country` 参数（默认保持旧行为兼容）。
- **结果可信度**：时间戳转换、日期时间回算、批量转换、Cron、性能分析五类结果全部绑定输入签名，输入变更即提示“结果已过期”并隐藏旧结果。
- **CSV 安全与诊断**：批量导出对 `= + - @` 开头单元格加前缀降级（UTF-8 BOM 保留，文件名带时间戳）；失败行转换为“无法识别的时间格式 / 超出可表示范围 / 请检查时间戳位数”等可操作中文诊断。
- **本地化与易用性**：新增 `weekday_name(locale='zh')`，批量结果与多时区对照表输出中文星期；时区 Tab 支持自定义 IANA 名称并给出“未识别”提示；Cron 改结构化返回 `{ok, runs, error}`（旧接口兼容层保留）；结果表全部字符串化消除 Arrow 告警。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/datetime_registry.py`——时间单位、时区、Cron 模板、多时区对照列、自定义工作日/节假日、批量解析自定义格式均为注册扩展点，与 regex/crypto/json registry 同风格；页面列表全部改从注册表读取，重复项注册显式要求 `replace=True`。

### 专项验证

- 专项回归 `tests/test_audit_datetime.py`：28 passed（逐条对应 issue）
- 全量 pytest：393 passed
- e2e（新增 `10-time-processor.e2e.ts`：时间戳转换与过期 / 批量中文诊断 / Cron 结构化与过期 / 自定义 IANA 时区）：4/4 passed，全套 40/40 passed
- GitHub：issues #250-#268 全部关闭，仓库 open issues = 0

## 图片处理工具专项审计（2026-11-25，Issues #270-#289）

### 审计范围与方式

- 对象：`src/qa_toolkit/utils/image_processing.py`（ImageProcessor 全量方法）+ `src/qa_toolkit/ui/pages/image_processor_page.py`（格式转换/指定体积/批量造图/尺寸/翻转/旋转/裁剪/水印 8 个 Tab）。
- 方式：候选问题写成 `.qa-audit/image_repro.py` 实测坐实，证伪项剔除（例如“导出复制 EXIF 导致隐私泄露”在 Pillow 11.3 下不成立，实际是**静默剥离且不可配置**，因此改提 #271），确认 20 项后提交 GitHub Issues #270-#289。
- 视角：除正确性外，重点覆盖测试专家关心的资源边界/动画保真，以及产品工程师关心的**拓展性、易用性**（格式与档位可注册、批量产物可追溯、动画与元数据策略可见）。
- 修复分支 `fix/image-audit`（commit `314c5c0`），PR #290 已合并至 `master`（merge commit `7c916fe`）。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| EXIF 方向（#270） | 带 `Orientation=6` 的 64×48 JPEG 经 `_load_image()` 后仍是 64×48，竖拍照片按横向预览/导出 |
| 元数据策略（#271） | 源图 `ImageDescription='GPS-LAT-31.23-LON-121.47'`，导出后 `getexif().get(270)` 为 `None`，无开关可选 |
| 资源上限（#272/#273） | 12000×12000 PNG（1.44 亿像素）只触发 Pillow 警告仍继续加载；`resize_image(img, 1_000_000, 1)` 直接向 Pillow 请求百万像素宽 |
| 参数校验（#274-#277） | `quality=-20/250` 都成功产出 JPG；`min_quality=90, max_quality=10` 不报错并返回 `target_achieved=True`；反向裁剪 `(50,40,5,5)` 得到 1×1；`convert_image_for_format(..., 'XYZ')` 静默返回原图 |
| 水印（#278/#279） | `opacity=5.0` 静默接受；4 元组颜色拼成 5 元组报英文错；无效字体走 `NamedTemporaryFile(delete=False)` 后 `os.unlink` 调用数为 0，临时文件泄漏 |
| 动画（#280） | 2 帧 GIF 经 `save_image_to_bytes(..., 'GIF')` 后 `n_frames=1`，页面无任何提示 |
| 结果可信（#281） | `target_bytes=100` 返回 `target_achieved=False` 与 note，页面仍显示“目标体积图片已生成” |
| 硬编码（#282） | 输出格式、预设体积/尺寸、裁剪比例、水印位置散落在页面常量与 8 个 selectbox，新增档位要改多处 |
| 文件名/追溯（#283/#284） | `Path('../../evil?name.png').stem` 得到 `evil?name` 直接进入下载名；批量 ZIP 只有图片，没有 manifest |
| 易用性（#285-#289） | 裁剪卡显示英文 `Current Selection`；切换宽/高锚点丢失比例结果；批量无进度；LA 透明像素转 JPG 变黑块；未知重采样算法静默回退 LANCZOS |

### 修复方案要点

- **方向与安全边界**：`_load_image()` 先校验上传字节数、声明像素数、内容格式，再 `load()`；静态图用 `ImageOps.exif_transpose` 校正方向，动画图保留多帧；资源上限通过 `configure_image_limits()` 可按环境调整。
- **核心校验**：质量限定 1-100、目标质量区间与缩放步长强校验、输出边长/像素预算校验、未知格式/算法/位置全部中文报错；反向裁剪改为先交换坐标再裁剪。
- **透明与背景**：LA/P 透明像素统一转 RGBA 后按可配置背景色合成，页面提供“透明区域背景色”，消除黑块。
- **水印**：opacity/font_size/color/rotation 严格校验，字体改用 `BytesIO` 不再落盘；所有失败统一带“添加水印失败”前缀，保留既有错误可见性契约。
- **动画保真**：新增 `extract_frames()` / `save_animated_image()`，格式转换、尺寸、翻转、旋转、裁剪、指定体积、批量均逐帧按同一比例处理并保留 duration/loop；不支持动画的格式明确提示“仅处理首帧”。
- **元数据与结果可信**：`save_image_to_bytes(preserve_metadata=True)` 显式保留 EXIF，页面默认关闭并提示隐私风险；目标体积未达标改 warning 展示 note；批量 ZIP 增加带 BOM 且防公式注入的 `manifest.csv`，记录目标/实际/缩放/是否达标；新增逐档进度条。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/image_registry.py`，把输出格式、重采样算法、预设体积、预设尺寸、裁剪比例、水印位置、资源上限做成可注册扩展点；重复注册要求 `replace=True`，Spec 冻结、查询返回副本；页面下拉全部从注册表生成。
- **易用性**：下载名与 ZIP 条目统一清洗控制字符/路径/系统保留字符；裁剪指标卡中文化；保持宽高比切换锚点时从 session_state 继承上次计算结果。

### 专项验证

- 专项回归 `tests/test_audit_image.py`：25 passed（逐条对应 issue）
- 全量 pytest：418 passed
- e2e（新增 `11-image-processor.e2e.ts`：入口与上传 / 格式转换 / 批量 manifest / 水印与动画提示）：4/4 passed；全套 44/44（另一次全套出现 1 例既有 TCG 示例载入偶发失败，单独重跑 3/3 通过）
- GitHub：issues #270-#289 全部关闭，仓库 open issues = 0

## IP/域名查询工具专项审计（2026-11-25，Issues #291-#310）

### 审计范围与方式

- 对象：`src/qa_toolkit/tools/ip_lookup.py`（IPQueryTool 全量方法）+ `src/qa_toolkit/ui/pages/ip_lookup_page.py`（单个查询 / 批量查询 / IPv4 转换 / 资产扩展 4 个 Tab）。
- 方式：候选问题写成 `.qa-audit/ip_repro.py` 实测坐实（含 mock 网络源、构造畸形 URL、超时 DNS、公式注入 CSV），确认 20 项后提交 GitHub Issues #291-#310。
- 视角：测试专家关注输入边界、网络超时、来源失败判定、导出安全；产品工程师关注**拓展性、易用性**（数据源/动作/转换方式可注册，状态与降级可见），不局限于当前业务。
- 修复分支 `fix/ip-lookup-audit`（commit `7e0c9a7`），PR #311 已合并至 `master`（merge commit `d937104`）。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 地址分类（#291） | `127.0.0.1`、`169.254.10.1` 都被归入「私有IP」，`is_private` 判断先于 `is_loopback`/`is_link_local` |
| 凭据泄露（#292） | `https://user:s3cr3t@example.com/login` 的 `original_input` 原样进入结果表与导出 JSON |
| 协议与端口（#293/#294） | `:99999`/`:abc` 只追加一条「已忽略端口」备注仍返回成功；`javascript:alert(1)`、`mailto:` 被当成合法域名 |
| 网络护栏（#295） | `socket.gethostbyaddr`/`getaddrinfo`/`getfqdn` 全部裸调用，无超时；慢 DNS 会长时间阻塞页面 |
| 缓存（#296/#297） | 同一 IP 连续两次查询发起 2 次地理请求；连续点击「获取当前公网 IP」重复打满服务 |
| 结果可信（#298/#299/#300） | crt.sh 与 HackerTarget 全失败仍返回 `success=True`；`limit=-1` 返回全部 300 条；ICP 接口 `code=401` 仍把 `data` 当备案成功 |
| 推断标注（#301） | 域名关键字/IP 段推断出的 ASN 无来源标记，易被当成权威数据 |
| 导出安全（#302） | 批量 CSV 单元格 `=HYPERLINK(...)` 原样导出，Excel/WPS 下可执行公式 |
| 易用性（#303/#304） | 修改输入后仍展示上一次结果；地理/资产降级只在表格里写一行文字，页面无醒目提示 |
| 拓展性（#305-#310） | 地理源、公网 IP 服务、转换方式、主域后缀/端口/国家映射、资产动作、批量上限/超时/缓存时长全部硬编码在类常量与页面下拉里 |

### 修复方案要点

- **输入与隐私**：回环/链路本地优先分类；URL 中的 userinfo 在解析阶段替换为 `***@` 并给出备注；非 http/https 协议、非法/越界端口直接拒绝并给中文原因。
- **网络护栏**：新增 `_run_with_timeout()` 守护线程包装 `gethostbyname_ex`/`getaddrinfo`/`getfqdn`/`gethostbyaddr`，超时返回部分结果并写入「解析提示」；所有第三方请求统一 `allow_redirects=False` + 可配置超时，URL 模板强制 HTTPS。
- **缓存**：地理结果与公网 IP 均带独立 TTL 缓存（默认 600s / 300s），`clear_cache()` 可主动失效；同时保留熔断降级逻辑，缓存命中会重置源失败计数。
- **结果可信度**：资产查询返回 `status=ok/partial/failed`，所有数据源失败即 `success=False`；`limit` 越界回落到注册表默认值；ICP 校验 `code` 与 `data`；ASN 推断结果显式追加 `[根据域名推断]` / `[根据IP段推断]` 标记。
- **导出与状态**：CSV 单元格对 `= + - @`、制表符/回车加前缀降级并保留 UTF-8 BOM；单条/批量/资产结果绑定输入签名，输入变化即提示「结果可能已过期」；来源状态、结果状态、降级说明改为醒目反馈卡；批量表格补文字汇总，IPv4 转换补文字摘要（表格是 canvas，读屏与自动化都读不到）。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/ip_lookup_registry.py`——地理数据源、公网 IP 服务、IPv4 转换方式、资产动作、可注册主域后缀、端口服务名、国家代码映射、协议白名单、运行参数全部做成注册扩展点；Spec 冻结、查询返回副本、重复注册要求 `replace=True`，页面下拉/按钮/能力摘要全部从注册表生成。
- **易用性**：首屏展示「当前注册的能力」摘要（数据源/服务/转换/动作/批量上限/缓存时长）；批量上限前置校验并提示截断；资产动作可按 key 注册并由 `run_asset_action()` 统一调度。

### 专项验证

- 专项回归 `tests/test_audit_ip.py`：24 passed（逐条对应 issue）
- 全量 pytest：442 passed（含 AppTest 脚本补丁自动还原，避免跨文件类方法污染）
- e2e（新增 `12-ip-lookup.e2e.ts`：注册能力摘要 / 单查询结果过期 / 批量空输入与汇总 CSV / IPv4 转换与非法协议拦截）：4/4 passed，全套 48/48 passed
- GitHub：issues #291-#310 全部评论并关闭，仓库 open issues = 0

## 接口性能测试工具专项审计（2026-11-25，Issues #312-#332）

### 审计范围与方式

- 对象：`src/qa_toolkit/core/api_performance_tool.py`（PerformanceTestTool 全量执行引擎：计划构建 / 虚拟用户 / 采样 / 统计 / HTML 报告 / CSV 参数化 / URL 构造）+ `src/qa_toolkit/ui/pages/api_performance_page.py`（JMeter 风格页面：Test Plan 树 / HTTP Request Defaults / Thread Group / CSV / Transaction / Assertion / Timer / Listener Dock / 下载中心）。
- 方式：候选问题写成 `.qa-audit/perf_repro.py` 实测坐实（fake clock 跑 duration 模式、mock upload、构造畸形 URL、CSV 公式注入、HTML 注入、worker 抛异常），确认 20 项后提交 GitHub Issues #312-#331；新增 e2e 回归 `13-api-performance.e2e.ts` 时又暴露 1 项边界缺陷，追加提交 #332，共 **21 项**。
- 视角：测试专家关注正确性（统计口径、并发异常、CSV 语义、URL 构造）、安全性（SSRF、注入、上传清理）、边界与大数据；产品工程师关注**拓展性、易用性**（注册式扩展点、状态反馈、文字摘要、口径说明），不局限于当前业务。
- 修复分支 `fix/api-performance-audit`（commit `22e37b2`），PR #333 已合并至 `master`（merge commit `017f2d6`）；e2e 全套 52/52 通过。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 结果过期（#312） | 改并发/URL 后仍展示上一次结果，无签名、无过期提示 |
| CSV EOF（#313） | Recycle 默认 True 且 Stop Thread 不互斥，EOF 后静默发送未替换的 `${var}` |
| URL 构造与导出（#314/#330） | `_build_full_url` 用 `params.update` 覆盖同名多值 query、list 值被 `str()` 成 `"['a','b']"`；导出 JSON 只有 6 个结果键，不含 plan/samples |
| 并发异常（#315/#316） | `future.result()` 冒泡导致整次结果与 HTML 报告全丢；duration 模式下 ramp-up / think-time 的 `sleep` 不受 deadline 约束，尾部 VU 0 样本且无告警 |
| 断言与分组（#317/#318） | 结果树用 400 字符预览二次推断断言；per_sampler 按 method+path 分组，同路径不同接口被静默合并 |
| 请求语义（#319/#320） | GET/HEAD 仍发 body、GET 的 `parameters` 被丢弃；`inf`/`nan` 被 `_to_float` 接受，多个时长参数无上限 |
| 目标地址（#321/#322） | 四字段自由拼接无协议白名单/端口校验，`urlparse(...).port` 非法时抛 ValueError；path_params 与 CSV 变量不编码，可注入路径与额外 query |
| 安全（#323/#324/#325） | 上传文件名直接拼路径且临时文件从不清理；CSV 公式注入、HTML 报告 status_code 与状态栏未转义；无协议白名单 / 内网拦截 / 重定向默认开启 / SSL 校验默认关闭（SSRF） |
| 统计口径（#326/#327/#328） | throughput 分母含 ramp-up 与 think-time；p90/p95 用线性插值却标 JMeter「90% Line」；错误截断无提示、失败样本无 error_type、timeline 丢空档秒、不完整事务参与统计 |
| 易用性（#329/#330） | 5 个 Listener 只有 canvas 无文字摘要；任务记录 payload 只有接口数量，10 用户与 200 用户两轮无法区分 |
| 拓展性（#331） | 断言类型、分位数、监听器页签、报告字段、CSV 模式、定时器、事务策略、运行上限全部硬编码，无任何 `core/*_registry.py` |
| **e2e 回归新发现（#332）** | **Server Name 留空、Port 填 `443@evil.com`，`st.code` 仍显示 `https://example.com` 且零提示**：`_compose_base_url_from_fields()` 的 `if not server_name: return fallback` 位于协议/端口校验之前，四字段校验被整体短路，非法输入被静默吞掉 |

### 修复方案要点

- **结果可信与状态反馈**：新增 `_compute_signature()` / `_CONFIG_SIGNATURE_KEYS` / `_is_result_stale()`，执行后写入 `result["input_signature"]`，配置变更即醒目提示「结果可能已过期」；所有 warning 统一反馈卡展示。
- **并发与统计正确性**：`future.result()` 与 `_run_virtual_user()` 双层异常隔离，worker 抛错转成失败样本；`_sleep_with_deadline()` 统一 ramp-up / think-time；`_build_timeline()` 补齐空档秒；事务样本带 `complete` 标记，不完整链路排除出事务统计；失败样本带 `error_type` 与 `truncation` 截断提示。
- **统计口径可解释**：`active_window_seconds` / `wall_throughput_rps` / `throughput_basis` 明确吞吐按活跃窗口计算、不含 Ramp-Up / Startup Delay；分位数默认 JMeter nearest-rank，可切 linear，分位点本身也可注册。
- **请求构造与 CSV**：query 同名参数 append、list 用 doseq 展开；GET/HEAD 抑制 body 并合并 `parameters`；`_encode_path_value()` + `quote()` 编码 path_params 与 URL 变量，`raw:` 显式跳过，未解析变量写入 `unresolved_variables` 告警；新增 `sampler_id` 按 id 分组/匹配/展示 materialized 值；CSV EOF 三态策略 `recycle` / `stop_thread` / `continue_empty`，页面 Recycle 与 Stop Thread 互斥联动。
- **安全护栏**：新增 `validate_target_url()` / `sanitize_server_name()` / `validate_port_text()`——协议白名单、userinfo 拒绝、端口 1-65535、内网/回环/链路本地/元数据地址拦截（显式开关放行）、默认关闭重定向、默认开启 SSL 校验；`_sanitize_csv_frame()` 防 CSV/HTML 公式注入、`html.escape()` 转义状态栏；上传文件名 basename + 字符白名单并在 `finally` 删除临时文件；`PerformanceLimits` 钳制所有数值输入，`inf`/`nan` 回落安全默认值。
- **PERF-21 补强（e2e 新发现）**：把协议白名单与 `validate_port_text()` 校验前置到「主机名为空」判断之前，非法端口/协议无论主机是否填写都会写入 `api_perf_url_error` 并在页面醒目提示；仅当已填字段全部合法且主机名为空时才回落 fallback 且不误报。补 `test_perf_21_validation_runs_even_without_server_name` 与 e2e 断言双重回归。
- **导出与易用性**：`build_export_payload()` 让下载 JSON 含 plan / samples / html_report / warnings / truncation；HTML 报告增测试配置快照与告警面板；Summary / Aggregate / Graph / Errors / Transactions 补中文文字摘要；任务 payload 记录配置摘要；所有关键 `number_input` 加来自注册表的 `max_value`；首屏展示「当前注册的能力」摘要。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/api_performance_registry.py`——断言类型、分位数口径与列表、监听器页签、结果字段、摘要指标、CSV 共享模式/EOF 策略、定时器策略、协议白名单、SSRF 校验、导出清洗器、运行上限全部提供 `register_*` / `configure_*` / `get_*` 扩展点；frozen dataclass Spec、查询返回副本、重复注册需 `replace=True`、`reset_performance_registry()` 保证测试隔离；页面下拉、按钮、能力摘要与导出字段全部注册表驱动。

### 专项验证

- 专项回归 `tests/test_audit_perf.py`：21 passed（逐条对应 #312-#332，含 e2e 新发现的 PERF-21）
- 全量 pytest：463 passed（独立 `--basetemp` 规避沙箱 `pytest-of-unknown` 残留 EEXIST）
- e2e（新增 `13-api-performance.e2e.ts`：注册能力摘要与安全默认 / HTTP Request Defaults 主机与端口校验 / CSV EOF 互斥 / 分位数与吞吐口径）：4/4 passed，全套 **52/52 passed**
- GitHub：issues #312-#332 全部评论并关闭，仓库 open issues = 0

## 接口安全测试工具专项审计（2026-11-25，Issues #334-#355）

### 审计范围与方式

- 对象：`src/qa_toolkit/core/api_security_tool.py`（SecurityTestTool 全量执行引擎：方案构建 / 被动审计 / 基线探测 / 多角色回归 / OWASP 清单 / 权限矩阵 / Nuclei 模板 / 风险看板 / 回归套件 / 报告打包）+ `src/qa_toolkit/ui/pages/api_security_page.py`（Streamlit 应用安全工作台：API 文档安全 / 移动包 / MobSF / Web 站点三视图，覆盖导入、范围鉴权、动作区、结果工作台与下载导出）。
- 方式：候选问题写成 `.qa-audit/security_repro.py` 实测坐实（`_to_int` 缺失导致 7 入口崩溃、对元数据地址真实发请求、URL 构造覆盖、CSV/YAML 注入、大小写响应头、角色保留字冲突、页签隐式探测等），确认 21 项后提交 GitHub Issues #334-#354；新增 e2e 回归 `14-api-security.e2e.ts` 时又暴露 1 项首屏安全边界不可见问题，追加提交 #355，共 **22 项**。
- 视角：测试专家关注正确性（入口可用性、空范围语义、URL 编码、响应头读取、数值健壮性、结果过期、错误观测）、安全性（SSRF、Header/CRLF、CSV 公式注入、Nuclei YAML 注入、上传文件名）、边界与大数据（运行上限、响应体限额、截断）；产品工程师关注**拓展性、易用性**（注册式扩展点、状态反馈、文字摘要、统一导出、可复现快照），不局限于当前业务。
- 修复分支 `fix/api-security-audit`（commit `cf4c396`），PR #356 已合并至 `master`（merge commit `e565386`）；全套 e2e 56/56 通过。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 整体不可用（#334） | `_normalize_interface()` 调用不存在的 `self._to_int`，`build_security_plan` / `analyze_interfaces` / `run_baseline_probe` / `build_authorization_matrix` / `build_nuclei_template_pack` / `build_regression_suite` / `run_role_batch_regression` 7 个入口全部 AttributeError，工具 100% 不可用 |
| 范围语义（#335） | `selected_indexes=[]` 被当成全选，清空选择仍对全部接口发请求；越界与重复索引不过滤 |
| SSRF（#336） | 对 `http://169.254.169.254/latest/meta-data/iam/security-credentials/` 真实发起请求，无协议白名单、无内网/元数据拦截，重定向与 SSL 校验默认值不安全 |
| URL 构造（#337） | `path_params` 未编码可注入路径与 query；同名 query 参数被覆盖；list 值被 `str()` 成 `"['a','b']"` |
| 响应头证据（#338） | 大小写敏感取 `X-Frame-Options`，服务返回小写头即漏报，证据列为空 |
| 运行上限（#339） | 接口数 / 角色数 / 请求数 / 超时 / 响应体均无上限，`inf`/`nan` 被接受 |
| 隐式发请求（#340） | 浏览「多角色回归」「下载导出」页签即隐式执行批量回归或补算并发网络请求 |
| CSV / YAML 注入（#341/#342） | 裸 `to_csv(index=False)` 直接导出 `=1+1` 等公式；Nuclei 模板 header 名与变量未校验，换行可注入 YAML |
| 结果过期（#343） | 改 Base URL / 鉴权头 / 范围后仍展示旧结论，无签名、无提示，导出无可复现快照 |
| 截断与报告（#344） | 静默截断无明细，Markdown 报告缺发现项明细与告警章节 |
| 页签可读（#345） | 12 个结果页签只有表格/canvas，无中文文字结论 |
| 拓展性（#346） | 规则、词表、OWASP、严重级别、角色等级、结果页签、Nuclei 模板、运行上限全部硬编码，零注册扩展点 |
| 数值健壮性（#347） | `int()` / `float()` 直接转换，`inf`/`nan` 与非数值导致崩溃或错误分桶 |
| 上传清理（#348） | 上传文件名直接拼路径且临时文件从不清理，可路径穿越 |
| 角色冲突（#349） | 角色名与 `Label` 等保留字段同名时状态码互相覆盖，重复角色名丢数据 |
| OWASP / 看板（#350） | 多 OWASP 标签只匹配第一个；风险看板跨 passive/probe/role 来源不去重，计数虚高 |
| CORS / Cookie（#351） | `null` 来源被视为可信、反射来源不识别、多 `Set-Cookie` 未拆分，安全基线漏报 |
| Header / Origin（#352） | 鉴权头可覆盖工具侧 `Origin`，CRLF 与控制字符未拒绝，无 RFC 7230 token 校验 |
| 导出口径（#353） | 各页签各自拼 JSON/CSV，字段口径不一，导出缺 config snapshot / warnings |
| 错误观测（#354） | 请求异常无分类、无截断样本标记、warnings 不集中反馈 |
| **e2e 回归新发现（#355）** | **安全默认值 / 运行上限 / 能力计数塞进 `st.expander(expanded=False)`，首屏 body 文本完全读不到「安全默认：仅允许 http/https」**：与接口性能测试页直接渲染的口径不一致，用户按下执行前看不到协议白名单、SSL / 重定向 / 内网拦截与运行上限 |

### 修复方案要点

- **入口与数值健壮性**：`_normalize_interface()` 改由注册中心 `to_int()` / `to_float()` / `clamp_*()` 统一处理，非有限值回落安全默认值，全部 7 个入口补冒烟与数值回归。
- **范围与 SSRF 护栏**：`_select_interfaces()` 区分 `None`（未指定=全选）与 `[]`（明确不选），空范围不发请求、去重与越界过滤；新增 `validate_target_url()`——协议白名单、userinfo/端口校验、内网/回环/链路本地/元数据地址默认拦截（显式开关放行）、默认关闭重定向、默认开启 SSL 校验；`build_probe_headers()` 走 RFC 7230 token 白名单、拒绝 CRLF/控制字符、工具侧强制 `Origin`，禁止鉴权头覆盖；`SecurityLimits` 约束接口 500 / 角色 20 / 请求 400 / 单接口探测 4 / 超时 60s / 总时长 300s / 响应体 512000B，请求前统一校验并在非法目标时转成 finding 而不发请求。
- **请求构造与结果可信**：`quote()` 编码 `path_params`、`raw:` 显式跳过编码、同名 query append 保留多值、list/tuple 用 `urlencode(doseq=True)` 展开，未解析 `{var}` 写入 warnings；`ProbeContext.header()` 大小写不敏感读响应头；配置签名 `_compute_security_signature()` / `_is_result_stale()` 在结果工作台醒目提示「结果可能已过期」；导出统一附 `config_snapshot` / `input_signature` / `registry_summary`；`stream=True` + `_read_response_body()` 限制响应体，记录 `error_type`（timeout / ssl_error / connection_error / dns_error / invalid_request / unknown）、`truncated` 样本、`truncation` 明细与集中 `warnings` 面板；Markdown 报告补发现项明细与告警章节。
- **导出安全**：`_sanitize_csv_frame()` 对所有 CSV 单元格按 `= + - @ \t \r` 前缀加 `'` 防公式注入；Nuclei 模板 header 名白名单校验、变量名带唯一序号后缀、路径换行/控制字符清理；`build_export_payload()` 与页面 `_build_download_payload()` 统一输出 plan / passive / probe / role / matrix / checklist / nuclei / dashboard / suite / warnings / truncation / config_snapshot / input_signature / registry_summary，下载页签只读已有结果，绝不隐式发请求。
- **页面与可读性**：上传文件名 `os.path.basename()` + 后缀白名单清洗并在 `finally` 删除临时文件；注册式 `build_text_summary()` 给 12 个结果页签补中文结论；结构化 `Role Codes` 隔离保留字冲突并保留历史平铺列兼容契约；`match_owasp_codes()` 支持 `API8:2023,API5:2023` 多标签，风险看板按 `(Category, Title, Target, Evidence)` 跨来源去重并写 `duplicate_merged` / `Sources`；CORS `null` / 反射来源与多 `Set-Cookie` 拆分检测；`RAW_FORMAT_MAP.get(..., "auto")` 避免老 session 触发 KeyError。
- **SEC-22 补强（e2e 新发现）**：把安全默认值 / 运行上限 / 能力计数的 `st.caption` 从默认折叠面板移到首屏直接渲染，仅 18 项明细 metric 保留可折叠，与接口性能测试页同一呈现口径；补 `test_sec_22_security_defaults_rendered_on_first_screen` 源码契约回归与 e2e 首屏断言双重验证。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/api_security_registry.py`——HTTP 方法、鉴权头名、敏感字段、错误标记、各类 HINTS、OWASP 条目、被动审计规则、基线探测规则、严重级别、角色等级、状态码分桶、套件/期望文案、结果页签、摘要指标、探测策略、Nuclei 模板、CSV 清洗器、运行上限、安全默认值全部提供 `register_*` / `configure_*` / `get_*` 扩展点；frozen dataclass Spec、查询返回副本、重复注册需 `replace=True`、`reset_security_registry()` 保证测试隔离；页面能力摘要、下拉、按钮、页签与导出结构全部注册表驱动。

### 专项验证

- 专项回归 `tests/test_audit_security.py`：22 passed（逐条对应 #334-#355，含 e2e 新发现的 SEC-22）
- 全量 pytest：485 passed（独立 `--basetemp` 规避沙箱 `pytest-of-unknown` 残留 EEXIST）
- e2e（新增 `14-api-security.e2e.ts`：注册能力摘要与安全默认 / 范围护栏与空选择不发请求 / 方案+被动审计全链路不崩溃 / 下载页签不隐式探测）：4/4 passed，全套 **56/56 passed**
- GitHub：issues #334-#355 全部评论并关闭，PR #356 已合并，仓库 open issues = 0


## 接口研发辅助工具专项审计（2026-11-26，Issues #357-#387）

### 审计范围与方式

- 对象：`src/qa_toolkit/core/api_dev_tools.py`（InterfaceDevTools 全量执行引擎：接口变更对比 / 标准化导出 / 文档质量体检 / 回归清单 / 断言模板 / Mock 服务脚本 / 请求代码片段）+ `src/qa_toolkit/ui/pages/api_dev_tools_page.py`（Streamlit 七页签工作台：标准化导出、回归清单生成、接口变更分析、接口文档体检、断言模板生成、Mock 服务生成、请求代码片段）+ 共享解析器 `src/qa_toolkit/core/api_test_core.py`（`parse_content` 远程文档拉取）。
- 方式：**两轮走查**。第一轮把候选问题写成 `.qa-audit/dev_repro.py` 实测坐实 21 项（DEV-01 ~ DEV-21，#357-#377）；完成注册式重构后，从测试专家 + 产品工程师视角对**重构后的代码**做二次走查，写 `.qa-audit/dev_round2_repro.py` 又坐实 10 项（DEV-22 ~ DEV-31，#378-#387），共 **31 项**。第二轮专门验证「重构没有覆盖到的边界」，例如字符串归一化篡改、`json.dumps` 生成的 Python 片段运行时崩溃、内联 `<script>` 闭合、远程拉取 SSRF、`True == 1` 掩盖类型变更、深层差异只报顶层 key 等。
- 视角：测试专家关注正确性（数据保真、URL 构造、类型比较、深层差异、循环引用、严格 JSON）、安全性（代码注入、Header CRLF、SSRF、XSS、CSV/Markdown 注入、路径穿越）、边界（运行上限、截断、非法状态码）；产品工程师关注**拓展性、易用性**（注册式扩展点、首屏安全默认值、结果过期反馈、文字摘要、统一导出快照、状态码分桶），不局限于当前业务。
- 修复分支 `fix/api-dev-tools-audit`（commit `478a5cc`），PR #388 已合并至 `master`（merge commit `31cc51e`）；全套 e2e 60/60 通过。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 调试代码默认关闭 SSL（#357） | Python requests 片段固定输出 `verify=False`，复制到真实项目即静默关闭 HTTPS 证书校验 |
| method 代码注入（#358） | `method='GET\nimport os; os.system(...)\nrequests.get'` 真的生成独立 `os.system(...)` 语句；接口文档来自上传文件，属不可信输入 |
| 未知语言静默回落（#359） | `language='Go'` 仍返回 `import requests ...`，无告警；语言/渲染器/后缀/高亮在 core 与 page 两处硬编码 |
| URL 构造（#360/#361） | `path_params={'id':'1/../../admin?debug=1#frag'}` 直接改变请求路径；同名 query 被覆盖、list 被 `str()` 成 `"['c','d']"` |
| 危险协议（#362） | `base_url='file:///etc/passwd'` 仍生成 curl，无协议白名单 / userinfo / 内网校验 |
| Mock 服务（#363~#366） | 自定义响应头只留两个固定 key 且静默丢弃；生成脚本无请求体/响应体上限；Header CRLF 未过滤；默认监听 `0.0.0.0`、CORS `*`、`port='abc'` 无反馈 |
| 稳定性（#367） | 循环引用 body 触发 `RecursionError`；断言风格与 `max_depth` 无校验 |
| 导出与页面（#368~#376） | Markdown/结构化文本注入、CSV 公式注入、上传文件名路径穿越且临时文件不删除、`RAW_FORMAT_MAP[...]` KeyError、复制按钮 `button_text` 未转义、结果过期无提示、7 个 dataframe 页签无文字结论、导出无 config snapshot / signature / warnings、无运行上限与截断告警、重复 method+path 被字典推导静默覆盖 |
| 拓展性（#373） | 质量规则、评分权重、词表、清单文案、优先级、Mock 默认值、运行上限全部硬编码，零注册扩展点 |
| **二次走查：数据保真（#378）** | `_normalize_value` 对所有字符串 `strip()`，`body={'token':'  ABC  '}` 归一化成 `'ABC'`，差异对比因此漏报真实变更 |
| **二次走查：Python 片段（#379）** | `json.dumps` 输出 `payload = {"enabled": true, "note": null}`，`compile()` 能过但运行 `NameError: name 'true' is not defined` |
| **二次走查：XSS（#380）** | `_create_copy_button('</script><img src=x onerror=alert(1)>')` 生成的 HTML 含裸 `</script>`，可提前闭合脚本块 |
| **二次走查：SSRF（#381）** | `parse_content` 贴 `http://169.254.169.254/latest/meta-data/` 即 `requests.get`，无内网/元数据拦截，也不校验重定向目标 |
| **二次走查：差异定位（#382/#383）** | `_describe_value_change(True, 1)` 返回「无变更」；`user.profile.level` 从 1 改成 2 只报「字段值变化: user」，无法定位深层字段 |
| **二次走查：参数与状态码（#384/#385）** | `path='/users/{id}'` + `parameters={'id':'7','verbose':'1'}` 让 `id` 混进请求体；`expected_status=99999` 体检零提示，也无 2xx/4xx/5xx 分桶 |
| **二次走查：URL 与 JSON（#386/#387）** | `_normalize_path('api/v1/users?page=1')` 保留 query，构造出双份 `?`；`NaN` 直接进导出 JSON，严格解析抛 `ValueError: NaN` |

### 修复方案要点

- **调试代码与 Mock 安全**：新增 HTTP 方法白名单与 `requests.request("METHOD", ...)` 参数化兜底，历史 `requests.post(` 契约靠 `REQUESTS_VERBS` 注册表保持兼容；默认 `verify=True`；`quote()` 编码 path_params + `raw:` 显式跳过 + 同名 query append + list doseq 展开 + 目标地址协议/userinfo/端口/内网护栏；Mock 脚本改静态模板 + `__QA_DEV_*__` 占位符，内置请求体/响应体/头/路由上限、413 处理、Header 清洗、默认 `127.0.0.1` 与安全 CORS 来源；端口/延迟钳制并写明确告警（同时修正默认端口 `0` 被钳成 `1` 的问题）。
- **两轮新发现的安全边界**：Python 渲染器改用 `format_python_literal()` 输出合法字面量 `True/False/None`；内联 `<script>` 字符串统一转义 `<`/`>`/`&`/U+2028/U+2029，杜绝 `</script>` 闭合；`api_test_core.py` 的 `_fetch_remote_content()` 复用目标地址校验，逐跳校验重定向、默认拒绝内网/元数据，页面提供「允许从内网/本地 URL 导入 Swagger 文档」显式开关并在首屏展示默认值；`_normalize_value` 不再 strip，非有限浮点清洗为 `null`，导出统一 `strict_json_dumps(..., allow_nan=False)`。
- **差异与契约正确性**：重复 method+path 分组逐条精确配对，无法配对的定义显式计入新增/删除并告警；`_describe_value_change` 先判类型再比值，bool/int/float 互换一律高风险；`_collect_field_changes()` 递归输出点号字段路径并受注册式 `max_field_paths` 上限约束；`parameters` 回落时剥离路径占位符；相对路径用 `urlparse` 拆出 path/query/fragment，原有 query 合并到 `query_params` 并写告警；循环引用用 visited id 集合压缩、深度上限钳制。
- **状态码与可读性**：新增注册式 `StatusCodeBucketSpec`（1xx/2xx/3xx/4xx/5xx），`invalid_expected_status` 定为高风险、`unexpected_status_bucket` 给 4xx/5xx 显式提示，分桶写入体检 summary 与回归清单 `status_bucket` 列；**高风险结论补进 `text_summary`**，不再只躺在 dataframe（canvas）里；注册式 `build_text_summary()` 给七个页签补中文结论；配置签名 + 结果过期醒目提示；统一导出 `config_snapshot` / `input_signature` / `registry_summary` / `warnings` / `truncation`。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/api_dev_registry.py`——HTTP 方法、代码片段语言/渲染器/下载后缀/高亮、断言风格、质量规则与评分权重、严重级别/风险等级、健康阈值、词表、清单文案、优先级策略、Mock 默认响应头与白名单、CSV/Markdown/结构化文本清洗器、协议白名单、Header 校验、状态码分桶、`DevLimits` 运行上限全部通过 `register_*` / `configure_*` / `get_*` 暴露；frozen dataclass Spec、查询返回副本、重复注册需 `replace=True`、`reset_dev_registry()` 保证测试隔离；页面能力摘要、radio、下载后缀、高亮语言、状态摘要全部注册表驱动。

### 专项验证

- 两轮复现脚本：`.qa-audit/dev_repro.py` 修复前 21/21 坐实、修复后 **0/21**；`.qa-audit/dev_round2_repro.py` 修复前 10/10 坐实、修复后 **0/10**（4 条静态口径已改为语义断言：自定义头显式告警、Markdown 无独立注入标题行、CSV 全部走 `_csv_bytes`、重复定义显式列出）。
- 专项回归 `tests/test_audit_dev.py`：**31 passed**（逐条对应 #357-#387）；`tests/test_audit_core_regressions.py` 的 Mock 脚本哈希随安全加固更新为 `cbb48436…`，并补可编译 + 资源护栏 + 安全默认值语义断言。
- 全量 pytest：**516 passed**（独立 `--basetemp` 规避沙箱 `pytest-of-unknown` 残留 EEXIST）。
- e2e（新增 `15-api-dev-tools.e2e.ts`：首屏注册能力/安全默认与 SSRF 开关 / 标准化文字结论与结果过期 / 代码片段内网拦截与 SSL 默认 / 体检非法状态码可读结论）：4/4 passed，全套 **60/60 passed**。
- GitHub：issues #357-#387 全部逐条评论并关闭，PR #388 已合并（merge commit `31cc51e`），仓库 open issues = 0。


## 接口自动化测试工具专项审计（2026-11-26，Issues #389-#423）

### 审计范围与方式

- 对象：`src/qa_toolkit/core/api_test_core.py`（InterfaceAutoTestCore：多格式解析、用例/脚本生成、执行、简要 HTML 报告）+ `src/qa_toolkit/ui/pages/api_automation_page.py`（Streamlit 工作台：示例/导入 → 预览 → 配置/环境/鉴权 → 生成/执行 → 结果导出）+ `src/qa_toolkit/reporting/report_generator.py`（EnhancedReportGenerator 详细 HTML 报告）+ 被「接口研发辅助」复用的共享解析器链路。
- 方式：**三轮走查**。第一轮把候选问题写成 `.qa-audit/auto_repro.py` 实测坐实 24 项（AUTO-01 ~ AUTO-24，#389-#412）；完成注册式重构后，写 `.qa-audit/auto_round2_repro.py` 对**重构后的代码**做 23 项边界探针（生成脚本注入/可执行性、报告与导出安全、断言/JSON/URL/注册中心隔离），坐实 AUTO-25；全套 e2e 又抓到由本轮修复引入的跨模块回归 AUTO-26；第三轮合并后台独立审计的 9 个新发现，写 `.qa-audit/auto_round3_repro.py` 坐实 AUTO-27 ~ AUTO-35（#415-#423）。共 **35 项**。
- 视角：测试专家关注正确性（递归断言假绿、统计篡改、非法状态码、严格 JSON、URL 编码、运行上限）、安全性（XSS、凭据明文、SSRF、Header CRLF、CSV 公式注入、TLS 默认关闭、上传临时文件不清理）、边界（大数据、循环引用、配置过期）；产品工程师关注**拓展性、易用性**（注册式扩展中心、首屏安全默认值、配置变更过期反馈、纯文字结论、惰性下载、精确清理二次确认），不局限于当前业务。
- 修复分支 `fix/api-automation-audit`，PR 合并至 `master`（PR #424，merge commit `76c2832`）；全套 e2e 64/64 通过。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 详细报告 XSS（#389） | `name='<script>alert(1)</script>'`、`path='/x"><script>…'`、`error` 进 `<pre>`，全文件无 `html.escape`，报告下载后在浏览器打开即执行 |
| 凭据明文（#390） | Bearer token / Basic 密码原样写进 `interface_manifest.json` 的 `config.auth` 与生成脚本 `CONFIG` |
| TLS 与 SSRF（#391/#393/#408） | 默认 `verify=False`；`base_url='http://169.254.169.254/...'` 无协议/内网/元数据校验；Swagger URL 导入缺「允许内网/本地」开关，本地联调被护栏误伤 |
| 注入与路径（#392/#394/#395） | path_params 不 `quote()` 可路径穿越；Header 无 RFC 7230 / CRLF 校验；CSV 单元格以 `= + - @` 开头直接导出 |
| 上传（#396） | 无大小/后缀上限，文件名不隔离，临时文件不删除 |
| 断言假绿（#397） | `compare_standard()` 跳过所有嵌套 dict/list，`response.data.user.id` 从 1 改成 2 仍判通过 |
| 统计与文件名（#398/#399） | 详细报告用 `test_details` 数量静默改写 `test_results.total`；`detailed_test_report_{秒}.html` 同秒覆盖 |
| 静默回落与非法值（#400/#401/#402） | 未知 method/format/mode 静默回落；`expected_status=99999` 生成永不可能通过的断言；manifest 含 `NaN`/`Infinity` 非法 JSON |
| 上限与签名（#403/#404） | timeout/retry/接口数/响应体无上限；生成签名只签接口清单，改 base_url/鉴权/模板后仍跑旧脚本 |
| 可读性与导出（#405/#406） | 结论只有 `st.dataframe`（canvas 读屏/e2e 读不到）；导出件无 `config_snapshot`/`input_signature`/`registry_summary`/`warnings`/`truncation` |
| 性能与清理（#407/#410） | 每次 rerun 急切构造 13 个模板下载项并写盘生成报告；清理按钮 `shutil.rmtree(test_dir)` 删掉整个共享目录且无二次确认 |
| 拓展性（#409/#411/#412） | 首屏不展示安全默认值与已注册能力；方法/格式/模式/鉴权/模板/上限/镜像全部硬编码，零 `register_*` 扩展点，模板数写死 13 |
| **第二轮：凭据脱敏分支（#413）** | `redact_auth_config()` 在 `enabled=False` 时提前 `return`，「填了凭据没勾启用」或 Basic Auth 只填密码时，token/密码仍明文落盘且 `get_warnings()` 为空 |
| **第二轮：跨模块回归（#414）** | 全套 e2e `15-api-dev-tools` 体检用例稳定失败：共享解析器把 `99999` 回落成 200 后，文档体检结论「高 0 / 中 1 / 低 2」，`不在合法 HTTP 范围（100-599）` 高风险消失 |
| **第三轮：哨兵碰撞（#415）** | `base_url='https://x.example/__CASES_JSON_LITERAL__.com'` 时 `str.replace` 二次污染，`compile()` 生成脚本抛 `SyntaxError` |
| **第三轮：Bruno 解析（#416）** | `build_bruno_template()` 的 `body:json` 块被非贪婪正则截在第一个 `}`，解析出半截 `{"username":"test","password":"123456"` 非法 JSON |
| **第三轮：统计溢出（#417）** | `total=1/passed=5` 时报告仍渲染 `500.0%` 成功率 |
| **第三轮：CSV 清洗绕过（#418）** | `\n/\r/\t/\x00/\u3000` 前缀 + `=1+1` 不被 `sanitize_csv_value` 前置单引号，Excel 仍执行公式 |
| **第三轮：静默清洗（#419）** | `expected_response` 里的 `NaN`/`Infinity` 被清洗为 `null` 但 `manifest.warnings=[]`，用户无感知 |
| **第三轮：注册点空转（#420/#421/#422/#423）** | 断言 comparator、报告模板、导出格式只登记 label 未被产物链消费；内置三种框架渲染器未注册（摘要计数 0）；首屏摘要把「仅登记」项也算作可用能力 |

### 修复方案要点

- **安全默认值与护栏**：新增注册式 `AutomationLimits`（接口/上传/超时/重试/响应体/Header/导出/脚本上限、`default_verify_ssl=True`、`allow_private_targets=False`、`allow_credentials_in_artifacts=False`）；`validate_target_url()` 做协议白名单、userinfo、端口、内网/回环/链路本地/元数据拦截；`sanitize_headers()` 按 RFC 7230 校验 Header 名并拒绝 CRLF/控制字符，非法头写 warnings 而非静默透传；`quote()` 编码 path_params + `raw:` 显式跳过 + 同名 query append + list doseq 展开；上传加大小/后缀白名单、uuid 文件名与 `try/finally` 删除。
- **凭据脱敏**：`redact_auth_config()` 统一清空 `token`/`password`/`api_key_value`/`custom_header_value`，生成脚本运行时通过 `credential_env_vars` 环境变量注入；**第二轮修正**：无论 `enabled` 是否为真都先脱敏，只有启用时才生成环境变量映射，堵住「填了凭据没勾启用」的明文落盘分支。
- **报告与导出安全**：详细/简要 HTML 全字段 `html.escape()`（含 `<pre>` 与属性上下文），method class 只用清洗后 slug；文件名加 `uuid4().hex[:8]`；CSV 统一 `sanitize_csv_value()` 前置 `'`；Markdown 单元格转义换行/管道符；`strict_json_dumps(allow_nan=False)` 把 `NaN`/`Infinity` 清洗为 `null` 并递归深度保护。
- **正确性与结果可信**：`compare_response()` 递归结构化比对 `smoke`/`standard`/`strict`，输出 `response.data.user.id` 点号路径，先比类型再比值（`True == 1` 不假绿），受深度/字段数上限约束；报告统计一律以 `test_results.total/passed/failed/errors` 为准，明细缺失只提示覆盖率；非法 `expected_status` 回落 200 并写 `status_bucket`/`status_valid`；**第二轮跨模块保真**：同时保留 `raw_expected_status` 原始值，`api_dev_tools` 体检/回归清单据此继续判高风险，生成脚本仍用 200。
- **状态反馈与易用性**：`_current_config_signature()` 把接口清单 + 执行模式/base_url/timeout/retry/verify_ssl/请求格式/模板风格/环境/鉴权/SSRF 开关/凭据开关一起签名，改配置后产物与结果显式标「已过期」；`build_text_summary()` 渲染纯文字结论；导出件带 `config_snapshot`/`input_signature`/`registry_summary`/`warnings`/`truncation`；HTML 报告与下载项按结果签名惰性缓存；清理只删 `get_known_generated_files()` 列出的产物并二次确认。
- **拓展性（重点）**：新增 `src/qa_toolkit/core/api_automation_registry.py`——HTTP 方法、请求格式、执行模式、框架渲染器、鉴权方式、模板风格、断言策略、状态码分桶、镜像源、导入模板、报告模板、导出格式、运行上限、协议白名单、Header 清洗器、HTML/Markdown/CSV 转义器、文字摘要模板全部注册化；frozen dataclass Spec + 查询返回副本 + `replace=True` 覆盖 + `reset_automation_registry()` 测试隔离；页面下拉框、镜像源、模板下载项、鉴权 label 映射、首屏能力摘要全部注册表驱动。
- **第三轮（#415-#423）**：① 生成脚本改用 `encode_json_literal()` 的 base64 表达式注入 CONFIG/CASES，base64 字母表不含下划线，从根本上杜绝哨兵二次替换（同时让历史三单引号注入用例更安全）；② `_extract_braces_block()` 用花括号配对（含字符串内引号判定）替代非贪婪正则，Bruno `body:json` 嵌套 JSON 完整还原；③ 报告统计接入 `normalize_test_stats()` 按比例钳制 + 告警，`success_rate` 上限 100%，杜绝 500%；④ CSV 公式清洗正则覆盖前导空白/控制字符/零宽字符；⑤ `json_warnings()` 把 NaN/Inf/递归深度清洗变成 manifest 可观测告警；⑥ 报告模板/导出格式升级为带 renderer/serializer 的 Spec，页面下载区改由 `get_export_items(ctx)` 驱动，报告头消费 `get_report_templates()`/`get_report_renderer()`；⑦ 内置三种框架渲染器就地注册（延迟 import 断开循环依赖）；⑧ `get_registry_summary()['接入状态']` 区分「已接入产物链」与「仅登记」，首屏只把可用项呈现给用户。

### 专项验证

- 三轮复现脚本：`.qa-audit/auto_repro.py` 修复前 24/24 坐实、修复后 **0/24**；`.qa-audit/auto_round2_repro.py` 修复前 1/23 坐实（AUTO-25）、修复后 **0/23**；`.qa-audit/auto_round3_repro.py` 修复前 9/9 坐实、修复后 **0/9**，三轮合计 35 项全部坐实并修复。
- 专项回归 `tests/test_audit_auto.py`：**35 passed**（逐条对应 #389-#423，含跨模块回归用例）；同步更新 `test_audit_security_injection.py` 的三单引号注入断言以匹配更安全的 base64 注入实现。
- 全量 pytest：**551 passed**（独立 `--basetemp` 规避沙箱 `pytest-of-unknown` 残留 EEXIST）。
- e2e（新增 `16-api-automation.e2e.ts`：首屏注册能力/安全默认值与 SSRF/凭据开关 / 生成阶段内网护栏告警可读 / 配置变更后产物过期 / 执行结果纯文字结论与精确清理二次确认）：4/4 passed，全套 **64/64 passed**；同时加固 07 号正则用例在全套串行下的会话污染，并修复 15 号研发辅助体检因共享解析器改动产生的跨模块回归。
- GitHub：issues #389-#423 全部逐条评论并关闭，PR 已合并（PR #424，merge commit `76c2832`），仓库 open issues = 0。


## 通用缺陷绩效分析重构专项审计（2026-11-26，Issues #425-#435）

### 背景与范围

- 原「禅道绩效统计」直接依赖禅道 MySQL `zt_bug`/`zt_product` 表与 SQL 聚合，绑定单一平台、归因方式写死、无统一模型与扩展点。用户要求重新设计为兼容 JIRA / TAPD / 云效 / 禅道等主流缺陷管理工具的通用能力，并明确「从拓展性、易用性考虑，不要局限于当前业务」。
- 交付架构：`core/tracking_registry.py` 注册中心（数据源 / 连接字段 / 归因 / SLA / 绩效规则 / 运行上限，全部 frozen Spec + 返回副本 + `replace` + `RLock` + `reset`）；`integrations/tracking/` 统一模型与 `TrackingAdapter` 协议、纯 Python 绩效/SLA 规则引擎；5 个适配器（禅道直连 DB、禅道 HTTP 代理、JIRA REST、TAPD Open API、云效 OpenAPI，HTTP 适配器可注入 transport）；通用页面 `tracking_performance_page.py` 与首页工具入口。
- 设计完成后按用户要求，以**测试专家 + 产品工程师**双视角再审一遍，问题不局限于 bug，覆盖正确性、安全性、易用性与拓展性，共坐实 11 项（TRACK-01~11 / #425-#435）；其中 TRACK-11 由新增 e2e 在浏览器层抓到。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 首屏不可用（#425） | 通用页面调用 `show_doc()` 但未导入，AppTest 异常 `name 'show_doc' is not defined`，全部功能不可达 |
| SLA 多算 1 小时（#426） | `compute_effective_hours(9:00, 12:00)` 返回 `4.0`（闭区间），绩效超时判定被整体抬高 |
| 角色链路空转（#427） | `QuerySpec(roles=('开发B',))` 仍返回 2 人；页面只有 `for ...: pass` 空循环，角色标签恒为 `—` |
| 凭据明文（#428） | 禅道 DB / 代理适配器 `self.config = cfg` 保存明文密码 / token，与 HTTP 适配器脱敏行为不一致 |
| 注册点空转（#429） | `register_performance_dimension()` 可注册，但全仓库无消费者，扩展方看不到任何变化 |
| JIRA 项目键（#430） | `get_connection_fields('jira')` 无 `project_key`，但 roles 路径依赖它，多项目只能取第一个 |
| 自定义 SLA 被遮蔽（#431） | 规则声明 `custom_normal=1`、页面下发 `normal_normal=72`，4 小时项未判超时 |
| HTTP 连接项（#432） | TAPD / 云效无 `timeout_seconds` / `verify_ssl` 字段，内网自签与慢服务无法在页面配置 |
| 误导性指标（#433） | qa / dev 归因下「提交数」恒为 0（归因人是 closer/resolver，不是 reporter），与「基数」口径自相矛盾 |
| 文档残留（#434） | 通用页面首屏仍展开「禅道绩效统计工具使用说明 / 数据库配置指南」，误导 JIRA/TAPD/云效用户 |
| **e2e 新发现：连接反馈（#435）** | 默认禅道配置缺用户名时点「连接并加载」，只显示「请先确认 禅道直连数据库适配器初始化失败…」，没有明确的连接失败结论 |

### 修复方案要点

- **架构**：注册中心 + 统一模型 + 适配器协议 + 纯 Python 规则引擎，页面只消费注册表；禅道旧页面与旧测试保持零回归。
- **正确性**：SLA 改半开区间 `[start, end)`，不足整小时按实际占比计入；角色过滤按 `Person.match_values` 生效，角色元数据构造 `Person` 传入引擎；自定义 SLA 键优先于 legacy 键；移除与归因口径冲突的「提交数」列，仅保留自洽的「基数 / 超时响应率」。
- **安全性**：禅道两个适配器统一走 `redact_connection_config()`，明文只用于建立连接 / 构造客户端，不留在可序列化属性上。
- **易用性与拓展性**：页面补齐角色多选与真实角色标签；绩效维度接入页面展示；`project_key`、TAPD / 云效 `timeout_seconds` / `verify_ssl` 全部改为声明式连接字段；通用文档条目替代禅道专属说明；连接失败统一用 `render_error_feedback("数据源连接失败：<原因>")` 给出明确结论，并缓存项目元数据减少 rerun 重复请求。

### 专项验证

- 复现脚本 `.qa-audit/tracking_repro.py`：修复前 **11/11 坐实**，修复后 **0/11**。
- 新架构契约测试 `tests/test_tracking_registry.py`、`tests/test_tracking_adapters.py`、`tests/test_tracking_rules.py`、`tests/test_tracking_performance_page.py`：60 passed；5 个禅道旧测试文件与 `test_tool_routes.py` 零回归，专项合计 **87 passed**。
- 全量 pytest：**611 passed**。
- e2e（新增 `17-tracking-performance.e2e.ts`：多数据源注册摘要与通用文档 / 连接失败明确结论且无异常）：2/2 passed，全套 **66/66 passed**。
- GitHub：issues #425-#435 全部逐条评论并关闭，PR #436 已合并（merge commit `c2af82b`），仓库 open issues = 0。

## 外部 MCP 消费层专项审计（2026-11-26，Issues #437-#446）

### 背景：从「把自己暴露成 MCP」改为「消费外部 MCP」

用户明确指出本机 Codex 已经接了云效 MCP，真实诉求是 **qa-toolkit 作为 MCP 客户端** 去消费外部能力：用禅道 / 云效 MCP 拿需求和缺陷，用飞书 / 蓝湖 MCP 读设计文档，再把非结构化需求变成可测试的结构化输入。因此不再先做 fake server，而是按真实协议对接。

已确认的真实配置（**凭据只引用环境变量，不复制值**）：

| 服务 | 形态 | 定义 | 用途 |
| --- | --- | --- | --- |
| 云效 | stdio | `npx -y alibabacloud-devops-mcp-server --toolsets=project-management` | 需求 / 任务 / 缺陷 / 评论 / 状态流转 |
| 蓝湖 | HTTP | `http://10.0.6.111:8000/mcp?role=测试&name=Lucas` | 设计标注与交互说明 |
| 禅道 | stdio | `mcp-zentao-11-3`（Cursor 已接） | 需求 / 任务 / 缺陷 |
| MasterGo | stdio | `@mastergo/magic-mcp` | 设计稿，与蓝湖同类 |
| 数据仓库 | stdio | 只读 MySQL MCP | 缺陷证据复核 |

云效实战经验被固化为语义映射规则：标题搜索优先、`viewIdentifier` 不是工作项 ID、精确编号才用描述字段检索、状态流转必须遵守 `30→29→100085`。

### 交付架构

- `core/mcp_client_registry.py`：stdio / HTTP 两类外部 Server 注册化；凭据只登记环境变量名，命令参数用 `${ENV}` 占位；frozen Spec、返回副本、`replace` 覆盖、`RLock`、`reset` 隔离。
- `core/mcp_config_import.py`：只读导入 Codex `config.toml` 与 Cursor `mcp.json`；明文凭据在导入瞬间替换为环境变量引用；别名归并 + 业务域过滤。
- `integrations/mcp/`：`StdioTransport`（逐行 JSON-RPC，跳过噪声）/ `HttpTransport`（JSON 与 SSE）、受控 `McpClient`、`ExternalCapabilitySpec` 语义映射与不可信内容隔离。
- `ui/components/mcp_import_panel.py`：用例生成器新增「从外部 MCP 导入需求 / 设计标注」入口，参数化 `target_key`，后续模块可直接复用。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 重复数据源（#437） | 导入后同时存在 `mastergo` / `mastergo-magic-mcp`、`zentao` / `zentao-11`、`adb_mysql` / `adb-mysql-mcp-server` |
| 写操作可绕过（#438） | 不经页面直调 `update_work_item` 返回 `ok=True`，UI 二次确认是唯一防线 |
| 工具缓存串源（#439） | 云效发现的工具在切到蓝湖后仍保留，可导致跨源误调用 |
| 候选静默截断（#440） | 25 条候选只显示 10 条，无任何总数提示 |
| 编号误判（#441） | `build_search_arguments('手机号 123')` 走 `subjectDescription` 宽泛搜索 |
| 文本无上限（#442） | 80 万字符外部描述原样进入用例生成器，无截断无告警 |
| stdio 噪声（#443） | stdout 混入 `npm warn deprecated` 后整次调用失败 |
| trace 泄密（#444） | `token=abc…; password=…` 字符串值原样写进 trace |
| 缺凭据无提示（#445） | 选中云效后不提示缺哪个环境变量，点到调用才报模糊错误 |
| 导入无过滤（#446） | 一次导入 14 项，playwright / GitHub / Excel 等淹没业务数据源 |

### 修复方案要点

- **架构**：只读导入 + 语义映射，外部 tool 名与本地槽位解耦；换 MCP 提供商只改映射。
- **安全**：写操作在客户端层默认拒绝，需显式 `allow_write`；按键名与字符串模式双重脱敏；HTTP 目标复用既有 SSRF 校验，私网默认拒绝；外部内容一律 `untrusted` 并做提示词注入检测。
- **正确性**：server 切换清空工具缓存；编号识别收紧为 `XX-1234` 或独立长编号；stdio 只接受与请求 id 匹配的 JSON-RPC 响应。
- **易用性**：别名归并、业务域过滤、候选总数提示、缺失环境变量提前展示。

### 专项验证

- 复现脚本 `.qa-audit/mcp_repro.py`：修复前 **10/10 坐实**，修复后 **0/10**。
- 契约测试 `tests/test_mcp_external.py`：27 passed（含 AppTest 页面冒烟）；用例生成器页面零回归。
- 全量 pytest：**638 passed**。
- e2e（新增 `18-mcp-import.e2e.ts`）：2/2 passed，全套 **68/68 passed**（首次运行一条既有「文本对比工具」导航时序用例偶发失败，重跑全绿，与本次改动无关）。
- GitHub：issues #437-#446 全部逐条评论并关闭，PR #447 已合并（merge commit `52ec407`），仓库 open issues = 0。

## 数据生成工具专项审计（2026-11-26，Issues #448-#460）

### 范围与视角

对 `tools/data_generator.py`（964 行单类）、主页面的 7 个基础生成入口 / Faker 高级生成器 / 4 个结构化造数场景 / 6 类边界值生成器做专项测试。以**测试专家 + 产品工程师**双视角设计独立探针 `.qa-audit/data_gen_repro.py`，不局限于 bug，同时覆盖数据质量、安全、易用性与拓展性，共坐实 **13 项问题（DG-01~13 / #448-#460）**。其中第 13 项是全套 e2e 连跑时暴露的工具切换时序问题，单跑不复现，属于连续会话下的真实易用性风险。

### 关键实测证据（修复前）

| 问题 | 实测结果 |
| --- | --- |
| 密码长度溢出（#448） | 请求 2 位、勾选 4 类字符，实得 4 位；备用实现先塞 4 类各 1 位，`range(2-4)` 直接跳过补齐 |
| 手机号位数漂移（#449） | `generate_random_phone_number('移动')` 300 次出现 11 位与 12 位；`1703/1705/1706` 为 4 位号段却固定补 8 位 |
| 未来出生日期（#450） | `min_age=0`、参考时刻 2026-01-01，种子 66 生成 `20260810`，年龄实为 -1 |
| 年龄区间底层异常（#451） | `min_age=60, max_age=18` 抛 `empty range for randrange`，无可读参数校验 |
| Faker 身份证绕过约束（#452） | 固定 `ssn()` 为 1990 男后，指定 60-70 岁仍原样返回；页面却宣称“严格符合” |
| seed 失效（#453） | 传 `seed=20261126` 两次生成姓名完全不同，无法复现回归数据 |
| 未知组合静默（#454） | 不存在的类别 / 子类别返回空列表，内部异常也被包装成“数据”文案 |
| 性别凭空补值（#455） | `sex='X'` 输出“性别： 男”，字符串 website 被逐字符拼接 |
| HTML 未转义（#456） | 生成结果直接拼进 `unsafe_allow_html` 的 `<div class="result-box">` |
| 无注册扩展点（#457） | 场景清单在 4 处硬编码，新增业务场景需改 964 行单类并发版 |
| locale 写死（#458） | 类支持任意 Faker locale，页面固定 `zh_CN` |
| 边界反例矛盾（#459） | `min_length=1` 时“长度不足”样例长 1 位，同批“最小长度边界”却标“应通过” |
| 工具切换偶发失效（#460） | 三次全套 e2e 分别落在图片处理、JSON、外部 MCP 三个不同用例；点击卡片后仍停留在默认数据生成页，单跑全部通过 |

### 修复方案要点

- **拓展性**：新增 `core/data_generator_registry.py`，造数场景 / 边界字段 / 生成地区均为 frozen Spec；getter 返回副本、`replace` 显式覆盖、`RLock`、`reset` 测试隔离；内置项默认注册，外部扩展可零改造接入。页面首屏展示注册摘要。
- **正确性**：手机号统一按 `11-len(prefix)` 补位；身份证出生日期不晚于参考时刻且按参考日精算年龄；Faker 身份证过地区 / 性别 / 年龄 / 校验位后才采用，否则回退受控生成；密码长度与复杂度冲突显式报错。
- **易用性**：Faker 模式补随机种子与参数变化自动清结果；结果渲染按生成时的类别而非当前选择；未知组合抛出可读错误；地区可切换；非法数值区间阻止生成。
- **安全与数据质量**：所有动态内容 `html.escape()` 后拼 HTML；未知性别显示“未知”而非猜测；边界反例与自身规则保持一致。
- **连续会话稳定性**：工具卡片桥接层在隐藏按钮未就绪时限时重试（20 次 × 60ms）并用 pending 标记防重复派发，点击不再被渲染时序吞掉。

### 专项验证

- 复现脚本 `.qa-audit/data_gen_repro.py`：修复前 **13/13 坐实**，修复后 **0/13**。
- 专项测试 `tests/test_data_generator.py` + `tests/test_data_generator_audit.py`：23 passed（含注册表契约、导航桥与 AppTest 页面冒烟）。
- 全量 pytest：**652 passed**。
- e2e（新增 `19-data-generator.e2e.ts`）：2/2 passed，全套 **70/70 passed**（修复导航桥后连续会话不再出现丢点击）。
- GitHub：issues #448-#460 全部逐条评论并关闭，PR #461 已合并（merge commit `91abeaa`），仓库 open issues = 0。

## 国际化（i18n）语言切换功能交付与验收（2026-11-26）

### 需求与定位

新增界面多语言能力：手动切换简体中文 / 繁體中文 / English / 한국어，并按访问者 IP 归属国家自动定位语言（例：美国 → English）。与前面几轮「审计 → issue → PR」专项不同，本次是功能交付，但仍按**拓展性 + 易用性**两条线做设计与验收；因不存在待修问题故未创建 issue，改动经 PR #462 合并入 master（merge commit `d41be8d`），仓库 open issues 保持 0。

### 设计要点

- **原文即键**：`core/i18n.py` 以简体中文原文作翻译键，未命中自动回退原文，新增页面零改造即可运行，避免一次性改写约 1.2 万行界面文案带来的大面积回归。
- **注册式扩展**：`LocaleSpec` / `register_locale()` / `register_translations()` / `register_tool_doc()` 与 `register_country_locale()` 沿用项目既有的 frozen Spec + 显式 `replace` + `RLock` + getter 返回副本惯例；词库外置 `config/locales/*.json`（四语言各 305 条词条 + 整篇工具文档槽位）。外部插件可补词条、补国家映射、甚至新增语种，不用改主入口。
- **优先级链**：`resolve_locale()` 统一「手动 `?lang=` > 浏览器本地偏好 > IP / 浏览器自动检测 > 默认 zh-CN」。手动切换写入 URL 与 localStorage；自动定位只在无 `lang` 参数时执行，用 sessionStorage 去重，超时/失败静默回退，不会反复刷新或卡住页面。
- **隐私与安全**：自动定位只取国家码，不读取、不保存 IP；`_json_for_js()` 转义 `<` 防止闭合 `</script>`；所有进入 `unsafe_allow_html` 的动态文案走 `th()`（翻译 + `html.escape`）；工具名保持中文内部路由键不变，仅展示层映射，避免破坏 `PAGE_TOOL_CONFIG` 路由与既有定位器。
- **覆盖面**：主入口 hero、工具切换器 / 卡片 / 横幅、结果展示区、数据生成整页（Faker + 7 个基础生成器）、反馈面板、作者侧栏、工具页外壳与文档组件全部接入 `t()` / `th()`；下拉项用 `format_func=t` 同步翻译。

### 验收证据

- 新增 `tests/test_i18n.py`：15 passed，覆盖四语言词条、原文回退、别名归一（`zh-Hant` / `en` / `ko` 等）、优先级与手动覆盖、国家映射注册、路由键稳定、AppTest 四语言渲染，以及自动定位脚本的 XSS 防护。
- AppTest 全应用冒烟：`?lang=` 为空 / `en-US` / `ko-KR` / `zh-TW` 均无异常，hero 分别为「测试工程师 / QA Engineer / QA 엔지니어 / 測試工程師」，侧边栏标签分别为「界面语言 / Interface language / 인터페이스 언어 / 介面語言」。
- 手动切换交互：侧边栏选择 `en-US` / `zh-TW` / `ko-KR` 后，`session_state` 值、侧边栏标签、hero 文案与 `?lang=` 参数同步生效，证明手动选择优先级真实可用（非仅 URL 注入）。
- 全量 pytest：**667 passed**（此前 652 + 本次 15），0 failed / 0 error。
- e2e：全套 **70/70 passed**（19 个测试文件，4m8s），中文定位器未受 i18n 改造影响。
- GitHub：分支 `feat/i18n-locale-switcher`（远端 commit `49c82e1`），PR **#462** 已合并（merge commit `d41be8d`）；本次为功能交付无对应 issue，open issues = 0。

### 顺带修复的基础设施问题

- **依赖缺陷（真实可复现）**：`requirements.txt` 未锁定 `pyarrow`，venv 中被升级到 26.0.1，与锁定的 `numpy==1.26.3` 冲突（`pyarrow requires NumPy 2.0 or newer`），导致 20 个用例中 `st.dataframe` 连锁报错、`st_cropper` 直接抛 `StreamlitAPIException`。已降级 pyarrow 至 17.0.0 并在 `requirements.txt` 显式 pin，避免新环境按 README 的 `pip install -r requirements.txt` 安装后必现。
- **沙箱临时目录噪声**：40 个 `tmp_path` 用例因宿主 broker 对 `/private/var/folders/.../T/pytest-of-root` 报 `EEXIST` 而 error，属运行环境限制；改用工作区内 `--basetemp` 后全部通过，非代码问题。
- **回归断言适配**：`test_tool_card_icons.py` 与 `test_dg09` 两条源码字符串断言随 i18n 改写更新，并补了 `th("<script>alert(1)</script>")` 的运行时转义断言，XSS 防护语义未被削弱。

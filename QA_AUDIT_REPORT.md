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

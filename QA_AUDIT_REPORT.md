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

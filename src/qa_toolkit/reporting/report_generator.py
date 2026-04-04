# enhanced_report_generator.py (优化版本)
import os
import json
import time
import datetime
from typing import Dict, List, Any
import streamlit as st

from qa_toolkit.paths import REPORTS_DIR


class EnhancedReportGenerator:
    """增强的测试报告生成器 - 优化版本"""

    def __init__(self):
        self.report_dir = str(REPORTS_DIR)
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_detailed_report(self, test_results: Dict[str, Any],
                                 framework: str,
                                 interfaces: List[Dict[str, Any]] = None,
                                 test_details: List[Dict[str, Any]] = None) -> str:
        """生成详细的HTML测试报告 - 修复单用例统计问题"""

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 修复时间统计
        start_time = test_results.get('start_time', time.time())
        end_time = test_results.get('end_time', time.time())
        duration = end_time - start_time

        # 修复统计信息计算 - 基于实际测试详情
        if test_details is None:
            test_details = test_results.get('test_details', [])

        # 关键修复：基于实际测试详情计算统计
        actual_total = len(test_details)
        passed = 0
        failed = 0
        errors = 0

        for detail in test_details:
            status = detail.get('status', 'unknown')
            if status == 'passed':
                passed += 1
            elif status == 'failed':
                failed += 1
            elif status == 'error':
                errors += 1

        # 优先使用基于详情的统计，如果详情为空则使用原始统计
        if actual_total > 0:
            total = actual_total
        else:
            total = test_results.get('total', 0)
            passed = test_results.get('passed', 0)
            failed = test_results.get('failed', 0)
            errors = test_results.get('errors', 0)

        # 确保数值有效性
        total = max(total, 0)
        passed = max(passed, 0)
        failed = max(failed, 0)
        errors = max(errors, 0)

        # 重新计算成功率
        success_rate = (passed / total * 100) if total > 0 else 0

        # 验证测试详情数据的完整性
        validated_test_details = self._validate_test_details(test_details, interfaces)

        # 生成详细的HTML报告
        html_content = self._generate_html_template(
            timestamp, duration, total, passed, failed, errors, success_rate,
            framework, validated_test_details, test_results
        )

        report_filename = f"detailed_test_report_{int(time.time())}.html"
        report_path = os.path.join(self.report_dir, report_filename)

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # 记录报告生成信息
            print(f"报告生成成功: {report_path}")
            print(f"统计信息: 接口数={len(validated_test_details)}, 总数={total}, 通过={passed}, 失败={failed}, 错误={errors}")

            return report_path
        except Exception as e:
            print(f"报告生成失败: {e}")
            return ""

    def _generate_fallback_test_details(self, interfaces: List[Dict[str, Any]],
                                        test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成回退的测试详情数据"""
        test_details = []

        total_interfaces = len(interfaces)
        passed_count = test_results.get('passed', 0)
        failed_count = test_results.get('failed', 0)
        error_count = test_results.get('errors', 0)

        # 根据统计结果分配状态
        for i, interface in enumerate(interfaces):
            if i < passed_count:
                status = 'passed'
                status_code = 200
                error_msg = ''
            elif i < passed_count + failed_count:
                status = 'failed'
                status_code = 500
                error_msg = '测试失败'
            else:
                status = 'error'
                status_code = 0
                error_msg = '测试错误'

            detail = {
                'name': interface.get('name', f'接口{i + 1}'),
                'method': interface.get('method', 'GET'),
                'path': interface.get('path', ''),
                'status': status,
                'status_code': status_code,
                'response_time': 0.5 + (i % 10) * 0.1,  # 模拟响应时间
                'headers': interface.get('headers', {}),
                'parameters': interface.get('parameters', {}),
                'response_body': '{}',
                'error': error_msg,
                'assertions': [
                    {
                        'description': '状态码断言',
                        'passed': status == 'passed',
                        'message': '' if status == 'passed' else f'期望200，实际{status_code}'
                    }
                ]
            }
            test_details.append(detail)

        return test_details

    def _validate_test_details(self, test_details: List[Dict[str, Any]],
                               interfaces: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """验证和修复测试详情数据"""
        if not test_details:
            return []

        validated_details = []

        for i, detail in enumerate(test_details):
            # 确保必要字段存在
            validated_detail = {
                'name': detail.get('name', f'接口{i + 1}'),
                'method': detail.get('method', 'GET'),
                'path': detail.get('path', ''),
                'status': detail.get('status', 'unknown'),
                'status_code': detail.get('status_code', 0),
                'response_time': max(detail.get('response_time', 0), 0),
                'headers': detail.get('headers', {}),
                'parameters': detail.get('parameters', {}),
                'response_body': detail.get('response_body', ''),
                'error': detail.get('error', ''),
                'assertions': detail.get('assertions', [])
            }

            # 如果提供了接口信息，尝试匹配和补充数据
            if interfaces and i < len(interfaces):
                interface = interfaces[i]
                if not validated_detail['name'] or validated_detail['name'].startswith('接口'):
                    validated_detail['name'] = interface.get('name', validated_detail['name'])
                if validated_detail['path'] == '':
                    validated_detail['path'] = interface.get('path', '')

            validated_details.append(validated_detail)

        return validated_details

    def _generate_html_template(self, timestamp, duration, total, passed,
                                failed, errors, success_rate, framework,
                                test_details, test_results):
        """生成HTML报告模板 - 修复单用例显示问题"""

        # 数据验证和修正 - 确保显示的数据准确
        total = max(total, 0)
        passed = max(passed, 0)
        failed = max(failed, 0)
        errors = max(errors, 0)

        # 关键修复：如果只有一个接口，确保总数正确
        if total > 1 and test_details and len(test_details) == 1:
            # 如果接口只有一个但总数显示多个，修正为1
            total = 1
            # 根据第一个测试详情的状态重新计算
            if test_details and len(test_details) > 0:
                first_status = test_details[0].get('status', 'unknown')
                if first_status == 'passed':
                    passed, failed, errors = 1, 0, 0
                elif first_status == 'failed':
                    passed, failed, errors = 0, 1, 0
                else:
                    passed, failed, errors = 0, 0, 1

        # 确保总数正确
        calculated_total = passed + failed + errors
        if total != calculated_total and calculated_total >= 0:
            total = calculated_total

        # 重新计算成功率
        success_rate = (passed / total * 100) if total > 0 else 0

        # 生成状态颜色
        status_color = '#28a745' if success_rate >= 80 else '#ffc107' if success_rate >= 60 else '#dc3545'

        # 生成实际测试用例数量信息
        actual_test_count = len(test_details) if test_details else 0
        display_info = ""
        if actual_test_count != total:
            display_info = f'''
            <div class="alert alert-info">
                <strong>📝 测试信息:</strong> 
                实际执行接口: <strong>{actual_test_count}</strong> 个 | 
                统计用例数: <strong>{total}</strong> 个
                {f'<br><small>注: 统计基于实际执行的接口测试</small>' if actual_test_count > 0 else ''}
            </div>
            '''

        return f'''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>接口自动化测试报告</title>
        <meta name="generator" content="InterfaceAutoTestTool"/>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>

    <style type="text/css" media="screen">
    body        {{ font-family: verdana, arial, helvetica, sans-serif; font-size: 80%; }}
    table       {{ font-size: 100%; }}
    pre         {{ white-space: pre-wrap;word-wrap: break-word; }}
    /* -- heading ---------------------------------------------------------------------- */
    h1 {{
        font-size: 16pt;
        color: gray;
    }}
    .heading {{
        margin-top: 0ex;
        margin-bottom: 1ex;
    }}
    .heading .attribute {{
        margin-top: 1ex;
        margin-bottom: 0;
    }}
    .heading .description {{
        margin-top: 2ex;
        margin-bottom: 3ex;
    }}
    .button{{  
        border:1px solid #cccccc;  
        cursor:pointer;  
        margin:10px 5px;  
        height:40px;  
        text-align:center;  
        border-radius: 4px;  
        border-color: #636263 #464647 #A1A3A5;  
        text-shadow: 0 1px 1px #F6F6F6;  
        background-image: -moz-linear-gradient(center top, #D9D9D9, #A6A6A6 49%, #A6A6A6 50%);  
        background-image: -webkit-gradient(linear, left top, left bottom, color-stop(0, #D9D9D9),color-stop(1, #A6A6A6));  
    }}  
    .buttonText{{  
        position:relative;  
        font-weight:bold;  
        top:10px;
        color: #58595B;  
    }}   
    /* -- report ------------------------------------------------------------------------ */
    #show_detail_line {{
        margin-top: 3ex;
        margin-bottom: 1ex;
    }}
    #result_table {{
        width: 99%;
        border-collapse: collapse;
    }}
    #header_row {{
        font-weight: bold;
        color: white;
        background-color: #777;
    }}
    #total_row  {{ font-weight: bold; }}
    .passClass  {{ background-color: #74A474; }}
    .failClass  {{ background-color: #FDD283; }}
    .errorClass {{ background-color: #FF6600; }}
    .passCase   {{ color: #6c6; }}
    .failCase   {{ color: #FF6600; font-weight: bold; }}
    .errorCase  {{ color: #c00; font-weight: bold; }}
    .hiddenRow  {{ display: none; }}
    .testcase   {{ margin-left: 2em; }}

    /* -- css div popup ------------------------------------------------------------------------ */
    a.popup_link {{
    }}
    a.popup_link:hover {{
        color: red;
    }}
    .popup_window {{
        display: none;
        position: relative;
        left: 0px;
        top: 0px;
        padding: 10px;
        background-color: #E6E6D6;
        font-family: "Lucida Console", "Courier New", Courier, monospace;
        text-align: left;
        font-size: 8pt;
        width: 500px;
    }}
    .interface-method {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 3px;
        color: white;
        font-weight: bold;
        font-size: 12px;
    }}
    .method-get {{ background-color: #28a745; }}
    .method-post {{ background-color: #007bff; }}
    .method-put {{ background-color: #ffc107; color: black; }}
    .method-delete {{ background-color: #dc3545; }}
    .method-patch {{ background-color: #6f42c1; }}

    .stats-card {{
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
    }}
    .stats-number {{
        font-size: 24px;
        font-weight: bold;
        margin: 5px 0;
    }}
    .stats-label {{
        font-size: 14px;
        color: #666;
    }}

    /* 图表样式 */
    .chart-container {{
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 20px 0;
    }}
    .chart-title {{
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 15px;
        color: #333;
        border-bottom: 2px solid #007bff;
        padding-bottom: 5px;
    }}
    .chart-row {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
    }}
    .chart-item {{
        flex: 1;
        margin: 0 10px;
        text-align: center;
    }}
    .chart-canvas {{
        max-width: 100%;
        height: 200px;
    }}
    .legend {{
        display: flex;
        justify-content: center;
        margin-top: 10px;
    }}
    .legend-item {{
        display: flex;
        align-items: center;
        margin: 0 10px;
    }}
    .legend-color {{
        width: 15px;
        height: 15px;
        border-radius: 3px;
        margin-right: 5px;
    }}

    /* 成功率显示样式 */
    .success-rate-badge {{
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 18px;
        margin: 10px 0;
    }}
    .data-consistency {{
        background: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        border-left: 4px solid #17a2b8;
    }}

    /* 单测试信息样式 */
    .single-test-info {{
        background: #e7f3ff;
        border-left: 4px solid #007bff;
        padding: 15px;
        margin: 15px 0;
        border-radius: 5px;
    }}
    .test-count-badge {{
        display: inline-block;
        padding: 4px 8px;
        background: #17a2b8;
        color: white;
        border-radius: 12px;
        font-size: 12px;
        margin-left: 10px;
    }}

    /* 按钮状态样式 */
    .btn-active {{
        opacity: 1;
        font-weight: bold;
    }}
    .btn-inactive {{
        opacity: 0.7;
        font-weight: normal;
    }}
    </style>

    <link href="https://cdn.bootcss.com/bootstrap/3.3.0/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
    <div class="container">
        <div class='heading'>
            <h1>🤖 接口自动化测试报告</h1>
            <p class='attribute'><strong>开始时间:</strong> {timestamp}</p>
            <p class='attribute'><strong>运行时长:</strong> {duration:.2f} 秒</p>
            <p class='attribute'><strong>测试框架:</strong> {framework}</p>
            <p class='attribute'><strong>测试统计:</strong> 
                <span style="color: #28a745;">通过 {passed}</span> | 
                <span style="color: #ffc107;">失败 {failed}</span> | 
                <span style="color: #dc3545;">错误 {errors}</span> |
                <span style="color: #007bff;">总计 {total}</span>
                <span class="test-count-badge">实际接口: {actual_test_count}</span>
            </p>
            <p class='attribute'><strong>测试结果:</strong> 
                <span class="success-rate-badge" style="background-color: {status_color}; color: white;">
                    {success_rate:.1f}% 成功率
                </span>
            </p>
        </div>

        {f'<div class="single-test-info"><strong>🧪 单接口测试:</strong> 本次测试执行了 <strong>1</strong> 个接口的自动化测试</div>' if actual_test_count == 1 else ''}

        {display_info}

        <!-- 数据一致性检查 -->
        <div class="data-consistency">
            <strong>📊 数据统计:</strong> 
            总用例数: <strong>{total}</strong> | 
            通过率: <strong>{success_rate:.1f}%</strong> | 
            测试状态: <strong>{'✅ 全部通过' if success_rate == 100 else '⚠️ 存在失败' if failed > 0 else '❌ 测试错误' if errors > 0 else '🔍 未知状态'}</strong>
        </div>

        <!-- 统计信息卡片 -->
        <div class="row">
            <div class="col-md-3">
                <div class="stats-card" style="border-left: 4px solid #007bff;">
                    <div class="stats-number">{total}</div>
                    <div class="stats-label">测试用例</div>
                    <small style="color: #666;">{actual_test_count} 个接口</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stats-card" style="border-left: 4px solid #28a745;">
                    <div class="stats-number" style="color: #28a745;">{passed}</div>
                    <div class="stats-label">通过</div>
                    <small style="color: #666;">{(passed / total * 100) if total > 0 else 0:.1f}%</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stats-card" style="border-left: 4px solid #ffc107;">
                    <div class="stats-number" style="color: #ffc107;">{failed}</div>
                    <div class="stats-label">失败</div>
                    <small style="color: #666;">{(failed / total * 100) if total > 0 else 0:.1f}%</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stats-card" style="border-left: 4px solid #dc3545;">
                    <div class="stats-number" style="color: #dc3545;">{errors}</div>
                    <div class="stats-label">错误</div>
                    <small style="color: #666;">{(errors / total * 100) if total > 0 else 0:.1f}%</small>
                </div>
            </div>
        </div>

        <!-- 图表展示 -->
        {self._generate_charts_section(passed, failed, errors, total, success_rate)}

        <!-- 测试详情控制 -->
        <div class="btn-group btn-group-sm" style="margin: 20px 0;">
            <button class="btn btn-default btn-active" onclick='javascript:showCase(0)'><strong>📈 总结</strong></button>
            <button class="btn btn-success btn-inactive" onclick='javascript:showCase(1)'><strong>✅ 通过 ({passed})</strong></button>
            <button class="btn btn-warning btn-inactive" onclick='javascript:showCase(2)'><strong>❌ 失败 ({failed})</strong></button>
            <button class="btn btn-danger btn-inactive" onclick='javascript:showCase(3)'><strong>⚠️ 错误 ({errors})</strong></button>
            <button class="btn btn-info btn-inactive" onclick='javascript:showCase(4)'><strong>📋 全部 ({total})</strong></button>
        </div>

        <table id='result_table' class="table table-bordered table-hover">
            <thead>
                <tr id='header_row'>
                    <td>测试接口</td>
                    <td>方法</td>
                    <td>路径</td>
                    <td>状态</td>
                    <td>响应时间</td>
                    <td>状态码</td>
                    <td>详情</td>
                </tr>
            </thead>
            <tbody>
                {self._generate_test_cases_rows(test_details)}

                <!-- 总计行 -->
                <tr id='total_row' style="background-color: #f8f9fa;">
                    <td colspan="3"><strong>测试统计</strong></td>
                    <td>
                        <span style="color: #28a745;">{passed}✅</span>
                        <span style="color: #ffc107;">{failed}❌</span>
                        <span style="color: #dc3545;">{errors}⚠️</span>
                    </td>
                    <td><strong>{duration:.2f}s</strong></td>
                    <td><strong style="color: {status_color};">{success_rate:.1f}%</strong></td>
                    <td><strong>{passed}/{total}</strong></td>
                </tr>
            </tbody>
        </table>

        {self._generate_error_details(test_details)}

    </div>

    <script language="javascript" type="text/javascript">
    // 筛选显示测试用例
    function showCase(level) {{
        trs = document.getElementsByTagName("tr");
        for (var i = 0; i < trs.length; i++) {{
            tr = trs[i];
            id = tr.id;
            if (id.substr(0,2) == 'Ft') {{
                if (level == 2 || level == 4) {{
                    tr.className = '';
                }} else {{
                    tr.className = 'hiddenRow';
                }}
            }}
            if (id.substr(0,2) == 'Pt') {{
                if (level == 1 || level == 4) {{
                    tr.className = '';
                }} else {{
                    tr.className = 'hiddenRow';
                }}
            }}
            if (id.substr(0,2) == 'Et') {{
                if (level == 3 || level == 4) {{
                    tr.className = '';
                }} else {{
                    tr.className = 'hiddenRow';
                }}
            }}
        }}

        // 更新按钮状态
        updateButtonState(level);
    }}

    // 更新按钮状态
    function updateButtonState(activeLevel) {{
        var buttons = document.querySelectorAll('.btn-group .btn');
        buttons.forEach(function(btn, index) {{
            if (index === activeLevel) {{
                btn.classList.add('btn-active');
                btn.classList.remove('btn-inactive');
            }} else {{
                btn.classList.add('btn-inactive');
                btn.classList.remove('btn-active');
            }}
        }});
    }}

    // 显示测试详情
    function showTestDetail(div_id){{
        var details_div = document.getElementById(div_id)
        var displayState = details_div.style.display
        if (displayState != 'block' ) {{
            displayState = 'block'
            details_div.style.display = 'block'
        }} else {{
            details_div.style.display = 'none'
        }}
    }}

    // 图表绘制函数
    function drawPieChart() {{
        var canvas = document.getElementById('pieChart');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var centerX = canvas.width / 2;
        var centerY = canvas.height / 2;
        var radius = Math.min(centerX, centerY) - 10;

        var data = [{passed}, {failed}, {errors}];
        var colors = ['#28a745', '#ffc107', '#dc3545'];
        var total = data.reduce((a, b) => a + b, 0);

        // 清空画布
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (total > 0) {{
            var startAngle = 0;
            for (var i = 0; i < data.length; i++) {{
                if (data[i] > 0) {{
                    var sliceAngle = 2 * Math.PI * data[i] / total;

                    ctx.beginPath();
                    ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
                    ctx.lineTo(centerX, centerY);
                    ctx.fillStyle = colors[i];
                    ctx.fill();

                    startAngle += sliceAngle;
                }}
            }}
        }} else {{
            // 没有数据时显示灰色圆
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            ctx.fillStyle = '#e9ecef';
            ctx.fill();
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('无数据', centerX, centerY);
        }}
    }}

    function drawBarChart() {{
        var canvas = document.getElementById('barChart');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var width = canvas.width;
        var height = canvas.height;

        var data = [{passed}, {failed}, {errors}];
        var colors = ['#28a745', '#ffc107', '#dc3545'];
        var labels = ['通过', '失败', '错误'];
        var maxData = Math.max(...data);

        // 清空画布
        ctx.clearRect(0, 0, width, height);

        if (maxData > 0) {{
            var barWidth = 60;
            var barSpacing = 30;
            var startX = 50;
            var chartHeight = height - 60;

            // 绘制坐标轴
            ctx.beginPath();
            ctx.moveTo(30, 20);
            ctx.lineTo(30, chartHeight);
            ctx.lineTo(width - 20, chartHeight);
            ctx.strokeStyle = '#333';
            ctx.stroke();

            // 绘制柱状图
            for (var i = 0; i < data.length; i++) {{
                var barHeight = (data[i] / maxData) * (chartHeight - 40);
                var x = startX + i * (barWidth + barSpacing);
                var y = chartHeight - barHeight;

                ctx.fillStyle = colors[i];
                ctx.fillRect(x, y, barWidth, barHeight);

                // 绘制数值
                ctx.fillStyle = '#333';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(data[i], x + barWidth / 2, y - 5);

                // 绘制标签
                ctx.fillText(labels[i], x + barWidth / 2, chartHeight + 15);
            }}
        }} else {{
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('无测试数据', width / 2, height / 2);
        }}
    }}

    function drawStatusChart() {{
        var canvas = document.getElementById('statusChart');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        var width = canvas.width;
        var height = canvas.height;

        var successRate = {success_rate};

        // 清空画布
        ctx.clearRect(0, 0, width, height);

        // 绘制背景圆
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, 50, 0, 2 * Math.PI);
        ctx.strokeStyle = '#e9ecef';
        ctx.lineWidth = 15;
        ctx.stroke();

        if (successRate > 0) {{
            // 绘制成功率圆弧
            var endAngle = 2 * Math.PI * successRate / 100;
            ctx.beginPath();
            ctx.arc(width / 2, height / 2, 50, -Math.PI / 2, -Math.PI / 2 + endAngle);
            ctx.strokeStyle = successRate >= 80 ? '#28a745' : (successRate >= 60 ? '#ffc107' : '#dc3545');
            ctx.lineWidth = 15;
            ctx.stroke();
        }}

        // 绘制中心文字
        ctx.fillStyle = '#333';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(successRate.toFixed(1) + '%', width / 2, height / 2);

        ctx.font = '12px Arial';
        ctx.fillText('成功率', width / 2, height / 2 + 20);
    }}

    // 页面加载时绘制图表
    window.onload = function() {{
        drawPieChart();
        drawBarChart();
        drawStatusChart();
        updateButtonState(0); // 默认显示总结视图
    }};
    </script>
    </body>
    </html>'''
    def _generate_charts_section(self, passed, failed, errors, total, success_rate):
        """生成图表展示部分"""
        return f'''
    <!-- 图表展示 -->
    <div class="chart-container">
        <div class="chart-title">📊 测试结果图表分析</div>

        <div class="chart-row">
            <div class="chart-item">
                <div style="font-weight: bold; margin-bottom: 10px;">饼状图分布</div>
                <canvas id="pieChart" width="250" height="200" class="chart-canvas"></canvas>
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #28a745;"></div>
                        <span>通过: {passed}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #ffc107;"></div>
                        <span>失败: {failed}</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #dc3545;"></div>
                        <span>错误: {errors}</span>
                    </div>
                </div>
            </div>

            <div class="chart-item">
                <div style="font-weight: bold; margin-bottom: 10px;">柱状图对比</div>
                <canvas id="barChart" width="250" height="200" class="chart-canvas"></canvas>
            </div>

            <div class="chart-item">
                <div style="font-weight: bold; margin-bottom: 10px;">成功率仪表盘</div>
                <canvas id="statusChart" width="250" height="200" class="chart-canvas"></canvas>
                <div style="margin-top: 10px; font-size: 14px; color: #666;">
                    总用例数: {total}<br>
                    通过率: {success_rate:.1f}%
                </div>
            </div>
        </div>
    </div>
    '''

    def _generate_test_cases_rows(self, test_details):
        """生成测试用例行"""
        if not test_details:
            return '<tr><td colspan="7" style="text-align: center;">暂无测试详情数据</td></tr>'

        rows = []
        for i, detail in enumerate(test_details):
            status = detail.get('status', 'unknown')
            method = detail.get('method', 'GET')
            path = detail.get('path', '')
            interface_name = detail.get('name', f'接口{i + 1}')
            response_time = detail.get('response_time', 0)
            status_code = detail.get('status_code', 'N/A')
            error_msg = detail.get('error', '')

            # 状态样式
            if status == 'passed':
                status_class = 'passCase'
                status_text = '✅ 通过'
                row_class = 'Pt'
            elif status == 'failed':
                status_class = 'failCase'
                status_text = '❌ 失败'
                row_class = 'Ft'
            else:
                status_class = 'errorCase'
                status_text = '⚠️ 错误'
                row_class = 'Et'

            # 方法样式
            method_class = f'method-{method.lower()}'

            row_id = f'{row_class}{i + 1}'

            row = f'''
            <tr id='{row_id}' class='{status_class}'>
                <td>{interface_name}</td>
                <td><span class="interface-method {method_class}">{method}</span></td>
                <td>{path}</td>
                <td class='{status_class}'>{status_text}</td>
                <td>{response_time:.2f}s</td>
                <td>{status_code}</td>
                <td>
                    <a class="popup_link" onfocus='this.blur();' href="javascript:showTestDetail('div_{row_id}')">
                        详情
                    </a>
                    <div id='div_{row_id}' class="popup_window">
                        <div style='text-align: right; color:red;cursor:pointer'>
                            <a onfocus='this.blur();' onclick="document.getElementById('div_{row_id}').style.display = 'none'">[x]</a>
                        </div>
                        <pre>
{self._format_test_detail(detail)}
                        </pre>
                    </div>
                </td>
            </tr>
            '''
            rows.append(row)

        return '\n'.join(rows)

    def _format_test_detail(self, detail):
        """格式化测试详情"""
        lines = []

        # 基本信息
        lines.append(f"接口名称: {detail.get('name', '未知')}")
        lines.append(f"请求方法: {detail.get('method', 'GET')}")
        lines.append(f"请求路径: {detail.get('path', '')}")
        lines.append(f"测试状态: {detail.get('status', 'unknown')}")
        lines.append(f"响应时间: {detail.get('response_time', 0):.2f}秒")
        lines.append(f"状态码: {detail.get('status_code', 'N/A')}")
        lines.append("")

        # 请求信息
        lines.append("=== 请求信息 ===")
        if detail.get('headers'):
            lines.append("请求头:")
            for k, v in detail.get('headers', {}).items():
                lines.append(f"  {k}: {v}")

        if detail.get('parameters'):
            lines.append("请求参数:")
            lines.append(f"  {json.dumps(detail.get('parameters', {}), indent=2, ensure_ascii=False)}")

        lines.append("")

        # 响应信息
        lines.append("=== 响应信息 ===")
        if detail.get('response_body'):
            try:
                # 尝试格式化JSON响应
                response_json = json.loads(detail['response_body'])
                lines.append("响应体:")
                lines.append(json.dumps(response_json, indent=2, ensure_ascii=False))
            except:
                lines.append(f"响应体: {detail['response_body']}")

        # 错误信息
        if detail.get('error'):
            lines.append("")
            lines.append("=== 错误信息 ===")
            lines.append(detail['error'])

        # 断言信息
        if detail.get('assertions'):
            lines.append("")
            lines.append("=== 断言结果 ===")
            for assertion in detail.get('assertions', []):
                status_icon = "✅" if assertion.get('passed') else "❌"
                lines.append(f"{status_icon} {assertion.get('description', '未知断言')}")
                if not assertion.get('passed') and assertion.get('message'):
                    lines.append(f"   错误: {assertion['message']}")

        return '\n'.join(lines)

    def _generate_error_details(self, test_details):
        """生成错误详情"""
        if not test_details:
            return ''

        error_details = [d for d in test_details if d.get('status') in ['failed', 'error']]
        if not error_details:
            return ''

        html = '''
        <div class="panel panel-danger">
            <div class="panel-heading">
                <h3 class="panel-title">❌ 失败和错误详情</h3>
            </div>
            <div class="panel-body">
        '''

        for i, error in enumerate(error_details):
            html += f'''
            <div class="alert alert-warning">
                <h5>{i + 1}. {error.get('name', '未知接口')}</h5>
                <p><strong>方法:</strong> {error.get('method', 'GET')} | <strong>路径:</strong> {error.get('path', '')}</p>
                <p><strong>状态码:</strong> {error.get('status_code', 'N/A')} | <strong>响应时间:</strong> {error.get('response_time', 0):.2f}s</p>
                <p><strong>错误信息:</strong> {error.get('error', '未知错误')}</p>
                <button class="btn btn-sm btn-default" onclick="document.getElementById('error_detail_{i}').style.display = 'block'">
                    查看完整错误详情
                </button>
                <div id="error_detail_{i}" style="display: none; margin-top: 10px;">
                    <pre>{error.get('error', '无错误信息')}</pre>
                </div>
            </div>
            '''

        html += '''
            </div>
        </div>
        '''

        return html

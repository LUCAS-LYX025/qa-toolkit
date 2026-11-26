"""统一缺陷绩效分析：数据源适配器 + 领域模型 + 可插拔规则引擎。

本包把原来与禅道强绑定的「取数 + 绩效计算」解耦为三层：
- ``models``：统一领域模型（WorkItem / Person / PerformanceRow / TimeoutDetail）；
- ``adapters``：各平台数据源适配器（禅道 DB / 禅道代理 / JIRA / TAPD / 云效）；
- ``rules``：纯 Python 绩效与 SLA 计算（归因规则 + 阈值 + 节假日 + 率）。

注册中心在 ``qa_toolkit.core.tracking_registry``，页面与测试都从注册表消费。
"""

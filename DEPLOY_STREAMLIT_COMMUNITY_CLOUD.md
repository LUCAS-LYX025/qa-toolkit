# Streamlit Community Cloud 部署手册

适用范围：

- 把当前工具箱部署到 Streamlit Community Cloud
- 以远程服务方式接入 MobSF
- 保留 OCR、图片处理、IP/域名查询、BI 分析等常规能力

不适用范围：

- 在 Community Cloud 中直接运行本地 Docker、MobSF 容器、ADB、Frida、Android 模拟器
- 在 Community Cloud 中直接准备 Android 动态分析环境

## 1. 部署前准备

确认仓库中已经存在以下文件：

- `streamlit_app.py`
- `requirements.txt`
- `packages.txt`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`

当前仓库已包含这些文件。

## 2. 创建应用

1. 把仓库推到 GitHub。
2. 打开 Streamlit Community Cloud。
3. 新建应用并选择当前仓库。
4. 按下面的参数填写：

- Repository: 当前仓库
- Branch: 你的发布分支，例如 `main`
- Main file path: `streamlit_app.py`
- Python version: `3.12`

## 3. 配置 Secrets

如果要启用 MobSF 远程能力，在 Community Cloud 的 App Settings -> Secrets 中填入：

```toml
[mobsf]
base_url = "https://your-mobsf.example.com"
api_key = "replace-with-your-mobsf-api-key"
timeout_seconds = 180
verify_ssl = true
include_pdf = false
```

说明：

- `base_url` 填 MobSF 根地址，不要只填到某个单独接口
- 如果你的 MobSF 在反向代理子路径下，填子路径根地址，例如 `https://demo.example.com/mobsf`
- `api_key` 建议只放在 Secrets，不要写进仓库

## 4. 首次上线后检查

建议按下面顺序点一遍：

1. 首页能正常打开
2. 图片处理工具上传一张图，确认裁剪和下载正常
3. IP/域名查询工具执行一次单查
4. BI 工具上传一个小样本文件，确认基础分析正常
5. 进入应用安全测试 -> MobSF 集成
6. 点“检查连通性”，确认远程 MobSF 可达
7. 上传一个 APK / IPA / APPX 做一次静态扫描

## 5. 功能可用性矩阵

可正常运行：

- 图片处理工具
- IP/域名查询工具
- BI 数据分析工具
- 本地 APK / IPA / APPX 静态预检
- 远程 MobSF 静态分析
- 远程 MobSF 报告拉取
- 远程 MobSF 动态报告拉取和二次整理
- OCR 相关功能

有前提才能运行：

- MobSF 集成：需要你自己提供一个外部可访问的 MobSF 服务
- MobSF 动态报告：需要 MobSF 服务所在环境已经准备好设备、模拟器、Frida、证书代理等

不能在 Community Cloud 中本地运行：

- 本机 Docker 启动 MobSF
- 本机 Android 模拟器
- 本机 ADB / Frida / 动态注入环境
- 持久依赖 `workspace/mobsf_profile.local.json` 的配置方式

## 6. 常见问题

### 6.1 MobSF 页面提示未配置

优先检查：

- Cloud Secrets 是否已保存
- Secrets 键名是否为 `[mobsf]` 下的 `base_url`、`api_key`
- 保存 Secrets 后是否重启应用

### 6.2 OCR 不可用

优先检查：

- 应用是否重新部署成功
- `packages.txt` 是否被 Cloud 正常识别
- 是否点过 `Reboot app`

### 6.3 PDF 转图片相关能力异常

优先检查：

- `poppler-utils` 是否随 `packages.txt` 安装
- 当前 PDF 是否过大或页面资源不足

### 6.4 MobSF 动态报告拉不下来

这通常不是 Cloud 本身的问题，而是远程 MobSF 动态环境还没准备好。优先检查：

- MobSF Dynamic Analyzer 页面里设备或模拟器是否就绪
- 目标应用是否已安装
- 是否已经执行过动态分析开始、停止和结果收集

## 7. 推荐发布策略

建议分两层：

- Community Cloud：提供工具箱 Web 界面、文件处理、结果整理和远程 API 客户端能力
- 独立安全环境：运行 MobSF、Android 动态环境、设备或模拟器

这样最稳定，也最符合 Community Cloud 的运行边界。

## 8. 上线前最后检查清单

发布前只需要快速确认这几项：

- GitHub 仓库里已经包含 `streamlit_app.py`
- GitHub 仓库里已经包含 `requirements.txt`
- GitHub 仓库里已经包含 `packages.txt`
- GitHub 仓库里已经包含 `.streamlit/config.toml`
- 如果要接 MobSF，Cloud Secrets 已填写 `[mobsf]`
- `Main file path` 填的是 `streamlit_app.py`
- Python 版本选的是 `3.12`
- 远程 MobSF 地址可以从公网或你的目标网络访问
- 远程 MobSF API Key 已验证可用
- 不把 `workspace/mobsf_profile.local.json` 当成云端长期配置

## 9. Cloud 后台填写模板

创建应用时，后台可以直接按下面填写：

- Repository: `你的 GitHub 仓库`
- Branch: `main`
- Main file path: `streamlit_app.py`
- Python version: `3.12`

Secrets 可以直接按下面贴：

```toml
[mobsf]
base_url = "https://your-mobsf.example.com"
api_key = "replace-with-your-mobsf-api-key"
timeout_seconds = 180
verify_ssl = true
include_pdf = false
```

如果这次不启用 MobSF：

- 可以先不填 `[mobsf]`
- 页面里 MobSF 相关能力会处于待配置状态
- 图片处理、IP/域名查询、BI 分析、OCR 等普通能力仍可用

## 10. 上线后冒烟通过标准

满足下面几点，就可以认为这次部署基本可用：

1. 首页打开无异常
2. 任意图片工具上传和下载正常
3. IP/域名工具能返回一次结果
4. BI 工具能读取一个小文件
5. 如果配置了 MobSF，“检查连通性”返回成功
6. 如果配置了 MobSF，上传一个 APK / IPA / APPX 能拿到静态分析结果

## 11. 故障排查速查表

| 症状 | 常见原因 | 处理动作 |
| --- | --- | --- |
| 应用构建失败 | `requirements.txt` 或 `packages.txt` 依赖没有正确安装 | 检查构建日志，确认根目录仍有 `requirements.txt`、`packages.txt`，修正后重新部署 |
| 页面能打开，但某些功能导入失败 | 新增依赖后应用没有重启，或云端安装没完成 | 在 Community Cloud 后台执行 `Reboot app`，必要时重新部署 |
| OCR 不可用 | `tesseract` 没装好或系统依赖没生效 | 检查 `packages.txt`，确认包含 `tesseract-ocr`、`tesseract-ocr-chi-sim`，然后重启应用 |
| PDF 转图片失败 | `poppler-utils` 未安装或大 PDF 超资源限制 | 确认 `packages.txt` 包含 `poppler-utils`，先用小 PDF 验证，再检查资源占用 |
| 图片处理大文件很慢或直接失败 | Community Cloud 内存或消息体限制触发 | 先用小文件验证；避免一次上传超大文件；必要时拆分文件或转到本机执行 |
| MobSF 页面提示未配置 | Secrets 未配置、键名不对，或保存后未重启 | 检查 Cloud Secrets 中 `[mobsf]` 段；确认 `base_url`、`api_key` 存在；保存后重启应用 |
| MobSF 连通性提示 404 / 接口路径不符合官方 API | `base_url` 填成了具体接口，不是根地址；或反向代理子路径填错 | 把地址改成 MobSF 根地址，例如 `https://host/mobsf`，不要填成 `/api/v1/scans` |
| MobSF 上传时报 `File format not Supported!` | 上传文件不是合法安装包，或只是改了后缀名 | 用真实 APK / IPA / APPX 包重试，不要只改文件扩展名 |
| Android 动态报告提示 `report is not available` | 远程 MobSF 还没生成动态报告 | 先在远程 MobSF 环境里执行开始分析、操作 App、停止并收集结果，再回来拉报告 |
| Android 动态分析提示 `Dynamic Analysis Failed` | 远程 MobSF 侧设备、模拟器、Frida、证书代理没准备好 | 去 MobSF 所在环境检查 Dynamic Analyzer，确认设备、代理和目标应用已就绪 |
| 重启后本地配置丢失 | Community Cloud 文件系统是临时的 | 不要依赖 `workspace/mobsf_profile.local.json`，长期配置统一放 `st.secrets` |
| BI 或图片工具处理大样本时被中断 | Cloud 资源上限不适合重计算任务 | 用小样本做在线分析；超大文件改到本机或独立环境执行 |

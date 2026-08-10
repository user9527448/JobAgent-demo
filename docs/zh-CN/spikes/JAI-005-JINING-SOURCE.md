# JAI-005 — 济宁公开招聘来源技术验证

> 英文原文：[JAI-005 — Jining public recruitment source Spike](../../spikes/JAI-005-JINING-SOURCE.md)。修改原文时必须在同一提交中同步更新本镜像。

## 结论

该来源可支持未来的 JOBAGENT Adapter：列表页能提供详情链接和日期，选定详情页具有稳定元数据、正文和 PDF 附件链接，选定的四页 PDF 每页都能提取非空文本。

这只是技术验证，不是生产爬虫。限速、重试、条件请求、存储和幂等性由 JAI-006 至 JAI-010 实现。

## 来源记录

| 项目 | 值 |
|---|---|
| 所有者 | 济宁市人力资源和社会保障局 |
| 分类 | 事业单位公开招聘 |
| 列表页 | `https://hrss.jining.gov.cn/col/col71291/index.html` |
| 详情样本 | `https://hrss.jining.gov.cn/art/2026/1/22/art_71291_2718366.html` |
| PDF 样本 | `https://hrss.jining.gov.cn/attach/0/566c19e3bedd4043b7786ffb15540704.pdf` |
| 页面类型 | UTF-8 静态 HTML 和文本型 PDF |
| 身份认证 | 无 |
| CAPTCHA | 无 |
| 计划频率 | 每天一次，顺序请求，间隔至少一秒 |

## 访问与合规检查

检查日期：2026-08-09。

- `robots.txt` 返回 HTTP 200，内容只有注释，没有声明禁止路径。
- 列表、详情和 PDF 无需登录、Cookie 或浏览器自动化即可返回 HTTP 200。
- 请求使用 `JOBAGENT/0.1 (+personal recruitment intelligence research; low-frequency)`。
- 技术验证按顺序发送请求，并为每类所需资源只保留一个固定样本。自动化测试完全离线。
- 未绕过登录、CAPTCHA、访问控制或来源限制。如果网站规则或访问行为发生变化，必须停止采集并重新审查。

## 已验证结构

### 列表发现

页面把记录以 HTML 形式嵌入 `<![CDATA[...]]>` 块。每条记录包含：

- 匹配 `art_71291_` 的详情路径；
- 锚点 `title` 属性中的完整标题；
- `span.sp_time` 中的发布日期。

由于条目标记位于 CDATA 中，只用 CSS 选择器解析外层页面不会返回条目。技术验证先提取每个 CDATA 片段，再把该片段作为 HTML 解析。

### 详情抽取

- 标题：`meta[name="ArticleTitle"]`；
- 发布时间：`meta[name="pubdate"]`；
- 正文：`#zoom .wenz`；
- PDF 附件：正文中 URL 包含 `.pdf` 的锚点。

下载链接使用 `module/download/downfile.jsp`，通过查询参数携带存储文件名，并重定向或直接流式返回 PDF 响应。

### PDF 抽取

PyMuPDF 能从全部四页提取文本。输出保留从 1 开始的页码，使后续字段证据能回指来源页面。所选文件为文本型 PDF，不需要 OCR。

## 复现

正常质量门禁会运行确定性的离线回归测试：

```powershell
python scripts/check.py
```

可选的在线检查只会顺序执行三次 GET 请求：

```powershell
python scripts/run_jining_spike.py
```

不要调度此技术验证脚本。JAI-008 提供生产 HTTP 策略。

## 已知限制与建议

- 列表格式是供应商专用格式，而且不够规范，因此 CDATA 处理需要契约固定样本。
- 发布元数据可能不同于页面后续更新时间；技术验证使用可见 `pubdate` 字段。
- PDF 表格读取顺序足以支持发现和证据定位，但尚未规范化为岗位行。
- 尚未覆盖扫描或加密 PDF。
- 列表包含招聘周期不同阶段的通知，未来 Adapter 需要公告类型分类。
- 在 JAI-011 将该来源提升为生产来源前，至少再增加两个详情固定样本，并继续由 JAI-008 公共客户端负责在线 HTTP 行为。

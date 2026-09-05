# JAI-025 匹配质量评审固定样本

> English guide: [JAI-025 matching-quality review fixture](../../../tests/fixtures/matching_quality/README.md)

`review-set.json` 包含 60 条完全合成、脱敏的岗位记录。它针对一份显式偏好快照和评估时刻保存拟议的二元相关性标注、原因分类与说明，不包含下载公告、求职者记录、凭据、个人数据或运行输出。

该固定样本用于确定性离线评审。拟议标注便于逐条检查；在把 JAI-025 标记为“已完成人工标注基准”之前，必须由项目负责人显式确认。

运行对比：

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_matching_quality.py
```

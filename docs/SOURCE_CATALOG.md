# 招聘信息目标网站库

本文档记录 JAI-011 的目标来源、接入状态和人工维护规则。机器可读配置以 [`config/source_catalog.toml`](../config/source_catalog.toml) 为准；本文档解释为什么收录、当前能否运行以及后续接入约束。

## 1. 覆盖目标

- 校招：优先教育主管部门、学生就业公共服务机构和公开招聘会信息。
- 江浙沪公职考试：覆盖公务员、事业单位的公开公告、报名时间、资格审查和考试安排。
- 央国企招聘：优先国务院国资委聚合公告，再逐步接入代表性央企的公开招聘门户。
- 只采集无需登录的公开列表、详情和附件；不进入报名表单，不处理验证码，不绕过访问控制。

## 2. 目标网站名单

| 类别 | 地区 | 官方来源 | 公开入口 | 状态 | 说明 |
|---|---|---|---|---|---|
| 校招 | 全国 | 国家大学生就业服务平台 | [职位信息](https://www.ncss.cn/student/jobs/index.html) | 待接入 | 教育部学生服务与素质发展中心公共平台；先验证无登录列表稳定性 |
| 校招 | 上海/长三角 | 上海学生就业创业服务网 | [首页](https://www.firstjob.shec.edu.cn/) | 待接入 | 上海市学生事务中心公开招聘会与长三角就业信息 |
| 公职考试 | 江苏 | 江苏省人事考试网 | [考试专题列表](https://jshrss.jiangsu.gov.cn/col/col57253/index.html) | 待接入 | 省级公务员报名入口由官方招录公告指向该站；只采集公开公告和时间安排 |
| 公职考试 | 浙江 | 浙江省公务员考试录用网 | [首页](https://gwy.zjks.gov.cn/) | 待接入 | 招考公告、报名统计和考试安排 |
| 公职考试 | 上海 | 上海市公务员局 | [首页](https://www.shacs.gov.cn/) | 待接入 | 只采集公开招录公告；不访问报名表单 |
| 公职考试 | 上海 | 上海市人力资源和社会保障局 | [通知公告](https://rsj.sh.gov.cn/tgsgg_17341/) | 待接入 | 事业单位公开招聘、报名确认与考试时间 |
| 央国企 | 全国 | 国务院国资委 | [公开招聘栏目](https://www.sasac.gov.cn/n2588035/n2588325/n2588350/index.html) | 已启用 | JAI-011 首个 Adapter；聚合中央企业校园和社会招聘公告 |
| 央国企 | 全国/江浙沪 | 国家电网 | [招聘平台](https://zhaopin.sgcc.com.cn/) | 待接入 | 动态门户，需先验证公开接口、服务条款和页面稳定性 |
| 央国企 | 全国/江浙沪 | 中国移动 | [招聘平台](https://job.10086.cn/) | 待接入 | 只接入无需登录的校招公告 |
| 央国企 | 全国/江浙沪 | 中国电信 | [集团招聘栏目](https://www.chinatelecom.com.cn/ct/zp/) | 待接入 | 优先集团公开栏目，避免依赖个人申请功能 |
| 央国企 | 全国/江浙沪 | 中国石油 | [高校毕业生招聘平台](https://zhaopin.cnpc.com.cn/) | 待接入 | 动态门户，需先验证公开列表稳定性 |

“待接入”只表示已登记候选来源，不表示当前程序会访问它。机器配置要求此类来源为 `implementation_status = "planned"` 且 `enabled = false`。

## 3. 手工维护方法

编辑 `config/source_catalog.toml` 中对应的 `[[sources]]`：

- `key`：稳定、唯一的机器标识；上线后不要随意改名。
- `category`：只能是 `campus`、`public_exam`、`state_owned`。
- `regions`：用 `national`、`jiangsu`、`zhejiang`、`shanghai` 等稳定英文标识。
- `base_url` / `list_url`：必须是无凭据的 HTTPS 官方 URL。
- `implementation_status`：`planned`、`active` 或 `blocked`。
- `enabled`：只有已有 Adapter 的 `active` 来源可设为 `true`。
- `include_keywords`：标题命中任一词才进入候选；空缺表示不做包含过滤。
- `exclude_keywords`：标题命中任一词立即排除，优先级高于包含词。
- `crawl_interval_minutes`：来源级建议间隔；实际请求仍受公共 HTTP 客户端限速约束。

修改后先运行：

```powershell
.\.venv\Scripts\python.exe scripts/run_source_preview.py --list
.\.venv\Scripts\python.exe -m pytest tests/crawlers/test_catalog.py -q
```

预览当前已启用的国资委来源（会真实访问公开网站，不写数据库）：

```powershell
.\.venv\Scripts\python.exe scripts/run_source_preview.py --source sasac-recruitment --limit 10
```

## 4. 新来源上线检查

1. 核对官方主体、HTTPS 入口、服务条款和 robots 规则。
2. 确认公开访问不需要登录、验证码或表单提交。
3. 每个来源保留至少 3 组脱敏列表/详情固定样本，并通过 Adapter 契约测试。
4. 先将配置保持 `planned`/`enabled = false`；Adapter、样本和失败可见性齐备后才改为 `active`。
5. 执行低频线上冒烟和两次幂等持久化验证后，才进入定时运行。

## 5. 当前环境限制

2026-08-10，当前 Windows 环境直接访问国资委页面时遇到 TLS 连接错误，只读浏览器检查又被安全策略拒绝。因此首个 Adapter 使用公开 URL、保守链接语义和最小化离线样本完成初步实现，尚未把线上冒烟标记为通过。网络恢复后应优先完成该检查；禁止以绕过安全策略的方式获取页面。

# JAI-005 济宁来源固定样本

> 英文原文：[JAI-005 Jining source fixtures](../../../tests/fixtures/jining/README.md)。修改原文时必须在同一提交中同步更新本镜像。

样本于 2026-08-09 从济宁市人力资源和社会保障局公开网站抓取。每项资源只发送一次顺序请求，并使用说明用途的 JOBAGENT User-Agent。

| 固定样本 | 原始 URL | SHA-256 |
|---|---|---|
| `list.html` | `https://hrss.jining.gov.cn/col/col71291/index.html` | `095CE3D43CA2E9787BD698294D201C24DC6A0A59C437015C83F46D74EF59E268` |
| `detail.html` | `https://hrss.jining.gov.cn/art/2026/1/22/art_71291_2718366.html` | `F43939B69007B0164BF6AF31D4A17B990F332207034EC7AEE9C5BC77A0F6026C` |
| `positions.pdf` | `https://hrss.jining.gov.cn/attach/0/566c19e3bedd4043b7786ffb15540704.pdf` | `0C008F81C5DAD4DEE2E130CC454EA066C9FFF13DC55A3B2D343ABF540A359EEF` |

这些样本包含官方公开招聘公告和公开的单位联系信息，不包含应聘者提交材料或非公开个人记录。测试必须离线使用这些文件，不得联系来源网站。

# 个人软件工厂

以 **Obsidian + Git + DSH** 管理可追溯、可验证、可改进的软件生产流程。

- 当前可用产线：**APP v0.1.0**（文档、项目级 Skill 和模板基线，尚未经真实 APP 项目验证）。
- 后续产线：**游戏**（仅预留架构位置，未实施）。
- 本仓库管理工厂规范与知识，不承载所有产品源码，不是已经部署的自动化 CI/CD 平台。
- 远程仓库：[nicoleDeep/software_factory](https://github.com/nicoleDeep/software_factory)。

## 从这里开始

1. 阅读 [APP 产线入口](<lines/app/README.md>)。
2. 在独立产品仓库中复制 [项目运行档案](<templates/project-run.md>)，填写目标、MVP、验收、风险和产线版本；留空项是未决事项，不是默认通过。
3. 按 [10 节点流程](<lines/app/pipeline.md>)推进，用 [任务包](<templates/task.md>)交付一个端到端功能切片。
4. 在 [5 道门禁](<lines/app/quality-gates.md>)记录证据与批准，不以 Agent 自评替代放行。
5. 遇到工厂流程问题时提交 [改进提案](<templates/improvement.md>)；产品修复与工厂升级分别管理。

## 导航

| 内容 | 入口 |
|---|---|
| Obsidian 首页 | [Home](<Home.md>) |
| 工厂分层与产线扩展 | [架构](<factory/architecture.md>) |
| 角色、状态、权限与证据 | [运行规范](<factory/operating-model.md>) |
| 真实项目驱动的演进 | [改进闭环](<factory/improvement-loop.md>) |
| APP 流程与 DSH 使用 | [APP](<lines/app/README.md>) / [DSH 操作指南](<lines/app/dsh-playbook.md>) |
| 游戏产线占位 | [游戏](<lines/game/README.md>) |
| 模板目录 | [模板](<templates/README.md>) |
| 项目索引 | [项目](<projects/README.md>) |
| 候选经验与改进 | [候选区](<00-Inbox/README.md>) / [改进记录](<improvements/README.md>) |
| 版本变化 | [更新记录](<CHANGELOG.md>) |

## 验证与版本

需要 Python 3.10+，无需额外 Python 包。在仓库根目录执行：

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

验证器检查受管理文档的本地链接、产线注册、10 节点/5 门禁映射、版本一致性和项目 Skill 元数据；**不证明 APP 已通过测试，也不自动批准任何门禁**。兼容 Obsidian 与 GitHub 的相对 Markdown 文件链接；当前不校验标题锚点。

APP 规范版本记录在 [VERSION](<lines/app/VERSION>)；项目还必须记录本仓库的确切 Git 提交 SHA，避免同名版本指向可变内容。更新产线不自动更新在途项目。

## 数据与提交

不提交密钥、真实客户资料、生产导出数据或完整敏感会话。Obsidian 配置默认留在本机。Git 版本历史不替代独立备份；push 前检查远程可见性与差异。未经明确批准不执行生产发布、破坏性迁移或自动扩大权限。

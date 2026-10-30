# 主页维护

主页由本仓库内的 SVG 图片组成，支持深浅色主题与手机窄屏布局。图片不依赖在线图床、字体服务或外部统计图片接口。

## 修改介绍

编辑 `profile.json` 中的昵称、介绍、工作方向、技术标签和精选公开仓库，然后同步更新 `README.md` 的文字版介绍与图片替代文本。发布前运行：

```bash
python scripts/build_profile.py
python scripts/build_profile.py --check
```

`build_profile.py` 仅使用 Python 标准库，根据本地数据生成 `assets/` 中的 SVG。`--check` 检查所有深浅色、桌面和窄屏图片是否与数据一致；不会访问网络。

## 自动刷新

`Update profile assets` 工作流每 8 小时刷新贡献动画和公开统计。修改介绍、生成脚本或工作流时也会运行，亦可在 Actions 页面手动触发。它沿用仓库的 `main` 分支。

流程为：生成贡献图 → 获取公开统计 → 渲染全部卡片 → 校验 → 提交图片和数据。网络、数据或渲染校验失败时不会提交不完整的更新，已经发布的图片继续可用。

自动化只使用 GitHub Actions 内置的 `GITHUB_TOKEN`，无需添加个人访问令牌。工作流只允许写入仓库内容，不读取私有项目统计。

## 数据口径

| 数据 | 范围 |
| --- | --- |
| 公开仓库 | 本账号拥有的公开非 Fork 仓库，包含主页仓库 |
| Stars | 上述仓库获得的 Stars 总数 |
| Pull Requests | 本账号在 GitHub 上创建的公开 PR，累计 |
| 已合并 PR | 上述公开 PR 中已合并的数量 |
| 语言分布 | 公开非 Fork 仓库的 GitHub Linguist 字节数合计，不代表熟练程度 |
| 贡献动画 | GitHub 个人主页贡献日历；与公开仓库统计不是同一口径 |

初始快照若尚未获取语言字节统计，卡片显示工作理念。成功刷新后自动显示语言分布；不使用估算值填充缺失数据。统计卡注明快照日期，完整快照保存在 `assets/stats.json`。

## 视觉与来源

终端介绍、方向卡片和数据卡片为本仓库原创实现，布局参考 [ggbdpq 的 GitHub 主页](https://github.com/ggbdpq/ggbdpq)。贡献动画由 [Platane/snk](https://github.com/Platane/snk) 生成，工作流固定到具体提交。所有图片使用本地系统字体，SVG 保留标题、描述及减少动态效果的设置。

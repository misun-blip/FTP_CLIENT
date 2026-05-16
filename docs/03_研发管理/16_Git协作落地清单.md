# Git 协作落地清单

## 1. 当前分支结构

```text
main      # 稳定、可演示版本
develop   # 日常集成分支
```

## 2. 首次推送远程仓库

当远程仓库创建完成后，执行：

```bash
git remote add origin <远程仓库地址>
git push -u origin main
git push -u origin develop
```

## 3. 组员首次拉取

```bash
git clone <远程仓库地址>
cd <项目目录>
git checkout develop
```

## 4. 每位成员创建自己的功能分支

```bash
git checkout develop
git pull
git checkout -b feature/<功能名>
```

示例：

```bash
git checkout -b feature/protocol
git checkout -b feature/download
git checkout -b feature/upload
git checkout -b feature/gui
git checkout -b feature/logger
```

## 5. 日常开发流程

```bash
git checkout develop
git pull
git checkout feature/<功能名>
git merge develop

# 开发、测试

git add .
git commit -m "feat: xxx"
git push -u origin feature/<功能名>
```

## 6. 合并规则

1. 功能分支先合并到 `develop`
2. `develop` 经过测试后再合并到 `main`
3. 不直接向 `main` 提交开发代码
4. 公共接口变更后必须同步更新文档

## 7. 建议的首批功能分支

| 成员 | 分支 |
|---|---|
| 成员 2 | `feature/protocol` |
| 成员 3 | `feature/download` |
| 成员 4 | `feature/upload` |
| 成员 5 | `feature/gui` |
| 成员 6 | `feature/logger-config-tests` |

## 8. 首次协作前必须确认

- [ ] 所有人安装 Git
- [ ] 所有人能 clone 仓库
- [ ] 所有人从 `develop` 开始开发
- [ ] 所有人知道不直接改 `main`
- [ ] 所有人知道自己的分支名


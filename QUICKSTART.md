# ⚽ Ai足势 - 5分钟快速开始

## 📦 文件结构

```
football-predict/
├── index.html              # 前端首页
├── admin.html              # 后台管理
├── firebase.json           # Firebase 配置
├── firestore.rules         # 数据库规则
├── sample_matches.json     # 示例赛事数据
├── deploy.sh               # 一键部署脚本
├── setup_cron.sh           # 定时任务设置
├── python-scripts/
│   └── generate_predictions.py  # 自动预测脚本
└── README.md               # 完整文档
```

---

## 🚀 三步部署

### 第1步：创建 Firebase 项目

1. 访问 https://console.firebase.google.com/
2. 点击「添加项目」→ 名称输入 `ai-football-predict`
3. 创建完成后，进入项目

### 第2步：启用 Firestore

1. 左侧菜单 → 「Firestore Database」
2. 点击「创建数据库」
3. 选择「以测试模式启动」
4. 选择服务器位置（推荐 `asia-east1`）

### 第3步：部署网站

#### 方法A：自动部署（推荐）

```bash
cd football-predict
./deploy.sh
```

#### 方法B：手动部署

```bash
# 安装 Firebase CLI
npm install -g firebase-tools

# 登录
firebase login

# 初始化（选择你的项目）
firebase init hosting

# 部署
firebase deploy
```

---

## 🎯 导入示例数据

部署完成后，网站是空的。需要导入示例数据：

### 方法1：通过后台导入

1. 访问 `https://你的项目.web.app/admin.html`
2. 登录管理员账号：
   - 用户名：`admin`
   - 密码：`admin888`
3. 点击「📋 导入赛程」
4. 复制 `sample_matches.json` 的内容粘贴进去
5. 点击「确认导入」

### 方法2：通过代码导入

```bash
# 安装 Firebase Admin SDK
pip3 install firebase-admin

# 下载服务账号密钥
# Firebase 控制台 → 项目设置 → 服务账号 → 生成新私钥
# 保存为 serviceAccountKey.json

# 运行导入脚本（需要自己写）
```

---

## 🤖 设置自动预测

### 第1步：下载服务账号密钥

1. Firebase 控制台 → 项目设置 → 服务账号
2. 点击「生成新私钥」
3. 下载 JSON 文件，重命名为 `serviceAccountKey.json`
4. 放到 `football-predict/` 目录

### 第2步：安装 Python 依赖

```bash
pip3 install pandas numpy scipy requests firebase-admin
```

### 第3步：设置定时任务

```bash
cd football-predict
./setup_cron.sh
```

选择执行时间（推荐每天凌晨2:00）

### 第4步：测试运行

```bash
cd football-predict
python3 python-scripts/generate_predictions.py
```

---

## ✅ 验证部署

### 检查前端

访问 `https://你的项目.web.app`

应该看到：
- ⚽ Ai足势 Logo
- 登录/注册界面
- 深色主题

### 检查后台

访问 `https://你的项目.web.app/admin.html`

应该看到：
- 数据统计（会员、钻石、赛事）
- 赛事管理
- 会员列表

### 测试功能

1. **注册账号** → 获得8钻石
2. **每日签到** → +1钻石
3. **查看赛事** → 需要1钻石解锁
4. **后台管理** → 导入/删除赛事

---

## 🔧 常见问题

### Q: Firebase 配置错误？

A: 检查 `index.html` 和 `admin.html` 中的 `firebaseConfig` 是否正确

### Q: 无法登录后台？

A: 默认账号是 `admin` / `admin888`，注意区分大小写

### Q: 预测脚本运行失败？

A: 检查：
1. `serviceAccountKey.json` 是否存在
2. Python 依赖是否安装
3. 网络连接是否正常

### Q: 定时任务没有执行？

A: 检查：
```bash
# 查看定时任务
crontab -l

# 查看日志
tail -f logs/predict.log
```

---

## 📊 下一步

1. **自定义联赛**：修改 `generate_predictions.py` 中的 `LEAGUES` 配置
2. **调整模型参数**：修改 `K`、`HOME_ADVANTAGE` 等参数
3. **添加更多球队Logo**：在后台管理中添加
4. **优化UI**：修改 CSS 样式

---

## 🎉 完成！

现在你有了一个完整的 AI 足球预测网站！

- 🌐 网站地址：`https://你的项目.web.app`
- 🔧 后台管理：`https://你的项目.web.app/admin.html`
- 📧 技术支持：Coze 平台

---

**⚠️ 重要提醒**

1. 部署后立即修改管理员密码
2. 生产环境请修改 Firestore 规则
3. 预测仅供参考，不构成投注建议

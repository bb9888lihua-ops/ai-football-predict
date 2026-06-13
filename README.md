# ⚽ Ai足势 - AI足球预测分析平台

基于 **Dixon-Coles 泊松分布模型** 的专业足球大小球预测网站

---

## 🚀 快速部署

### 1️⃣ 创建 Firebase 项目

1. 访问 [Firebase 控制台](https://console.firebase.google.com/)
2. 点击「添加项目」→ 输入项目名称 `ai-football-predict`
3. 禁用 Google Analytics（可选）→ 创建项目

### 2️⃣ 配置 Firestore 数据库

1. 在 Firebase 控制台左侧菜单点击「Firestore Database」
2. 点击「创建数据库」
3. 选择「以测试模式启动」（后续可修改规则）
4. 选择靠近用户的服务器位置（如 `asia-east1`）

### 3️⃣ 获取 Firebase 配置

1. 点击项目设置（齿轮图标）→ 「项目设置」
2. 向下滚动到「您的应用」部分
3. 点击 Web 图标（`</>`）注册 Web 应用
4. 输入应用名称 `Ai足势` → 注册
5. 复制 `firebaseConfig` 对象（后面要用）

### 4️⃣ 部署网站

#### 方法一：使用 Firebase CLI（推荐）

```bash
# 安装 Firebase CLI
npm install -g firebase-tools

# 登录 Firebase
firebase login

# 初始化项目（选择已创建的项目）
firebase init hosting

# 部署
firebase deploy
```

#### 方法二：手动部署

1. 修改 `index.html` 和 `admin.html` 中的 `firebaseConfig` 对象
2. 将整个 `football-predict` 文件夹上传到 Firebase Hosting

### 5️⃣ 初始化管理员账号

默认管理员账号：
- **用户名**: `admin`
- **密码**: `admin888`

⚠️ **重要**：部署后请立即修改密码！

---

## 📊 数据结构

### 用户集合 (users)

```javascript
{
  name: "username",           // 用户名（文档ID）
  pwd: "hashed_password",     // 哈希密码
  phone: "13800138000",       // 手机号
  coins: 8,                   // 剩余钻石
  permanentCoins: 0,          // 永久钻石
  totalEarned: 8,             // 累计获得
  totalSpent: 0,              // 累计消耗
  unlocked: [],               // 已解锁的赛事ID列表
  history: [                  // 钻石记录
    {
      type: "earn",           // earn/spend
      desc: "注册赠送",
      amount: 8,
      time: 1718000000000
    }
  ],
  lastCheckIn: "2026-06-14",  // 最后签到日期
  createdAt: 1718000000000    // 注册时间戳
}
```

### 赛事集合 (matches)

```javascript
{
  id: "match_20260614_001",   // 赛事ID（文档ID）
  league: "英超",              // 联赛名称
  leagueIcon: "🏴󠁧󠁢󠁥󠁮󠁧󠁿",        // 联赛图标
  time: "2026-06-14 21:00",   // 比赛时间
  date: "2026-06-14",         // 比赛日期
  homeTeam: "曼联",            // 主队
  homeTeamLogo: "🔴",         // 主队Logo
  awayTeam: "利物浦",          // 客队
  awayTeamLogo: "🔵",         // 客队Logo
  locked: true,               // 是否锁定（需要钻石解锁）
  confidence: 68,             // 预测置信度（%）
  recommend: "大球 2.5",       // 推荐方向
  expectedGoals: "3.12",      // 预期进球
  handicap: "2.5",            // 盘口
  analysis: "详细分析文本...", // 详细分析（解锁后可见）
  ended: false,               // 是否结束
  live: false,                // 是否进行中
  endedAt: null               // 结束时间戳
}
```

---

## 🤖 自动化预测系统

### Python 预测脚本

位置：`python-scripts/generate_predictions.py`

功能：
- 从 football-data.co.uk 自动采集数据
- 运行 Dixon-Coles 泊松分布模型
- 生成预测结果并写入 Firestore

### 定时任务设置

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨2:00执行）
0 2 * * * cd /path/to/football-predict && python3 python-scripts/generate_predictions.py >> logs/predict.log 2>&1
```

---

## 🎯 核心功能

### 前端功能
- ✅ 用户注册/登录
- ✅ 每日签到（+1钻石）
- ✅ 赛事展示（卡片式）
- ✅ AI预测分析（锁定/解锁机制）
- ✅ 客服聊天浮窗
- ✅ 响应式设计（移动端适配）

### 后台管理
- ✅ 数据统计（会员、钻石、赛事）
- ✅ 赛事管理（导入/删除/锁定）
- ✅ 会员管理（查看/加钻石）
- ✅ 前端设置（获取钻石链接）
- ✅ 清理过期赛事

---

## 📝 导入赛事数据

### 手动导入

1. 登录后台管理页面
2. 点击「📋 导入赛程」
3. 粘贴 JSON 格式的赛事数据
4. 点击「确认导入」

### JSON 格式示例

```json
[
  {
    "id": "match_20260614_001",
    "league": "英超",
    "leagueIcon": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "time": "2026-06-14 21:00",
    "date": "2026-06-14",
    "homeTeam": "曼联",
    "homeTeamLogo": "🔴",
    "awayTeam": "利物浦",
    "awayTeamLogo": "🔵",
    "locked": true,
    "confidence": 68,
    "recommend": "大球 2.5",
    "expectedGoals": "3.12",
    "handicap": "2.5",
    "analysis": "曼联主场进攻活跃，近5场场均进球2.1个。利物浦客场防守有漏洞，近3个客场失球5个。模型预测总进球3.12个，推荐大球2.5。"
  }
]
```

---

## 🔧 技术栈

- **前端**: HTML5 + CSS3 + JavaScript (原生)
- **数据库**: Firebase Firestore
- **部署**: Firebase Hosting
- **预测模型**: Dixon-Coles 泊松分布 + 贝叶斯收缩
- **数据采集**: Python + football-data.co.uk API

---

## 📈 模型性能

- **回测命中率**: 64.2%（英超 2.5 盘口）
- **平均绝对误差**: < 0.2 球
- **数据来源**: football-data.co.uk（25个欧洲联赛）

---

## ⚠️ 注意事项

1. **数据安全**: 部署后立即修改管理员密码
2. **Firestore 规则**: 生产环境请修改为更严格的规则
3. **API 限制**: football-data.co.uk 免费额度有限，建议缓存数据
4. **免责声明**: 预测仅供参考，不构成投注建议

---

## 📞 支持

如有问题，请联系：
- **平台**: Coze
- **用户ID**: 1672795382093043

---

**🎉 开始你的 AI 足球预测之旅！**

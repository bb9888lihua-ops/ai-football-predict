#!/bin/bash
# Ai足势 - 一键部署脚本

echo "=========================================="
echo "⚽ Ai足势 - 一键部署"
echo "=========================================="
echo ""

# 检查 Firebase CLI
if ! command -v firebase &> /dev/null; then
    echo "❌ 未安装 Firebase CLI"
    echo "正在安装..."
    npm install -g firebase-tools
fi

# 检查登录状态
if ! firebase projects:list &> /dev/null; then
    echo "🔐 请登录 Firebase"
    firebase login
fi

# 选择项目
echo ""
echo "📋 请选择 Firebase 项目："
firebase projects:list

read -p "输入项目ID（如：ai-football-predict）: " PROJECT_ID

# 初始化 Firebase
echo ""
echo "⚙️  初始化 Firebase..."
firebase use $PROJECT_ID

# 部署 Hosting
echo ""
echo "🚀 部署网站..."
firebase deploy --only hosting

echo ""
echo "=========================================="
echo "✅ 部署成功！"
echo "=========================================="
echo ""
echo "🌐 网站地址: https://$PROJECT_ID.web.app"
echo "🔧 后台管理: https://$PROJECT_ID.web.app/admin.html"
echo ""
echo "📝 默认管理员账号："
echo "   用户名: admin"
echo "   密码: admin888"
echo ""
echo "⚠️  请立即修改密码！"
echo ""
echo "📊 下一步："
echo "1. 登录后台管理页面"
echo "2. 导入示例数据（sample_matches.json）"
echo "3. 配置 Python 脚本实现自动预测"
echo ""

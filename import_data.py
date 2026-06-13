#!/usr/bin/env python3
"""导入示例数据到 Firestore"""
import json
import firebase_admin
from firebase_admin import credentials, firestore
import os

# 初始化 Firebase
cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json'))
firebase_admin.initialize_app(cred)
db = firestore.client()

print(" 连接 Firestore 成功！")

# 导入示例赛事
with open(os.path.join(os.path.dirname(__file__), 'sample_matches.json'), 'r', encoding='utf-8') as f:
    matches = json.load(f)

print(f"📦 导入 {len(matches)} 场赛事...")
for match in matches:
    doc_id = match.get('id', match.get('matchId', ''))
    if doc_id:
        db.collection('matches').document(str(doc_id)).set(match)
        print(f"  ✅ {match.get('homeTeam', '?')} vs {match.get('awayTeam', '?')}")

# 创建管理员账号
import hashlib
admin_password = hashlib.sha256(('admin888' + 'ai_football_salt').encode()).hexdigest()
admin_doc = {
    'username': 'admin',
    'password': admin_password,
    'role': 'admin',
    'createdAt': firestore.SERVER_TIMESTAMP
}
db.collection('admins').document('admin').set(admin_doc)
print("  ✅ 管理员账号 admin/admin888 已创建")

# 创建默认设置
settings = {
    'diamondPerRegister': 8,
    'diamondPerCheckin': 1,
    'diamondPerUnlock': 1,
    'getDiamondUrl': ''
}
db.collection('settings').document('config').set(settings)
print("  ✅ 默认设置已创建")

print("\n🎉 数据导入完成！")
print(f"📊 赛事数: {len(matches)}")
print(f" 管理员: admin / admin888")

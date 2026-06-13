#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ai足势 - 自动生成预测脚本
基于 Dixon-Coles 泊松分布模型
"""

import os
import sys
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import poisson
import firebase_admin
from firebase_admin import credentials, firestore

# ===== 配置 =====
FIREBASE_CONFIG_PATH = os.environ.get('FIREBASE_CONFIG', 'serviceAccountKey.json')
DATA_DIR = 'leagues'
LOG_DIR = 'logs'

# 模型参数（固定值）
RECENT_N = 15          # 近期比赛场次
K = 5.0                # 收缩系数
HOME_ADVANTAGE = 1.15  # 主场优势
MAX_GOALS = 8          # 概率矩阵上限

# 联赛配置
LEAGUES = {
    'E0': {'name': '英超', 'icon': '🏴󠁧󠁢󠁥󠁮󠁧󠁿'},
    'E1': {'name': '英冠', 'icon': '🏴󠁧󠁢󠁥󠁮󠁧󠁿'},
    'SP1': {'name': '西甲', 'icon': '🇪🇸'},
    'SP2': {'name': '西乙', 'icon': '🇪🇸'},
    'I1': {'name': '意甲', 'icon': '🇮🇹'},
    'I2': {'name': '意乙', 'icon': '🇮🇹'},
    'D1': {'name': '德甲', 'icon': '🇩🇪'},
    'D2': {'name': '德乙', 'icon': '🇩🇪'},
    'F1': {'name': '法甲', 'icon': '🇫🇷'},
    'F2': {'name': '法乙', 'icon': '🇫🇷'},
}

# ===== 初始化 =====
def init_firebase():
    """初始化 Firebase"""
    if not os.path.exists(FIREBASE_CONFIG_PATH):
        print(f"错误：找不到 Firebase 配置文件 {FIREBASE_CONFIG_PATH}")
        print("请从 Firebase 控制台下载 serviceAccountKey.json")
        sys.exit(1)

    cred = credentials.Certificate(FIREBASE_CONFIG_PATH)
    firebase_admin.initialize_app(cred)
    return firestore.client()

def ensure_dirs():
    """确保目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

# ===== 数据采集 =====
def download_league_data(league_code, season='2526'):
    """下载联赛数据"""
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        filepath = os.path.join(DATA_DIR, f"{league_code}_{season}.csv")
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"✅ 下载成功: {league_code} {season}")
        return filepath
    except Exception as e:
        print(f"❌ 下载失败: {league_code} {season} - {e}")
        return None

def load_data(league_code, season='2526'):
    """加载联赛数据"""
    filepath = os.path.join(DATA_DIR, f"{league_code}_{season}.csv")
    if not os.path.exists(filepath):
        return None
    try:
        df = pd.read_csv(filepath)
        # 验证必要字段
        required = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
        if not all(col in df.columns for col in required):
            return None
        return df
    except Exception as e:
        print(f"加载数据失败: {e}")
        return None

# ===== 模型计算 =====
def calculate_team_stats(df, team, recent_n=RECENT_N):
    """计算球队统计数据"""
    # 主场比赛
    home_matches = df[df['HomeTeam'] == team].head(recent_n)
    home_scored = home_matches['FTHG'].mean() if len(home_matches) > 0 else 0
    home_conceded = home_matches['FTAG'].mean() if len(home_matches) > 0 else 0

    # 客场比赛
    away_matches = df[df['AwayTeam'] == team].head(recent_n)
    away_scored = away_matches['FTAG'].mean() if len(away_matches) > 0 else 0
    away_conceded = away_matches['FTHG'].mean() if len(away_matches) > 0 else 0

    # 综合统计
    all_matches = pd.concat([
        home_matches[['FTHG', 'FTAG']].rename(columns={'FTHG': 'scored', 'FTAG': 'conceded'}),
        away_matches[['FTAG', 'FTHG']].rename(columns={'FTAG': 'scored', 'FTHG': 'conceded'})
    ]).head(recent_n)

    avg_scored = all_matches['scored'].mean() if len(all_matches) > 0 else 0
    avg_conceded = all_matches['conceded'].mean() if len(all_matches) > 0 else 0

    return {
        'home_scored': home_scored,
        'home_conceded': home_conceded,
        'away_scored': away_scored,
        'away_conceded': away_conceded,
        'avg_scored': avg_scored,
        'avg_conceded': avg_conceded,
        'matches': len(all_matches)
    }

def calculate_league_baseline(df, recent_matches=200):
    """计算联赛基准"""
    recent = df.head(recent_matches)
    league_avg = (recent['FTHG'].sum() + recent['FTAG'].sum()) / (len(recent) * 2)
    baseline = league_avg / 2.0  # 关键：除以2
    return league_avg, baseline

def bayesian_shrinkage(observed, baseline, n, k=K):
    """贝叶斯收缩"""
    weight = n / (n + k)
    return weight * observed + (1 - weight) * baseline

def calculate_expected_goals(home_stats, away_stats, baseline):
    """计算预期进球"""
    # 收缩后的统计
    shrink_home_scored = bayesian_shrinkage(home_stats['home_scored'], baseline, home_stats['matches'])
    shrink_home_conceded = bayesian_shrinkage(home_stats['home_conceded'], baseline, home_stats['matches'])
    shrink_away_scored = bayesian_shrinkage(away_stats['away_scored'], baseline, away_stats['matches'])
    shrink_away_conceded = bayesian_shrinkage(away_stats['away_conceded'], baseline, away_stats['matches'])

    # 攻防强度
    attack_home = shrink_home_scored / baseline if baseline > 0 else 1
    weakness_away = shrink_away_conceded / baseline if baseline > 0 else 1
    attack_away = shrink_away_scored / baseline if baseline > 0 else 1
    weakness_home = shrink_home_conceded / baseline if baseline > 0 else 1

    # 预期进球
    lambda_home = attack_home * weakness_away * baseline * HOME_ADVANTAGE
    lambda_away = attack_away * weakness_home * baseline

    return lambda_home, lambda_away

def calculate_probabilities(lambda_home, lambda_away):
    """计算概率矩阵"""
    # 构建 8x8 比分概率矩阵
    prob_matrix = np.zeros((MAX_GOALS, MAX_GOALS))
    for h in range(MAX_GOALS):
        for a in range(MAX_GOALS):
            prob_matrix[h, a] = poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)

    # 计算进球数分布
    total_goals_prob = np.zeros(2 * MAX_GOALS)
    for h in range(MAX_GOALS):
        for a in range(MAX_GOALS):
            total_goals_prob[h + a] += prob_matrix[h, a]

    # 计算大小球概率
    over_25 = sum(total_goals_prob[3:])  # 3球及以上
    under_25 = sum(total_goals_prob[:3])  # 0-2球
    over_35 = sum(total_goals_prob[4:])  # 4球及以上
    under_35 = sum(total_goals_prob[:4])  # 0-3球

    # 最可能比分
    score_probs = []
    for h in range(4):
        for a in range(4):
            score_probs.append({
                'score': f"{h}-{a}",
                'prob': prob_matrix[h, a]
            })
    score_probs.sort(key=lambda x: x['prob'], reverse=True)

    return {
        'lambda_home': lambda_home,
        'lambda_away': lambda_away,
        'expected_total': lambda_home + lambda_away,
        'over_25': over_25,
        'under_25': under_25,
        'over_35': over_35,
        'under_35': under_35,
        'top_scores': score_probs[:5]
    }

def generate_prediction(home_team, away_team, df):
    """生成单场比赛预测"""
    # 计算统计
    home_stats = calculate_team_stats(df, home_team)
    away_stats = calculate_team_stats(df, away_team)
    league_avg, baseline = calculate_league_baseline(df)

    # 计算预期进球
    lambda_home, lambda_away = calculate_expected_goals(home_stats, away_stats, baseline)
    probs = calculate_probabilities(lambda_home, lambda_away)

    # 推荐方向
    if probs['expected_total'] > 2.8:
        recommend = "大球 2.5"
        handicap = "2.5"
        confidence = int(probs['over_25'] * 100)
    elif probs['expected_total'] < 2.2:
        recommend = "小球 2.5"
        handicap = "2.5"
        confidence = int(probs['under_25'] * 100)
    elif probs['expected_total'] > 3.3:
        recommend = "大球 3.5"
        handicap = "3.5"
        confidence = int(probs['over_35'] * 100)
    else:
        recommend = "小球 3.5"
        handicap = "3.5"
        confidence = int(probs['under_35'] * 100)

    # 生成分析文本
    analysis = f"{home_team}主场近{home_stats['matches']}场场均进球{home_stats['home_scored']:.1f}个，"
    analysis += f"{away_team}客场场均进球{away_stats['away_scored']:.1f}个。"
    analysis += f"模型预测总进球{probs['expected_total']:.2f}个，推荐{recommend}。"

    return {
        'confidence': confidence,
        'recommend': recommend,
        'expectedGoals': f"{probs['expected_total']:.2f}",
        'handicap': handicap,
        'analysis': analysis,
        'lambda_home': lambda_home,
        'lambda_away': lambda_away,
        'top_scores': probs['top_scores']
    }

# ===== 主流程 =====
def main():
    """主函数"""
    print("=" * 70)
    print("⚽ Ai足势 - 自动生成预测")
    print("=" * 70)
    print(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    ensure_dirs()
    db = init_firebase()

    # 下载最新数据
    print("📥 开始采集数据...")
    for code in ['E0', 'SP1', 'I1', 'D1', 'F1']:
        download_league_data(code, '2526')
    print()

    # 生成预测（示例：明天的比赛）
    print("🤖 生成预测...")
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime('%Y-%m-%d')

    # 这里应该从数据源获取明天的赛程
    # 示例：手动指定几场比赛
    sample_matches = [
        ('E0', '曼联', '利物浦', '21:00'),
        ('SP1', '巴塞罗那', '皇家马德里', '23:00'),
        ('D1', '拜仁慕尼黑', '多特蒙德', '21:30'),
    ]

    predictions = []
    for league_code, home, away, time in sample_matches:
        df = load_data(league_code, '2526')
        if df is None:
            print(f"⚠️ 跳过: {league_code} 数据不可用")
            continue

        pred = generate_prediction(home, away, df)
        match_id = f"match_{date_str.replace('-', '')}_{len(predictions)+1:03d}"

        match_data = {
            'id': match_id,
            'league': LEAGUES[league_code]['name'],
            'leagueIcon': LEAGUES[league_code]['icon'],
            'time': f"{date_str} {time}",
            'date': date_str,
            'homeTeam': home,
            'homeTeamLogo': '🏠',
            'awayTeam': away,
            'awayTeamLogo': '✈️',
            'locked': True,
            'confidence': pred['confidence'],
            'recommend': pred['recommend'],
            'expectedGoals': pred['expectedGoals'],
            'handicap': pred['handicap'],
            'analysis': pred['analysis'],
            'ended': False,
            'live': False
        }

        # 写入 Firestore
        db.collection('matches').document(match_id).set(match_data)
        predictions.append(match_data)
        print(f"✅ {home} vs {away} - {pred['recommend']} (置信度 {pred['confidence']}%)")

    print()
    print(f"🎉 成功生成 {len(predictions)} 场预测")
    print("=" * 70)

if __name__ == '__main__':
    main()

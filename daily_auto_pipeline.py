#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动化流水线：数据采集 → 竞彩预测 → 报告发送
铁律：每天北京时间11:00自动执行
"""

import subprocess
import sys
import os
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).parent
BRIDGE = os.path.expanduser("~/.coze/bridge/bin/coze-bridge")
AGENT_ID = "7650442795123081491"
SESSION_ID = "7650443180743229750"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def run_cmd(cmd, timeout=600):
    """执行命令并返回结果"""
    log(f"  执行: {cmd[:100]}...")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(WORKSPACE)
        )
        if result.returncode != 0:
            log(f"  ⚠️  退出码 {result.returncode}: {result.stderr[:200]}")
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        log(f"  ❌ 命令超时 ({timeout}s)")
        return -1, "", "timeout"
    except Exception as e:
        log(f"  ❌ 命令异常: {e}")
        return -1, "", str(e)


def gen_match_id(home_team, away_team, match_time):
    """基于比赛内容生成唯一ID，避免重新部署后ID重复导致解锁记录错乱"""
    raw = f"{home_team}|{away_team}|{match_time}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
    date_part = match_time.split(' ')[0].replace('-', '') if ' ' in match_time else '00000000'
    return f"match_{date_part}_{short_hash}"


def step1_collect_data():
    """Step 1: 从football-data.co.uk采集最新联赛数据"""
    log("=" * 50)
    log("📥 Step 1: 采集最新联赛数据 (football-data.co.uk)")
    log("=" * 50)

    collector = WORKSPACE / "auto_data_collector.py"
    if not collector.exists():
        log(f"❌ 找不到 {collector}")
        return False

    code, stdout, stderr = run_cmd(
        f"python3 {collector}", timeout=300
    )

    # 输出关键信息
    for line in stdout.split('\n'):
        if any(k in line for k in ['✅', '❌', '下载', '更新', '总计', '验证', '报告']):
            log(f"  {line.strip()}")

    if code != 0:
        log("❌ 数据采集失败")
        return False

    log("✅ Step 1 完成")
    return True


def step2_scrape_and_predict():
    """Step 2: 采集竞彩赛程并运行AI预测"""
    log("=" * 50)
    log("🔮 Step 2: 采集竞彩赛程 + AI预测")
    log("=" * 50)

    scraper = WORKSPACE / "sporttery_scraper.py"
    if not scraper.exists():
        log(f"❌ 找不到 {scraper}")
        return None

    code, stdout, stderr = run_cmd(
        f"python3 {scraper}", timeout=300
    )

    # 输出关键信息
    for line in stdout.split('\n'):
        if any(k in line for k in ['✅', '❌', '采集', '预测', '报告', '赛事']):
            log(f"  {line.strip()}")

    if code != 0:
        log("❌ 竞彩采集/预测失败")
        return None

    # 找到生成的报告文件
    today_str = datetime.now().strftime("%Y%m%d")
    report_file = WORKSPACE / f"prediction_{today_str}.md"

    if report_file.exists():
        log(f"✅ Step 2 完成，报告: {report_file}")
        return report_file
    else:
        # 尝试找最新的sporttery报告（旧格式）
        for f in sorted(WORKSPACE.glob(f"sporttery_predictions_{today_str}*.md"), reverse=True):
            log(f"✅ Step 2 完成，报告: {f}")
            return f
        log("⚠️  未找到报告文件")
        return None


def step2_5_generate_website():
    """Step 2.5: 生成公开网站"""
    log("=" * 50)
    log("🌐 Step 2.5: 生成公开预测网站")
    log("=" * 50)

    generator = WORKSPACE / "generate_website.py"
    if not generator.exists():
        log(f"❌ 找不到 {generator}")
        return False

    code, stdout, stderr = run_cmd(
        f"python3 {generator}", timeout=60
    )

    for line in stdout.split('\n'):
        if any(k in line for k in ['✅', '❌', '🔍', '📊', '🔨', '📦']):
            log(f"  {line.strip()}")

    if code != 0:
        log(f"❌ 网站生成失败: {stderr[:200]}")
        return False

    log("✅ Step 2.5 完成")
    return True


def step2_6_update_github_pages():
    """Step 2.6: 更新GitHub Pages的matches.json（真实比赛数据）"""
    log("=" * 50)
    log("🌐 Step 2.6: 更新GitHub Pages比赛数据")
    log("=" * 50)

    # 查找最新预测文件
    pred_dir = WORKSPACE / "sporttery_data"
    pred_files = sorted(pred_dir.glob("predictions_*.json"), reverse=True)
    if not pred_files:
        log("❌ 没有找到预测文件，跳过GitHub Pages更新")
        return False

    latest_pred = pred_files[0]
    log(f"  使用预测文件: {latest_pred.name}")

    try:
        with open(latest_pred, encoding='utf-8') as f:
            predictions = json.load(f)
        if isinstance(predictions, dict):
            predictions = predictions.get("predictions", [])
    except Exception as e:
        log(f"❌ 读取预测文件失败: {e}")
        return False

    # TheSportsDB 球队名映射（用于搜索真实队徽）
    THESPORTSDB_NAMES = {
        # 国家队
        "Brazil": "Brazil", "Norway": "Norway", "Mexico": "Mexico",
        "England": "England", "Argentina": "Argentina", "France": "France",
        "Germany": "Germany", "Spain": "Spain", "Japan": "Japan",
        "South Korea": "South Korea", "USA": "USA", "Canada": "Canada",
        "Sweden": "Sweden", "Denmark": "Denmark", "Finland": "Finland",
        "Iceland": "Iceland",
        # 韩K
        "FC Seoul": "FC Seoul", "Incheon United": "Incheon United",
        "Gwangju FC": "Gwangju FC", "Ulsan HD": "Ulsan HD",
        "Gimcheon Sangmu": "Gimcheon Sangmu", "Jeju SK": "Jeju United",
        # 瑞典超
        "Kalmar": "Kalmar FF", "Orgryte": "Orgryte IS",
        "Goteborg": "IFK Goteborg", "AIK": "AIK Solna",
        "Elfsborg": "IF Elfsborg", "Hammarby": "Hammarby IF",
        "Djurgarden": "Djurgardens IF", "Halmstad": "Halmstads BK",
        "Malmo": "Malmo FF", "Norrkoping": "IFK Norrkoping",
        "Hacken": "BK Hacken", "Brommapojkarna": "IF Brommapojkarna",
        "Mjallby": "Mjallby AIF", "Sirius": "IK Sirius",
        "Varnamo": "IFK Varnamo", "Halland": "Halmstads BK",
        # 挪超
        "Molde": "Molde FK", "Bodo Glimt": "FK Bodo/Glimt",
        "Rosenborg": "Rosenborg BK", "Viking": "Viking FK",
        # 日职
        "Kawasaki Frontale": "Kawasaki Frontale", "Yokohama F Marinos": "Yokohama F. Marinos",
        "Urawa Red Diamonds": "Urawa Red Diamonds", "Cerezo Osaka": "Cerezo Osaka",
        "FC Tokyo": "FC Tokyo", "Kashima Antlers": "Kashima Antlers",
    }

    CN_TO_EN = {
        "巴西": "Brazil", "挪威": "Norway", "墨西哥": "Mexico", "英格兰": "England",
        "阿根廷": "Argentina", "法国": "France", "德国": "Germany", "西班牙": "Spain",
        "日本": "Japan", "韩国": "South Korea", "美国": "USA", "加拿大": "Canada",
        "瑞典": "Sweden", "丹麦": "Denmark", "芬兰": "Finland", "冰岛": "Iceland",
        "首尔FC": "FC Seoul", "仁川联": "Incheon United",
        "光州FC": "Gwangju FC", "蔚山现代": "Ulsan HD",
        "金泉尚武": "Gimcheon Sangmu", "济州SK": "Jeju SK", "济州联": "Jeju SK",
        "卡尔马": "Kalmar", "厄尔格里特": "Orgryte",
        "IFK哥德堡": "Goteborg", "哥德堡": "Goteborg",
        "AIK索尔纳": "AIK", "索尔纳": "AIK",
        "埃尔夫斯堡": "Elfsborg", "哈马比": "Hammarby",
        "佐加顿斯": "Djurgarden", "尤尔加登": "Djurgarden",
        "哈尔姆斯塔德": "Halmstad",
        "马尔默": "Malmo", "诺尔雪平": "Norrkoping",
        "赫根": "Hacken", "布洛马波卡纳": "Brommapojkarna",
        "米亚尔比": "Mjallby", "天狼星": "Sirius",
        "瓦尔纳默": "Varnamo",
        "莫尔德": "Molde", "博德闪耀": "Bodo Glimt",
        "罗森博格": "Rosenborg", "维京": "Viking",
        "川崎前锋": "Kawasaki Frontale", "横滨水手": "Yokohama F Marinos",
        "浦和红钻": "Urawa Red Diamonds", "大阪樱花": "Cerezo Osaka",
        "FC东京": "FC Tokyo", "鹿岛鹿角": "Kashima Antlers",
    }

    LEAGUE_ICONS = {
        "世界杯": "🏆", "韩职": "🇰🇷", "瑞超": "🇸🇪", "SWE": "🇸🇪",
        "international": "🏆", "韩K": "🇰🇷", "挪超": "🇳🇴",
        "日职": "🇯🇵", "芬超": "🇫🇮", "冰岛超": "🇮🇸",
    }

    # TheSportsDB 队徽缓存
    _badge_cache = {}

    def fetch_thesportsdb_badge(team_en):
        """从TheSportsDB获取球队真实队徽URL"""
        if team_en in _badge_cache:
            return _badge_cache[team_en]

        search_name = THESPORTSDB_NAMES.get(team_en, team_en)
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={search_name.replace(' ', '%20')}"
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=8)
            data = json.loads(resp.read())
            if data.get('teams'):
                badge = data['teams'][0].get('strBadge', '')
                if badge and 'thesportsdb.com' in badge:
                    _badge_cache[team_en] = badge
                    return badge
        except Exception as e:
            log(f"  ⚠️ TheSportsDB查询失败 {team_en}: {e}")
        _badge_cache[team_en] = None
        return None

    def logo_url(team_en):
        """获取球队真实队徽URL（TheSportsDB优先）"""
        badge = fetch_thesportsdb_badge(team_en)
        if badge:
            return badge
        return "⚽"  # 找不到则用足球emoji

    def logo_to_base64(url):
        """下载logo图片并转为base64 data URI，失败则返回原URL"""
        if not url or not url.startswith('http'):
            return url
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read()
            b64 = base64.b64encode(data).decode()
            return f'data:image/png;base64,{b64}'
        except Exception as e:
            log(f"  ⚠️ logo下载失败 {url}: {e}")
            return url

    def get_mismatch(pred):
        lh, la = pred['lambda_home'], pred['lambda_away']
        if lh > la * 1.5: return "主强客弱"
        elif la > lh * 1.5: return "客强主弱"
        return "势均力敌"

    def poisson_win_probs(lh, la, max_goals=8):
        """从泊松参数计算主胜/平/客胜概率"""
        import math
        def poisson_pmf(k, lam):
            return math.exp(-lam) * (lam ** k) / math.factorial(k)
        p_home, p_draw, p_away = 0.0, 0.0, 0.0
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                p = poisson_pmf(i, lh) * poisson_pmf(j, la)
                if i > j: p_home += p
                elif i == j: p_draw += p
                else: p_away += p
        return p_home, p_draw, p_away

    def gen_analysis(pred):
        home = pred['match']['home']
        away = pred['match']['away']
        lh = pred['lambda_home']
        la = pred['lambda_away']
        total = lh + la
        hs = pred.get('h_stats', {})
        a_s = pred.get('a_stats', {})
        h_scored = hs.get('scored', 0)
        h_conceded = hs.get('conceded', 0)
        a_scored = a_s.get('scored', 0)
        a_conceded = a_s.get('conceded', 0)
        p_home, p_draw, p_away = poisson_win_probs(lh, la)

        lines = []
        # ⚡ 进球预期
        diff = total - 2.5
        if diff > 0.3:
            lines.append(
                f'<span style="color:#00d4ff">⚡</span> '
                f'<b>进球预期</b> — 总进球{total:.2f}'
                f'，偏离2.5盘{abs(diff):.2f}球，大球概率高'
            )
        elif diff < -0.3:
            lines.append(
                f'<span style="color:#00d4ff">⚡</span> '
                f'<b>进球预期</b> — 总进球{total:.2f}'
                f'，偏离2.5盘{abs(diff):.2f}球，小球概率高'
            )
        else:
            lines.append(
                f'<span style="color:#00d4ff">⚡</span> '
                f'<b>进球预期</b> — 总进球{total:.2f}，接近2.5盘'
            )
        #  实力对比
        strength_diff = abs(lh - la)
        if strength_diff >= 0.5:
            strong = home if lh > la else away
            lines.append(
                f'<span style="color:#a855f7"></span> '
                f'<b>实力对比</b> — {strong}实力占优'
                f'（λ差值{strength_diff:.2f}）'
            )
        # 🎯 推荐方向
        rec = pred.get('v3_pred_25', '')
        mismatch = get_mismatch(pred)
        advice = []
        if rec in ('大球', '小球'):
            advice.append(rec)
        if mismatch in ('主强客弱',):
            advice.append(f"{home}胜")
        elif mismatch in ('客强主弱',):
            advice.append(f"{away}胜")
        if advice:
            lines.append(
                f'<span style="color:#22c55e">🎯</span> '
                f'<b>推荐方向</b> — {" + ".join(advice)}'
            )
        return "<br>".join(lines)

    matches = []
    for pred in predictions:
        home_cn = pred['home_team']
        away_cn = pred['away_team']
        home_en = pred.get('home_team_en', CN_TO_EN.get(home_cn, home_cn))
        away_en = pred.get('away_team_en', CN_TO_EN.get(away_cn, away_cn))
        date_part, time_part = pred['match_time'].split(' ')
        league_cn = pred.get('league_cn', pred.get('league', ''))
        total_goals = pred['lambda_home'] + pred['lambda_away']
        rec = pred.get('v3_pred_25', '未知')
        conf = pred.get('v3_conf_25', 50)

        matches.append({
            "id": gen_match_id(home_cn, away_cn, pred['match_time']),
            "league": league_cn,
            "leagueIcon": LEAGUE_ICONS.get(league_cn, '⚽'),
            "date": date_part, "time": time_part,
            "homeTeam": home_cn,
            "homeTeamLogo": logo_url(home_en),
            "awayTeam": away_cn,
            "awayTeamLogo": logo_url(away_en),
            "locked": False,
            "confidence": round(conf),
            "recommend": rec,
            "lambdaHome": f"{pred['lambda_home']:.2f}",
            "lambdaAway": f"{pred['lambda_away']:.2f}",
            "totalGoals": f"{total_goals:.2f}",
            "expectedGoals": f"{total_goals:.2f}",
            "overUnder": rec,
            "analysis": gen_analysis(pred),
            "mismatch": get_mismatch(pred),
        })

    # 将logo URL转为base64嵌入（不依赖外部CDN）
    logo_cache = {}
    for m in matches:
        for key in ['homeTeamLogo', 'awayTeamLogo']:
            url = m.get(key, '')
            if url and url.startswith('http'):
                if url not in logo_cache:
                    logo_cache[url] = logo_to_base64(url)
                m[key] = logo_cache[url]
    log(f"  logo转换完成，缓存 {len(logo_cache)} 个")

    # 写入matches.json
    matches_path = WORKSPACE / "football-predict" / "data" / "matches.json"
    matches_path.parent.mkdir(parents=True, exist_ok=True)
    with open(matches_path, 'w', encoding='utf-8') as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    log(f"  生成 {len(matches)} 场真实比赛数据（logo已嵌入base64）")

    # 部署到GitHub Pages
    content_b64 = base64.b64encode(matches_path.read_bytes()).decode()

    # 获取当前SHA
    code, stdout, stderr = run_cmd(
        "gh api repos/bb9888lihua-ops/ai-football-predict/contents/data/matches.json --jq .sha",
        timeout=30
    )
    if code != 0:
        log(f"❌ 获取GitHub SHA失败: {stderr[:200]}")
        return False
    sha = stdout.strip()

    # 推送更新
    code, stdout, stderr = run_cmd(
        f'gh api repos/bb9888lihua-ops/ai-football-predict/contents/data/matches.json '
        f'-X PUT -f message="自动更新预测数据" '
        f'-f content="{content_b64}" -f sha="{sha}" -f branch="master" --jq .commit.sha',
        timeout=30
    )
    if code != 0:
        log(f"❌ 部署GitHub Pages失败: {stderr[:200]}")
        return False

    log(f"✅ Step 2.6 完成，GitHub Pages已更新 ({len(matches)}场比赛)")
    return True


def step2_75_deploy_website():
    """Step 2.75: 部署网站到Coze Code"""
    log("=" * 50)
    log("🚀 Step 2.75: 部署网站到Coze Code")
    log("=" * 50)

    html_file = WORKSPACE / "public_site" / "index.html"
    if not html_file.exists():
        log(f"❌ 找不到 {html_file}，跳过部署")
        return False

    COZE_PROJECT_ID = "7653897862404685887"
    DEPLOY_PATH = "/workspace/projects/public/index.html"

    # 读取HTML内容（仅用于日志）
    html_content = html_file.read_text(encoding="utf-8")
    log(f"  HTML文件大小: {len(html_content)} 字符")

    # 写入Coze Code项目 — 用文件重定向避免shell解析HTML特殊字符
    write_cmd = (
        f"coze code message send "
        f"'请将以下内容写入 {DEPLOY_PATH}，不要修改任何内容，直接写入：' "
        f"--stdin -p {COZE_PROJECT_ID} < {html_file}"
    )

    code, stdout, stderr = run_cmd(write_cmd, timeout=120)
    if code != 0:
        log(f"❌ 写入Coze Code失败: {stderr[:200]}")
        return False

    log("  ✅ 文件已写入Coze Code项目")

    # 部署
    deploy_cmd = f"coze code deploy {COZE_PROJECT_ID}"
    code, stdout, stderr = run_cmd(deploy_cmd, timeout=60)
    if code != 0:
        log(f"❌ 部署失败: {stderr[:200]}")
        return False

    # 检查部署状态（Next.js项目部署需要60-90秒，循环等待）
    import time
    max_wait = 120  # 最多等2分钟
    interval = 10   # 每10秒检查一次
    elapsed = 0
    status_cmd = f"coze code deploy status {COZE_PROJECT_ID}"

    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        code, stdout, stderr = run_cmd(status_cmd, timeout=30)
        if "Succeeded" in stdout:
            log(f"✅ Step 2.75 完成，网站已部署上线 (等待{elapsed}秒)")
            return True
        elif "Failed" in stdout:
            log(f"❌ 部署失败: {stdout[:200]}")
            return False
        else:
            log(f"  ⏳ 部署中... 已等待{elapsed}秒")

    log(f"⚠️  部署超时({max_wait}秒)，请手动检查")
    return True  # 部署命令已成功，只是状态未确认


def step3_send_report(report_file):
    """Step 3: 发送报告给用户"""
    log("=" * 50)
    log("📤 Step 3: 发送预测报告")
    log("=" * 50)

    if not report_file or not Path(report_file).exists():
        log("❌ 没有报告可发送")
        return False

    cmd = (
        f'{BRIDGE} send file "{report_file}" '
        f'--agent-id {AGENT_ID} --session-id {SESSION_ID} '
        f'--caption "📊 {datetime.now().strftime("%Y-%m-%d")} 竞彩AI预测报告"'
    )

    code, stdout, stderr = run_cmd(cmd, timeout=60)

    if code == 0:
        log(f"✅ 报告已发送: {report_file}")
        return True
    else:
        log(f"❌ 发送失败: {stderr}")
        return False


def main():
    """主函数：执行完整的每日自动化流水线"""
    log("=" * 60)
    log("🏆 每日自动化流水线启动")
    log(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"📂 工作目录: {WORKSPACE}")
    log("=" * 60)

    start_time = datetime.now()

    # Step 1: 采集数据
    data_ok = step1_collect_data()

    # Step 2: 竞彩预测（即使数据采集部分失败也尝试，可能已有最新数据）
    report_file = step2_scrape_and_predict()

    # Step 2.5: 生成公开网站
    if report_file:
        step2_5_generate_website()

    # Step 2.6: 更新GitHub Pages比赛数据
    step2_6_update_github_pages()

    # Step 2.75: 部署网站到Coze Code
    if report_file:
        step2_75_deploy_website()

    # Step 3: 发送报告
    if report_file:
        step3_send_report(report_file)
    else:
        log("⚠️  无预测报告可发送")

    # 汇总
    elapsed = (datetime.now() - start_time).total_seconds()
    log("=" * 60)
    log(f"✅ 流水线完成，耗时 {elapsed:.0f} 秒")
    log("=" * 60)

    return 0 if report_file else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n⚠️  用户中断")
        sys.exit(0)
    except Exception as e:
        log(f"\n❌ 流水线异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
generate_website.py — 生成AI足势公开预测网站
读取每日预测JSON，生成静态HTML网站到 public_site/
"""

import json
import glob
import os
import math
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(__file__).parent
DATA_DIR = WORKSPACE / "sporttery_data"
OUTPUT_DIR = WORKSPACE / "public_site"


def _gen_match_id(home_team, away_team, match_time):
    """基于比赛内容生成唯一ID，避免重新部署后ID重复导致解锁记录错乱"""
    raw = f"{home_team}|{away_team}|{match_time}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
    date_part = match_time.split(' ')[0].replace('-', '') if ' ' in match_time else '00000000'
    return f"match_{date_part}_{short_hash}"


def _extract_matches(raw):
    """从预测JSON中提取比赛列表，兼容两种格式"""
    # 格式1: 直接是列表 (sporttery_scraper标准输出)
    if isinstance(raw, list):
        # 标准化match_id为内容哈希，避免位置ID导致解锁记录错乱
        for item in raw:
            ht = item.get("home_team", item.get("home", ""))
            at = item.get("away_team", item.get("away", ""))
            mt = item.get("match_time", item.get("time", ""))
            if ht and at and mt:
                item["match_id"] = _gen_match_id(ht, at, mt)
        return raw
    # 格式2: dict with "predictions" key (verified格式)
    if isinstance(raw, dict) and "predictions" in raw:
        preds = raw["predictions"]
        if isinstance(preds, list):
            # 标准化字段名到网站期望的格式
            normalized = []
            for p in preds:
                ht = p.get("home", p.get("home_team", ""))
                at = p.get("away", p.get("away_team", ""))
                mt = p.get("time", p.get("match_time", ""))
                normalized.append({
                    "match_id": _gen_match_id(ht, at, mt),
                    "league_cn": p.get("league", p.get("league_cn", "")),
                    "home_team": ht,
                    "away_team": at,
                    "match_time": mt,
                    "lambda_home": p.get("lambda_home", 0),
                    "lambda_away": p.get("lambda_away", 0),
                    "v3_pred_25": p.get("over25", p.get("v3_pred_25", "")),
                    "v3_conf_25": p.get("warning", p.get("v3_conf_25", 0)),
                })
            return normalized
    return []


def find_latest_predictions():
    """找到每天的预测文件（每天取最新的一个），返回最近7天"""
    pattern = str(DATA_DIR / "predictions_*.json")
    files = sorted(glob.glob(pattern))

    # 按日期分组，每天的所有文件按排序倒序（最新在前）
    by_date = {}
    for f in files:
        basename = os.path.basename(f)
        date_str = basename.split("_")[1]  # YYYYMMDD
        by_date.setdefault(date_str, []).append(f)

    # 取最近7天
    dates = sorted(by_date.keys(), reverse=True)[:7]
    result = []
    for d in dates:
        # 优先选 _HHMMSS.json 标准格式（按时间戳倒序），_verified 作为最后备选
        day_files = sorted(by_date[d], reverse=True)
        standard = [f for f in day_files if not f.endswith("_verified.json")]
        fallback = [f for f in day_files if f.endswith("_verified.json")]
        matches = []
        chosen_file = None
        for f in standard + fallback:
            with open(f, "r", encoding="utf-8") as fp:
                raw = json.load(fp)
            matches = _extract_matches(raw)
            if matches:
                chosen_file = f
                break
        if matches:
            result.append({
                "date": d,
                "file": os.path.basename(chosen_file),
                "matches": matches,
            })
    return result


def poisson_pmf(k, lam):
    """泊松概率"""
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def compute_score_matrix(lam_home, lam_away, max_goals=6):
    """计算比分概率矩阵"""
    matrix = []
    for i in range(max_goals):
        row = []
        for j in range(max_goals):
            p = poisson_pmf(i, lam_home) * poisson_pmf(j, lam_away)
            row.append(round(p * 100, 1))
        matrix.append(row)
    return matrix


def _build_extra_css():
    """Build extra CSS for user registration system (regular string, no f-string issues)"""
    return """
/* Navbar */
.navbar{background:rgba(10,14,23,0.95);backdrop-filter:blur(10px);border-bottom:1px solid rgba(30,42,74,0.5);padding:0 20px;display:flex;align-items:center;justify-content:space-between;height:56px;position:sticky;top:0;z-index:100}
.navbar-brand{font-size:20px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.navbar-actions{display:flex;align-items:center;gap:10px}
.btn-nav{padding:7px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all 0.2s}
.btn-login{background:transparent;color:#94a3b8;border:1px solid rgba(148,163,185,0.3)}
.btn-login:hover{color:#e2e8f0;border-color:rgba(148,163,185,0.6)}
.btn-register{background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff}
.btn-register:hover{opacity:0.9;transform:translateY(-1px)}
.user-avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#f59e0b,#ef4444);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;color:#fff;cursor:pointer;border:2px solid rgba(245,158,11,0.3);transition:all 0.2s;position:relative}
.user-avatar:hover{border-color:#f59e0b;transform:scale(1.05)}
.user-dropdown{position:absolute;top:calc(100% + 8px);right:0;width:220px;background:rgba(15,20,34,0.98);backdrop-filter:blur(20px);border:1px solid rgba(30,42,74,0.6);border-radius:12px;padding:8px 0;display:none;z-index:200;box-shadow:0 12px 40px rgba(0,0,0,0.5)}
.user-dropdown.open{display:block}
.user-dropdown-header{padding:12px 16px;border-bottom:1px solid rgba(30,42,74,0.4);display:flex;align-items:center;gap:10px}
.user-dropdown-avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#f59e0b,#ef4444);display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:700;color:#fff}
.user-dropdown-info{flex:1;overflow:hidden}
.user-dropdown-name{font-size:14px;font-weight:600;color:#e8eaf0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.user-dropdown-time{font-size:11px;color:#4a5568;margin-top:2px}
.user-dropdown-item{padding:10px 16px;display:flex;align-items:center;gap:10px;cursor:pointer;transition:background 0.15s;color:#94a3b8;font-size:13px}
.user-dropdown-item:hover{background:rgba(30,42,74,0.4);color:#e8eaf0}
.user-dropdown-item .dd-count{margin-left:auto;background:rgba(239,68,68,0.15);color:#ef4444;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.user-dropdown-divider{height:1px;background:rgba(30,42,74,0.4);margin:4px 0}

/* Auth Modals */
.modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);display:none;align-items:center;justify-content:center;z-index:1000}
.modal-overlay.open{display:flex}
.auth-modal{background:rgba(15,20,34,0.98);border:1px solid rgba(30,42,74,0.6);border-radius:20px;padding:36px 32px;width:100%;max-width:400px;position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.5)}
.auth-modal h2{font-size:22px;font-weight:700;text-align:center;margin-bottom:6px;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.auth-modal .auth-subtitle{text-align:center;color:#4a5568;font-size:13px;margin-bottom:24px}
.auth-modal .close-btn{position:absolute;top:16px;right:16px;background:none;border:none;color:#4a5568;font-size:20px;cursor:pointer;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:50%;transition:all 0.2s}
.auth-modal .close-btn:hover{background:rgba(30,42,74,0.5);color:#e8eaf0}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:13px;color:#7a8bb5;margin-bottom:6px;font-weight:500}
.form-group input{width:100%;padding:11px 14px;background:rgba(10,14,23,0.6);border:1px solid rgba(30,42,74,0.5);border-radius:10px;color:#e8eaf0;font-size:14px;outline:none;transition:border-color 0.2s}
.form-group input:focus{border-color:#f59e0b}
.form-group input::placeholder{color:#3a4560}
.btn-auth{width:100%;padding:12px;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.2s;background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff;margin-top:8px}
.btn-auth:hover{opacity:0.9;transform:translateY(-1px)}
.btn-auth:disabled{opacity:0.5;cursor:not-allowed;transform:none}
.auth-switch{text-align:center;margin-top:18px;font-size:13px;color:#4a5568}
.auth-switch a{color:#f59e0b;cursor:pointer;font-weight:500}
.auth-switch a:hover{text-decoration:underline}
.auth-msg{padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:14px;display:none}
.auth-msg.error{display:block;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);color:#ef4444}
.auth-msg.success{display:block;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.2);color:#22c55e}

/* Toast */
.toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%) translateY(20px);background:rgba(15,20,34,0.95);border:1px solid rgba(30,42,74,0.5);border-radius:12px;padding:12px 24px;color:#e8eaf0;font-size:14px;z-index:2000;opacity:0;transition:all 0.3s;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.toast.success{border-color:rgba(34,197,94,0.3)}
.toast.error{border-color:rgba(239,68,68,0.3)}

/* Lock overlay */
.lock-overlay{position:absolute;inset:0;background:rgba(10,14,23,0.78);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:14px;z-index:5;cursor:pointer;transition:opacity 0.3s}
.lock-overlay:hover{background:rgba(10,14,23,0.72)}
.lock-overlay .lock-icon{font-size:2rem;margin-bottom:8px}
.lock-overlay .lock-text{color:#94a3b8;font-size:0.85rem;margin-bottom:12px;text-align:center;line-height:1.5}
.lock-overlay .unlock-btn{background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff;border:none;padding:8px 22px;border-radius:20px;font-weight:600;font-size:13px;cursor:pointer;transition:all 0.2s;box-shadow:0 4px 16px rgba(245,158,11,0.3)}
.lock-overlay .unlock-btn:hover{transform:translateY(-1px);box-shadow:0 6px 20px rgba(245,158,11,0.4)}
.lock-overlay .lock-login-hint{color:#7a8bb5;font-size:0.75rem;margin-top:8px;text-decoration:underline;cursor:pointer}
.unlocked-badge{position:absolute;top:10px;right:44px;background:rgba(16,185,129,0.15);color:#10b981;font-size:11px;font-weight:600;padding:3px 10px;border-radius:12px;z-index:6;border:1px solid rgba(16,185,129,0.2)}
.credits-display{display:inline-flex;align-items:center;gap:3px;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);border-radius:16px;padding:2px 8px;font-size:11px;font-weight:600;color:#f59e0b;margin-left:6px}
.credits-display.zero{color:#ef4444;background:rgba(239,68,68,0.1);border-color:rgba(239,68,68,0.2)}
.lockable-content{position:relative}

/* Customer Service Panel */
.cs-panel{position:fixed;top:0;right:-360px;width:340px;height:100vh;background:rgba(10,14,23,0.98);border-left:1px solid rgba(30,42,74,0.5);z-index:1500;transition:right 0.3s;overflow-y:auto}
.cs-panel.open{right:0}
.cs-panel-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid rgba(30,42,74,0.4)}
.cs-panel-header h3{font-size:16px;color:#e8eaf0;margin:0}
.cs-panel-body{padding:20px}
.cs-panel-close{background:none;border:none;color:#4a5568;font-size:20px;cursor:pointer;width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:50%}
.cs-panel-close:hover{background:rgba(30,42,74,0.5);color:#e8eaf0}
.cs-info p{color:#94a3b8;font-size:14px;margin-bottom:16px;line-height:1.6}
.cs-item{background:rgba(30,42,74,0.3);border-radius:10px;padding:12px 16px;margin-bottom:10px;font-size:14px;color:#c8cdd8}
.cs-item strong{color:#f59e0b}
"""


def _build_navbar():
    """Build navbar HTML"""
    return """
<div class="navbar" id="navbar">
  <div class="navbar-brand">🪔 AI足势</div>
  <div class="navbar-actions" id="navActions">
    <button class="btn-nav btn-login" onclick="showLogin()">登录</button>
    <button class="btn-nav btn-register" onclick="showRegister()">注册</button>
  </div>
</div>
"""


def _build_modals():
    """Build auth modals HTML"""
    return """
<!-- Register Modal -->
<div class="modal-overlay" id="registerModal">
  <div class="auth-modal">
    <button class="close-btn" onclick="closeAllModals()">&times;</button>
    <h2>注册账号</h2>
    <p class="auth-subtitle">创建AI足势账号</p>
    <div class="auth-msg" id="regMsg"></div>
    <div class="form-group">
      <label>用户名</label>
      <input type="text" id="regUsername" placeholder="请输入用户名" maxlength="20">
    </div>
    <div class="form-group">
      <label>密码</label>
      <input type="password" id="regPassword" placeholder="请输入密码（至少6位）" maxlength="32">
    </div>
    <div class="form-group">
      <label>确认密码</label>
      <input type="password" id="regPassword2" placeholder="请再次输入密码" maxlength="32">
    </div>
    <div class="form-group">
      <label>手机号 <span style="color:#4a5568;font-weight:400">（选填，可用于登录）</span></label>
      <input type="tel" id="regPhone" placeholder="请输入手机号" maxlength="11">
    </div>
    <button class="btn-auth" id="regBtn" onclick="doRegister()">注 册</button>
    <div class="auth-switch">已有账号？<a onclick="showLogin()">立即登录</a></div>
  </div>
</div>

<!-- Login Modal -->
<div class="modal-overlay" id="loginModal">
  <div class="auth-modal">
    <button class="close-btn" onclick="closeAllModals()">&times;</button>
    <h2>登录</h2>
    <p class="auth-subtitle">欢迎回到AI足势</p>
    <div class="auth-msg" id="loginMsg"></div>
    <div class="form-group">
      <label>用户名 / 手机号</label>
      <input type="text" id="loginUsername" placeholder="请输入用户名或手机号">
    </div>
    <div class="form-group">
      <label>密码</label>
      <input type="password" id="loginPassword" placeholder="请输入密码">
    </div>
    <button class="btn-auth" id="loginBtn" onclick="doLogin()">登 录</button>
    <div class="auth-switch">没有账号？<a onclick="showRegister()">立即注册</a></div>
  </div>
</div>

<!-- Customer Service Panel -->
<div class="cs-panel" id="csPanel">
  <div class="cs-panel-header">
    <h3>📞 联系客服</h3>
    <button class="cs-panel-close" onclick="toggleCsPanel()">&times;</button>
  </div>
  <div class="cs-panel-body">
    <div class="cs-info">
      <p>积分不足？请联系客服充值</p>
      <div class="cs-item">📱 微信: <strong>ai_football_cs</strong></div>
      <div class="cs-item">📧 邮箱: <strong>support@aifushi.com</strong></div>
      <div class="cs-item">🕐 工作时间: 9:00 - 22:00</div>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>
"""


def _build_user_js():
    """Build UserDB JavaScript module and UI functions (regular string, no f-string)"""
    return r"""
<script>
// ========== UserDB Module ==========
var UserDB = (function() {
  var USERS_KEY = 'aifushi_users';
  var SESSION_KEY = 'aifushi_session';

  function hashPassword(pwd) {
    // SHA-256 + salt (mirrors import_data.py's hashlib.sha256(pwd + 'ai_football_salt'))
    return crypto.subtle.digest('SHA-256',
      new TextEncoder().encode(pwd + 'ai_football_salt')
    ).then(function(buf) {
      return Array.from(new Uint8Array(buf))
        .map(function(b) { return b.toString(16).padStart(2, '0'); }).join('');
    });
  }

  function getUsers() {
    try { return JSON.parse(localStorage.getItem(USERS_KEY)) || {}; }
    catch(e) { return {}; }
  }
  function saveUsers(u) { localStorage.setItem(USERS_KEY, JSON.stringify(u)); }

  function register(username, password, phone) {
    return hashPassword(password).then(function(pwdHash) {
      var users = getUsers();
      if (users[username]) return { ok: false, msg: '用户名已存在' };
      if (phone) {
        for (var u in users) { if (users[u].phone === phone) return { ok: false, msg: '该手机号已注册' }; }
      }
      users[username] = {
        pwd_hash: pwdHash,
        phone: phone || '',
        createdAt: new Date().toISOString(),
        credits: 0,
        unlocked: []
      };
      saveUsers(users);
      localStorage.setItem(SESSION_KEY, JSON.stringify({ username: username, loginAt: new Date().toISOString() }));
      return { ok: true };
    });
  }

  function login(usernameOrPhone, password) {
    return hashPassword(password).then(function(pwdHash) {
      var users = getUsers();
      var found = null;
      if (users[usernameOrPhone]) {
        found = usernameOrPhone;
      } else {
        for (var u in users) {
          if (users[u].phone === usernameOrPhone) { found = u; break; }
        }
      }
      if (!found) return { ok: false, msg: '用户不存在' };
      if (users[found].pwd_hash !== pwdHash) return { ok: false, msg: '密码错误' };
      localStorage.setItem(SESSION_KEY, JSON.stringify({ username: found, loginAt: new Date().toISOString() }));
      return { ok: true, username: found };
    });
  }

  function logout() { localStorage.removeItem(SESSION_KEY); }

  function getSession() {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY)); }
    catch(e) { return null; }
  }

  function getUserData() {
    var s = getSession();
    if (!s) return null;
    var users = getUsers();
    return users[s.username] || null;
  }

  function getCredits() {
    var d = getUserData();
    if (!d) return 0;
    return d.credits || 0;
  }

  function isUnlocked(matchId) {
    var d = getUserData();
    if (!d || !d.unlocked) return false;
    return d.unlocked.indexOf(matchId) >= 0;
  }

  function unlockMatch(matchId) {
    var s = getSession();
    if (!s) return { ok: false, msg: '请先登录' };
    var users = getUsers();
    var user = users[s.username];
    if (!user) return { ok: false, msg: '用户不存在' };
    if (!user.unlocked) user.unlocked = [];
    if (user.unlocked.indexOf(matchId) >= 0) return { ok: false, msg: '已解锁' };
    if ((user.credits || 0) < 1) return { ok: false, msg: '积分不足' };
    user.credits -= 1;
    user.unlocked.push(matchId);
    saveUsers(users);
    return { ok: true };
  }

  function addCredits(username, amount) {
    var users = getUsers();
    if (!users[username]) return false;
    users[username].credits = (users[username].credits || 0) + amount;
    saveUsers(users);
    return true;
  }

  return {
    hashPassword: hashPassword, register: register, login: login, logout: logout,
    getSession: getSession, getUserData: getUserData,
    getCredits: getCredits, isUnlocked: isUnlocked, unlockMatch: unlockMatch, addCredits: addCredits
  };
})();

// ========== UI Functions ==========
function showToast(msg, type) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type ? ' ' + type : '');
  setTimeout(function() { t.className = 'toast'; }, 2500);
}

function showRegister() {
  closeAllModals();
  document.getElementById('registerModal').classList.add('open');
  document.getElementById('regUsername').focus();
}
function showLogin() {
  closeAllModals();
  document.getElementById('loginModal').classList.add('open');
  document.getElementById('loginUsername').focus();
}
function closeAllModals() {
  document.querySelectorAll('.modal-overlay').forEach(function(m) { m.classList.remove('open'); });
}

function doRegister() {
  var username = document.getElementById('regUsername').value.trim();
  var password = document.getElementById('regPassword').value;
  var password2 = document.getElementById('regPassword2').value;
  var phone = document.getElementById('regPhone').value.trim();
  var msgEl = document.getElementById('regMsg');
  var btn = document.getElementById('regBtn');

  if (!username || username.length < 2) { msgEl.className='auth-msg error'; msgEl.textContent='用户名至少2个字符'; return; }
  if (!password || password.length < 6) { msgEl.className='auth-msg error'; msgEl.textContent='密码至少6位'; return; }
  if (password !== password2) { msgEl.className='auth-msg error'; msgEl.textContent='两次密码不一致'; return; }
  if (phone && !/^1\d{10}$/.test(phone)) { msgEl.className='auth-msg error'; msgEl.textContent='手机号格式不正确'; return; }

  btn.disabled = true; btn.textContent = '注册中...';
  UserDB.register(username, password, phone).then(function(res) {
    btn.disabled = false; btn.textContent = '注 册';
    if (res.ok) {
      msgEl.className = 'auth-msg success'; msgEl.textContent = '注册成功！';
      setTimeout(function() { closeAllModals(); updateNavbar(); showToast('注册成功，欢迎！', 'success'); }, 800);
    } else {
      msgEl.className = 'auth-msg error'; msgEl.textContent = res.msg;
    }
  });
}

function doLogin() {
  var username = document.getElementById('loginUsername').value.trim();
  var password = document.getElementById('loginPassword').value;
  var msgEl = document.getElementById('loginMsg');
  var btn = document.getElementById('loginBtn');

  if (!username) { msgEl.className='auth-msg error'; msgEl.textContent='请输入用户名或手机号'; return; }
  if (!password) { msgEl.className='auth-msg error'; msgEl.textContent='请输入密码'; return; }

  btn.disabled = true; btn.textContent = '登录中...';
  UserDB.login(username, password).then(function(res) {
    btn.disabled = false; btn.textContent = '登 录';
    if (res.ok) {
      closeAllModals();
      updateNavbar();
      renderCardsWithFavs();
      showToast('登录成功！', 'success');
    } else {
      msgEl.className = 'auth-msg error'; msgEl.textContent = res.msg;
    }
  });
}

function doLogout() {
  UserDB.logout();
  updateNavbar();
  renderCardsWithFavs();
  showToast('已退出登录', 'success');
}

function updateNavbar() {
  var actions = document.getElementById('navActions');
  var session = UserDB.getSession();
  if (session) {
    var userData = UserDB.getUserData();
    var initial = session.username.charAt(0).toUpperCase();
    var credits = UserDB.getCredits();
    var creditsClass = credits > 0 ? 'credits-display' : 'credits-display zero';
    var loginTime = new Date(session.loginAt).toLocaleString('zh-CN');
    var csItem = credits < 1 ? '<div class="user-dropdown-item" onclick="event.stopPropagation();toggleCsPanel();var dd=document.getElementById(\'userDropdown\');if(dd)dd.classList.remove(\'open\')"><span>📞 联系客服充值积分</span></div><div class="user-dropdown-divider"></div>' : '';
    actions.innerHTML = '<div class="user-avatar" onclick="toggleUserPanel()" id="userAvatarBtn">' + initial +
      '<span class="' + creditsClass + '">💰 ' + credits + '</span>' +
      '<div class="user-dropdown" id="userDropdown">' +
      '<div class="user-dropdown-header"><div class="user-dropdown-avatar">' + initial + '</div>' +
      '<div class="user-dropdown-info"><div class="user-dropdown-name">' + session.username + '</div>' +
      '<div class="user-dropdown-time">登录于 ' + loginTime + '</div></div></div>' +
      '<div class="user-dropdown-item" style="cursor:default"><span>💰</span>积分余额: ' + credits + '</div>' +
      csItem +
      '<div class="user-dropdown-item" onclick="event.stopPropagation();doLogout()"><span>🚪 退出登录</span></div>' +
      '</div></div>';
  } else {
    actions.innerHTML = '<button class="btn-nav btn-login" onclick="showLogin()">登录</button>' +
      '<button class="btn-nav btn-register" onclick="showRegister()">注册</button>';
  }
}

function toggleUserPanel() {
  var dd = document.getElementById('userDropdown');
  if (dd) dd.classList.toggle('open');
}

function unlockMatch(matchId) {
  if (!UserDB.getSession()) {
    showToast('请先登录后再解锁', 'error');
    showLogin();
    return;
  }
  if (UserDB.isUnlocked(matchId)) {
    showToast('该比赛已解锁', 'info');
    return;
  }
  var credits = UserDB.getCredits();
  if (credits < 1) {
    showToast('积分不足，请联系官方客服充值', 'error');
    return;
  }
  var result = UserDB.unlockMatch(matchId);
  if (result.ok) {
    showToast('🔓 解锁成功！积分-1', 'success');
    updateNavbar();
    renderCardsWithFavs();
  } else {
    showToast(result.msg || '解锁失败', 'error');
  }
}

function isMatchFree(matchId) {
  var cards = document.querySelectorAll('.match-card');
  if (cards.length > 0 && cards[0].getAttribute('data-match-id') === matchId) return true;
  return false;
}

function toggleCsPanel() {
  var panel = document.getElementById('csPanel');
  if (panel) panel.classList.toggle('open');
}

function renderCardsWithFavs() {
  var cards = document.querySelectorAll('.match-card');
  var isLoggedIn = !!UserDB.getSession();
  cards.forEach(function(card) {
    var mid = card.getAttribute('data-match-id');

    // Lock overlay logic
    var lockable = card.querySelector('.lockable-content');
    if (!lockable) return;
    var existingOverlay = card.querySelector('.lock-overlay');
    var existingBadge = card.querySelector('.unlocked-badge');
    if (existingBadge) existingBadge.remove();

        var free = isMatchFree(mid);
    if (free) {
      // Free match: no lock
      lockable.style.filter = '';
      lockable.style.pointerEvents = '';
      if (existingOverlay) existingOverlay.remove();
      return;
    }

var unlocked = isLoggedIn && UserDB.isUnlocked(mid);
    if (unlocked) {
      // Unlocked: show content, show badge
      lockable.style.filter = '';
      lockable.style.pointerEvents = '';
      if (existingOverlay) existingOverlay.remove();
      var ub = document.createElement('div');
      ub.className = 'unlocked-badge';
      ub.textContent = '✅ 已解锁';
      card.appendChild(ub);
      return;
    }

    // Locked: blur content, show overlay
    lockable.style.filter = 'blur(8px)';
    lockable.style.pointerEvents = 'none';
    if (!existingOverlay) {
      var overlay = document.createElement('div');
      overlay.className = 'lock-overlay';
      if (isLoggedIn) {
        var credits = UserDB.getCredits();
        overlay.innerHTML = '<div class="lock-icon">🔒</div>' +
          '<div class="lock-text">付费分析内容<br>解锁需消耗1积分</div>' +
          '<button class="unlock-btn" onclick="event.stopPropagation();unlockMatch(\'' + mid + '\')">🔓 解锁 (剩余' + credits + '积分)</button>';
      } else {
        overlay.innerHTML = '<div class="lock-icon">🔒</div>' +
          '<div class="lock-text">付费分析内容<br>登录后查看</div>' +
          '<div class="lock-login-hint" onclick="event.stopPropagation();showLogin()">点击登录</div>';
      }
      card.appendChild(overlay);
    } else {
      // Update existing overlay (credits may have changed)
      if (isLoggedIn) {
        var credits = UserDB.getCredits();
        existingOverlay.innerHTML = '<div class="lock-icon">🔒</div>' +
          '<div class="lock-text">付费分析内容<br>解锁需消耗1积分</div>' +
          '<button class="unlock-btn" onclick="event.stopPropagation();unlockMatch(\'' + mid + '\')">🔓 解锁 (剩余' + credits + '积分)</button>';
      }
    }
  });
}

// ========== Init ==========
document.addEventListener('DOMContentLoaded', function() {
  updateNavbar();
  renderCardsWithFavs();
});

// ESC to close modals
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeAllModals();
    var dd = document.getElementById('userDropdown');
    if (dd) dd.classList.remove('open');
    var cp = document.getElementById('csPanel');
    if (cp) cp.classList.remove('open');
  }
});

// Enter to submit forms
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    if (document.getElementById('registerModal').classList.contains('open')) doRegister();
    if (document.getElementById('loginModal').classList.contains('open')) doLogin();
  }
});

// Click outside modal to close
document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay) closeAllModals();
  });
});

// Click outside dropdown to close
document.addEventListener('click', function(e) {
  var avatar = document.getElementById('userAvatarBtn');
  var dd = document.getElementById('userDropdown');
  if (dd && avatar && !avatar.contains(e.target)) dd.classList.remove('open');
});
</script>
"""


def generate_html(all_days):
    """生成完整HTML"""
    today = all_days[0]
    today_str = today["date"]
    today_date = datetime.strptime(today_str, "%Y%m%d").strftime("%Y年%m月%d日")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 生成今日预测卡片（每场两行）
    match_cards = []
    valid_matches = [m for m in today["matches"] if "lambda_home" in m and "lambda_away" in m]
    for i, m in enumerate(valid_matches):
        lh = m["lambda_home"]
        la = m["lambda_away"]
        total = lh + la
        pred25 = m["v3_pred_25"]
        conf25 = m["v3_conf_25"]

        # 判断悬殊：|λ主 - λ客| ≥ 0.5
        is_mismatch = abs(lh - la) >= 0.5

        # 2.5球推荐：偏差≥0.5才推荐，否则不建议
        deviation = total - 2.5
        if abs(deviation) >= 0.5:
            if pred25 == "大球":
                cls25 = "over"
                icon25 = "🔴"
                txt25 = "大球"
            else:
                cls25 = "under"
                icon25 = "🟢"
                txt25 = "小球"
            conf_txt = f"{conf25:.0f}%"
        else:
            cls25 = "none"
            icon25 = ""
            txt25 = "不建议"
            conf_txt = "-"

        if is_mismatch:
            stronger = m["home_team"] if lh > la else m["away_team"]
            mismatch_tag = f'<span class="mismatch-tag">💪{stronger}</span>'
        else:
            mismatch_tag = ""

        match_time = m["match_time"].split(" ")[1] if " " in m["match_time"] else m["match_time"]
        match_id = m.get('match_id', str(i))
        teams_str = f"{m['home_team']} vs {m['away_team']}"

        card = f"""<div class="match-card{' mismatch-border' if is_mismatch else ''}" data-match-id="{match_id}" data-league="{m['league_cn']}" data-teams="{teams_str}" data-time="{match_time}">
  <div class="card-top">
    <span class="c-match-id">{match_id}</span>
    <span class="c-league">{m['league_cn']}</span>
    <span class="c-time">⏰ {match_time}</span>
    <span class="c-teams">{m['home_team']} <span class="c-vs">vs</span> {m['away_team']}</span>
  </div>
  <div class="lockable-content" style="position:relative">
  <div class="card-bottom">
    <span class="c-pred pred-{cls25}">{(icon25 + ' ') if icon25 else ''}{txt25}</span>
    <div class="c-stats-row">
      <div class="c-stat"><span class="c-label">主队预计</span><span class="c-val">{lh:.2f}球</span></div>
      <div class="c-stat"><span class="c-label">客队预计</span><span class="c-val">{la:.2f}球</span></div>
      <div class="c-stat"><span class="c-label">总进球</span><span class="c-val c-total">{total:.2f}球</span></div>
    </div>
    <span class="c-winner">{mismatch_tag}</span>
  </div>
  </div>
</div>"""
        match_cards.append(card)

    cards_html = "\n".join(match_cards)

    # 今日比赛数（仅统计有效预测）
    total_matches = len(valid_matches)

    # Build extra CSS, navbar, modals, JS as regular strings (no f-string brace issues)
    extra_css = _build_extra_css()
    navbar_html = _build_navbar()
    modals_html = _build_modals()
    user_js = _build_user_js()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI足势 — 智能足球预测</title>
<meta name="description" content="AI足势 - 基于V3泊松模型的专业足球大小球预测，每日自动更新">
<meta name="theme-color" content="#0a0e17">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www/svg/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚽</text></svg>">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;background:linear-gradient(135deg,#0a0e17 0%,#1a1f2e 100%);color:#e8eaf0;min-height:100vh;overflow-x:hidden}}
a{{color:#10b981;text-decoration:none}}

/* Header */
.header{{background:rgba(10,14,23,0.95);backdrop-filter:blur(10px);border-bottom:1px solid rgba(30,42,74,0.5);padding:20px;text-align:center;position:sticky;top:0;z-index:100}}
.header h1{{font-size:28px;background:linear-gradient(135deg,#10b981,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:6px}}
.header .subtitle{{color:#7a8bb5;font-size:14px}}
.header .update-time{{color:#4a5568;font-size:12px;margin-top:4px}}

/* Container */
.container{{max-width:900px;margin:0 auto;padding:20px}}

/* Section title */
.section-title{{font-size:20px;font-weight:700;margin-bottom:16px;padding-left:12px;border-left:3px solid #10b981}}

/* Today section */
.today-section{{margin-bottom:30px}}
.today-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding:0 12px}}
.today-date{{font-size:20px;font-weight:600}}
.today-badge{{background:linear-gradient(135deg,#10b981,#3b82f6);color:#fff;padding:6px 16px;border-radius:20px;font-size:14px;font-weight:600}}

/* Match Cards — 上下两行布局 */
.match-card{{background:rgba(20,25,41,0.7);border:1px solid rgba(30,42,74,0.5);border-radius:14px;margin-bottom:14px;overflow:hidden;transition:border-color 0.2s;position:relative}}
.match-card:hover{{border-color:rgba(59,130,246,0.4)}}
.mismatch-border{{border-left:4px solid #f59e0b}}

/* 上行：比赛信息 */
.card-top{{display:flex;align-items:center;padding:14px 16px;gap:14px;border-bottom:1px solid rgba(30,42,74,0.4)}}
.c-match-id{{color:#7a8bb5;font-size:14px;white-space:nowrap;min-width:70px}}
.c-league{{color:#a5b4fc;font-size:15px;font-weight:600;white-space:nowrap}}
.c-time{{color:#e8eaf0;font-size:16px;font-weight:700;white-space:nowrap}}
.c-teams{{flex:1;font-size:18px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.c-vs{{color:#4a5568;font-size:13px;margin:0 6px}}

/* 下行：预测数据 */
.card-bottom{{display:flex;align-items:center;padding:12px 16px;gap:16px;background:rgba(10,14,23,0.3)}}
.c-pred{{font-size:20px;font-weight:700;white-space:nowrap;min-width:90px}}
.c-stats-row{{display:flex;gap:16px;flex:1;justify-content:center}}
.c-stat{{display:flex;flex-direction:column;align-items:center;min-width:70px}}
.c-label{{color:#7a8bb5;font-size:11px;margin-bottom:2px}}
.c-val{{color:#a5b4fc;font-size:16px;font-weight:600;font-family:'SF Mono',monospace}}
.c-total{{color:#f59e0b;font-weight:700}}
.c-winner{{margin-left:auto}}

/* 2.5球颜色 */
.pred-over{{color:#ef4444}}
.pred-under{{color:#10b981}}
.pred-none{{color:#4a5568;font-size:15px!important}}

/* 悬殊标签 */
.mismatch-tag{{background:rgba(245,158,11,0.2);color:#f59e0b;padding:4px 12px;border-radius:12px;font-size:14px;white-space:nowrap}}

/* Model info */
.model-section{{margin-bottom:30px}}
.model-card{{background:rgba(30,42,74,0.3);border:1px solid rgba(30,42,74,0.5);border-radius:16px;padding:24px}}
.model-card h3{{font-size:16px;margin-bottom:12px;color:#10b981}}
.model-card p{{color:#7a8bb5;font-size:14px;line-height:1.8;margin-bottom:8px}}
.model-card .params{{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}}
.model-card .param{{background:rgba(10,14,23,0.5);border-radius:8px;padding:8px 14px;font-size:13px}}
.model-card .param strong{{color:#a5b4fc}}

/* Footer */
.footer{{text-align:center;padding:30px 20px;border-top:1px solid rgba(30,42,74,0.3);margin-top:20px}}
.footer p{{color:#4a5568;font-size:13px;line-height:1.8}}
.footer .disclaimer{{color:#ef4444;font-size:12px;margin-top:8px}}

{extra_css}

/* Responsive */
@media(max-width:768px){{
  .navbar{{padding:0 12px;height:50px}}
  .navbar-brand{{font-size:17px}}
  .btn-nav{{padding:6px 12px;font-size:12px}}
  .header h1{{font-size:22px}}
  .container{{padding:12px}}
  .card-top,.card-bottom{{padding:10px 12px;gap:8px;flex-wrap:wrap}}
  .c-teams{{font-size:16px;width:100%}}
  .c-time{{font-size:14px}}
  .c-val{{font-size:14px}}
  .c-pred{{font-size:18px}}
  .c-stat{{min-width:60px}}
  .auth-modal{{margin:16px;padding:28px 20px}}
}}
</style>
</head>
<body>

{navbar_html}

<div class="header">
  <h1>⚽ AI足势</h1>
  <div class="subtitle">基于V3泊松模型 · 37万+场历史数据 · 每日自动更新</div>
  <div class="update-time">最后更新：{update_time}</div>
</div>

<div class="container">

  <div class="today-section">
    <div class="today-header">
      <div class="today-date">📅 {today_date} 预测</div>
      <div class="today-badge">今日 {total_matches} 场</div>
    </div>
    <div class="cards-wrap">
{cards_html}
    </div>
    <p style="color:#7a8bb5;font-size:12px;margin-top:12px;padding-left:12px">📏 推荐规则：总进球偏离2.5盘≥0.5球才推荐（🔴大球/🟢小球），偏离&lt;0.5球显示"不建议"</p>
  </div>

  <div class="model-section">
    <div class="section-title">🧠 模型说明</div>
    <div class="model-card">
      <h3>V3 Dixon-Coles 泊松预测模型</h3>
      <p>本系统采用改进的Dixon-Coles泊松分布模型，基于超过37万场历史比赛数据进行预测。模型综合考虑球队近期状态、联赛攻防水平和主场优势等因素。</p>
      <p>核心方法：通过贝叶斯收缩估计球队攻防参数，结合泊松分布计算各比分概率，最终得出大小球推荐。</p>
      <div class="params">
        <div class="param"><strong>HA = 1.10</strong> 主场优势系数</div>
        <div class="param"><strong>K = 5.0</strong> 贝叶斯收缩强度</div>
        <div class="param"><strong>窗口 = 200天</strong> 联赛均值计算</div>
        <div class="param"><strong>近N=10场</strong> 球队近期状态</div>
      </div>
    </div>
  </div>

</div>

<div class="footer">
  <p>AI足势 — 智能足球预测分析平台</p>
  <p>数据来源：372,902场历史比赛 · 覆盖国际/欧洲/各大联赛</p>
  <p>每日北京时间 11:00 自动更新</p>
  <p class="disclaimer">⚠️ 数据仅供参考，不构成任何投注建议。请理性看待预测结果。</p>
</div>

{modals_html}

{user_js}

</body>
</html>"""
    return html


def main():
    print("🔍 扫描预测数据...")
    all_days = find_latest_predictions()

    if not all_days:
        print("❌ 未找到预测数据文件")
        return False

    print(f"📊 找到 {len(all_days)} 天数据")
    for d in all_days:
        valid = sum(1 for m in d["matches"] if "lambda_home" in m)
        total = len(d["matches"])
        note = f" (含{total - valid}场异常)" if total > valid else ""
        print(f"   {d['date']}: {valid} 场{note}")

    # 生成HTML
    print("🔨 生成网站...")
    html = generate_html(all_days)

    # 输出
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(output_file) / 1024
    print(f"✅ 网站已生成: {output_file}")
    print(f"   文件大小: {size_kb:.1f} KB")

    # 同时输出data.json供未来扩展
    data_file = OUTPUT_DIR / "data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(all_days, f, ensure_ascii=False, indent=2)
    print(f"📦 数据文件: {data_file}")

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

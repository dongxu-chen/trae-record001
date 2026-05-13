import json, strutils, hashes, os, locks

type
  AdminUser* = object
    username*: string
    passwordHash*: string
  
  AdminStore* = object
    users*: Table[string, AdminUser]
    sessions*: Table[string, string]
    filePath*: string
    lock*: Lock

proc hashPassword*(password: string): string =
  result = $hash(password & "jokes_api_salt_2026")

proc newAdminStore*(filePath: string): AdminStore =
  result = AdminStore(
    users: initTable[string, AdminUser](),
    sessions: initTable[string, string](),
    filePath: filePath,
    lock: initLock(result.lock)
  )
  if fileExists(filePath):
    result.loadFromFile()
  else:
    result.addDefaultAdmin()

proc saveToFile*(store: var AdminStore) =
  withLock store.lock:
    var usersArray = newJArray()
    for username, user in store.users:
      usersArray.add(%*{
        "username": username,
        "passwordHash": user.passwordHash
      })
    
    let jsonContent = %*{"users": usersArray}
    writeFile(store.filePath, $jsonContent)

proc loadFromFile*(store: var AdminStore) =
  withLock store.lock:
    if not fileExists(store.filePath):
      return
    
    let content = readFile(store.filePath)
    let jsonData = parseJson(content)
    let usersArray = jsonData["users"]
    
    for userNode in usersArray:
      let user = AdminUser(
        username: userNode["username"].getStr(),
        passwordHash: userNode["passwordHash"].getStr()
      )
      store.users[user.username] = user

proc addDefaultAdmin*(store: var AdminStore) =
  withLock store.lock:
    if not store.users.hasKey("admin"):
      let defaultAdmin = AdminUser(
        username: "admin",
        passwordHash: hashPassword("admin123")
      )
      store.users["admin"] = defaultAdmin
      store.saveToFile()

proc authenticate*(store: var AdminStore, username, password: string): bool =
  withLock store.lock:
    if not store.users.hasKey(username):
      return false
    
    let storedHash = store.users[username].passwordHash
    let inputHash = hashPassword(password)
    return storedHash == inputHash

proc createSession*(store: var AdminStore, username: string): string =
  withLock store.lock:
    let sessionId = $hash(username & $getTime() & "session_salt")
    store.sessions[sessionId] = username
    return sessionId

proc validateSession*(store: AdminStore, sessionId: string): Option[string] =
  withLock store.lock:
    if store.sessions.hasKey(sessionId):
      return some(store.sessions[sessionId])
    return none(string)

proc destroySession*(store: var AdminStore, sessionId: string) =
  withLock store.lock:
    if store.sessions.hasKey(sessionId):
      store.sessions.del(sessionId)

proc addUser*(store: var AdminStore, username, password: string): bool =
  withLock store.lock:
    if store.users.hasKey(username):
      return false
    
    let newUser = AdminUser(
      username: username,
      passwordHash: hashPassword(password)
    )
    store.users[username] = newUser
    store.saveToFile()
    return true

proc changePassword*(store: var AdminStore, username, oldPassword, newPassword: string): bool =
  withLock store.lock:
    if not store.users.hasKey(username):
      return false
    
    let oldHash = hashPassword(oldPassword)
    if store.users[username].passwordHash != oldHash:
      return false
    
    store.users[username].passwordHash = hashPassword(newPassword)
    store.saveToFile()
    return true

proc generateAdminHtml*(): string =
  result = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>笑话管理后台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #333; margin-bottom: 10px; }
        .nav { display: flex; gap: 10px; }
        .nav button { padding: 10px 20px; border: none; background: #4CAF50; color: white; border-radius: 4px; cursor: pointer; }
        .nav button:hover { background: #45a049; }
        .nav button.active { background: #2E7D32; }
        .card { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card h2 { color: #333; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #4CAF50; }
        .submission { border: 1px solid #e0e0e0; padding: 15px; border-radius: 4px; margin-bottom: 15px; }
        .submission-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .submission-meta { color: #666; font-size: 14px; }
        .submission-category { background: #e3f2fd; color: #1976d2; padding: 4px 8px; border-radius: 12px; font-size: 12px; }
        .submission-content { margin: 10px 0; line-height: 1.6; }
        .submission-actions { display: flex; gap: 10px; margin-top: 15px; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn-approve { background: #4CAF50; color: white; }
        .btn-approve:hover { background: #45a049; }
        .btn-reject { background: #f44336; color: white; }
        .btn-reject:hover { background: #d32f2f; }
        .joke-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #eee; }
        .joke-item:last-child { border-bottom: none; }
        .vote-score { font-size: 24px; font-weight: bold; color: #4CAF50; min-width: 60px; text-align: center; }
        .login-form { max-width: 400px; margin: 100px auto; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #333; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn-login { width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        .btn-login:hover { background: #45a049; }
        .hidden { display: none !important; }
        .error { color: #f44336; margin-bottom: 10px; }
        .empty-state { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div id="loginSection" class="card login-form">
            <h2>管理员登录</h2>
            <div id="loginError" class="error hidden"></div>
            <div class="form-group">
                <label>用户名</label>
                <input type="text" id="username" placeholder="请输入用户名">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="password" placeholder="请输入密码">
            </div>
            <button class="btn-login" onclick="login()">登录</button>
            <p style="margin-top: 15px; font-size: 12px; color: #666;">默认账号: admin / admin123</p>
        </div>
        
        <div id="adminSection" class="hidden">
            <div class="header">
                <h1>笑话管理后台</h1>
                <div class="nav">
                    <button class="active" onclick="showTab('pending')">待审核</button>
                    <button onclick="showTab('top')">热门排行</button>
                    <button onclick="showTab('approved')">已通过</button>
                    <button onclick="logout()" style="margin-left: auto; background: #f44336;">退出</button>
                </div>
            </div>
            
            <div id="pendingTab" class="card">
                <h2>待审核笑话</h2>
                <div id="pendingList"></div>
            </div>
            
            <div id="topTab" class="card hidden">
                <h2>热门笑话排行</h2>
                <div id="topList"></div>
            </div>
            
            <div id="approvedTab" class="card hidden">
                <h2>已通过审核</h2>
                <div id="approvedList"></div>
            </div>
        </div>
    </div>

    <script>
        let sessionId = localStorage.getItem('adminSession');
        
        function showTab(tabName) {
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.card').forEach(c => c.classList.add('hidden'));
            
            event.target.classList.add('active');
            document.getElementById(tabName + 'Tab').classList.remove('hidden');
            
            if (tabName === 'pending') loadPending();
            else if (tabName === 'top') loadTop();
            else if (tabName === 'approved') loadApproved();
        }
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/admin/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    sessionId = data.sessionId;
                    localStorage.setItem('adminSession', sessionId);
                    document.getElementById('loginSection').classList.add('hidden');
                    document.getElementById('adminSection').classList.remove('hidden');
                    loadPending();
                } else {
                    document.getElementById('loginError').textContent = data.message || '登录失败';
                    document.getElementById('loginError').classList.remove('hidden');
                }
            } catch (e) {
                document.getElementById('loginError').textContent = '网络错误';
                document.getElementById('loginError').classList.remove('hidden');
            }
        }
        
        async function logout() {
            if (sessionId) {
                await fetch('/admin/logout', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + sessionId }
                });
            }
            localStorage.removeItem('adminSession');
            sessionId = null;
            document.getElementById('adminSection').classList.add('hidden');
            document.getElementById('loginSection').classList.remove('hidden');
        }
        
        async function loadPending() {
            const response = await fetch('/admin/submissions/pending', {
                headers: { 'Authorization': 'Bearer ' + sessionId }
            });
            
            if (response.status === 401) {
                logout();
                return;
            }
            
            const data = await response.json();
            const list = document.getElementById('pendingList');
            
            if (data.submissions.length === 0) {
                list.innerHTML = '<div class="empty-state">暂无待审核的笑话</div>';
                return;
            }
            
            list.innerHTML = data.submissions.map(sub => `
                <div class="submission" id="sub-${sub.id}">
                    <div class="submission-header">
                        <span class="submission-category">${escapeHtml(sub.category)}</span>
                        <span class="submission-meta">提交者: ${escapeHtml(sub.submittedBy)} | ${sub.submittedAt}</span>
                    </div>
                    <div class="submission-content">
                        <strong>问题:</strong> ${escapeHtml(sub.question)}<br>
                        <strong>答案:</strong> ${escapeHtml(sub.answer)}
                    </div>
                    <div class="submission-actions">
                        <button class="btn btn-approve" onclick="approve(${sub.id})">通过</button>
                        <button class="btn btn-reject" onclick="reject(${sub.id})">拒绝</button>
                    </div>
                </div>
            `).join('');
        }
        
        async function loadTop() {
            const response = await fetch('/admin/jokes/top', {
                headers: { 'Authorization': 'Bearer ' + sessionId }
            });
            
            if (response.status === 401) {
                logout();
                return;
            }
            
            const data = await response.json();
            const list = document.getElementById('topList');
            
            if (data.jokes.length === 0) {
                list.innerHTML = '<div class="empty-state">暂无投票数据</div>';
                return;
            }
            
            list.innerHTML = data.jokes.map((joke, index) => `
                <div class="joke-item">
                    <span style="font-weight: bold; min-width: 30px;">#${index + 1}</span>
                    <div style="flex: 1; margin: 0 20px;">
                        <strong>${escapeHtml(joke.question)}</strong><br>
                        <span style="color: #666;">${escapeHtml(joke.answer)}</span>
                    </div>
                    <span class="vote-score">${joke.votes > 0 ? '+' : ''}${joke.votes}</span>
                </div>
            `).join('');
        }
        
        async function loadApproved() {
            const response = await fetch('/admin/submissions/approved', {
                headers: { 'Authorization': 'Bearer ' + sessionId }
            });
            
            if (response.status === 401) {
                logout();
                return;
            }
            
            const data = await response.json();
            const list = document.getElementById('approvedList');
            
            if (data.submissions.length === 0) {
                list.innerHTML = '<div class="empty-state">暂无已通过的提交</div>';
                return;
            }
            
            list.innerHTML = data.submissions.map(sub => `
                <div class="submission">
                    <div class="submission-header">
                        <span class="submission-category">${escapeHtml(sub.category)}</span>
                        <span class="submission-meta">审核通过: ${sub.reviewedAt || '-'}</span>
                    </div>
                    <div class="submission-content">
                        <strong>问题:</strong> ${escapeHtml(sub.question)}<br>
                        <strong>答案:</strong> ${escapeHtml(sub.answer)}
                    </div>
                </div>
            `).join('');
        }
        
        async function approve(id) {
            const response = await fetch(`/admin/submissions/${id}/approve`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + sessionId 
                }
            });
            
            if (response.status === 401) {
                logout();
                return;
            }
            
            if (response.ok) {
                document.getElementById('sub-' + id).style.display = 'none';
            }
        }
        
        async function reject(id) {
            const response = await fetch(`/admin/submissions/${id}/reject`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + sessionId 
                }
            });
            
            if (response.status === 401) {
                logout();
                return;
            }
            
            if (response.ok) {
                document.getElementById('sub-' + id).style.display = 'none';
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        if (sessionId) {
            document.getElementById('loginSection').classList.add('hidden');
            document.getElementById('adminSection').classList.remove('hidden');
            loadPending();
        }
    </script>
</body>
</html>
"""
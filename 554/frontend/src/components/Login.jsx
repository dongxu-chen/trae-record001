import React, { useState } from 'react'
import axios from 'axios'

function Login({ onLogin, showToast }) {
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username || !password) {
      showToast('请填写用户名和密码', 'error')
      return
    }

    setLoading(true)
    try {
      const url = isRegister ? '/api/user/register' : '/api/user/login'
      const data = isRegister 
        ? { username, password, nickname: nickname || username }
        : { username, password }
      
      const res = await axios.post(url, data)
      
      if (res.data.code === 200) {
        showToast(isRegister ? '注册成功' : '登录成功', 'success')
        if (!isRegister) {
          onLogin(res.data.data)
        } else {
          setIsRegister(false)
        }
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast(err.response?.data?.message || '操作失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h2>{isRegister ? '注册账号' : '用户签到系统'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
            />
          </div>
          {isRegister && (
            <div className="form-group">
              <label>昵称</label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="请输入昵称"
              />
            </div>
          )}
          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
            />
          </div>
          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? '处理中...' : (isRegister ? '注册' : '登录')}
          </button>
        </form>
        <div className="login-switch">
          {isRegister ? (
            <>已有账号？<button onClick={() => setIsRegister(false)}>去登录</button></>
          ) : (
            <>没有账号？<button onClick={() => setIsRegister(true)}>去注册</button></>
          )}
        </div>
      </div>
    </div>
  )
}

export default Login

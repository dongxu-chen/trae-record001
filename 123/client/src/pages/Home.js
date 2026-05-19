import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Home() {
  const [role, setRole] = useState(null);
  const [examId, setExamId] = useState('');
  const [userId, setUserId] = useState('');
  const [name, setName] = useState('');
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (role === 'examinee') {
      navigate('/examinee', { state: { examId, userId, name } });
    } else {
      navigate('/proctor', { state: { examId, userId, name } });
    }
  };

  if (!role) {
    return (
      <div className="home-container">
        <h1 className="home-title">在线考试防作弊系统</h1>
        <div className="role-buttons">
          <button 
            className="role-button examinee-btn"
            onClick={() => setRole('examinee')}
          >
            我是考生
          </button>
          <button 
            className="role-button proctor-btn"
            onClick={() => setRole('proctor')}
          >
            我是监考
          </button>
        </div>
        <div style={{ marginTop: '30px' }}>
          <button 
            className="role-button"
            onClick={() => navigate('/recordings')}
            style={{ 
              backgroundColor: '#6c757d',
              width: '300px'
            }}
          >
            录制管理
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="home-container">
      <h1 className="home-title">
        {role === 'examinee' ? '考生登录' : '监考登录'}
      </h1>
      <form className="login-form" onSubmit={handleSubmit}>
        <div className="form-group">
          <label>考试ID</label>
          <input 
            type="text" 
            value={examId}
            onChange={(e) => setExamId(e.target.value)}
            required
            placeholder="请输入考试ID"
          />
        </div>
        <div className="form-group">
          <label>用户ID</label>
          <input 
            type="text" 
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
            placeholder="请输入用户ID"
          />
        </div>
        <div className="form-group">
          <label>姓名</label>
          <input 
            type="text" 
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="请输入姓名"
          />
        </div>
        <button type="submit" className="submit-btn">进入考试</button>
      </form>
    </div>
  );
}

export default Home;

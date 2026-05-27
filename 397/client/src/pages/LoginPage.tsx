import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { authAPI } from '../services/api';
import { loginSuccess } from '../store';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const response = await authAPI.login(values);
      dispatch(loginSuccess(response));
      message.success('登录成功');
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12" style={{ background: '#0F172A' }}>
      <Card className="w-full max-w-md" style={{ background: '#1E293B', borderRadius: '16px' }}>
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            <span className="bg-gradient-to-r from-blue-500 to-indigo-600 bg-clip-text text-transparent">
              Dashboard
            </span>
            <span className="text-orange-500">Market</span>
          </h1>
          <p className="text-slate-400">欢迎回来，请登录您的账户</p>
        </div>

        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="email"
            rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#94A3B8' }} />}
              placeholder="邮箱地址"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#94A3B8' }} />}
              placeholder="密码"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading} size="large">
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="text-center text-slate-400">
          还没有账户？ <Link to="/register" className="text-blue-400">立即注册</Link>
        </div>

        <div className="mt-6 pt-6 border-t border-slate-700">
          <p className="text-center text-slate-500 text-sm mb-4">演示账户</p>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="p-2 rounded-lg bg-slate-800">
              <p className="text-white">admin@example.com</p>
              <p className="text-slate-500">123456</p>
            </div>
            <div className="p-2 rounded-lg bg-slate-800">
              <p className="text-white">creator1@example.com</p>
              <p className="text-slate-500">123456</p>
            </div>
            <div className="p-2 rounded-lg bg-slate-800">
              <p className="text-white">user1@example.com</p>
              <p className="text-slate-500">123456</p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;

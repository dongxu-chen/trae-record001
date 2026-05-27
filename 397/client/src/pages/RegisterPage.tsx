import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { authAPI } from '../services/api';
import { loginSuccess } from '../store';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; email: string; password: string }) => {
    setLoading(true);
    try {
      const response = await authAPI.register(values);
      dispatch(loginSuccess(response));
      message.success('注册成功');
      navigate('/');
    } catch (error: any) {
      message.error(error.response?.data?.message || '注册失败');
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
          <p className="text-slate-400">创建新账户，开始使用模板市场</p>
        </div>

        <Form
          name="register"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }, { min: 3, message: '用户名至少3个字符' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#94A3B8' }} />}
              placeholder="用户名"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item
            name="email"
            rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input
              prefix={<MailOutlined style={{ color: '#94A3B8' }} />}
              placeholder="邮箱地址"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6个字符' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#94A3B8' }} />}
              placeholder="密码"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#94A3B8' }} />}
              placeholder="确认密码"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading} size="large">
              注册
            </Button>
          </Form.Item>
        </Form>

        <div className="text-center text-slate-400">
          已有账户？ <Link to="/login" className="text-blue-400">立即登录</Link>
        </div>
      </Card>
    </div>
  );
};

export default RegisterPage;

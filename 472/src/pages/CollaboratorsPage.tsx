import { Users, Mail, Shield, UserPlus } from 'lucide-react';
import { useState } from 'react';
import { Modal } from '../components/Modal';
import { mockUsers } from '../utils/mockData';

export const CollaboratorsPage = () => {
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');

  const roles = ['管理员', '标注员', '查看者'];

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">协作者管理</h1>
          <p className="text-slate-400">管理项目团队成员和权限</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="flex items-center gap-2 px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all hover:shadow-lg hover:shadow-blue-600/30"
        >
          <UserPlus className="w-5 h-5" />
          邀请成员
        </button>
      </div>

      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-slate-400" />
            <span className="text-white font-medium">团队成员 ({mockUsers.length})</span>
          </div>
        </div>

        <div className="divide-y divide-slate-700">
          {mockUsers.map((user, index) => (
            <div key={user.id} className="p-4 flex items-center justify-between hover:bg-slate-700/30 transition-colors">
              <div className="flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg"
                  style={{ backgroundColor: user.color }}
                >
                  {user.name.charAt(0)}
                </div>
                <div>
                  <p className="text-white font-medium">{user.name}</p>
                  <p className="text-sm text-slate-400">{user.name.toLowerCase().replace(/\s/g, '')}@example.com</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <select
                  className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  defaultValue={index === 0 ? roles[0] : roles[1]}
                >
                  {roles.map((role) => (
                    <option key={role} value={role}>{role}</option>
                  ))}
                </select>
                <button className="p-2 text-slate-400 hover:text-red-400 transition-colors">
                  <Shield className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Modal isOpen={showInviteModal} onClose={() => setShowInviteModal(false)} title="邀请协作者">
        <form onSubmit={(e) => { e.preventDefault(); setShowInviteModal(false); setInviteEmail(''); }} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">邮箱地址</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="输入邮箱地址"
                className="w-full pl-10 pr-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">角色</label>
            <select className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500">
              {roles.map((role) => (
                <option key={role} value={role}>{role}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowInviteModal(false)}
              className="flex-1 px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              发送邀请
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

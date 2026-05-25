import { useEffect, useState } from 'react'
import { Users, Plus, MoreVertical, Crown, Edit3, Eye, Mail, X, Check } from 'lucide-react'

interface TeamMember {
  id: string
  name: string
  email: string
  role: 'admin' | 'editor' | 'viewer'
  avatar?: string
  status: 'active' | 'pending'
  joinedAt: string
}

const mockMembers: TeamMember[] = [
  {
    id: '1',
    name: '管理员',
    email: 'admin@example.com',
    role: 'admin',
    status: 'active',
    joinedAt: '2024-01-01',
  },
  {
    id: '2',
    name: '设计师小王',
    email: 'designer@example.com',
    role: 'editor',
    status: 'active',
    joinedAt: '2024-02-15',
  },
  {
    id: '3',
    name: '开发者小李',
    email: 'dev@example.com',
    role: 'viewer',
    status: 'pending',
    joinedAt: '2024-03-01',
  },
]

const roleConfig = {
  admin: { label: '管理员', icon: Crown, color: 'bg-amber-100 text-amber-700' },
  editor: { label: '编辑者', icon: Edit3, color: 'bg-primary-100 text-primary-700' },
  viewer: { label: '查看者', icon: Eye, color: 'bg-gray-100 text-gray-700' },
}

export default function Team() {
  const [members, setMembers] = useState<TeamMember[]>(mockMembers)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'editor' | 'viewer'>('viewer')
  const [actionMenu, setActionMenu] = useState<string | null>(null)

  const handleInvite = () => {
    if (!inviteEmail.trim()) return

    const newMember: TeamMember = {
      id: Math.random().toString(36).slice(2),
      name: inviteEmail.split('@')[0],
      email: inviteEmail,
      role: inviteRole,
      status: 'pending',
      joinedAt: new Date().toISOString().split('T')[0],
    }

    setMembers((prev) => [...prev, newMember])
    setShowInviteModal(false)
    setInviteEmail('')
    setInviteRole('viewer')
  }

  const changeMemberRole = (memberId: string, newRole: 'admin' | 'editor' | 'viewer') => {
    setMembers((prev) =>
      prev.map((m) => (m.id === memberId ? { ...m, role: newRole } : m))
    )
    setActionMenu(null)
  }

  const removeMember = (memberId: string) => {
    if (confirm('确定要移除该成员吗？')) {
      setMembers((prev) => prev.filter((m) => m.id !== memberId))
      setActionMenu(null)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-gray-900">团队管理</h1>
          <p className="text-gray-500 mt-1">管理团队成员和访问权限</p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="btn btn-primary gap-2"
        >
          <Plus size={18} />
          邀请成员
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(roleConfig).map(([role, config]) => {
          const count = members.filter((m) => m.role === role).length
          const Icon = config.icon
          return (
            <div key={role} className="card p-5">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg ${config.color} flex items-center justify-center`}>
                  <Icon size={20} />
                </div>
                <div>
                  <p className="font-medium text-gray-900">{config.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{count}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="card">
        <div className="p-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">成员列表</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {members.map((member) => {
            const RoleIcon = roleConfig[member.role].icon
            return (
              <div key={member.id} className="p-4 flex items-center gap-4 hover:bg-gray-50">
                <div className="w-12 h-12 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-primary-600 font-semibold">
                    {member.name.charAt(0).toUpperCase()}
                  </span>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900">{member.name}</p>
                    {member.status === 'pending' && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full">
                        待接受
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500">{member.email}</p>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1.5 ${roleConfig[member.role].color}`}
                >
                  <RoleIcon size={14} />
                  {roleConfig[member.role].label}
                </span>

                <div className="relative">
                  <button
                    onClick={() => setActionMenu(actionMenu === member.id ? null : member.id)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <MoreVertical size={18} className="text-gray-500" />
                  </button>

                  {actionMenu === member.id && (
                    <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10 min-w-[140px] animate-scale-in">
                      <p className="px-3 py-1.5 text-xs text-gray-500 font-medium">更改角色</p>
                      {member.role !== 'admin' && (
                        <button
                          onClick={() => changeMemberRole(member.id, 'admin')}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Crown size={14} />
                          设为管理员
                        </button>
                      )}
                      {member.role !== 'editor' && (
                        <button
                          onClick={() => changeMemberRole(member.id, 'editor')}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Edit3 size={14} />
                          设为编辑者
                        </button>
                      )}
                      {member.role !== 'viewer' && (
                        <button
                          onClick={() => changeMemberRole(member.id, 'viewer')}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                        >
                          <Eye size={14} />
                          设为查看者
                        </button>
                      )}
                      <div className="border-t border-gray-100 my-1" />
                      <button
                        onClick={() => removeMember(member.id)}
                        className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                      >
                        移除成员
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md animate-scale-in">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-display text-xl font-bold text-gray-900">邀请成员</h2>
              <button
                onClick={() => setShowInviteModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">邮箱地址</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="input pl-10"
                    placeholder="colleague@company.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">角色权限</label>
                <div className="space-y-2">
                  {(['editor', 'viewer'] as const).map((role) => {
                    const config = roleConfig[role]
                    const Icon = config.icon
                    return (
                      <label
                        key={role}
                        className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                          inviteRole === role
                            ? 'border-primary-500 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <input
                          type="radio"
                          name="role"
                          value={role}
                          checked={inviteRole === role}
                          onChange={(e) => setInviteRole(e.target.value as typeof inviteRole)}
                          className="hidden"
                        />
                        <div
                          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                            inviteRole === role ? 'border-primary-500' : 'border-gray-300'
                          }`}
                        >
                          {inviteRole === role && (
                            <div className="w-2.5 h-2.5 bg-primary-500 rounded-full" />
                          )}
                        </div>
                        <div className={`w-8 h-8 rounded-lg ${config.color} flex items-center justify-center`}>
                          <Icon size={16} />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{config.label}</p>
                          <p className="text-xs text-gray-500">
                            {role === 'editor' ? '可以上传和编辑图标' : '仅可以浏览和下载图标'}
                          </p>
                        </div>
                      </label>
                    )
                  })}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowInviteModal(false)}
                className="btn btn-secondary"
              >
                取消
              </button>
              <button
                onClick={handleInvite}
                disabled={!inviteEmail.trim()}
                className="btn btn-primary"
              >
                发送邀请
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

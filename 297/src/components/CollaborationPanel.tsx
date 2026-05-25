import { Users, Lock, Lock as LockIcon } from 'lucide-react'
import { useCollaborationStore } from '@/store/collaborationStore'
import { useAuthStore } from '@/store/authStore'

export default function CollaborationPanel() {
  const { onlineUsers, regionLocks } = useCollaborationStore()
  const user = useAuthStore((state) => state.user)

  const myLocks = regionLocks.filter(l => l.userId === user?.id)
  const otherLocks = regionLocks.filter(l => l.userId !== user?.id)

  return (
    <div className="glass-panel rounded-xl p-4 w-56">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white">协作用户</h3>
        <Users className="w-4 h-4 text-zinc-400" />
      </div>
      <div className="space-y-2 mb-4">
        {onlineUsers.map((user) => (
          <div
            key={user.id}
            className="flex items-center gap-3 p-2 rounded-lg hover:bg-zinc-800 transition-colors"
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ backgroundColor: user.color + '33' }}
            >
              <span
                className="text-sm font-medium"
                style={{ color: user.color }}
              >
                {user.username.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1">
              <p className="text-sm text-white">{user.username}</p>
            </div>
            <div className="w-2 h-2 rounded-full bg-green-400" />
          </div>
        ))}
        {onlineUsers.length === 0 && (
          <p className="text-sm text-zinc-500 text-center py-4">
            暂无在线用户
          </p>
        )}
      </div>

      {regionLocks.length > 0 && (
        <>
          <div className="h-px bg-zinc-700 my-3" />
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">区域锁</h3>
            <Lock className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="space-y-2">
            {myLocks.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-primary-400 font-medium">我的锁</p>
                {myLocks.map(lock => (
                  <div key={lock.id} className="flex items-center gap-2 p-2 rounded-lg bg-primary-500/10">
                    <LockIcon className="w-3 h-3 text-primary-400" />
                    <div className="flex-1">
                      <p className="text-xs text-primary-300">
                        ({lock.center.x.toFixed(0)}, {lock.center.z.toFixed(0)})
                      </p>
                      <p className="text-[10px] text-zinc-500">
                        {new Date(lock.expiresAt).toLocaleTimeString()} 过期
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {otherLocks.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-red-400 font-medium">他人锁</p>
                {otherLocks.map(lock => (
                  <div key={lock.id} className="flex items-center gap-2 p-2 rounded-lg bg-red-500/10">
                    <LockIcon className="w-3 h-3 text-red-400" />
                    <div className="flex-1">
                      <p className="text-xs text-red-300">
                        {lock.userName}
                      </p>
                      <p className="text-[10px] text-zinc-500">
                        ({lock.center.x.toFixed(0)}, {lock.center.z.toFixed(0)})
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

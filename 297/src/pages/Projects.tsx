import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  FolderOpen,
  BarChart3,
  Upload,
  Calendar,
  Loader2,
} from 'lucide-react'
import { Project } from '@/types'
import { projectApi } from '@/services/api'
import { useAuthStore } from '@/store/authStore'

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newProject, setNewProject] = useState({ name: '', description: '' })
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const data = await projectApi.getAll()
      setProjects(data)
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await projectApi.create(newProject)
      setShowCreateModal(false)
      setNewProject({ name: '', description: '' })
      loadProjects()
    } catch (error) {
      console.error('Failed to create project:', error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">项目列表</h1>
            <p className="text-zinc-400 mt-1">管理您的点云标注项目</p>
          </div>
          {user?.role === 'admin' && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              创建项目
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              className="glass-panel rounded-xl p-6 hover:border-primary-500/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-primary-500/20 rounded-lg flex items-center justify-center">
                  <FolderOpen className="w-6 h-6 text-primary-400" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500">
                    {project.pointCloudPath ? (
                      <span className="text-green-400">已上传</span>
                    ) : (
                      <span className="text-yellow-400">待上传</span>
                    )}
                  </span>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-white mb-2">
                {project.name}
              </h3>
              <p className="text-zinc-400 text-sm mb-4 line-clamp-2">
                {project.description || '暂无描述'}
              </p>

              <div className="flex items-center gap-4 text-xs text-zinc-500 mb-4">
                <div className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {new Date(project.createdAt).toLocaleDateString()}
                </div>
              </div>

              <div className="flex gap-2">
                <Link
                  to={`/annotate/${project.id}`}
                  className="flex-1 btn-secondary text-center text-sm py-2"
                >
                  开始标注
                </Link>
                <Link
                  to={`/statistics/${project.id}`}
                  className="p-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors"
                >
                  <BarChart3 className="w-4 h-4" />
                </Link>
                {user?.role === 'admin' && !project.pointCloudPath && (
                  <label className="p-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors cursor-pointer">
                    <Upload className="w-4 h-4" />
                    <input
                      type="file"
                      className="hidden"
                      accept=".las,.laz,.ply"
                      onChange={async (e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          await projectApi.uploadPointCloud(project.id, file)
                          loadProjects()
                        }
                      }}
                    />
                  </label>
                )}
              </div>
            </div>
          ))}

          {projects.length === 0 && (
            <div className="col-span-full text-center py-16">
              <FolderOpen className="w-16 h-16 text-zinc-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-zinc-400 mb-2">
                暂无项目
              </h3>
              <p className="text-zinc-500">
                {user?.role === 'admin'
                  ? '点击上方按钮创建第一个项目'
                  : '等待管理员创建项目'}
              </p>
            </div>
          )}
        </div>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="glass-panel rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-6">创建新项目</h2>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  项目名称
                </label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) =>
                    setNewProject({ ...newProject, name: e.target.value })
                  }
                  className="input-field w-full"
                  placeholder="请输入项目名称"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  项目描述
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) =>
                    setNewProject({ ...newProject, description: e.target.value })
                  }
                  className="input-field w-full h-24 resize-none"
                  placeholder="请输入项目描述"
                />
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 btn-secondary"
                >
                  取消
                </button>
                <button type="submit" className="flex-1 btn-primary">
                  创建
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

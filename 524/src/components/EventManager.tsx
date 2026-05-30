import { useState, useEffect } from 'react'
import { fetchEvents, createEvent, deleteEvent } from '@/api'
import { EVENT_TYPES } from '@/types'
import type { EventInfo, EventCreate } from '@/types'
import { Calendar, Plus, Trash2, Clock, MapPin, AlertTriangle } from 'lucide-react'

export default function EventManager() {
  const [events, setEvents] = useState<EventInfo[]>([])
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<EventCreate>({
    event_type: 'concert',
    title: '',
    event_date: new Date().toISOString().split('T')[0],
    start_hour: 19,
    end_hour: 22,
    impact_zone_ids: 'A,B,C',
    impact_factor: 1.5,
    description: '',
  })

  useEffect(() => {
    loadEvents()
  }, [])

  async function loadEvents() {
    try {
      const data = await fetchEvents(true)
      setEvents(data)
    } catch (e) {
      console.error('Failed to load events:', e)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await createEvent(formData)
      setFormData({
        event_type: 'concert',
        title: '',
        event_date: new Date().toISOString().split('T')[0],
        start_hour: 19,
        end_hour: 22,
        impact_zone_ids: 'A,B,C',
        impact_factor: 1.5,
        description: '',
      })
      setShowForm(false)
      loadEvents()
    } catch (err) {
      console.error('Failed to create event:', err)
    }
  }

  async function handleDelete(id: number) {
    if (confirm('确定删除此事件吗？')) {
      try {
        await deleteEvent(id)
        loadEvents()
      } catch (err) {
        console.error('Failed to delete event:', err)
      }
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Calendar className="w-4 h-4 text-brand-orange" />
          事件管理
        </h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30 hover:bg-brand-cyan/20 transition-all"
        >
          <Plus className="w-3 h-3" />
          添加事件
        </button>
      </div>

      {showForm && (
        <div className="glass-card p-4 animate-slide-up">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">事件类型</label>
                <select
                  value={formData.event_type}
                  onChange={(e) => setFormData({ ...formData, event_type: e.target.value })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                >
                  {Object.entries(EVENT_TYPES).map(([key, val]) => (
                    <option key={key} value={key}>
                      {val.icon} {val.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">影响因子</label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="3"
                  value={formData.impact_factor}
                  onChange={(e) => setFormData({ ...formData, impact_factor: parseFloat(e.target.value) })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] text-slate-400 mb-1">事件名称</label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="如：周杰伦演唱会"
                className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">日期</label>
                <input
                  type="date"
                  value={formData.event_date}
                  onChange={(e) => setFormData({ ...formData, event_date: e.target.value })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">影响区域</label>
                <input
                  type="text"
                  value={formData.impact_zone_ids}
                  onChange={(e) => setFormData({ ...formData, impact_zone_ids: e.target.value })}
                  placeholder="A,B,C"
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">开始时间</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={formData.start_hour}
                  onChange={(e) => setFormData({ ...formData, start_hour: parseInt(e.target.value) })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">结束时间</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={formData.end_hour}
                  onChange={(e) => setFormData({ ...formData, end_hour: parseInt(e.target.value) })}
                  className="w-full px-2 py-1.5 rounded-lg text-xs bg-brand-dark border border-brand-border text-white focus:outline-none focus:border-brand-cyan"
                  required
                />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white transition-all"
              >
                取消
              </button>
              <button
                type="submit"
                className="px-3 py-1.5 rounded-lg text-xs bg-brand-cyan text-brand-dark font-medium hover:bg-brand-cyan/90 transition-all"
              >
                创建
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-2 max-h-96 overflow-auto">
        {events.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            暂无事件
          </div>
        ) : (
          events.map((event) => {
            const typeInfo = EVENT_TYPES[event.event_type] || { label: '其他', color: '#64748B', icon: '📅' }
            return (
              <div
                key={event.id}
                className="glass-card p-3 hover:border-slate-600 transition-all"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
                      style={{ background: `${typeInfo.color}15`, border: `1px solid ${typeInfo.color}30` }}
                    >
                      {typeInfo.icon}
                    </div>
                    <div>
                      <div className="text-xs font-medium text-white">{event.title}</div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-500">
                        <span
                          className="px-1.5 py-0.5 rounded text-[9px] font-medium"
                          style={{ background: `${typeInfo.color}15`, color: typeInfo.color }}
                        >
                          {typeInfo.label}
                        </span>
                        <span>x{event.impact_factor}</span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(event.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-brand-orange hover:bg-brand-orange/10 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {event.event_date}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {event.start_hour.toString().padStart(2, '0')}:00 - {event.end_hour.toString().padStart(2, '0')}:00
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {event.impact_zone_ids}
                  </span>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

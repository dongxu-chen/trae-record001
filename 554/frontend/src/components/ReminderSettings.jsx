import React, { useState, useEffect } from 'react'
import axios from 'axios'

function ReminderSettings({ user, showToast }) {
  const [reminders, setReminders] = useState([])
  const [reminderTypes, setReminderTypes] = useState([])
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchReminderData()
  }, [user.id])

  const fetchReminderData = async () => {
    try {
      const [remindersRes, typesRes, channelsRes] = await Promise.all([
        axios.get(`/api/reminder/user/${user.id}`),
        axios.get('/api/reminder/types'),
        axios.get('/api/reminder/channels')
      ])

      if (remindersRes.data.code === 200) {
        setReminders(remindersRes.data.data)
      }
      if (typesRes.data.code === 200) {
        setReminderTypes(typesRes.data.data)
      }
      if (channelsRes.data.code === 200) {
        setChannels(channelsRes.data.data)
      }
    } catch (err) {
      console.error('获取提醒设置失败', err)
    }
  }

  const toggleReminder = async (type, enabled) => {
    setLoading(true)
    try {
      const existing = reminders.find(r => r.reminderType === type)
      const reminder = {
        userId: user.id,
        reminderType: type,
        enabled: enabled,
        reminderTime: existing?.reminderTime || '20:00',
        pushChannel: existing?.pushChannel || 'APP',
        advanceMinutes: existing?.advanceMinutes || 30
      }

      const res = await axios.post('/api/reminder', reminder)
      if (res.data.code === 200) {
        showToast(enabled ? '已开启提醒' : '已关闭提醒', 'success')
        fetchReminderData()
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast('设置失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  const updateReminderTime = async (type, field, value) => {
    setLoading(true)
    try {
      const existing = reminders.find(r => r.reminderType === type)
      const reminder = {
        userId: user.id,
        reminderType: type,
        enabled: existing?.enabled !== false,
        reminderTime: field === 'time' ? value : existing?.reminderTime || '20:00',
        pushChannel: field === 'channel' ? value : existing?.pushChannel || 'APP',
        advanceMinutes: field === 'advance' ? parseInt(value) : existing?.advanceMinutes || 30
      }

      const res = await axios.post('/api/reminder', reminder)
      if (res.data.code === 200) {
        showToast('设置已更新', 'success')
        fetchReminderData()
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast('设置失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  const isReminderEnabled = (type) => {
    const reminder = reminders.find(r => r.reminderType === type)
    return reminder?.enabled === true
  }

  const getReminderValue = (type, field) => {
    const reminder = reminders.find(r => r.reminderType === type)
    if (field === 'time') return reminder?.reminderTime || '20:00'
    if (field === 'channel') return reminder?.pushChannel || 'APP'
    if (field === 'advance') return reminder?.advanceMinutes || 30
    return null
  }

  return (
    <div className="card">
      <div className="card-title">
        <span>🔔</span>
        <span>签到提醒设置</span>
      </div>

      <div style={{ marginBottom: '20px', padding: '15px', background: '#f0f9ff', borderRadius: '10px' }}>
        <div style={{ fontWeight: 'bold', color: '#0369a1', marginBottom: '8px' }}>
          ⚠️ 温馨提示
        </div>
        <div style={{ fontSize: '13px', color: '#666', lineHeight: '1.6' }}>
          开启连续签到临期提醒，当您已连续签到多日，即将断签时会收到提醒，
          帮您保持连续签到记录，获取更多奖励！
        </div>
      </div>

      {reminderTypes.map((type, index) => (
        <div key={index} style={{ 
          marginBottom: '20px', 
          padding: '15px', 
          background: '#f8f9fa', 
          borderRadius: '10px' 
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div>
              <div style={{ fontWeight: 'bold', color: '#333' }}>{type.name}</div>
              <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
                {type.description}
              </div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={isReminderEnabled(type.type)}
                onChange={(e) => toggleReminder(type.type, e.target.checked)}
                disabled={loading}
              />
              <span className="slider"></span>
            </label>
          </div>

          {isReminderEnabled(type.type) && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>
                  提醒时间
                </label>
                <input
                  type="time"
                  value={getReminderValue(type.type, 'time')}
                  onChange={(e) => updateReminderTime(type.type, 'time', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: '#666', display: 'block', marginBottom: '4px' }}>
                  推送方式
                </label>
                <select
                  value={getReminderValue(type.type, 'channel')}
                  onChange={(e) => updateReminderTime(type.type, 'channel', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    fontSize: '14px',
                    background: 'white'
                  }}
                >
                  {channels.map((ch, i) => (
                    <option key={i} value={ch.channel}>{ch.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      ))}

      <style>{`
        .switch {
          position: relative;
          display: inline-block;
          width: 48px;
          height: 26px;
        }
        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: #ccc;
          transition: .3s;
          border-radius: 26px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 20px;
          width: 20px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: .3s;
          border-radius: 50%;
        }
        input:checked + .slider {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        input:checked + .slider:before {
          transform: translateX(22px);
        }
      `}</style>
    </div>
  )
}

export default ReminderSettings

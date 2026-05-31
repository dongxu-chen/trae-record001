import React from 'react'

function RewardModal({ data, onClose }) {
  if (!data) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-icon">{data.icon}</div>
        <h3 className="modal-title">{data.title}</h3>
        <p className="modal-desc">{data.desc}</p>
        
        {data.reward && (
          <div style={{ 
            background: '#f8f9fa', 
            padding: '15px', 
            borderRadius: '10px',
            marginBottom: '20px'
          }}>
            <div style={{ fontWeight: 'bold', color: '#667eea', fontSize: '18px' }}>
              {data.reward.name}
            </div>
            <div style={{ color: '#666', fontSize: '14px', marginTop: '5px' }}>
              {data.reward.type === 'POINTS' 
                ? `+${data.reward.value} 积分` 
                : `+${data.reward.value} 张补签卡`}
            </div>
          </div>
        )}
        
        <button className="modal-btn" onClick={onClose}>
          太棒了！
        </button>
      </div>
    </div>
  )
}

export default RewardModal

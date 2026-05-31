import React from 'react'

function TreasuresGrid({ treasures, onClaim }) {
  if (!treasures || treasures.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
        暂无宝箱配置
      </div>
    )
  }

  return (
    <div className="treasures-grid">
      {treasures.map((treasure) => (
        <div 
          key={treasure.id}
          className={`treasure-item 
            ${treasure.achieved ? 'achieved' : ''} 
            ${treasure.claimed ? 'claimed' : ''}`}
          onClick={() => treasure.achieved && !treasure.claimed && onClaim(treasure.id)}
        >
          <div className="treasure-icon">
            {treasure.icon || '📦'}
          </div>
          <div className="treasure-name">{treasure.name}</div>
          <div className="treasure-days">
            {treasure.totalDays}天累计签到
          </div>
          {treasure.achieved && !treasure.claimed && (
            <button className="treasure-btn">
              领取奖励
            </button>
          )}
          {treasure.claimed && (
            <div style={{ marginTop: '10px', fontSize: '12px', color: '#4caf50' }}>
              ✓ 已领取
            </div>
          )}
          {!treasure.achieved && (
            <div style={{ marginTop: '10px', fontSize: '12px', color: '#999' }}>
              未达成
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default TreasuresGrid

import React from 'react'

function RewardsList({ rewards }) {
  if (!rewards || rewards.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
        暂无奖励配置
      </div>
    )
  }

  const getRewardIcon = (type) => {
    switch (type) {
      case 'POINTS':
        return '💰'
      case 'RECHECK_CARD':
        return '🎫'
      default:
        return '🎁'
    }
  }

  return (
    <div className="rewards-list">
      {rewards.map((reward, index) => (
        <div 
          key={index} 
          className={`reward-item ${reward.achieved ? 'achieved' : ''}`}
        >
          <div className="reward-day">
            {reward.achieved ? '✓' : `${reward.dayIndex}天`}
          </div>
          <div className="reward-info">
            <div className="reward-name">
              {getRewardIcon(reward.type)} {reward.name}
            </div>
            <div className="reward-desc">
              {reward.type === 'POINTS' ? `${reward.value} 积分` : `${reward.value} 张补签卡`}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default RewardsList

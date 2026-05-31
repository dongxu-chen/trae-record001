import React from 'react'
import dayjs from 'dayjs'

function Calendar({ periodType, currentDate, calendarData, onDateChange, onRecheck, showToast }) {
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  
  const getCalendarDays = () => {
    if (periodType === 'DAILY' || periodType === 'MONTHLY') {
      const firstDay = currentDate.startOf('month')
      const lastDay = currentDate.endOf('month')
      const startPadding = firstDay.day()
      
      const days = []
      
      for (let i = startPadding - 1; i >= 0; i--) {
        days.push({
          date: firstDay.subtract(i + 1, 'day'),
          isCurrentMonth: false
        })
      }
      
      for (let i = 0; i < lastDay.date(); i++) {
        days.push({
          date: firstDay.add(i, 'day'),
          isCurrentMonth: true
        })
      }
      
      const remaining = 42 - days.length
      for (let i = 0; i < remaining; i++) {
        days.push({
          date: lastDay.add(i + 1, 'day'),
          isCurrentMonth: false
        })
      }
      
      return days
    } else if (periodType === 'WEEKLY') {
      const weekStart = currentDate.startOf('week')
      const days = []
      for (let i = 0; i < 7; i++) {
        days.push({
          date: weekStart.add(i, 'day'),
          isCurrentMonth: true
        })
      }
      return days
    }
    return []
  }

  const isChecked = (date) => {
    const dateStr = date.format('YYYY-MM-DD')
    return calendarData.checkinDates?.includes(dateStr) || 
           calendarData.recheckDates?.includes(dateStr)
  }

  const isRechecked = (date) => {
    const dateStr = date.format('YYYY-MM-DD')
    return calendarData.recheckDates?.includes(dateStr)
  }

  const isToday = (date) => {
    return date.format('YYYY-MM-DD') === dayjs().format('YYYY-MM-DD')
  }

  const handleDayClick = (day) => {
    const dateStr = day.date.format('YYYY-MM-DD')
    const today = dayjs()
    const maxRecheckDays = 7
    
    if (day.date.isAfter(today.subtract(1, 'day'))) {
      showToast('不能补签未来或今日的日期', 'info')
      return
    }
    
    const daysAgo = today.diff(day.date, 'day')
    if (daysAgo > maxRecheckDays) {
      showToast(`只能补签过去${maxRecheckDays}天内的日期`, 'error')
      return
    }
    
    if (isChecked(day.date)) {
      showToast('该日期已签到', 'info')
      return
    }
    
    if (calendarData.recheckCards <= 0) {
      showToast('补签卡不足', 'error')
      return
    }
    
    if (calendarData.remainingRecheckCount <= 0) {
      showToast('本月补签次数已达上限', 'error')
      return
    }
    
    if (confirm(`确定使用1张补签卡补签 ${dateStr} 吗？\n（已过期${daysAgo}天，补签有效期${maxRecheckDays}天）`)) {
      onRecheck(dateStr)
    }
  }

  const handlePrev = () => {
    if (periodType === 'WEEKLY') {
      onDateChange(currentDate.subtract(1, 'week'))
    } else {
      onDateChange(currentDate.subtract(1, 'month'))
    }
  }

  const handleNext = () => {
    if (periodType === 'WEEKLY') {
      onDateChange(currentDate.add(1, 'week'))
    } else {
      onDateChange(currentDate.add(1, 'month'))
    }
  }

  const getTitle = () => {
    if (periodType === 'WEEKLY') {
      const weekStart = currentDate.startOf('week')
      const weekEnd = currentDate.endOf('week')
      return `${weekStart.format('MM月DD日')} - ${weekEnd.format('MM月DD日')}`
    } else {
      return currentDate.format('YYYY年MM月')
    }
  }

  const days = getCalendarDays()

  return (
    <div className="calendar">
      <div className="calendar-header">
        <h3>{getTitle()}</h3>
        <div className="calendar-nav">
          <button onClick={handlePrev}>‹</button>
          <button onClick={handleNext}>›</button>
        </div>
      </div>
      
      <div className="calendar-grid">
        {weekdays.map(day => (
          <div key={day} className="calendar-weekday">{day}</div>
        ))}
        
        {days.map((day, index) => (
          <div
            key={index}
            className={`calendar-day 
              ${!day.isCurrentMonth ? 'other-month' : ''} 
              ${isToday(day.date) ? 'today' : ''} 
              ${isRechecked(day.date) ? 'rechecked' : isChecked(day.date) ? 'checked' : ''}`}
            onClick={() => day.isCurrentMonth && handleDayClick(day)}
          >
            {day.date.date()}
            {isRechecked(day.date) && <span className="recheck-tag">补</span>}
          </div>
        ))}
      </div>
      
      <div style={{ marginTop: '15px', fontSize: '12px', color: '#666' }}>
        <span style={{ marginRight: '20px' }}>
          <span style={{ display: 'inline-block', width: '12px', height: '12px', 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
            borderRadius: '3px', marginRight: '5px', verticalAlign: 'middle' }}></span>
          已签到
        </span>
        <span style={{ marginRight: '20px' }}>
          <span style={{ display: 'inline-block', width: '12px', height: '12px', 
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', 
            borderRadius: '3px', marginRight: '5px', verticalAlign: 'middle' }}></span>
          已补签
        </span>
        <span>点击过去7天内的日期可补签</span>
      </div>
    </div>
  )
}

export default Calendar

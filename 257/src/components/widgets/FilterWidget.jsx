import React, { useState } from 'react'
import { useDispatch } from 'react-redux'
import { setFilter } from '../../store/dashboardSlice'
import { eventBus, EVENTS } from '../../utils/eventBus'

export default function FilterWidget({ id, config }) {
  const dispatch = useDispatch()
  const { filterKey = 'category', options = ['全部'], label = '筛选' } = config
  const [value, setValue] = useState('全部')

  const handleChange = (e) => {
    const newValue = e.target.value
    setValue(newValue)
    dispatch(setFilter({ key: filterKey, value: newValue }))
    eventBus.emit(EVENTS.FILTER_CHANGED, { key: filterKey, value: newValue })
  }

  return (
    <div className="filter-widget">
      <label className="filter-label">{label}</label>
      <select className="filter-select" value={value} onChange={handleChange}>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  )
}

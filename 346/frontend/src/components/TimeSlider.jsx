import { useState } from 'react'
import { Slider, Button, Space, DatePicker, Popover, Switch } from 'antd'
import { ClockCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const TimeSlider = ({ onChange }) => {
  const [enabled, setEnabled] = useState(false)
  const [range, setRange] = useState([0, 100])
  const [dateRange, setDateRange] = useState(null)
  const [mode, setMode] = useState('slider')

  const handleSliderChange = (value) => {
    setRange(value)
    if (enabled && onChange) {
      const minDate = dayjs().subtract(365, 'day').valueOf()
      const maxDate = dayjs().valueOf()
      const start = minDate + (value[0] / 100) * (maxDate - minDate)
      const end = minDate + (value[1] / 100) * (maxDate - minDate)
      onChange([start, end])
    }
  }

  const handleDateRangeChange = (dates) => {
    setDateRange(dates)
    if (enabled && onChange && dates) {
      onChange([dates[0].valueOf(), dates[1].valueOf()])
    }
  }

  const handleToggle = (checked) => {
    setEnabled(checked)
    if (!checked && onChange) {
      onChange(null)
    } else if (onChange) {
      if (mode === 'slider') {
        handleSliderChange(range)
      } else if (dateRange) {
        handleDateRangeChange(dateRange)
      }
    }
  }

  const handleReset = () => {
    setRange([0, 100])
    setDateRange(null)
    if (onChange) {
      onChange(null)
    }
  }

  const content = (
    <div style={{ width: 280 }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <Space style={{ marginBottom: 8 }}>
            <Button
              type={mode === 'slider' ? 'primary' : 'default'}
              size="small"
              onClick={() => setMode('slider')}
            >
              滑块模式
            </Button>
            <Button
              type={mode === 'date' ? 'primary' : 'default'}
              size="small"
              onClick={() => setMode('date')}
            >
              日期模式
            </Button>
          </Space>
        </div>

        {mode === 'slider' ? (
          <div>
            <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>
              时间范围: {range[0]}% - {range[1]}%
            </div>
            <Slider
              range
              value={range}
              onChange={handleSliderChange}
              disabled={!enabled}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999', marginTop: 4 }}>
              <span>1年前</span>
              <span>今天</span>
            </div>
          </div>
        ) : (
          <div>
            <RangePicker
              value={dateRange}
              onChange={handleDateRangeChange}
              disabled={!enabled}
              style={{ width: '100%' }}
            />
          </div>
        )}

        <Button size="small" block onClick={handleReset}>
          重置
        </Button>
      </Space>
    </div>
  )

  return (
    <div className="time-slider-container">
      <Space>
        <Switch
          checked={enabled}
          onChange={handleToggle}
          size="small"
        />
        <Popover
          content={content}
          title="时间过滤"
          trigger="click"
          placement="bottomRight"
        >
          <Button
            type={enabled ? 'primary' : 'default'}
            size="small"
            icon={<ClockCircleOutlined />}
          >
            时间过滤
          </Button>
        </Popover>
      </Space>
    </div>
  )
}

export default TimeSlider

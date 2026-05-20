import { observer } from 'mobx-react-lite'

const SkuSelector = observer(({ store }) => {
  const { specs, selectedSpecs, availableSpecOptions, selectSpec } = store

  return (
    <div className="sku-selector">
      {specs.map((group) => (
        <div key={group.id} className="spec-group">
          <div className="spec-label">
            <span>{group.name}</span>
            {selectedSpecs[group.id] && (
              <span className="selected-value">
                {group.options.find(opt => opt.id === selectedSpecs[group.id])?.name}
              </span>
            )}
          </div>
          <div className="spec-options">
            {availableSpecOptions[group.id]?.map((option) => {
              const isSelected = selectedSpecs[group.id] === option.id
              const isDisabled = !option.available

              return (
                <button
                  key={option.id}
                  className={`spec-option ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                  onClick={() => !isDisabled && selectSpec(group.id, option.id)}
                  disabled={isDisabled}
                >
                  {group.id === 'color' && (
                    <span
                      className="color-dot"
                      style={{ backgroundColor: option.value }}
                    />
                  )}
                  <span className="option-name">{option.name}</span>
                  {isDisabled && <span className="sold-out">已售罄</span>}
                </button>
              )
            })}
          </div>
        </div>
      ))}

      <style jsx>{`
        .sku-selector {
          padding: 16px;
          background: #fff;
        }
        .spec-group {
          margin-bottom: 20px;
        }
        .spec-group:last-child {
          margin-bottom: 0;
        }
        .spec-label {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          font-size: 14px;
          color: #666;
        }
        .spec-label > span:first-child {
          font-weight: 500;
          color: #333;
        }
        .selected-value {
          color: #ff4d4f;
          font-size: 13px;
        }
        .spec-options {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }
        .spec-option {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 20px;
          background: #fff;
          font-size: 14px;
          color: #333;
          transition: all 0.2s ease;
          position: relative;
        }
        .spec-option:hover:not(.disabled) {
          border-color: #ff4d4f;
          background: #fff2f0;
        }
        .spec-option.selected {
          border-color: #ff4d4f;
          background: #fff2f0;
          color: #ff4d4f;
        }
        .spec-option.disabled {
          opacity: 0.5;
          cursor: not-allowed;
          text-decoration: line-through;
        }
        .color-dot {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          border: 1px solid rgba(0, 0, 0, 0.1);
        }
        .option-name {
          white-space: nowrap;
        }
        .sold-out {
          position: absolute;
          top: -8px;
          right: -8px;
          background: #ff4d4f;
          color: #fff;
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 10px;
          text-decoration: none;
        }
        @media (max-width: 768px) {
          .sku-selector {
            padding: 12px;
          }
          .spec-option {
            padding: 6px 12px;
            font-size: 13px;
          }
          .color-dot {
            width: 14px;
            height: 14px;
          }
        }
      `}</style>
    </div>
  )
})

export default SkuSelector

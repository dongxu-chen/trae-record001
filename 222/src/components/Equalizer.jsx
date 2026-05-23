export default function Equalizer({ eqBands, onEqChange }) {
  const bands = [
    { key: 'low', label: '低音', freq: '60Hz' },
    { key: 'mid', label: '中音', freq: '1kHz' },
    { key: 'high', label: '高音', freq: '10kHz' }
  ]

  return (
    <div className="equalizer">
      <div className="equalizer-title">
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z"/>
        </svg>
        均衡器
      </div>
      <div className="eq-bands">
        {bands.map((band) => (
          <div key={band.key} className="eq-band">
            <span className="label">{band.label}</span>
            <div className="slider-container">
              <input
                type="range"
                className="eq-slider"
                min="-12"
                max="12"
                value={eqBands[band.key]}
                onChange={(e) => onEqChange(band.key, parseFloat(e.target.value))}
              />
            </div>
            <span className="value">{eqBands[band.key] > 0 ? '+' : ''}{eqBands[band.key]}dB</span>
          </div>
        ))}
      </div>
    </div>
  )
}

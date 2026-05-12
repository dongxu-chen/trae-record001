import useStore, { materialPresets } from '../store/store'
import './MaterialSwatch.css'

export default function MaterialSwatch() {
  const currentMaterial = useStore((state) => state.materialType)
  const setMaterialType = useStore((state) => state.setMaterialType)
  const currentColor = useStore((state) => state.color)

  const getMaterialStyle = (preset) => ({
    backgroundColor: currentColor,
    metalness: preset.metalness,
    roughness: preset.roughness,
  })

  return (
    <div className="material-swatch">
      <h3 className="control-title">选择材质</h3>
      <div className="material-grid">
        {materialPresets.map((preset) => (
          <button
            key={preset.id}
            className={`material-card ${currentMaterial === preset.id ? 'active' : ''}`}
            onClick={() => setMaterialType(preset.id)}
          >
            <div 
              className="material-preview"
              style={getMaterialStyle(preset)}
            />
            <div className="material-info">
              <span className="material-name">{preset.name}</span>
              <div className="material-props">
                <span className="prop-badge">
                  金属度: {preset.metalness.toFixed(1)}
                </span>
                <span className="prop-badge">
                  粗糙度: {preset.roughness.toFixed(1)}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

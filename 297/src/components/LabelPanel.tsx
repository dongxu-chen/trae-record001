import { LABEL_COLORS, LABEL_NAMES, LabelType } from '@/types'
import { useAnnotationStore } from '@/store/annotationStore'
import { cn } from '@/utils/cn'

const labels: LabelType[] = ['ground', 'vehicle', 'pedestrian']

export default function LabelPanel() {
  const { currentLabel, setCurrentLabel, annotations } = useAnnotationStore()

  const countByLabel = labels.reduce((acc, label) => {
    acc[label] = annotations.filter((a) => a.label === label).length
    return acc
  }, {} as Record<LabelType, number>)

  return (
    <div className="glass-panel rounded-xl p-4 w-56">
      <h3 className="text-sm font-semibold text-white mb-3">语义标签</h3>
      <div className="space-y-2">
        {labels.map((label) => {
          const isActive = currentLabel === label
          return (
            <button
              key={label}
              onClick={() => setCurrentLabel(label)}
              className={cn(
                'w-full flex items-center justify-between p-3 rounded-lg transition-all',
                isActive
                  ? 'bg-zinc-700 ring-2 ring-offset-1 ring-offset-zinc-800'
                  : 'hover:bg-zinc-800',
              )}
              style={{
                boxShadow: isActive ? `0 0 0 2px ${LABEL_COLORS[label]}` : undefined,
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: LABEL_COLORS[label] }}
                />
                <span className="text-sm text-white">{LABEL_NAMES[label]}</span>
              </div>
              <span className="text-xs text-zinc-400">
                {countByLabel[label]}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

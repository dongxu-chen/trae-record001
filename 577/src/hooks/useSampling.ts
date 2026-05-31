import { useCallback, useRef } from 'react'
import { useAppStore, type SampleConfig, type SampleStats, type StratifyIndex } from '@/store/appStore'

interface WorkerResponse {
  type: 'SUCCESS' | 'ERROR' | 'CLEANUP_DONE'
  result?: {
    indices: number[]
    sampleData: Record<string, unknown>[]
    stats: SampleStats
  }
  error?: string
}

export function useSampling() {
  const workerRef = useRef<Worker | null>(null)
  const setSampleResult = useAppStore((s) => s.setSampleResult)
  const setIsSampling = useAppStore((s) => s.setIsSampling)

  const sample = useCallback(
    (data: Record<string, unknown>[], config: SampleConfig, stratifyIndex?: StratifyIndex | null) => {
      setIsSampling(true)

      if (workerRef.current) {
        workerRef.current.terminate()
      }

      const workerCode = `
        let _dataRef = null;

        self.onmessage = function(e) {
          const msg = e.data;

          if (msg.type === 'CLEANUP') {
            _dataRef = null;
            if (typeof gc === 'function') gc();
            self.postMessage({ type: 'CLEANUP_DONE' });
            return;
          }

          try {
            _dataRef = msg.data;
            const config = msg.config;
            const stratifyGroups = msg.stratifyGroups || null;
            let result;

            switch (config.method) {
              case 'random':
                result = randomSample(_dataRef, config.ratio);
                break;
              case 'stratified':
                result = stratifiedSample(_dataRef, config.ratio, stratifyGroups);
                break;
              case 'systematic':
                result = systematicSample(_dataRef, config.ratio, config.stepSize);
                break;
              default:
                throw new Error('Unknown method: ' + config.method);
            }

            self.postMessage({ type: 'SUCCESS', result: result });

            _dataRef = null;
            result = null;
          } catch (error) {
            _dataRef = null;
            self.postMessage({ type: 'ERROR', error: error.message || 'Unknown error' });
          }
        };

        function randomSample(data, ratio) {
          const totalSize = data.length;
          const sampleSize = Math.max(1, Math.round(totalSize * ratio));
          const indices = [];
          const pool = Array.from({ length: totalSize }, (_, i) => i);
          for (let i = pool.length - 1; i > 0 && indices.length < sampleSize; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [pool[i], pool[j]] = [pool[j], pool[i]];
            indices.push(pool[i]);
          }
          while (indices.length < sampleSize) {
            indices.push(pool[indices.length]);
          }
          indices.sort((a, b) => a - b);
          const sampleData = indices.map(i => data[i]);
          return { indices, sampleData, stats: { sampleSize, totalSize, ratio } };
        }

        function stratifiedSample(data, ratio, precomputedGroups) {
          const totalSize = data.length;
          const groups = precomputedGroups;
          const indices = [];
          const distribution = {};
          const groupKeys = Object.keys(groups);

          for (let g = 0; g < groupKeys.length; g++) {
            const groupKey = groupKeys[g];
            const groupIndices = groups[groupKey];
            const groupSampleSize = Math.max(1, Math.round(groupIndices.length * ratio));
            const shuffled = groupIndices.slice();
            for (let i = shuffled.length - 1; i > 0; i--) {
              const j = Math.floor(Math.random() * (i + 1));
              [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
            }
            const selected = shuffled.slice(0, groupSampleSize);
            for (let s = 0; s < selected.length; s++) indices.push(selected[s]);
            distribution[groupKey] = selected.length;
          }

          indices.sort((a, b) => a - b);
          const sampleData = indices.map(i => data[i]);
          return { indices, sampleData, stats: { sampleSize: indices.length, totalSize, ratio, distribution } };
        }

        function systematicSample(data, ratio, stepSize) {
          const totalSize = data.length;
          const sampleSize = Math.max(1, Math.round(totalSize * ratio));
          const step = stepSize || Math.max(1, Math.floor(totalSize / sampleSize));
          const startIndex = Math.floor(Math.random() * step);
          const indices = [];
          for (let i = startIndex; i < totalSize && indices.length < sampleSize; i += step) {
            indices.push(i);
          }
          const sampleData = indices.map(i => data[i]);
          return { indices, sampleData, stats: { sampleSize: indices.length, totalSize, ratio } };
        }
      `

      const blob = new Blob([workerCode], { type: 'application/javascript' })
      workerRef.current = new Worker(URL.createObjectURL(blob))

      workerRef.current.onmessage = (e: MessageEvent<WorkerResponse>) => {
        const response = e.data
        if (response.type === 'SUCCESS' && response.result) {
          setSampleResult(
            response.result.sampleData,
            response.result.indices,
            response.result.stats,
          )
          if (workerRef.current) {
            workerRef.current.postMessage({ type: 'CLEANUP' })
          }
        } else if (response.type === 'ERROR') {
          console.error('Sampling error:', response.error)
          setIsSampling(false)
        }
      }

      workerRef.current.onerror = () => {
        setIsSampling(false)
      }

      const stratifyGroups = (config.method === 'stratified' && stratifyIndex?.groups)
        ? stratifyIndex.groups
        : null

      workerRef.current.postMessage({
        data,
        config,
        stratifyGroups,
      })
    },
    [setSampleResult, setIsSampling],
  )

  const terminate = useCallback(() => {
    if (workerRef.current) {
      workerRef.current.terminate()
      workerRef.current = null
    }
  }, [])

  return { sample, terminate }
}

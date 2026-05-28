import { useEffect, useRef } from 'react';
import { GUI } from 'dat.gui';
import { useTerrainStore } from '@/store/terrainStore';
import { useHeightmapStore } from '@/store/heightmapStore';

export function useTerrainGUI() {
  const guiRef = useRef<GUI | null>(null);

  const noiseType = useTerrainStore((s) => s.noiseType);
  const amplitude = useTerrainStore((s) => s.amplitude);
  const frequency = useTerrainStore((s) => s.frequency);
  const octaves = useTerrainStore((s) => s.octaves);
  const persistence = useTerrainStore((s) => s.persistence);
  const lacunarity = useTerrainStore((s) => s.lacunarity);
  const seed = useTerrainStore((s) => s.seed);
  const chunkSize = useTerrainStore((s) => s.chunkSize);
  const chunks = useTerrainStore((s) => s.chunks);
  const lodBias = useTerrainStore((s) => s.lodBias);
  const wireframe = useTerrainStore((s) => s.wireframe);
  const showWater = useTerrainStore((s) => s.showWater);
  const waterLevel = useTerrainStore((s) => s.waterLevel);
  const showShadows = useTerrainStore((s) => s.showShadows);
  const autoRotate = useTerrainStore((s) => s.autoRotate);
  const terrainSet = useTerrainStore((s) => s.set);
  const terrainRandomize = useTerrainStore((s) => s.randomize);
  const terrainReset = useTerrainStore((s) => s.reset);

  const brushMode = useHeightmapStore((s) => s.brushMode);
  const brushSize = useHeightmapStore((s) => s.brushSize);
  const brushStrength = useHeightmapStore((s) => s.brushStrength);
  const tools = useHeightmapStore((s) => s.tools);
  const erosion = useHeightmapStore((s) => s.erosion);
  const vegetation = useHeightmapStore((s) => s.vegetation);
  const applyErosion = useHeightmapStore((s) => s.applyErosion);
  const heightmapSet = useHeightmapStore((s) => s.set);

  useEffect(() => {
    const gui = new GUI({ width: 320 });
    guiRef.current = gui;
    gui.domElement.style.position = 'fixed';
    gui.domElement.style.top = '80px';
    gui.domElement.style.right = '16px';
    gui.domElement.style.zIndex = '100';

    const ctrl = {
      get noiseType() { return noiseType; },
      get amplitude() { return amplitude; },
      get frequency() { return frequency; },
      get octaves() { return octaves; },
      get persistence() { return persistence; },
      get lacunarity() { return lacunarity; },
      get seed() { return seed; },
      get chunkSize() { return chunkSize; },
      get chunks() { return chunks; },
      get lodBias() { return lodBias; },
      get wireframe() { return wireframe; },
      get showWater() { return showWater; },
      get waterLevel() { return waterLevel; },
      get showShadows() { return showShadows; },
      get autoRotate() { return autoRotate; },
      get brushMode() { return brushMode; },
      get brushSize() { return brushSize; },
      get brushStrength() { return brushStrength; },
      get sculpting() { return tools.sculpting; },
      get erosion_iterations() { return erosion.iterations; },
      get erosion_erosionRate() { return erosion.erosionRate; },
      get erosion_depositionRate() { return erosion.depositionRate; },
      get veg_enabled() { return vegetation.enabled; },
      get veg_density() { return vegetation.density; },
      get veg_treeCount() { return vegetation.treeCount; },
      get veg_grassCount() { return vegetation.grassCount; },
      get veg_maxAltitude() { return vegetation.maxAltitude; },
      get veg_maxSlope() { return vegetation.maxSlope; },
    };

    const noise = gui.addFolder('📊 噪声参数');
    noise.add(ctrl, 'noiseType', ['simplex', 'perlin']).onChange((v) => terrainSet('noiseType', v));
    noise.add(ctrl, 'amplitude', 10, 200, 1).onChange((v) => terrainSet('amplitude', v)).name('高度幅度');
    noise.add(ctrl, 'frequency', 0.002, 0.05, 0.001).onChange((v) => terrainSet('frequency', v)).name('频率');
    noise.add(ctrl, 'octaves', 1, 10, 1).onChange((v) => terrainSet('octaves', v)).name('噪声层数');
    noise.add(ctrl, 'persistence', 0.1, 1, 0.01).onChange((v) => terrainSet('persistence', v)).name('持续度');
    noise.add(ctrl, 'lacunarity', 1, 4, 0.01).onChange((v) => terrainSet('lacunarity', v)).name('间隙度');
    noise.add(ctrl, 'seed', 0, 999999, 1).onChange((v) => terrainSet('seed', v)).name('随机种子');
    noise.open();

    const terrainFolder = gui.addFolder('🗺️ 地形设置');
    terrainFolder.add(ctrl, 'chunkSize', 100, 400, 10).onChange((v) => terrainSet('chunkSize', v)).name('分块尺寸');
    terrainFolder.add(ctrl, 'chunks', 1, 7, 1).onChange((v) => terrainSet('chunks', v)).name('分块数量');
    terrainFolder.add(ctrl, 'lodBias', 0.5, 3, 0.1).onChange((v) => terrainSet('lodBias', v)).name('LOD 距离');
    terrainFolder.add(ctrl, 'wireframe').onChange((v) => terrainSet('wireframe', v)).name('线框模式');
    terrainFolder.open();

    const water = gui.addFolder('💧 水体设置');
    water.add(ctrl, 'showWater').onChange((v) => terrainSet('showWater', v)).name('显示水体');
    water.add(ctrl, 'waterLevel', -50, 50, 0.5).onChange((v) => terrainSet('waterLevel', v)).name('水面高度');
    water.open();

    const sculpt = gui.addFolder('✏️ 雕刻工具');
    sculpt.add(ctrl, 'sculpting').onChange((v) => {
      heightmapSet('tools', { ...tools, sculpting: v });
    }).name('启用雕刻');
    sculpt.add(ctrl, 'brushMode', ['raise', 'lower', 'smooth']).onChange((v) => {
      heightmapSet('brushMode', v);
    }).name('刷子模式');
    sculpt.add(ctrl, 'brushSize', 5, 100, 1).onChange((v) => {
      heightmapSet('brushSize', v);
    }).name('刷子大小');
    sculpt.add(ctrl, 'brushStrength', 1, 30, 0.5).onChange((v) => {
      heightmapSet('brushStrength', v);
    }).name('刷子强度');
    sculpt.open();

    const erosionFolder = gui.addFolder('🌊 侵蚀模拟');
    erosionFolder.add(ctrl, 'erosion_iterations', 10, 200, 10).onChange((v) => {
      heightmapSet('erosion', { ...erosion, iterations: v });
    }).name('粒子数量');
    erosionFolder.add(ctrl, 'erosion_erosionRate', 0.1, 1, 0.01).onChange((v) => {
      heightmapSet('erosion', { ...erosion, erosionRate: v });
    }).name('侵蚀速率');
    erosionFolder.add(ctrl, 'erosion_depositionRate', 0.1, 1, 0.01).onChange((v) => {
      heightmapSet('erosion', { ...erosion, depositionRate: v });
    }).name('沉积速率');
    erosionFolder.add({ 运行侵蚀: async () => {
      const worldSize = chunkSize * chunks;
      await applyErosion(worldSize);
    }}, '运行侵蚀').name('🚀 运行水力侵蚀');
    erosionFolder.open();

    const vegFolder = gui.addFolder('🌲 植被系统');
    vegFolder.add(ctrl, 'veg_enabled').onChange((v) => {
      heightmapSet('vegetation', { ...vegetation, enabled: v });
    }).name('显示植被');
    vegFolder.add(ctrl, 'veg_density', 0.1, 1, 0.05).onChange((v) => {
      heightmapSet('vegetation', { ...vegetation, density: v });
    }).name('植被密度');
    vegFolder.add(ctrl, 'veg_treeCount', 500, 5000, 100).onChange((v) => {
      heightmapSet('vegetation', { ...vegetation, treeCount: v });
    }).name('树木数量');
    vegFolder.add(ctrl, 'veg_grassCount', 1000, 10000, 500).onChange((v) => {
      heightmapSet('vegetation', { ...vegetation, grassCount: v });
    }).name('草数量');
    vegFolder.add(ctrl, 'veg_maxAltitude', 0.3, 1, 0.05).onChange((v) => {
      heightmapSet('vegetation', { ...vegetation, maxAltitude: v });
    }).name('最高海拔');
    vegFolder.add(ctrl, 'veg_maxSlope', 0.1, 1, 0.05).onChange((v) => {
      heightmapSet('vegetation', { ...vegetation, maxSlope: v });
    }).name('最大坡度');
    vegFolder.open();

    const render = gui.addFolder('✨ 渲染设置');
    render.add(ctrl, 'showShadows').onChange((v) => terrainSet('showShadows', v)).name('阴影');
    render.add(ctrl, 'autoRotate').onChange((v) => terrainSet('autoRotate', v)).name('自动旋转');
    render.add({ 随机: () => terrainRandomize() }, '随机').name('🎲 随机种子');
    render.add({ 重置: () => terrainReset() }, '重置').name('↩️ 重置参数');
    render.open();

    return () => gui.destroy();
  }, [
    noiseType, amplitude, frequency, octaves, persistence, lacunarity, seed,
    chunkSize, chunks, lodBias, wireframe, showWater, waterLevel, showShadows, autoRotate,
    brushMode, brushSize, brushStrength, tools, erosion, vegetation,
    terrainSet, terrainRandomize, terrainReset, applyErosion, heightmapSet,
  ]);

  return guiRef;
}

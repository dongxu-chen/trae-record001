import { useSceneStore } from '../../store/useSceneStore';

export function Lights() {
  const { lights } = useSceneStore();

  return (
    <>
      {lights.map((light) => {
        if (light.type === 'ambient') {
          return (
            <ambientLight
              key={light.id}
              color={light.color}
              intensity={light.intensity}
            />
          );
        }
        if (light.type === 'directional') {
          return (
            <directionalLight
              key={light.id}
              color={light.color}
              intensity={light.intensity}
              position={light.position || [5, 5, 5]}
              castShadow
              shadow-mapSize-width={1024}
              shadow-mapSize-height={1024}
            />
          );
        }
        if (light.type === 'point') {
          return (
            <pointLight
              key={light.id}
              color={light.color}
              intensity={light.intensity}
              position={light.position || [0, 3, 0]}
              castShadow
              distance={20}
            />
          );
        }
        return null;
      })}
    </>
  );
}

import * as THREE from 'three';

export interface SampleModel {
  model: THREE.Group;
  animations: THREE.AnimationClip[];
}

interface BoneConfig {
  name: string;
  parent: string | null;
  position: [number, number, number];
  length: number;
  radius: number;
  color: number;
}

const BONE_CONFIGS: BoneConfig[] = [
  { name: 'hips', parent: null, position: [0, 1.2, 0], length: 0.3, radius: 0.25, color: 0x4a90d9 },
  { name: 'spine', parent: 'hips', position: [0, 0.25, 0], length: 0.4, radius: 0.22, color: 0x4a90d9 },
  { name: 'chest', parent: 'spine', position: [0, 0.4, 0], length: 0.35, radius: 0.2, color: 0x4a90d9 },
  { name: 'neck', parent: 'chest', position: [0, 0.35, 0], length: 0.15, radius: 0.08, color: 0xe8c4a0 },
  { name: 'head', parent: 'neck', position: [0, 0.15, 0], length: 0.25, radius: 0.15, color: 0xe8c4a0 },
  { name: 'shoulder.L', parent: 'chest', position: [-0.25, 0.25, 0], length: 0.12, radius: 0.08, color: 0xe8c4a0 },
  { name: 'arm.L', parent: 'shoulder.L', position: [-0.12, 0, 0], length: 0.35, radius: 0.07, color: 0xe8c4a0 },
  { name: 'forearm.L', parent: 'arm.L', position: [-0.35, 0, 0], length: 0.3, radius: 0.06, color: 0xe8c4a0 },
  { name: 'hand.L', parent: 'forearm.L', position: [-0.3, 0, 0], length: 0.08, radius: 0.05, color: 0xe8c4a0 },
  { name: 'shoulder.R', parent: 'chest', position: [0.25, 0.25, 0], length: 0.12, radius: 0.08, color: 0xe8c4a0 },
  { name: 'arm.R', parent: 'shoulder.R', position: [0.12, 0, 0], length: 0.35, radius: 0.07, color: 0xe8c4a0 },
  { name: 'forearm.R', parent: 'arm.R', position: [0.35, 0, 0], length: 0.3, radius: 0.06, color: 0xe8c4a0 },
  { name: 'hand.R', parent: 'forearm.R', position: [0.3, 0, 0], length: 0.08, radius: 0.05, color: 0xe8c4a0 },
  { name: 'thigh.L', parent: 'hips', position: [-0.12, -0.15, 0], length: 0.45, radius: 0.1, color: 0x5a6b7c },
  { name: 'leg.L', parent: 'thigh.L', position: [0, -0.45, 0], length: 0.4, radius: 0.08, color: 0x5a6b7c },
  { name: 'foot.L', parent: 'leg.L', position: [0, -0.4, 0.1], length: 0.15, radius: 0.06, color: 0x3d2817 },
  { name: 'thigh.R', parent: 'hips', position: [0.12, -0.15, 0], length: 0.45, radius: 0.1, color: 0x5a6b7c },
  { name: 'leg.R', parent: 'thigh.R', position: [0, -0.45, 0], length: 0.4, radius: 0.08, color: 0x5a6b7c },
  { name: 'foot.R', parent: 'leg.R', position: [0, -0.4, 0.1], length: 0.15, radius: 0.06, color: 0x3d2817 },
];

function createBones(): Map<string, THREE.Bone> {
  const bones = new Map<string, THREE.Bone>();
  const boneMap = new Map<string, BoneConfig>();

  BONE_CONFIGS.forEach((config) => {
    boneMap.set(config.name, config);
    const bone = new THREE.Bone();
    bone.name = config.name;
    bone.position.set(...config.position);
    bones.set(config.name, bone);
  });

  BONE_CONFIGS.forEach((config) => {
    if (config.parent) {
      const parentBone = bones.get(config.parent);
      const childBone = bones.get(config.name);
      if (parentBone && childBone) {
        parentBone.add(childBone);
      }
    }
  });

  return bones;
}

function createSkinMesh(
  bones: Map<string, THREE.Bone>,
  boneConfig: BoneConfig,
  boneIndex: number
): THREE.Mesh {
  const geometry = new THREE.CylinderGeometry(
    boneConfig.radius,
    boneConfig.radius * 0.8,
    boneConfig.length,
    8
  );

  geometry.rotateX(Math.PI / 2);

  const positionAttribute = geometry.getAttribute('position');
  const skinIndices = new Float32Array(positionAttribute.count * 4);
  const skinWeights = new Float32Array(positionAttribute.count * 4);

  for (let i = 0; i < positionAttribute.count; i++) {
    skinIndices[i * 4] = boneIndex;
    skinIndices[i * 4 + 1] = 0;
    skinIndices[i * 4 + 2] = 0;
    skinIndices[i * 4 + 3] = 0;

    skinWeights[i * 4] = 1.0;
    skinWeights[i * 4 + 1] = 0;
    skinWeights[i * 4 + 2] = 0;
    skinWeights[i * 4 + 3] = 0;
  }

  geometry.setAttribute('skinIndex', new THREE.BufferAttribute(skinIndices, 4));
  geometry.setAttribute('skinWeight', new THREE.BufferAttribute(skinWeights, 4));

  const material = new THREE.MeshStandardMaterial({
    color: boneConfig.color,
    roughness: 0.7,
    metalness: 0.1,
    skinning: true,
  });

  const mesh = new THREE.SkinnedMesh(geometry, material);
  const bone = bones.get(boneConfig.name);
  if (bone) {
    mesh.bind(new THREE.Skeleton([bone]));
    bone.add(mesh);
  }

  return mesh;
}

function createWalkAnimation(bones: Map<string, THREE.Bone>): THREE.AnimationClip {
  const duration = 1.0;
  const tracks: THREE.KeyframeTrack[] = [];
  const amplitude = Math.PI / 6;
  const hipAmplitude = 0.08;

  const walkCycle = (phase: number) => ({
    thigh: Math.sin(phase) * amplitude,
    leg: Math.abs(Math.sin(phase)) * amplitude * 0.8,
    arm: -Math.sin(phase) * amplitude * 0.7,
    forearm: Math.abs(Math.sin(phase + Math.PI)) * amplitude * 0.5,
  });

  const times = [0, 0.25, 0.5, 0.75, 1.0];

  BONE_CONFIGS.forEach((config) => {
    const bone = bones.get(config.name);
    if (!bone) return;

    const name = config.name;

    if (name === 'hips') {
      const hipY = [
          [0, hipAmplitude, 0, -hipAmplitude, 0],
        ];
      tracks.push(
        new THREE.VectorKeyframeTrack(
          `${name}.position`,
          times,
          hipY.flatMap((y) => [0, y[0], 0])
        )
      );
    }

    if (name === 'thigh.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return walkCycle(phase).thigh;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'thigh.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return walkCycle(phase).thigh;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'leg.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return walkCycle(phase).leg;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'leg.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return walkCycle(phase).leg;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'arm.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return walkCycle(phase).arm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'arm.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return walkCycle(phase).arm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'forearm.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return walkCycle(phase).forearm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'forearm.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return walkCycle(phase).forearm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }
  });

  return new THREE.AnimationClip('walk', duration, tracks);
}

function createRunAnimation(bones: Map<string, THREE.Bone>): THREE.AnimationClip {
  const duration = 0.5;
  const tracks: THREE.KeyframeTrack[] = [];
  const amplitude = Math.PI / 3;
  const hipAmplitude = 0.15;

  const runCycle = (phase: number) => ({
    thigh: Math.sin(phase) * amplitude * 1.5,
    leg: Math.abs(Math.sin(phase)) * amplitude,
    arm: -Math.sin(phase) * amplitude * 1.2,
    forearm: Math.abs(Math.sin(phase + Math.PI)) * amplitude * 0.7,
  });

  const times = [0, 0.125, 0.25, 0.375, 0.5];

  BONE_CONFIGS.forEach((config) => {
    const bone = bones.get(config.name);
    if (!bone) return;

    const name = config.name;

    if (name === 'hips') {
      const hipY = [0, hipAmplitude, 0, -hipAmplitude, 0];
      tracks.push(
        new THREE.VectorKeyframeTrack(
          `${name}.position`,
          times,
          hipY.flatMap((y) => [0, 1.2 + y, 0])
        )
      );
    }

    if (name === 'thigh.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return runCycle(phase).thigh;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'thigh.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return runCycle(phase).thigh;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'leg.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return runCycle(phase).leg;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'leg.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return runCycle(phase).leg;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'arm.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return runCycle(phase).arm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'arm.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return runCycle(phase).arm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'forearm.L') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2;
        return runCycle(phase).forearm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }

    if (name === 'forearm.R') {
      const values = times.map((t) => {
        const phase = (t / duration) * Math.PI * 2 + Math.PI;
        return runCycle(phase).forearm;
      });
      tracks.push(new THREE.QuaternionKeyframeTrack(
        `${name}.quaternion`,
        times,
        values.flatMap((v) => new THREE.Quaternion().setFromEuler(new THREE.Euler(v, 0, 0)).toArray())
      ));
    }
  });

  return new THREE.AnimationClip('run', duration, tracks);
}

export function createSampleModel(): SampleModel {
  const model = new THREE.Group();
  model.name = 'SampleHumanoid';

  const bones = createBones();

  const rootBone = bones.get('hips');
  if (rootBone) {
    model.add(rootBone);
  }

  BONE_CONFIGS.forEach((config, index) => {
    createSkinMesh(bones, config, index);
  });

  const walkClip = createWalkAnimation(bones);
  const runClip = createRunAnimation(bones);

  return {
    model,
    animations: [walkClip, runClip],
  };
}

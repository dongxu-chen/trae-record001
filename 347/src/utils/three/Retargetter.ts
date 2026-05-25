import * as THREE from 'three';

export interface RetargetMapping {
  sourceBoneName: string;
  targetBoneName: string;
  translationWeight: number;
  rotationWeight: number;
  scaleWeight: number;
  mirror?: boolean;
}

export interface RetargetOptions {
  scale: number;
  offset: THREE.Vector3;
  preservePosition: boolean;
  preserveRotation: boolean;
  mirror: boolean;
  boneMapping?: RetargetMapping[];
  hipBoneName?: string;
  rootBoneName?: string;
}

export const DEFAULT_RETARGET_OPTIONS: RetargetOptions = {
  scale: 1,
  offset: new THREE.Vector3(0, 0, 0),
  preservePosition: true,
  preserveRotation: true,
  mirror: false,
};

export const STANDARD_BONE_NAMES = {
  HIPS: ['Hips', 'hip', 'Hip', 'C_Hip', 'c_hip', 'Root', 'root', 'Pelvis', 'pelvis'],
  SPINE: ['Spine', 'spine', 'Spine1', 'SpineA', 'C_Spine_01', 'c_spine_01'],
  CHEST: ['Chest', 'chest', 'Spine2', 'SpineB', 'C_Spine_02', 'c_spine_02'],
  NECK: ['Neck', 'neck', 'C_Neck', 'c_neck'],
  HEAD: ['Head', 'head', 'C_Head', 'c_head'],
  LEFT_SHOULDER: ['LeftShoulder', 'L_Shoulder', 'LeftArm', 'l_shoulder', 'L_Arm'],
  LEFT_ARM: ['LeftArm', 'L_Arm', 'LeftForeArm', 'l_arm'],
  LEFT_FOREARM: ['LeftForeArm', 'L_ForeArm', 'LeftElbow', 'l_elbow'],
  LEFT_HAND: ['LeftHand', 'L_Hand', 'LeftWrist', 'l_wrist'],
  RIGHT_SHOULDER: ['RightShoulder', 'R_Shoulder', 'RightArm', 'r_shoulder', 'R_Arm'],
  RIGHT_ARM: ['RightArm', 'R_Arm', 'RightForeArm', 'r_arm'],
  RIGHT_FOREARM: ['RightForeArm', 'R_ForeArm', 'RightElbow', 'r_elbow'],
  RIGHT_HAND: ['RightHand', 'R_Hand', 'RightWrist', 'r_wrist'],
  LEFT_LEG: ['LeftLeg', 'L_Leg', 'LeftThigh', 'l_thigh', 'LeftUpLeg'],
  LEFT_SHIN: ['LeftShin', 'L_Shin', 'LeftCalf', 'l_calf', 'LeftLeg', 'LeftKnee'],
  LEFT_FOOT: ['LeftFoot', 'L_Foot', 'LeftAnkle', 'l_ankle'],
  RIGHT_LEG: ['RightLeg', 'R_Leg', 'RightThigh', 'r_thigh', 'RightUpLeg'],
  RIGHT_SHIN: ['RightShin', 'R_Shin', 'RightCalf', 'r_calf', 'RightLeg', 'RightKnee'],
  RIGHT_FOOT: ['RightFoot', 'R_Foot', 'RightAnkle', 'r_ankle'],
};

export class BoneMapper {
  static createAutomaticMapping(
    sourceSkeleton: THREE.Skeleton,
    targetSkeleton: THREE.Skeleton
  ): RetargetMapping[] {
    const mapping: RetargetMapping[] = [];

    const sourceBoneNames = sourceSkeleton.bones.map((b) => b.name);
    const targetBoneNames = targetSkeleton.bones.map((b) => b.name);

    const categories: [string[], string[]][] = [
      [STANDARD_BONE_NAMES.HIPS, STANDARD_BONE_NAMES.HIPS],
      [STANDARD_BONE_NAMES.SPINE, STANDARD_BONE_NAMES.SPINE],
      [STANDARD_BONE_NAMES.CHEST, STANDARD_BONE_NAMES.CHEST],
      [STANDARD_BONE_NAMES.NECK, STANDARD_BONE_NAMES.NECK],
      [STANDARD_BONE_NAMES.HEAD, STANDARD_BONE_NAMES.HEAD],
      [STANDARD_BONE_NAMES.LEFT_SHOULDER, STANDARD_BONE_NAMES.LEFT_SHOULDER],
      [STANDARD_BONE_NAMES.LEFT_ARM, STANDARD_BONE_NAMES.LEFT_ARM],
      [STANDARD_BONE_NAMES.LEFT_FOREARM, STANDARD_BONE_NAMES.LEFT_FOREARM],
      [STANDARD_BONE_NAMES.LEFT_HAND, STANDARD_BONE_NAMES.LEFT_HAND],
      [STANDARD_BONE_NAMES.RIGHT_SHOULDER, STANDARD_BONE_NAMES.RIGHT_SHOULDER],
      [STANDARD_BONE_NAMES.RIGHT_ARM, STANDARD_BONE_NAMES.RIGHT_ARM],
      [STANDARD_BONE_NAMES.RIGHT_FOREARM, STANDARD_BONE_NAMES.RIGHT_FOREARM],
      [STANDARD_BONE_NAMES.RIGHT_HAND, STANDARD_BONE_NAMES.RIGHT_HAND],
      [STANDARD_BONE_NAMES.LEFT_LEG, STANDARD_BONE_NAMES.LEFT_LEG],
      [STANDARD_BONE_NAMES.LEFT_SHIN, STANDARD_BONE_NAMES.LEFT_SHIN],
      [STANDARD_BONE_NAMES.LEFT_FOOT, STANDARD_BONE_NAMES.LEFT_FOOT],
      [STANDARD_BONE_NAMES.RIGHT_LEG, STANDARD_BONE_NAMES.RIGHT_LEG],
      [STANDARD_BONE_NAMES.RIGHT_SHIN, STANDARD_BONE_NAMES.RIGHT_SHIN],
      [STANDARD_BONE_NAMES.RIGHT_FOOT, STANDARD_BONE_NAMES.RIGHT_FOOT],
    ];

    categories.forEach(([sourceNames, targetNames]) => {
      const sourceMatch = BoneMapper.findBone(sourceBoneNames, sourceNames);
      const targetMatch = BoneMapper.findBone(targetBoneNames, targetNames);

      if (sourceMatch && targetMatch) {
        mapping.push({
          sourceBoneName: sourceMatch,
          targetBoneName: targetMatch,
          translationWeight: 1,
          rotationWeight: 1,
          scaleWeight: 0,
        });
      }
    });

    const directMatches = BoneMapper.findDirectMatches(sourceBoneNames, targetBoneNames);
    directMatches.forEach((match) => {
      if (!mapping.find((m) => m.sourceBoneName === match.source)) {
        mapping.push({
          sourceBoneName: match.source,
          targetBoneName: match.target,
          translationWeight: 1,
          rotationWeight: 1,
          scaleWeight: 0,
        });
      }
    });

    return mapping;
  }

  private static findBone(
    boneNames: string[],
    candidates: string[]
  ): string | null {
    for (const candidate of candidates) {
      const match = boneNames.find(
        (name) =>
          name.toLowerCase() === candidate.toLowerCase() ||
          name.toLowerCase().includes(candidate.toLowerCase())
      );
      if (match) return match;
    }
    return null;
  }

  private static findDirectMatches(
    sourceNames: string[],
    targetNames: string[]
  ): { source: string; target: string }[] {
    const matches: { source: string; target: string }[] = [];

    sourceNames.forEach((sourceName) => {
      const targetMatch = targetNames.find(
        (targetName) => sourceName.toLowerCase() === targetName.toLowerCase()
      );
      if (targetMatch) {
        matches.push({ source: sourceName, target: targetMatch });
      }
    });

    return matches;
  }
}

export class AnimationRetargetter {
  static retargetClip(
    sourceClip: THREE.AnimationClip,
    sourceSkeleton: THREE.Skeleton,
    targetSkeleton: THREE.Skeleton,
    options: RetargetOptions = DEFAULT_RETARGET_OPTIONS
  ): THREE.AnimationClip {
    const mapping = options.boneMapping ||
      BoneMapper.createAutomaticMapping(sourceSkeleton, targetSkeleton);

    const sourceRootBone = BoneMapper.findRootBone(sourceSkeleton);
    const targetRootBone = BoneMapper.findRootBone(targetSkeleton);

    const sourceBoneMap = new Map(sourceSkeleton.bones.map((b) => [b.name, b]));
    const targetBoneMap = new Map(targetSkeleton.bones.map((b) => [b.name, b]));

    const scaleFactor = options.scale;

    const tracks: THREE.KeyframeTrack[] = [];

    mapping.forEach((boneMapping) => {
      const sourceBone = sourceBoneMap.get(boneMapping.sourceBoneName);
      const targetBone = targetBoneMap.get(boneMapping.targetBoneName);

      if (!sourceBone || !targetBone) return;

      const sourcePath = AnimationRetargetter.getBonePath(sourceBone, sourceRootBone);
      const targetPath = AnimationRetargetter.getBonePath(targetBone, targetRootBone);

      const sourcePositionTrack = sourceClip.tracks.find(
        (t) => t.name === `${sourcePath}.position`
      );
      const sourceQuaternionTrack = sourceClip.tracks.find(
        (t) => t.name === `${sourcePath}.quaternion`
      );
      const sourceScaleTrack = sourceClip.tracks.find(
        (t) => t.name === `${sourcePath}.scale`
      );

      if (boneMapping.translationWeight > 0 && sourcePositionTrack) {
        const times = sourcePositionTrack.times;
        const values = new Float32Array(times.length * 3);

        for (let i = 0; i < times.length; i++) {
          const srcValue = sourcePositionTrack.values;
          let x = srcValue[i * 3] * scaleFactor;
          let y = srcValue[i * 3 + 1] * scaleFactor;
          let z = srcValue[i * 3 + 2] * scaleFactor;

          if (options.mirror || boneMapping.mirror) {
            x = -x;
          }

          x *= boneMapping.translationWeight;
          y *= boneMapping.translationWeight;
          z *= boneMapping.translationWeight;

          const isHip = sourceBone.name.toLowerCase().includes('hip') ||
            sourceBone.name.toLowerCase().includes('pelvis') ||
            sourceBone.name.toLowerCase().includes('root');

          if (!options.preservePosition && !isHip) {
            x = targetBone.position.x;
            y = targetBone.position.y;
            z = targetBone.position.z;
          }

          values[i * 3] = x;
          values[i * 3 + 1] = y;
          values[i * 3 + 2] = z;
        }

        tracks.push(
          new THREE.VectorKeyframeTrack(
            `${targetPath}.position`,
            times,
            values
          )
        );
      }

      if (boneMapping.rotationWeight > 0 && sourceQuaternionTrack) {
        const times = sourceQuaternionTrack.times;
        const values = new Float32Array(times.length * 4);

        for (let i = 0; i < times.length; i++) {
          const srcValue = sourceQuaternionTrack.values;
          let qx = srcValue[i * 4];
          let qy = srcValue[i * 4 + 1];
          let qz = srcValue[i * 4 + 2];
          let qw = srcValue[i * 4 + 3];

          if (options.mirror || boneMapping.mirror) {
            qy = -qy;
            qz = -qz;
          }

          const srcQuat = new THREE.Quaternion(qx, qy, qz, qw);
          const tgtQuat = targetBone.quaternion.clone();

          const finalQuat = tgtQuat.slerp(srcQuat, boneMapping.rotationWeight);

          values[i * 4] = finalQuat.x;
          values[i * 4 + 1] = finalQuat.y;
          values[i * 4 + 2] = finalQuat.z;
          values[i * 4 + 3] = finalQuat.w;
        }

        tracks.push(
          new THREE.QuaternionKeyframeTrack(
            `${targetPath}.quaternion`,
            times,
            values
          )
        );
      }

      if (boneMapping.scaleWeight > 0 && sourceScaleTrack) {
        tracks.push(
          new THREE.VectorKeyframeTrack(
            `${targetPath}.scale`,
            sourceScaleTrack.times,
            sourceScaleTrack.values
          )
        );
      }
    });

    return new THREE.AnimationClip(sourceClip.name, sourceClip.duration, tracks);
  }

  static retargetPose(
    sourceBone: THREE.Bone,
    targetBone: THREE.Bone,
    options: RetargetOptions = DEFAULT_RETARGET_OPTIONS
  ): void {
    const scaleFactor = options.scale;

    targetBone.position.x = sourceBone.position.x * scaleFactor;
    targetBone.position.y = sourceBone.position.y * scaleFactor;
    targetBone.position.z = sourceBone.position.z * scaleFactor;

    if (options.mirror) {
      targetBone.position.x = -targetBone.position.x;
    }

    targetBone.quaternion.copy(sourceBone.quaternion);

    if (options.mirror) {
      targetBone.quaternion.y = -targetBone.quaternion.y;
      targetBone.quaternion.z = -targetBone.quaternion.z;
    }

    targetBone.updateMatrixWorld(true);
  }

  private static findRootBone(skeleton: THREE.Skeleton): THREE.Bone {
    let root = skeleton.bones[0];
    while (root && root.parent && root.parent.type === 'Bone') {
      root = root.parent as THREE.Bone;
    }
    return root;
  }

  private static getBonePath(bone: THREE.Bone, root: THREE.Bone): string {
    if (bone === root) return bone.name;

    const path: string[] = [];
    let current: THREE.Object3D | null = bone;

    while (current && current !== root) {
      path.unshift(current.name);
      current = current.parent;
    }

    if (current) path.unshift(current.name);

    return path.join('/');
  }
}

export class SkeletonUtils {
  static calculateScaleFactor(
    sourceSkeleton: THREE.Skeleton,
    targetSkeleton: THREE.Skeleton
  ): number {
    const sourceHeight = SkeletonUtils.calculateSkeletonHeight(sourceSkeleton);
    const targetHeight = SkeletonUtils.calculateSkeletonHeight(targetSkeleton);

    if (sourceHeight > 0 && targetHeight > 0) {
      return targetHeight / sourceHeight;
    }

    return 1;
  }

  private static calculateSkeletonHeight(skeleton: THREE.Skeleton): number {
    const bounds = new THREE.Box3();

    skeleton.bones.forEach((bone) => {
      const position = new THREE.Vector3();
      bone.getWorldPosition(position);
      bounds.expandByPoint(position);
    });

    return bounds.max.y - bounds.min.y;
  }

  static getBoneHierarchy(skeleton: THREE.Skeleton): {
    root: THREE.Bone;
    levels: THREE.Bone[][];
  } {
    const root = SkeletonUtils.findRootBone(skeleton);
    const levels: THREE.Bone[][] = [];

    const traverse = (bone: THREE.Bone, level: number) => {
      if (!levels[level]) levels[level] = [];
      levels[level].push(bone);

      bone.children.forEach((child) => {
        if (child instanceof THREE.Bone) {
          traverse(child, level + 1);
        }
      });
    };

    traverse(root, 0);

    return { root, levels };
  }

  static findRootBone(skeleton: THREE.Skeleton): THREE.Bone {
    let root = skeleton.bones[0];
    while (root && root.parent && root.parent.type === 'Bone') {
      root = root.parent as THREE.Bone;
    }
    return root;
  }

  static findBoneByName(skeleton: THREE.Skeleton, name: string): THREE.Bone | null {
    const lowerName = name.toLowerCase();
    return skeleton.bones.find(
      (bone) => bone.name.toLowerCase() === lowerName
    ) || null;
  }

  static findBoneByPartialName(skeleton: THREE.Skeleton, partial: string): THREE.Bone | null {
    const lowerPartial = partial.toLowerCase();
    return skeleton.bones.find(
      (bone) => bone.name.toLowerCase().includes(lowerPartial)
    ) || null;
  }
}

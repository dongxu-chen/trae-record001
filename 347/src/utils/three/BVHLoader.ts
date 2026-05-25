import * as THREE from 'three';

export interface BVHJoint {
  name: string;
  offset: THREE.Vector3;
  channels: string[];
  children: BVHJoint[];
  parent: BVHJoint | null;
  endSite?: THREE.Vector3;
}

export interface BVHMotionData {
  frames: number;
  frameTime: number;
  jointData: Map<string, number[][]>;
}

export interface BVHData {
  root: BVHJoint;
  joints: Map<string, BVHJoint>;
  motion: BVHMotionData;
}

export class BVHParser {
  private joints: Map<string, BVHJoint> = new Map();
  private jointOrder: string[] = [];

  parse(content: string): BVHData {
    const lines = content.split('\n').map((l) => l.trim());
    let index = 0;

    while (index < lines.length && !lines[index].toUpperCase().startsWith('HIERARCHY')) {
      index++;
    }

    if (index >= lines.length) {
      throw new Error('Invalid BVH file: Missing HIERARCHY section');
    }

    index++;

    const root = this.parseHierarchy(lines, index, null);
    index = root.parseEndIndex;

    while (index < lines.length && !lines[index].toUpperCase().startsWith('MOTION')) {
      index++;
    }

    if (index >= lines.length) {
      throw new Error('Invalid BVH file: Missing MOTION section');
    }

    index++;

    const framesMatch = lines[index].match(/Frames:\s*(\d+)/i);
    if (!framesMatch) {
      throw new Error('Invalid BVH file: Missing Frames count');
    }
    const frames = parseInt(framesMatch[1], 10);
    index++;

    const frameTimeMatch = lines[index].match(/Frame\s*Time:\s*([\d.]+)/i);
    if (!frameTimeMatch) {
      throw new Error('Invalid BVH file: Missing Frame Time');
    }
    const frameTime = parseFloat(frameTimeMatch[1]);
    index++;

    const motionData = this.parseMotionData(lines, index, frames);

    return {
      root: root.joint,
      joints: this.joints,
      motion: {
        frames,
        frameTime,
        jointData: motionData,
      },
    };
  }

  private parseHierarchy(
    lines: string[],
    startIndex: number,
    parent: BVHJoint | null
  ): { joint: BVHJoint; parseEndIndex: number } {
    let index = startIndex;
    const line = lines[index];

    let jointName = '';
    if (line.toUpperCase().startsWith('ROOT')) {
      jointName = line.replace(/^ROOT\s+/i, '').trim();
    } else if (line.toUpperCase().startsWith('JOINT')) {
      jointName = line.replace(/^JOINT\s+/i, '').trim();
    } else {
      throw new Error(`Expected ROOT or JOINT at line ${index + 1}`);
    }

    const joint: BVHJoint = {
      name: jointName,
      offset: new THREE.Vector3(),
      channels: [],
      children: [],
      parent,
    };

    this.joints.set(jointName, joint);
    this.jointOrder.push(jointName);

    index++;

    if (lines[index] !== '{') {
      throw new Error(`Expected '{' at line ${index + 1}`);
    }
    index++;

    const offsetMatch = lines[index].match(/OFFSET\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)/i);
    if (offsetMatch) {
      joint.offset.set(
        parseFloat(offsetMatch[1]),
        parseFloat(offsetMatch[2]),
        parseFloat(offsetMatch[3])
      );
    }
    index++;

    const channelsMatch = lines[index].match(/CHANNELS\s+(\d+)\s+(.+)/i);
    if (channelsMatch) {
      const channelCount = parseInt(channelsMatch[1], 10);
      joint.channels = channelsMatch[2].trim().split(/\s+/);
      if (joint.channels.length !== channelCount) {
        throw new Error(`Channel count mismatch at line ${index + 1}`);
      }
    }
    index++;

    while (index < lines.length) {
      const currentLine = lines[index];

      if (currentLine.toUpperCase().startsWith('JOINT')) {
        const childResult = this.parseHierarchy(lines, index, joint);
        joint.children.push(childResult.joint);
        index = childResult.parseEndIndex;
      } else if (currentLine.toUpperCase().startsWith('END SITE')) {
        index++;
        if (lines[index] === '{') {
          index++;
        }
        const endOffsetMatch = lines[index].match(/OFFSET\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)/i);
        if (endOffsetMatch) {
          joint.endSite = new THREE.Vector3(
            parseFloat(endOffsetMatch[1]),
            parseFloat(endOffsetMatch[2]),
            parseFloat(endOffsetMatch[3])
          );
        }
        index++;
        if (lines[index] === '}') {
          index++;
        }
      } else if (currentLine === '}') {
        index++;
        break;
      } else {
        index++;
      }
    }

    return { joint, parseEndIndex: index };
  }

  private parseMotionData(
    lines: string[],
    startIndex: number,
    frames: number
  ): Map<string, number[][]> {
    const jointData = new Map<string, number[][]>();
    this.jointOrder.forEach((name) => jointData.set(name, []));

    for (let frame = 0; frame < frames && startIndex + frame < lines.length; frame++) {
      const values = lines[startIndex + frame].trim().split(/\s+/).map(parseFloat);
      let valueIndex = 0;

      for (const jointName of this.jointOrder) {
        const joint = this.joints.get(jointName);
        if (!joint) continue;

        const channelValues: number[] = [];
        for (let c = 0; c < joint.channels.length; c++) {
          channelValues.push(values[valueIndex++]);
        }

        const data = jointData.get(jointName)!;
        data[frame] = channelValues;
      }
    }

    return jointData;
  }
}

export class BVHConverter {
  private static readonly CHANNEL_MAP: Record<string, number> = {
    XPOSITION: 0,
    YPOSITION: 1,
    ZPOSITION: 2,
    ZROTATION: 5,
    XROTATION: 3,
    YROTATION: 4,
  };

  static toSkeleton(
    bvhData: BVHData,
    scale: number = 0.01
  ): { root: THREE.Bone; skeleton: THREE.Skeleton } {
    const boneMap = new Map<string, THREE.Bone>();

    const createBone = (joint: BVHJoint, parentBone: THREE.Bone | null): THREE.Bone => {
      const bone = new THREE.Bone();
      bone.name = joint.name;
      bone.position.set(
        joint.offset.x * scale,
        joint.offset.y * scale,
        joint.offset.z * scale
      );

      if (parentBone) {
        parentBone.add(bone);
      }

      boneMap.set(joint.name, bone);

      joint.children.forEach((child) => {
        createBone(child, bone);
      });

      return bone;
    };

    const rootBone = createBone(bvhData.root, null);
    const skeleton = new THREE.Skeleton(Array.from(boneMap.values()));

    return { root: rootBone, skeleton };
  }

  static toAnimationClip(
    bvhData: BVHData,
    scale: number = 0.01
  ): THREE.AnimationClip {
    const { root, motion, joints } = bvhData;
    const tracks: THREE.KeyframeTrack[] = [];
    const { frames, frameTime, jointData } = motion;

    const times = new Float32Array(frames);
    for (let i = 0; i < frames; i++) {
      times[i] = i * frameTime;
    }

    const processJoint = (joint: BVHJoint, path: string) => {
      const data = jointData.get(joint.name);
      if (!data || data.length === 0) return;

      const positionValues = new Float32Array(frames * 3);
      const quaternionValues = new Float32Array(frames * 4);

      for (let frame = 0; frame < frames; frame++) {
        const frameData = data[frame] || [];

        let px = joint.offset.x;
        let py = joint.offset.y;
        let pz = joint.offset.z;
        let rx = 0, ry = 0, rz = 0;

        joint.channels.forEach((channel, i) => {
          const value = frameData[i] ?? 0;
          switch (channel.toUpperCase()) {
            case 'XPOSITION': px = value; break;
            case 'YPOSITION': py = value; break;
            case 'ZPOSITION': pz = value; break;
            case 'XROTATION': rx = THREE.MathUtils.degToRad(value); break;
            case 'YROTATION': ry = THREE.MathUtils.degToRad(value); break;
            case 'ZROTATION': rz = THREE.MathUtils.degToRad(value); break;
          }
        });

        positionValues[frame * 3] = px * scale;
        positionValues[frame * 3 + 1] = py * scale;
        positionValues[frame * 3 + 2] = pz * scale;

        const euler = new THREE.Euler(rx, ry, rz, 'XYZ');
        const quat = new THREE.Quaternion().setFromEuler(euler);
        quaternionValues[frame * 4] = quat.x;
        quaternionValues[frame * 4 + 1] = quat.y;
        quaternionValues[frame * 4 + 2] = quat.z;
        quaternionValues[frame * 4 + 3] = quat.w;
      }

      const hasPositionData = joint.channels.some((c) =>
        c.toUpperCase().includes('POSITION')
      );

      if (hasPositionData) {
        tracks.push(
          new THREE.VectorKeyframeTrack(
            `${path}.position`,
            times,
            positionValues
          )
        );
      }

      tracks.push(
        new THREE.QuaternionKeyframeTrack(
          `${path}.quaternion`,
          times,
          quaternionValues
        )
      );

      joint.children.forEach((child) => {
        processJoint(child, `${path}/${child.name}`);
      });
    };

    processJoint(root, root.name);

    return new THREE.AnimationClip('BVH Animation', -1, tracks);
  }

  static getJointNames(bvhData: BVHData): string[] {
    const names: string[] = [];
    const traverse = (joint: BVHJoint) => {
      names.push(joint.name);
      joint.children.forEach(traverse);
    };
    traverse(bvhData.root);
    return names;
  }

  static getFrameData(
    bvhData: BVHData,
    frameIndex: number
  ): Map<string, { position: THREE.Vector3; rotation: THREE.Euler }> {
    const result = new Map<string, { position: THREE.Vector3; rotation: THREE.Euler }>();
    const { motion, joints } = bvhData;

    const traverse = (joint: BVHJoint) => {
      const data = motion.jointData.get(joint.name);
      if (data && data[frameIndex]) {
        const frameData = data[frameIndex];
        let px = joint.offset.x;
        let py = joint.offset.y;
        let pz = joint.offset.z;
        let rx = 0, ry = 0, rz = 0;

        joint.channels.forEach((channel, i) => {
          const value = frameData[i] ?? 0;
          switch (channel.toUpperCase()) {
            case 'XPOSITION': px = value; break;
            case 'YPOSITION': py = value; break;
            case 'ZPOSITION': pz = value; break;
            case 'XROTATION': rx = value; break;
            case 'YROTATION': ry = value; break;
            case 'ZROTATION': rz = value; break;
          }
        });

        result.set(joint.name, {
          position: new THREE.Vector3(px, py, pz),
          rotation: new THREE.Euler(
            THREE.MathUtils.degToRad(rx),
            THREE.MathUtils.degToRad(ry),
            THREE.MathUtils.degToRad(rz),
            'XYZ'
          ),
        });
      }

      joint.children.forEach(traverse);
    };

    traverse(bvhData.root);
    return result;
  }
}

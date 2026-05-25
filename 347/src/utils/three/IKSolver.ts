import * as THREE from 'three';

export interface IKChain {
  bones: THREE.Bone[];
  target: THREE.Vector3;
  poleTarget?: THREE.Vector3;
  maxIterations: number;
  tolerance: number;
  poleAngle?: number;
}

export interface IKConstraint {
  bone: THREE.Bone;
  minAngle: THREE.Euler;
  maxAngle: THREE.Euler;
}

export class IKSolver {
  private static readonly UP_VECTOR = new THREE.Vector3(0, 1, 0);

  static solveFABRIK(
    chain: IKChain,
    constraints: IKConstraint[] = []
  ): boolean {
    const { bones, target, maxIterations = 10, tolerance = 0.001 } = chain;

    if (bones.length < 2) return false;

    const bonePositions: THREE.Vector3[] = [];
    const boneLengths: number[] = [];

    bones.forEach((bone, i) => {
      bonePositions.push(bone.position.clone());
      if (i < bones.length - 1) {
        boneLengths.push(
          bones[i + 1].position.distanceTo(bones[i].position)
        );
      }
    });

    const worldPositions: THREE.Vector3[] = bones.map((bone) => {
      const worldPos = new THREE.Vector3();
      bone.getWorldPosition(worldPos);
      return worldPos;
    });

    const totalLength = boneLengths.reduce((a, b) => a + b, 0);
    const rootPos = worldPositions[0].clone();
    const targetDistance = target.distanceTo(rootPos);

    if (targetDistance > totalLength) {
      const direction = target.clone().sub(rootPos).normalize();
      for (let i = 0; i < bones.length - 1; i++) {
        worldPositions[i + 1] = worldPositions[i]
          .clone()
          .add(direction.clone().multiplyScalar(boneLengths[i]));
      }
    } else {
      let distance = worldPositions[worldPositions.length - 1].distanceTo(target);
      let iteration = 0;

      while (distance > tolerance && iteration < maxIterations) {
        worldPositions[worldPositions.length - 1] = target.clone();

        for (let i = worldPositions.length - 2; i >= 0; i--) {
          const current = worldPositions[i];
          const next = worldPositions[i + 1];
          const direction = next.clone().sub(current).normalize();
          worldPositions[i] = next
            .clone()
            .sub(direction.clone().multiplyScalar(boneLengths[i]));
        }

        worldPositions[0] = rootPos.clone();

        for (let i = 0; i < worldPositions.length - 1; i++) {
          const current = worldPositions[i];
          const next = worldPositions[i + 1];
          const direction = next.clone().sub(current).normalize();
          worldPositions[i + 1] = current
            .clone()
            .add(direction.clone().multiplyScalar(boneLengths[i]));
        }

        distance = worldPositions[worldPositions.length - 1].distanceTo(target);
        iteration++;
      }
    }

    if (chain.poleTarget && bones.length >= 3) {
      this.applyPoleConstraint(worldPositions, chain.poleTarget, boneLengths);
    }

    this.applyConstraints(worldPositions, bones, constraints);

    for (let i = 0; i < bones.length - 1; i++) {
      const currentLocal = new THREE.Vector3();
      const nextLocal = new THREE.Vector3();

      if (i === 0) {
        bones[i].parent?.worldToLocal(currentLocal.copy(worldPositions[i]));
        bones[i].position.copy(currentLocal);
      }

      bones[i].parent?.worldToLocal(nextLocal.copy(worldPositions[i + 1]));
      const direction = nextLocal
        .clone()
        .sub(bones[i].position)
        .normalize();

      const quaternion = new THREE.Quaternion();
      quaternion.setFromUnitVectors(this.UP_VECTOR, direction);
      bones[i].quaternion.copy(quaternion);
    }

    return worldPositions[worldPositions.length - 1].distanceTo(target) <= tolerance;
  }

  static solveCCD(
    chain: IKChain,
    constraints: IKConstraint[] = []
  ): boolean {
    const { bones, target, maxIterations = 30, tolerance = 0.001 } = chain;

    if (bones.length < 2) return false;

    const endEffector = bones[bones.length - 1];
    let iteration = 0;
    let distance = Infinity;

    while (distance > tolerance && iteration < maxIterations) {
      for (let i = bones.length - 2; i >= 0; i--) {
        const bone = bones[i];
        const endPos = new THREE.Vector3();
        const targetPos = target.clone();
        const bonePos = new THREE.Vector3();

        endEffector.getWorldPosition(endPos);
        bone.getWorldPosition(bonePos);

        const toEnd = endPos.clone().sub(bonePos).normalize();
        const toTarget = targetPos.clone().sub(bonePos).normalize();

        const rotationAxis = new THREE.Vector3().crossVectors(toEnd, toTarget).normalize();
        const rotationAngle = Math.acos(
          Math.max(-1, Math.min(1, toEnd.dot(toTarget)))
        );

        if (rotationAngle > 0.0001) {
          const rotation = new THREE.Quaternion().setFromAxisAngle(
            rotationAxis,
            rotationAngle
          );

          const currentQuat = bone.quaternion.clone();
          bone.quaternion.premultiply(rotation);

          const constraint = constraints.find((c) => c.bone === bone);
          if (constraint) {
            this.enforceConstraint(bone, constraint);
          }

          bone.updateMatrixWorld(true);
        }
      }

      const currentEndPos = new THREE.Vector3();
      endEffector.getWorldPosition(currentEndPos);
      distance = currentEndPos.distanceTo(target);
      iteration++;
    }

    return distance <= tolerance;
  }

  private static applyPoleConstraint(
    positions: THREE.Vector3[],
    poleTarget: THREE.Vector3,
    lengths: number[]
  ): void {
    if (positions.length < 3) return;

    const root = positions[0];
    const mid = positions[1];
    const end = positions[positions.length - 1];

    const toEnd = end.clone().sub(root);
    const planeNormal = toEnd.clone().normalize();

    const projectedMid = mid.clone().sub(
      planeNormal.clone().multiplyScalar(mid.clone().sub(root).dot(planeNormal))
    );
    const projectedPole = poleTarget.clone().sub(
      planeNormal.clone().multiplyScalar(poleTarget.clone().sub(root).dot(planeNormal))
    );

    const toMid = projectedMid.clone().sub(root);
    const toPole = projectedPole.clone().sub(root);

    const angle = Math.atan2(
      toPole.x * toMid.z - toPole.z * toMid.x,
      toPole.x * toMid.x + toPole.z * toMid.z
    );

    const rotation = new THREE.Quaternion().setFromAxisAngle(
      planeNormal,
      angle
    );

    for (let i = 1; i < positions.length; i++) {
      const relative = positions[i].clone().sub(root);
      relative.applyQuaternion(rotation);
      positions[i] = root.clone().add(relative);
    }
  }

  private static applyConstraints(
    positions: THREE.Vector3[],
    bones: THREE.Bone[],
    constraints: IKConstraint[]
  ): void {
    constraints.forEach((constraint) => {
      const index = bones.indexOf(constraint.bone);
      if (index >= 0 && index < positions.length - 1) {
        this.enforceConstraint(bones[index], constraint);
      }
    });
  }

  private static enforceConstraint(
    bone: THREE.Bone,
    constraint: IKConstraint
  ): void {
    const euler = new THREE.Euler().setFromQuaternion(
      bone.quaternion,
      'XYZ'
    );

    euler.x = Math.max(
      constraint.minAngle.x,
      Math.min(constraint.maxAngle.x, euler.x)
    );
    euler.y = Math.max(
      constraint.minAngle.y,
      Math.min(constraint.maxAngle.y, euler.y)
    );
    euler.z = Math.max(
      constraint.minAngle.z,
      Math.min(constraint.maxAngle.z, euler.z)
    );

    bone.quaternion.setFromEuler(euler);
  }

  static createFootIKChain(
    bones: THREE.Bone[],
    groundTarget: THREE.Vector3,
    poleTarget?: THREE.Vector3
  ): IKChain {
    return {
      bones,
      target: groundTarget,
      poleTarget,
      maxIterations: 15,
      tolerance: 0.001,
    };
  }

  static createHandIKChain(
    bones: THREE.Bone[],
    handTarget: THREE.Vector3,
    poleTarget?: THREE.Vector3
  ): IKChain {
    return {
      bones,
      target: handTarget,
      poleTarget,
      maxIterations: 15,
      tolerance: 0.001,
    };
  }

  static createKneeConstraint(bone: THREE.Bone): IKConstraint {
    return {
      bone,
      minAngle: new THREE.Euler(0, 0, -0.1),
      maxAngle: new THREE.Euler(0, 0, Math.PI * 0.9),
    };
  }

  static createElbowConstraint(bone: THREE.Bone): IKConstraint {
    return {
      bone,
      minAngle: new THREE.Euler(0, 0, -Math.PI * 0.9),
      maxAngle: new THREE.Euler(0, 0, 0.1),
    };
  }
}

export class IKController {
  private ikTargets: Map<string, {
    chain: IKChain;
    constraints: IKConstraint[];
    enabled: boolean;
  }> = new Map();

  addTarget(
    id: string,
    chain: IKChain,
    constraints: IKConstraint[] = []
  ): void {
    this.ikTargets.set(id, { chain, constraints, enabled: true });
  }

  removeTarget(id: string): void {
    this.ikTargets.delete(id);
  }

  setTargetEnabled(id: string, enabled: boolean): void {
    const target = this.ikTargets.get(id);
    if (target) {
      target.enabled = enabled;
    }
  }

  setTargetPosition(id: string, position: THREE.Vector3): void {
    const target = this.ikTargets.get(id);
    if (target) {
      target.chain.target.copy(position);
    }
  }

  solveAll(): void {
    this.ikTargets.forEach(({ chain, constraints, enabled }) => {
      if (enabled) {
        IKSolver.solveFABRIK(chain, constraints);
      }
    });
  }

  solve(id: string): void {
    const target = this.ikTargets.get(id);
    if (target && target.enabled) {
      IKSolver.solveFABRIK(target.chain, target.constraints);
    }
  }
}

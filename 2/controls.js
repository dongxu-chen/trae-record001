import * as THREE from 'three';

export class MoleculeControls {
    constructor(camera, orbitControls) {
        this.camera = camera;
        this.orbitControls = orbitControls;

        this.initialCameraPosition = camera.position.clone();
        this.initialTarget = orbitControls.target.clone();
        this._tempVector = new THREE.Vector3();
    }

    centerOnMolecule(molecule) {
        if (!molecule || !molecule.atoms || molecule.atoms.length === 0) {
            this.reset();
            return;
        }

        const atoms = molecule.atoms;

        const boundingBox = this.calculateBoundingBox(atoms);
        const center = this.calculateCenter(boundingBox);
        const size = this.calculateSize(boundingBox);

        const maxDimension = Math.max(size.x, Math.max(size.y, size.z));
        const distance = this.calculateOptimalDistance(maxDimension);

        const minDist = this.orbitControls.minDistance || 0.1;
        const maxDist = this.orbitControls.maxDistance || Infinity;
        const clampedDistance = Math.max(minDist, Math.min(maxDist, distance));

        this.orbitControls.target.copy(center);

        const direction = this._tempVector.copy(this.camera.position)
            .sub(this.orbitControls.target)
            .normalize();

        this.camera.position.copy(center)
            .add(direction.multiplyScalar(clampedDistance));

        this.orbitControls.update();
    }

    calculateBoundingBox(atoms) {
        let minX = Infinity, minY = Infinity, minZ = Infinity;
        let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

        for (const atom of atoms) {
            const pos = atom.position;
            minX = Math.min(minX, pos.x);
            minY = Math.min(minY, pos.y);
            minZ = Math.min(minZ, pos.z);
            maxX = Math.max(maxX, pos.x);
            maxY = Math.max(maxY, pos.y);
            maxZ = Math.max(maxZ, pos.z);
        }

        return {
            min: new THREE.Vector3(minX, minY, minZ),
            max: new THREE.Vector3(maxX, maxY, maxZ)
        };
    }

    calculateCenter(boundingBox) {
        return new THREE.Vector3(
            (boundingBox.min.x + boundingBox.max.x) / 2,
            (boundingBox.min.y + boundingBox.max.y) / 2,
            (boundingBox.min.z + boundingBox.max.z) / 2
        );
    }

    calculateSize(boundingBox) {
        return new THREE.Vector3(
            boundingBox.max.x - boundingBox.min.x,
            boundingBox.max.y - boundingBox.min.y,
            boundingBox.max.z - boundingBox.min.z
        );
    }

    calculateOptimalDistance(maxDimension) {
        const fov = this.camera.fov * (Math.PI / 180);
        const aspect = this.camera.aspect;

        const halfFov = fov / 2;
        const halfSize = maxDimension / 2;

        let distance = halfSize / Math.tan(halfFov);

        if (aspect < 1) {
            distance = distance / aspect;
        }

        distance = distance * 1.5;

        return Math.max(distance, 5);
    }

    _clampDistance() {
        const minDist = this.orbitControls.minDistance || 0.1;
        const maxDist = this.orbitControls.maxDistance || Infinity;

        const offset = this._tempVector.copy(this.camera.position)
            .sub(this.orbitControls.target);

        let distance = offset.length();

        if (distance < minDist) {
            distance = minDist;
        } else if (distance > maxDist) {
            distance = maxDist;
        } else {
            return;
        }

        offset.normalize().multiplyScalar(distance);
        this.camera.position.copy(this.orbitControls.target).add(offset);
    }

    reset() {
        this.camera.position.copy(this.initialCameraPosition);
        this.orbitControls.target.copy(this.initialTarget);
        this._clampDistance();
        this.orbitControls.update();
    }

    setAutoRotate(enabled) {
        this.orbitControls.autoRotate = enabled;
    }

    setAutoRotateSpeed(speed) {
        this.orbitControls.autoRotateSpeed = speed;
    }

    zoomIn(amount = 0.1) {
        const offset = this._tempVector.copy(this.camera.position)
            .sub(this.orbitControls.target);

        const currentDistance = offset.length();
        const minDist = this.orbitControls.minDistance || 0.1;

        const targetDistance = currentDistance * (1 - amount);

        if (targetDistance >= minDist) {
            this.camera.position.copy(this.orbitControls.target)
                .add(offset.normalize().multiplyScalar(targetDistance));
        } else {
            this.camera.position.copy(this.orbitControls.target)
                .add(offset.normalize().multiplyScalar(minDist));
        }

        this.orbitControls.update();
    }

    zoomOut(amount = 0.1) {
        const offset = this._tempVector.copy(this.camera.position)
            .sub(this.orbitControls.target);

        const currentDistance = offset.length();
        const maxDist = this.orbitControls.maxDistance || Infinity;

        const targetDistance = currentDistance * (1 + amount);

        if (targetDistance <= maxDist) {
            this.camera.position.copy(this.orbitControls.target)
                .add(offset.normalize().multiplyScalar(targetDistance));
        } else {
            this.camera.position.copy(this.orbitControls.target)
                .add(offset.normalize().multiplyScalar(maxDist));
        }

        this.orbitControls.update();
    }

    pan(x, y) {
        const panSpeed = 0.002;
        const panX = x * panSpeed * (this.camera.position.z / 10);
        const panY = y * panSpeed * (this.camera.position.z / 10);

        const right = this._tempVector;
        const up = new THREE.Vector3();

        this.camera.getWorldDirection(right);
        right.crossVectors(this.camera.up, right).normalize();
        up.copy(this.camera.up);

        const offset = new THREE.Vector3();
        offset.addScaledVector(right, -panX);
        offset.addScaledVector(up, panY);

        this.camera.position.add(offset);
        this.orbitControls.target.add(offset);
        this.orbitControls.update();
    }

    setTarget(x, y, z) {
        this.orbitControls.target.set(x, y, z);
        this._clampDistance();
        this.orbitControls.update();
    }

    setCameraPosition(x, y, z) {
        this.camera.position.set(x, y, z);
        this._clampDistance();
        this.orbitControls.update();
    }

    setMinDistance(distance) {
        this.orbitControls.minDistance = distance;
        this._clampDistance();
        this.orbitControls.update();
    }

    setMaxDistance(distance) {
        this.orbitControls.maxDistance = distance;
        this._clampDistance();
        this.orbitControls.update();
    }

    setZoomSpeed(speed) {
        this.orbitControls.zoomSpeed = speed;
    }

    setRotateSpeed(speed) {
        this.orbitControls.rotateSpeed = speed;
    }

    setPanSpeed(speed) {
        this.orbitControls.panSpeed = speed;
    }

    enableDamping(enabled) {
        this.orbitControls.enableDamping = enabled;
    }

    setDampingFactor(factor) {
        this.orbitControls.dampingFactor = factor;
    }
}

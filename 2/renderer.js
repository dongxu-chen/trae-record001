import * as THREE from 'three';
import { VoxelShader, SliceShader } from './voxel_shader.js';

const BASE_ATOM_RADIUS = 1.0;
const BASE_BOND_RADIUS = 0.1;
const BASE_BOND_LENGTH = 1.0;
const UP_VECTOR = new THREE.Vector3(0, 1, 0);

export class MoleculeRenderer {
    constructor(scene) {
        this.scene = scene;
        this.moleculeGroup = new THREE.Group();
        this.atomMeshes = [];
        this.bondMeshes = [];
        this.atomScale = 1.0;
        this.bondScale = 1.0;
        this.atomsVisible = true;
        this.bondsVisible = true;
        this._tempVector1 = new THREE.Vector3();
        this._tempVector2 = new THREE.Vector3();
        this._tempQuaternion = new THREE.Quaternion();

        this.scene.add(this.moleculeGroup);

        this._atomGeometry = null;
        this._bondGeometry = null;
        this._atomMaterialCache = new Map();

        this._voxelEnabled = false;
        this._voxelMesh = null;
        this._voxelTexture = null;
        this._voxelMaterial = null;
        this._voxelVolume = null;

        this._isoValue = 0.5;
        this._voxelOpacity = 0.8;
        this._voxelColor = new THREE.Color(0x00ff88);
        this._voxelVisible = true;
    }

    _getAtomGeometry() {
        if (!this._atomGeometry) {
            this._atomGeometry = new THREE.SphereGeometry(BASE_ATOM_RADIUS, 32, 32);
        }
        return this._atomGeometry;
    }

    _getBondGeometry() {
        if (!this._bondGeometry) {
            this._bondGeometry = new THREE.CylinderGeometry(
                BASE_BOND_RADIUS,
                BASE_BOND_RADIUS,
                BASE_BOND_LENGTH,
                16
            );
        }
        return this._bondGeometry;
    }

    _getAtomMaterial(color) {
        let material = this._atomMaterialCache.get(color);
        if (!material) {
            material = new THREE.MeshPhongMaterial({
                color: color,
                shininess: 80,
                specular: 0x333333,
                flatShading: false
            });
            this._atomMaterialCache.set(color, material);
        }
        return material;
    }

    render(molecule) {
        this.clear();

        const { atoms, bonds, volume } = molecule;

        this._createAtomMeshes(atoms);
        this._createBondMeshes(atoms, bonds);

        if (volume) {
            this._createVoxelRendering(volume);
        }

        this.updateVisibility();
    }

    _createAtomMeshes(atoms) {
        const geometry = this._getAtomGeometry();

        for (const atom of atoms) {
            const material = this._getAtomMaterial(atom.color);
            const mesh = new THREE.Mesh(geometry, material);

            mesh.position.set(
                atom.position.x,
                atom.position.y,
                atom.position.z
            );

            const scale = atom.radius * this.atomScale;
            mesh.scale.set(scale, scale, scale);

            mesh.userData = {
                atom: atom,
                baseScale: atom.radius
            };

            this.atomMeshes.push(mesh);
            this.moleculeGroup.add(mesh);
        }
    }

    _createBondMeshes(atoms, bonds) {
        const geometry = this._getBondGeometry();

        for (const bond of bonds) {
            const atom1 = atoms[bond.atom1Index];
            const atom2 = atoms[bond.atom2Index];

            const mesh = this._createBondMesh(atom1, atom2, geometry);
            this.bondMeshes.push(mesh);
            this.moleculeGroup.add(mesh);
        }
    }

    _createBondMesh(atom1, atom2, geometry) {
        const start = this._tempVector1.set(
            atom1.position.x,
            atom1.position.y,
            atom1.position.z
        );

        const end = this._tempVector2.set(
            atom2.position.x,
            atom2.position.y,
            atom2.position.z
        );

        const direction = this._tempVector1.copy(end).sub(start);
        const length = direction.length();

        const material = new THREE.MeshPhongMaterial({
            color: 0xaaaaaa,
            shininess: 40,
            specular: 0x222222,
            flatShading: false
        });

        const mesh = new THREE.Mesh(geometry, material);

        const midpoint = this._tempVector1.copy(start).add(end).multiplyScalar(0.5);
        mesh.position.copy(midpoint);

        mesh.scale.set(
            this.bondScale,
            length,
            this.bondScale
        );

        direction.normalize();
        this._tempQuaternion.setFromUnitVectors(UP_VECTOR, direction);
        mesh.quaternion.copy(this._tempQuaternion);

        mesh.userData = {
            atom1,
            atom2,
            length
        };

        return mesh;
    }

    _createVoxelRendering(volume) {
        this._clearVoxel();
        this._voxelVolume = volume;

        const { data, size, spacing, origin } = volume;

        let normalizedData;
        if (volume.minValue !== volume.maxValue) {
            normalizedData = new Float32Array(data.length);
            const range = volume.maxValue - volume.minValue;
            for (let i = 0; i < data.length; i++) {
                normalizedData[i] = (data[i] - volume.minValue) / range;
            }
        } else {
            normalizedData = data;
        }

        this._voxelTexture = new THREE.Data3DTexture(
            normalizedData,
            size.x,
            size.y,
            size.z
        );
        this._voxelTexture.format = THREE.RedFormat;
        this._voxelTexture.type = THREE.FloatType;
        this._voxelTexture.minFilter = THREE.LinearFilter;
        this._voxelTexture.magFilter = THREE.LinearFilter;
        this._voxelTexture.unpackAlignment = 1;
        this._voxelTexture.needsUpdate = true;

        const uniforms = THREE.UniformsUtils.clone(VoxelShader.uniforms);
        uniforms.volumeData.value = this._voxelTexture;
        uniforms.volumeSize.value.set(size.x, size.y, size.z);
        uniforms.volumeSpacing.value.set(spacing.x, spacing.y, spacing.z);
        uniforms.volumeOrigin.value.set(origin.x, origin.y, origin.z);
        uniforms.isoValue.value = this._isoValue;
        uniforms.color.value.copy(this._voxelColor);
        uniforms.opacity.value = this._voxelOpacity;

        this._voxelMaterial = new THREE.ShaderMaterial({
            uniforms: uniforms,
            vertexShader: VoxelShader.vertexShader,
            fragmentShader: VoxelShader.fragmentShader,
            transparent: true,
            side: THREE.BackSide,
            depthWrite: false
        });

        const boxWidth = size.x * spacing.x;
        const boxHeight = size.y * spacing.y;
        const boxDepth = size.z * spacing.z;

        const boxGeometry = new THREE.BoxGeometry(boxWidth, boxHeight, boxDepth);

        this._voxelMesh = new THREE.Mesh(boxGeometry, this._voxelMaterial);

        const centerX = origin.x + boxWidth / 2;
        const centerY = origin.y + boxHeight / 2;
        const centerZ = origin.z + boxDepth / 2;
        this._voxelMesh.position.set(centerX, centerY, centerZ);

        this._voxelMesh.visible = this._voxelVisible;
        this._voxelEnabled = true;

        this.moleculeGroup.add(this._voxelMesh);
    }

    _clearVoxel() {
        if (this._voxelMesh) {
            this.moleculeGroup.remove(this._voxelMesh);
            this._voxelMesh.geometry.dispose();
            this._voxelMesh = null;
        }

        if (this._voxelTexture) {
            this._voxelTexture.dispose();
            this._voxelTexture = null;
        }

        if (this._voxelMaterial) {
            this._voxelMaterial.dispose();
            this._voxelMaterial = null;
        }

        this._voxelVolume = null;
        this._voxelEnabled = false;
    }

    setAtomScale(scale) {
        this.atomScale = scale;
        for (const mesh of this.atomMeshes) {
            const baseScale = mesh.userData.baseScale;
            const newScale = baseScale * scale;
            mesh.scale.set(newScale, newScale, newScale);
        }
    }

    setBondScale(scale) {
        this.bondScale = scale;
        for (const mesh of this.bondMeshes) {
            mesh.scale.x = scale;
            mesh.scale.z = scale;
        }
    }

    setIsoValue(value) {
        this._isoValue = value;
        if (this._voxelMaterial && this._voxelMaterial.uniforms) {
            this._voxelMaterial.uniforms.isoValue.value = value;
        }
    }

    getIsoValue() {
        return this._isoValue;
    }

    setVoxelOpacity(value) {
        this._voxelOpacity = value;
        if (this._voxelMaterial && this._voxelMaterial.uniforms) {
            this._voxelMaterial.uniforms.opacity.value = value;
        }
    }

    getVoxelOpacity() {
        return this._voxelOpacity;
    }

    setVoxelColor(hexColor) {
        this._voxelColor.setHex(hexColor);
        if (this._voxelMaterial && this._voxelMaterial.uniforms) {
            this._voxelMaterial.uniforms.color.value.copy(this._voxelColor);
        }
    }

    updateVoxelCamera(cameraPosition) {
        if (this._voxelMaterial && this._voxelMaterial.uniforms) {
            this._voxelMaterial.uniforms.cameraPos.value.copy(cameraPosition);
        }
    }

    updateVoxelLight(lightPosition) {
        if (this._voxelMaterial && this._voxelMaterial.uniforms) {
            this._voxelMaterial.uniforms.lightPos.value.copy(lightPosition);
        }
    }

    showAtoms(visible) {
        this.atomsVisible = visible;
        this.updateVisibility();
    }

    showBonds(visible) {
        this.bondsVisible = visible;
        this.updateVisibility();
    }

    showVoxel(visible) {
        this._voxelVisible = visible;
        if (this._voxelMesh) {
            this._voxelMesh.visible = visible;
        }
    }

    isVoxelEnabled() {
        return this._voxelEnabled;
    }

    updateVisibility() {
        for (const mesh of this.atomMeshes) {
            mesh.visible = this.atomsVisible;
        }
        for (const mesh of this.bondMeshes) {
            mesh.visible = this.bondsVisible;
        }
    }

    clear() {
        for (const mesh of this.atomMeshes) {
            this.moleculeGroup.remove(mesh);
            if (Array.isArray(mesh.material)) {
                mesh.material.forEach(m => m.dispose());
            }
        }
        this.atomMeshes = [];

        for (const mesh of this.bondMeshes) {
            this.moleculeGroup.remove(mesh);
            if (Array.isArray(mesh.material)) {
                mesh.material.forEach(m => m.dispose());
            } else {
                mesh.material.dispose();
            }
        }
        this.bondMeshes = [];

        this._clearVoxel();
    }

    dispose() {
        this.clear();

        if (this._atomGeometry) {
            this._atomGeometry.dispose();
            this._atomGeometry = null;
        }

        if (this._bondGeometry) {
            this._bondGeometry.dispose();
            this._bondGeometry = null;
        }

        for (const material of this._atomMaterialCache.values()) {
            material.dispose();
        }
        this._atomMaterialCache.clear();

        this.scene.remove(this.moleculeGroup);
    }
}

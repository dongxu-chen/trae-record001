class SceneNode {
    constructor(name = "Node") {
        this.id = SceneNode.nextId++;
        this.name = name;
        this.parent = null;
        this.children = [];
        
        this.translation = [0, 0, 0];
        this.rotation = [0, 0, 0, 1];
        this.scale = [1, 1, 1];
        this.matrix = MathUtils.mat4Identity();
        this.worldMatrix = MathUtils.mat4Identity();
        
        this.meshes = [];
        this.visible = true;
        this.pickable = true;
        this.userData = {};
    }

    setTranslation(x, y, z) {
        this.translation = [x, y, z];
        this.updateMatrix();
    }

    setRotationEuler(x, y, z) {
        const cx = Math.cos(x / 2);
        const sx = Math.sin(x / 2);
        const cy = Math.cos(y / 2);
        const sy = Math.sin(y / 2);
        const cz = Math.cos(z / 2);
        const sz = Math.sin(z / 2);
        
        this.rotation = [
            sx * cy * cz - cx * sy * sz,
            cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz,
            cx * cy * cz + sx * sy * sz
        ];
        this.updateMatrix();
    }

    setScale(x, y, z) {
        this.scale = [x, y, z];
        this.updateMatrix();
    }

    updateMatrix() {
        let m = MathUtils.mat4Identity();
        m = MathUtils.mat4Translate(m, this.translation);
        
        const [rx, ry, rz, rw] = this.rotation;
        const x2 = rx * rx;
        const y2 = ry * ry;
        const z2 = rz * rz;
        const xy = rx * ry;
        const xz = rx * rz;
        const yz = ry * rz;
        const wx = rw * rx;
        const wy = rw * ry;
        const wz = rw * rz;
        
        const rotMatrix = [
            1 - 2 * (y2 + z2), 2 * (xy + wz), 2 * (xz - wy), 0,
            2 * (xy - wz), 1 - 2 * (x2 + z2), 2 * (yz + wx), 0,
            2 * (xz + wy), 2 * (yz - wx), 1 - 2 * (x2 + y2), 0,
            0, 0, 0, 1
        ];
        
        m = MathUtils.mat4Multiply(m, rotMatrix);
        m = MathUtils.mat4Scale(m, this.scale);
        
        this.matrix = m;
        this.updateWorldMatrix();
    }

    updateWorldMatrix() {
        if (this.parent) {
            this.worldMatrix = MathUtils.mat4Multiply(this.parent.worldMatrix, this.matrix);
        } else {
            this.worldMatrix = MathUtils.mat4Copy(this.matrix);
        }
        
        for (const child of this.children) {
            child.updateWorldMatrix();
        }
    }

    addChild(child) {
        if (child.parent) {
            child.parent.removeChild(child);
        }
        child.parent = this;
        this.children.push(child);
        child.updateWorldMatrix();
    }

    removeChild(child) {
        const index = this.children.indexOf(child);
        if (index !== -1) {
            this.children.splice(index, 1);
            child.parent = null;
            child.updateWorldMatrix();
        }
    }

    getChildByName(name) {
        for (const child of this.children) {
            if (child.name === name) return child;
            const found = child.getChildByName(name);
            if (found) return found;
        }
        return null;
    }

    traverse(callback) {
        callback(this);
        for (const child of this.children) {
            child.traverse(callback);
        }
    }

    clone() {
        const clone = new SceneNode(this.name);
        clone.translation = [...this.translation];
        clone.rotation = [...this.rotation];
        clone.scale = [...this.scale];
        clone.matrix = MathUtils.mat4Copy(this.matrix);
        clone.meshes = [...this.meshes];
        clone.visible = this.visible;
        clone.pickable = this.pickable;
        
        for (const child of this.children) {
            clone.addChild(child.clone());
        }
        
        return clone;
    }
}

SceneNode.nextId = 0;

class SceneGraph {
    constructor() {
        this.root = new SceneNode("Root");
        this.nodesById = new Map();
        this.nodesById.set(this.root.id, this.root);
    }

    addNode(node, parent = null) {
        const parentNode = parent || this.root;
        parentNode.addChild(node);
        node.traverse(n => this.nodesById.set(n.id, n));
        return node;
    }

    removeNode(node) {
        if (node.parent) {
            node.parent.removeChild(node);
        }
        node.traverse(n => this.nodesById.delete(n.id));
    }

    getNodeById(id) {
        return this.nodesById.get(id);
    }

    getNodeByName(name) {
        return this.root.getChildByName(name);
    }

    traverse(callback) {
        this.root.traverse(callback);
    }

    getVisibleMeshes() {
        const meshes = [];
        this.traverse(node => {
            if (node.visible && node.meshes.length > 0) {
                for (const mesh of node.meshes) {
                    meshes.push({
                        node,
                        mesh,
                        worldMatrix: node.worldMatrix
                    });
                }
            }
        });
        return meshes;
    }

    getPickableMeshes() {
        const meshes = [];
        this.traverse(node => {
            if (node.visible && node.pickable && node.meshes.length > 0) {
                for (const mesh of node.meshes) {
                    meshes.push({
                        node,
                        mesh,
                        worldMatrix: node.worldMatrix
                    });
                }
            }
        });
        return meshes;
    }

    clear() {
        this.root = new SceneNode("Root");
        this.nodesById.clear();
        this.nodesById.set(this.root.id, this.root);
    }
}

class Mesh {
    constructor(primitives = []) {
        this.primitives = primitives;
    }
}

class Primitive {
    constructor() {
        this.vertexBuffer = null;
        this.indexBuffer = null;
        this.normalBuffer = null;
        this.colorBuffer = null;
        this.texCoordBuffer = null;
        
        this.vertexCount = 0;
        this.indexCount = 0;
        this.drawMode = WebGLRenderingContext.TRIANGLES;
        
        this.material = null;
        this.boundingBox = { min: [0, 0, 0], max: [0, 0, 0] };
    }
}

class Material {
    constructor(options = {}) {
        this.id = Material.nextId++;
        this.name = options.name || `Material_${this.id}`;
        
        this.baseColorFactor = options.baseColorFactor ? [...options.baseColorFactor] : [1, 1, 1, 1];
        this.metallicFactor = options.metallicFactor !== undefined ? options.metallicFactor : 0;
        this.roughnessFactor = options.roughnessFactor !== undefined ? options.roughnessFactor : 1;
        this.emissiveFactor = options.emissiveFactor ? [...options.emissiveFactor] : [0, 0, 0];
        
        this.baseColorTexture = options.baseColorTexture || null;
        this.metallicRoughnessTexture = options.metallicRoughnessTexture || null;
        this.normalTexture = options.normalTexture || null;
        this.emissiveTexture = options.emissiveTexture || null;
        
        this.doubleSided = options.doubleSided || false;
        this.wireframe = options.wireframe || false;
        
        this.alphaMode = options.alphaMode || 'OPAQUE';
        this.alphaCutoff = options.alphaCutoff !== undefined ? options.alphaCutoff : 0.5;
        
        this.normalScale = options.normalScale !== undefined ? options.normalScale : 1;
        this.emissiveStrength = options.emissiveStrength !== undefined ? options.emissiveStrength : 1;
        this.occlusionStrength = options.occlusionStrength !== undefined ? options.occlusionStrength : 1;
        
        this.userData = {};
        this._onChange = null;
    }

    onChanged(callback) {
        this._onChange = callback;
    }

    _notifyChanged() {
        if (this._onChange) {
            this._onChange(this);
        }
    }

    setBaseColor(r, g, b, a = 1) {
        this.baseColorFactor = [r, g, b, a];
        this._notifyChanged();
        return this;
    }

    setMetallic(value) {
        this.metallicFactor = MathUtils.clamp(value, 0, 1);
        this._notifyChanged();
        return this;
    }

    setRoughness(value) {
        this.roughnessFactor = MathUtils.clamp(value, 0, 1);
        this._notifyChanged();
        return this;
    }

    setEmissive(r, g, b) {
        this.emissiveFactor = [r, g, b];
        this._notifyChanged();
        return this;
    }

    setDoubleSided(value) {
        this.doubleSided = !!value;
        this._notifyChanged();
        return this;
    }

    setWireframe(value) {
        this.wireframe = !!value;
        this._notifyChanged();
        return this;
    }

    setAlphaMode(mode) {
        this.alphaMode = mode;
        this._notifyChanged();
        return this;
    }

    setAlphaCutoff(value) {
        this.alphaCutoff = value;
        this._notifyChanged();
        return this;
    }

    setNormalScale(value) {
        this.normalScale = value;
        this._notifyChanged();
        return this;
    }

    setEmissiveStrength(value) {
        this.emissiveStrength = value;
        this._notifyChanged();
        return this;
    }

    clone() {
        return new Material({
            name: this.name + '_copy',
            baseColorFactor: [...this.baseColorFactor],
            metallicFactor: this.metallicFactor,
            roughnessFactor: this.roughnessFactor,
            emissiveFactor: [...this.emissiveFactor],
            doubleSided: this.doubleSided,
            wireframe: this.wireframe,
            alphaMode: this.alphaMode,
            alphaCutoff: this.alphaCutoff,
            normalScale: this.normalScale,
            emissiveStrength: this.emissiveStrength,
            occlusionStrength: this.occlusionStrength,
            baseColorTexture: this.baseColorTexture,
            metallicRoughnessTexture: this.metallicRoughnessTexture,
            normalTexture: this.normalTexture,
            emissiveTexture: this.emissiveTexture
        });
    }

    toJSON() {
        return {
            name: this.name,
            baseColorFactor: [...this.baseColorFactor],
            metallicFactor: this.metallicFactor,
            roughnessFactor: this.roughnessFactor,
            emissiveFactor: [...this.emissiveFactor],
            doubleSided: this.doubleSided,
            wireframe: this.wireframe,
            alphaMode: this.alphaMode,
            alphaCutoff: this.alphaCutoff,
            normalScale: this.normalScale,
            emissiveStrength: this.emissiveStrength,
            occlusionStrength: this.occlusionStrength
        };
    }

    fromJSON(json) {
        if (json.name) this.name = json.name;
        if (json.baseColorFactor) this.baseColorFactor = [...json.baseColorFactor];
        if (json.metallicFactor !== undefined) this.metallicFactor = json.metallicFactor;
        if (json.roughnessFactor !== undefined) this.roughnessFactor = json.roughnessFactor;
        if (json.emissiveFactor) this.emissiveFactor = [...json.emissiveFactor];
        if (json.doubleSided !== undefined) this.doubleSided = json.doubleSided;
        if (json.wireframe !== undefined) this.wireframe = json.wireframe;
        if (json.alphaMode) this.alphaMode = json.alphaMode;
        if (json.alphaCutoff !== undefined) this.alphaCutoff = json.alphaCutoff;
        if (json.normalScale !== undefined) this.normalScale = json.normalScale;
        if (json.emissiveStrength !== undefined) this.emissiveStrength = json.emissiveStrength;
        if (json.occlusionStrength !== undefined) this.occlusionStrength = json.occlusionStrength;
        this._notifyChanged();
        return this;
    }
}

Material.nextId = 0;

Material.Presets = {
    Standard: () => new Material({
        name: 'Standard',
        baseColorFactor: [1, 1, 1, 1],
        metallicFactor: 0,
        roughnessFactor: 1
    }),

    Metal: () => new Material({
        name: 'Metal',
        baseColorFactor: [0.9, 0.9, 0.9, 1],
        metallicFactor: 1,
        roughnessFactor: 0.2
    }),

    Plastic: () => new Material({
        name: 'Plastic',
        baseColorFactor: [0.8, 0.2, 0.2, 1],
        metallicFactor: 0,
        roughnessFactor: 0.5
    }),

    Glass: () => new Material({
        name: 'Glass',
        baseColorFactor: [0.9, 0.95, 1, 0.7],
        metallicFactor: 0,
        roughnessFactor: 0.05,
        alphaMode: 'BLEND'
    }),

    Rubber: () => new Material({
        name: 'Rubber',
        baseColorFactor: [0.15, 0.15, 0.18, 1],
        metallicFactor: 0,
        roughnessFactor: 0.95
    }),

    Gold: () => new Material({
        name: 'Gold',
        baseColorFactor: [1.0, 0.766, 0.336, 1],
        metallicFactor: 1,
        roughnessFactor: 0.3
    }),

    Chrome: () => new Material({
        name: 'Chrome',
        baseColorFactor: [0.9, 0.9, 0.95, 1],
        metallicFactor: 1,
        roughnessFactor: 0.05
    }),

    Wood: () => new Material({
        name: 'Wood',
        baseColorFactor: [0.6, 0.35, 0.2, 1],
        metallicFactor: 0,
        roughnessFactor: 0.8
    })
};

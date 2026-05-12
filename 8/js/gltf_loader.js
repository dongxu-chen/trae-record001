class GLTFLoader {
    constructor(gl) {
        this.gl = gl;
        this.basePath = '';
        this._textures = new Map();
        this._images = new Map();
    }

    async loadFromFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    if (file.name.endsWith('.glb')) {
                        const scene = await this.parseGLB(e.target.result);
                        resolve(scene);
                    } else {
                        const json = JSON.parse(e.target.result);
                        this.basePath = file.name.substring(0, file.name.lastIndexOf('/') + 1);
                        const scene = await this.parseJSON(json);
                        resolve(scene);
                    }
                } catch (err) {
                    reject(err);
                }
            };
            reader.onerror = reject;
            reader.readAsArrayBuffer(file);
        });
    }

    async parseGLB(buffer) {
        const dataView = new DataView(buffer);
        const magic = dataView.getUint32(0, true);
        if (magic !== 0x46546C67) {
            throw new Error('Invalid GLB magic number');
        }

        let offset = 12;
        let jsonChunks = [];
        let binaryChunk = null;

        while (offset < buffer.byteLength) {
            const chunkLength = dataView.getUint32(offset, true);
            const chunkType = dataView.getUint32(offset + 4, true);
            offset += 8;

            const chunkData = buffer.slice(offset, offset + chunkLength);
            offset += chunkLength;

            if (chunkType === 0x4E4F534A) {
                jsonChunks.push(new TextDecoder('utf-8').decode(chunkData));
            } else if (chunkType === 0x004E4942) {
                binaryChunk = chunkData;
            }
        }

        const json = JSON.parse(jsonChunks.join(''));
        return await this.parseJSON(json, binaryChunk);
    }

    async parseJSON(json, binaryBuffer = null) {
        this._textures.clear();
        this._images.clear();

        const buffers = [];
        
        for (let i = 0; i < (json.buffers || []).length; i++) {
            const buffer = json.buffers[i];
            if (buffer.uri) {
                if (buffer.uri.startsWith('data:')) {
                    const base64 = buffer.uri.split(',')[1];
                    const binary = atob(base64);
                    const bytes = new Uint8Array(binary.length);
                    for (let j = 0; j < binary.length; j++) {
                        bytes[j] = binary.charCodeAt(j);
                    }
                    buffers[i] = bytes.buffer;
                } else if (binaryBuffer) {
                    buffers[i] = binaryBuffer;
                }
            } else if (binaryBuffer) {
                buffers[i] = binaryBuffer;
            }
        }

        const bufferViews = [];
        for (const view of (json.bufferViews || [])) {
            bufferViews.push({
                buffer: buffers[view.buffer],
                byteOffset: view.byteOffset || 0,
                byteLength: view.byteLength,
                byteStride: view.byteStride || 0,
                target: view.target
            });
        }

        const accessors = [];
        for (const acc of (json.accessors || [])) {
            const view = bufferViews[acc.bufferView || 0];
            accessors.push({
                ...acc,
                view
            });
        }

        await this._loadImages(json, binaryBuffer);
        await this._loadTextures(json);
        const materials = await this._loadMaterials(json);

        const meshes = [];
        for (const m of (json.meshes || [])) {
            const mesh = new Mesh();
            for (const p of m.primitives) {
                const primitive = new Primitive();
                
                const positionAcc = accessors[p.attributes.POSITION];
                if (positionAcc) {
                    const positions = this.readAccessor(positionAcc);
                    primitive.vertexBuffer = WebGLUtils.createBuffer(this.gl, positions);
                    primitive.vertexCount = positionAcc.count;
                    
                    primitive.boundingBox = {
                        min: positionAcc.min ? positionAcc.min.slice() : [0, 0, 0],
                        max: positionAcc.max ? positionAcc.max.slice() : [0, 0, 0]
                    };
                }

                if (p.attributes.NORMAL !== undefined) {
                    const normalAcc = accessors[p.attributes.NORMAL];
                    const normals = this.readAccessor(normalAcc);
                    primitive.normalBuffer = WebGLUtils.createBuffer(this.gl, normals);
                }

                if (p.attributes.TEXCOORD_0 !== undefined) {
                    const uvAcc = accessors[p.attributes.TEXCOORD_0];
                    const uvs = this.readAccessor(uvAcc);
                    primitive.texCoordBuffer = WebGLUtils.createBuffer(this.gl, uvs);
                }

                if (p.attributes.COLOR_0 !== undefined) {
                    const colorAcc = accessors[p.attributes.COLOR_0];
                    const colors = this.readAccessor(colorAcc);
                    primitive.colorBuffer = WebGLUtils.createBuffer(this.gl, colors);
                }

                if (p.indices !== undefined) {
                    const indexAcc = accessors[p.indices];
                    const indices = this.readAccessor(indexAcc);
                    primitive.indexBuffer = WebGLUtils.createBuffer(
                        this.gl, indices, 
                        this.gl.ELEMENT_ARRAY_BUFFER
                    );
                    primitive.indexCount = indexAcc.count;
                }

                if (p.material !== undefined) {
                    primitive.material = materials[p.material];
                } else {
                    primitive.material = new Material();
                }

                primitive.drawMode = p.mode !== undefined ? p.mode : this.gl.TRIANGLES;
                mesh.primitives.push(primitive);
            }
            meshes.push(mesh);
        }

        const nodes = [];
        for (const n of (json.nodes || [])) {
            const node = new SceneNode(n.name || `Node_${nodes.length}`);
            
            if (n.matrix) {
                node.matrix = n.matrix.slice();
                const trs = MathUtils.decomposeTRS(node.matrix);
                node.translation = trs.translation;
                node.scale = trs.scale;
            } else {
                if (n.translation) node.translation = n.translation.slice();
                if (n.rotation) node.rotation = n.rotation.slice();
                if (n.scale) node.scale = n.scale.slice();
                node.updateMatrix();
            }

            if (n.mesh !== undefined) {
                node.meshes = [meshes[n.mesh]];
            }

            nodes.push(node);
        }

        for (let i = 0; i < nodes.length; i++) {
            const jsonNode = json.nodes[i];
            if (jsonNode.children) {
                for (const childIndex of jsonNode.children) {
                    nodes[i].addChild(nodes[childIndex]);
                }
            }
        }

        const scene = new SceneGraph();
        const sceneIndex = json.scene || 0;
        const sceneData = json.scenes ? json.scenes[sceneIndex] : null;
        
        if (sceneData && sceneData.nodes) {
            for (const rootIndex of sceneData.nodes) {
                scene.addNode(nodes[rootIndex]);
            }
        } else if (nodes.length > 0) {
            scene.addNode(nodes[0]);
        }

        return scene;
    }

    async _loadImages(json, binaryBuffer) {
        const gl = this.gl;
        const imagePromises = [];

        for (let i = 0; i < (json.images || []).length; i++) {
            const imageData = json.images[i];
            
            const promise = new Promise(async (resolve) => {
                let imageSource = null;

                if (imageData.bufferView !== undefined) {
                    const bufferView = json.bufferViews[imageData.bufferView];
                    const buffer = binaryBuffer;
                    const byteOffset = bufferView.byteOffset || 0;
                    const byteLength = bufferView.byteLength;
                    
                    const view = new Uint8Array(buffer, byteOffset, byteLength);
                    const blob = new Blob([view], { type: imageData.mimeType || 'image/png' });
                    imageSource = URL.createObjectURL(blob);
                } else if (imageData.uri) {
                    if (imageData.uri.startsWith('data:')) {
                        imageSource = imageData.uri;
                    } else {
                        imageSource = this.basePath + imageData.uri;
                    }
                }

                if (imageSource) {
                    try {
                        const img = await this._loadImageElement(imageSource);
                        const texture = gl.createTexture();
                        gl.bindTexture(gl.TEXTURE_2D, texture);
                        
                        const level = 0;
                        const internalFormat = gl.RGBA;
                        const srcFormat = gl.RGBA;
                        const srcType = gl.UNSIGNED_BYTE;
                        
                        gl.bindTexture(gl.TEXTURE_2D, texture);
                        gl.texImage2D(gl.TEXTURE_2D, level, internalFormat, srcFormat, srcType, img);
                        
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
                        gl.generateMipmap(gl.TEXTURE_2D);
                        
                        this._images.set(i, { texture, image: img, loaded: true });
                    } catch (err) {
                        console.warn(`Failed to load image ${i}:`, err);
                        this._images.set(i, { texture: null, loaded: false });
                    }
                } else {
                    this._images.set(i, { texture: null, loaded: false });
                }
                
                resolve();
            });
            
            imagePromises.push(promise);
        }

        await Promise.all(imagePromises);
    }

    _loadImageElement(src) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = src;
        });
    }

    async _loadTextures(json) {
        for (let i = 0; i < (json.textures || []).length; i++) {
            const textureData = json.textures[i];
            const imageIndex = textureData.source !== undefined ? textureData.source : textureData.source;
            
            if (imageIndex !== undefined && this._images.has(imageIndex)) {
                const image = this._images.get(imageIndex);
                this._textures.set(i, {
                    texture: image.texture,
                    sampler: textureData.sampler,
                    loaded: image.loaded
                });
            } else {
                this._textures.set(i, { texture: null, loaded: false });
            }
        }
    }

    async _loadMaterials(json) {
        const materials = [];
        
        for (const mat of (json.materials || [])) {
            const material = new Material();
            
            if (mat.pbrMetallicRoughness) {
                const pbr = mat.pbrMetallicRoughness;
                
                if (pbr.baseColorFactor) {
                    material.baseColorFactor = pbr.baseColorFactor.slice();
                }
                
                material.metallicFactor = pbr.metallicFactor !== undefined ? pbr.metallicFactor : 0;
                material.roughnessFactor = pbr.roughnessFactor !== undefined ? pbr.roughnessFactor : 1;
                
                if (pbr.baseColorTexture && pbr.baseColorTexture.index !== undefined) {
                    const textureInfo = this._textures.get(pbr.baseColorTexture.index);
                    if (textureInfo && textureInfo.texture) {
                        material.baseColorTexture = textureInfo.texture;
                    }
                }
                
                if (pbr.metallicRoughnessTexture && pbr.metallicRoughnessTexture.index !== undefined) {
                    const textureInfo = this._textures.get(pbr.metallicRoughnessTexture.index);
                    if (textureInfo && textureInfo.texture) {
                        material.metallicRoughnessTexture = textureInfo.texture;
                    }
                }
            }
            
            if (mat.normalTexture && mat.normalTexture.index !== undefined) {
                const textureInfo = this._textures.get(mat.normalTexture.index);
                if (textureInfo && textureInfo.texture) {
                    material.normalTexture = textureInfo.texture;
                }
            }
            
            if (mat.emissiveTexture && mat.emissiveTexture.index !== undefined) {
                const textureInfo = this._textures.get(mat.emissiveTexture.index);
                if (textureInfo && textureInfo.texture) {
                    material.emissiveTexture = textureInfo.texture;
                }
            }
            
            if (mat.emissiveFactor) {
                material.emissiveFactor = mat.emissiveFactor.slice();
            }
            
            if (mat.doubleSided) {
                material.doubleSided = true;
            }
            
            if (mat.alphaMode) {
                material.alphaMode = mat.alphaMode;
                material.alphaCutoff = mat.alphaCutoff !== undefined ? mat.alphaCutoff : 0.5;
            }
            
            materials.push(material);
        }
        
        return materials;
    }

    readAccessor(accessor) {
        const { view, componentType, type, count } = accessor;
        const byteOffset = accessor.byteOffset || 0;
        
        if (!view || !view.buffer) {
            return new Float32Array(count * (type === 'SCALAR' ? 1 : type === 'VEC2' ? 2 : type === 'VEC3' ? 3 : 4));
        }
        
        let TypedArray;
        let componentSize;
        switch (componentType) {
            case 5120: TypedArray = Int8Array; componentSize = 1; break;
            case 5121: TypedArray = Uint8Array; componentSize = 1; break;
            case 5122: TypedArray = Int16Array; componentSize = 2; break;
            case 5123: TypedArray = Uint16Array; componentSize = 2; break;
            case 5125: TypedArray = Uint32Array; componentSize = 4; break;
            case 5126: TypedArray = Float32Array; componentSize = 4; break;
            default: TypedArray = Float32Array; componentSize = 4;
        }

        let componentCount;
        switch (type) {
            case 'SCALAR': componentCount = 1; break;
            case 'VEC2': componentCount = 2; break;
            case 'VEC3': componentCount = 3; break;
            case 'VEC4': componentCount = 4; break;
            case 'MAT2': componentCount = 4; break;
            case 'MAT3': componentCount = 9; break;
            case 'MAT4': componentCount = 16; break;
            default: componentCount = 1;
        }

        const byteStride = view.byteStride || componentSize * componentCount;
        const data = new TypedArray(count * componentCount);
        const sourceBuffer = new Uint8Array(view.buffer);
        
        for (let i = 0; i < count; i++) {
            const offset = view.byteOffset + byteOffset + i * byteStride;
            const componentData = new TypedArray(
                sourceBuffer.buffer,
                sourceBuffer.byteOffset + offset,
                componentCount
            );
            for (let j = 0; j < componentCount; j++) {
                data[i * componentCount + j] = componentData[j];
            }
        }

        return data;
    }

    createPrimitiveGeometry(gl, type) {
        const mesh = new Mesh();
        const primitive = new Primitive();
        primitive.material = new Material();

        let positions, indices, normals;

        switch (type) {
            case 'cube':
                positions = new Float32Array([
                    -1, -1,  1,  1, -1,  1,  1,  1,  1, -1,  1,  1,
                    -1, -1, -1, -1,  1, -1,  1,  1, -1,  1, -1, -1,
                    -1,  1, -1, -1,  1,  1,  1,  1,  1,  1,  1, -1,
                    -1, -1, -1,  1, -1, -1,  1, -1,  1, -1, -1,  1,
                     1, -1, -1,  1,  1, -1,  1,  1,  1,  1, -1,  1,
                    -1, -1, -1, -1, -1,  1, -1,  1,  1, -1,  1, -1
                ]);
                normals = new Float32Array([
                    0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1,
                    0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1,
                    0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0,
                    0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0,
                    1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0,
                    -1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0
                ]);
                indices = new Uint16Array([
                    0, 1, 2, 0, 2, 3,
                    4, 5, 6, 4, 6, 7,
                    8, 9, 10, 8, 10, 11,
                    12, 13, 14, 12, 14, 15,
                    16, 17, 18, 16, 18, 19,
                    20, 21, 22, 20, 22, 23
                ]);
                primitive.boundingBox = { min: [-1, -1, -1], max: [1, 1, 1] };
                break;

            case 'sphere':
                const latBands = 32;
                const lonBands = 32;
                positions = [];
                normals = [];
                indices = [];
                
                for (let lat = 0; lat <= latBands; lat++) {
                    const theta = lat * Math.PI / latBands;
                    const sinTheta = Math.sin(theta);
                    const cosTheta = Math.cos(theta);
                    
                    for (let lon = 0; lon <= lonBands; lon++) {
                        const phi = lon * 2 * Math.PI / lonBands;
                        const sinPhi = Math.sin(phi);
                        const cosPhi = Math.cos(phi);
                        
                        const x = cosPhi * sinTheta;
                        const y = cosTheta;
                        const z = sinPhi * sinTheta;
                        
                        positions.push(x, y, z);
                        normals.push(x, y, z);
                    }
                }
                
                for (let lat = 0; lat < latBands; lat++) {
                    for (let lon = 0; lon < lonBands; lon++) {
                        const first = lat * (lonBands + 1) + lon;
                        const second = first + lonBands + 1;
                        indices.push(first, second, first + 1);
                        indices.push(second, second + 1, first + 1);
                    }
                }
                positions = new Float32Array(positions);
                normals = new Float32Array(normals);
                indices = new Uint16Array(indices);
                primitive.boundingBox = { min: [-1, -1, -1], max: [1, 1, 1] };
                break;

            case 'plane':
                positions = new Float32Array([-1, 0, -1, 1, 0, -1, 1, 0, 1, -1, 0, 1]);
                normals = new Float32Array([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]);
                indices = new Uint16Array([0, 1, 2, 0, 2, 3]);
                primitive.boundingBox = { min: [-1, 0, -1], max: [1, 0, 1] };
                break;

            case 'cylinder':
                const radialSegments = 32;
                const heightSegments = 1;
                positions = [];
                normals = [];
                indices = [];
                
                for (let y = 0; y <= heightSegments; y++) {
                    const yPos = -1 + (y / heightSegments) * 2;
                    for (let i = 0; i <= radialSegments; i++) {
                        const angle = (i / radialSegments) * Math.PI * 2;
                        const x = Math.cos(angle);
                        const z = Math.sin(angle);
                        positions.push(x, yPos, z);
                        normals.push(x, 0, z);
                    }
                }
                
                for (let y = 0; y < heightSegments; y++) {
                    for (let i = 0; i < radialSegments; i++) {
                        const a = y * (radialSegments + 1) + i;
                        const b = a + radialSegments + 1;
                        indices.push(a, b, a + 1, b, b + 1, a + 1);
                    }
                }
                positions = new Float32Array(positions);
                normals = new Float32Array(normals);
                indices = new Uint16Array(indices);
                primitive.boundingBox = { min: [-1, -1, -1], max: [1, 1, 1] };
                break;

            default:
                positions = new Float32Array([-1, -1, 0, 1, -1, 0, 0, 1, 0]);
                indices = new Uint16Array([0, 1, 2]);
                normals = new Float32Array([0, 0, 1, 0, 0, 1, 0, 0, 1]);
                primitive.boundingBox = { min: [-1, -1, 0], max: [1, 1, 0] };
        }

        primitive.vertexBuffer = WebGLUtils.createBuffer(gl, positions);
        primitive.normalBuffer = WebGLUtils.createBuffer(gl, normals);
        primitive.indexBuffer = WebGLUtils.createBuffer(gl, indices, gl.ELEMENT_ARRAY_BUFFER);
        primitive.vertexCount = positions.length / 3;
        primitive.indexCount = indices.length;
        mesh.primitives.push(primitive);

        return mesh;
    }
}

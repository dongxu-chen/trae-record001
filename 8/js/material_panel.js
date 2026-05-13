class MaterialPanel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = containerId;
            this.container.className = 'material-panel';
        }
        
        this.currentMaterial = null;
        this.currentNode = null;
        this.currentPrimitive = null;
        this.onMaterialChanged = null;
        
        this._buildUI();
    }

    _buildUI() {
        this.container.innerHTML = `
            <div class="material-panel-header">
                <h2>材质编辑器</h2>
                <select id="material-presets" class="material-select">
                    <option value="">应用预设材质...</option>
                    <option value="Standard">Standard</option>
                    <option value="Metal">Metal</option>
                    <option value="Plastic">Plastic</option>
                    <option value="Glass">Glass</option>
                    <option value="Rubber">Rubber</option>
                    <option value="Gold">Gold</option>
                    <option value="Chrome">Chrome</option>
                    <option value="Wood">Wood</option>
                </select>
            </div>
            
            <div class="material-panel-empty" id="material-empty">
                双击物体编辑材质
            </div>
            
            <div class="material-panel-content" id="material-content" style="display: none;">
                <div class="material-section">
                    <h3>基本设置</h3>
                    <div class="property-row">
                        <label>名称</label>
                        <input type="text" id="mat-name">
                    </div>
                </div>
                
                <div class="material-section">
                    <h3>基础颜色 (Base Color)</h3>
                    <div class="color-picker-row">
                        <input type="color" id="mat-basecolor">
                        <input type="number" id="mat-opacity" min="0" max="1" step="0.01" value="1">
                        <span class="label">Alpha</span>
                    </div>
                </div>
                
                <div class="material-section">
                    <h3>金属度 / 粗糙度</h3>
                    <div class="slider-row">
                        <label>金属度 (Metallic)</label>
                        <input type="range" id="mat-metallic" min="0" max="1" step="0.01" value="0">
                        <span class="slider-value" id="mat-metallic-val">0.00</span>
                    </div>
                    <div class="slider-row">
                        <label>粗糙度 (Roughness)</label>
                        <input type="range" id="mat-roughness" min="0" max="1" step="0.01" value="1">
                        <span class="slider-value" id="mat-roughness-val">1.00</span>
                    </div>
                </div>
                
                <div class="material-section">
                    <h3>自发光 (Emissive)</h3>
                    <div class="color-picker-row">
                        <input type="color" id="mat-emissive" value="#000000">
                        <input type="number" id="mat-emissive-strength" min="0" max="10" step="0.1" value="1">
                        <span class="label">强度</span>
                    </div>
                </div>
                
                <div class="material-section">
                    <h3>高级设置</h3>
                    <div class="property-row">
                        <label>双面渲染</label>
                        <input type="checkbox" id="mat-doublesided">
                    </div>
                    <div class="property-row">
                        <label>线框模式</label>
                        <input type="checkbox" id="mat-wireframe">
                    </div>
                    <div class="property-row">
                        <label>透明模式</label>
                        <select id="mat-alphamode">
                            <option value="OPAQUE">OPAQUE (不透明)</option>
                            <option value="MASK">MASK (遮罩)</option>
                            <option value="BLEND">BLEND (混合)</option>
                        </select>
                    </div>
                    <div class="slider-row" id="mat-alphacutoff-row" style="display: none;">
                        <label>Alpha 遮罩阈值</label>
                        <input type="range" id="mat-alphacutoff" min="0" max="1" step="0.01" value="0.5">
                        <span class="slider-value" id="mat-alphacutoff-val">0.50</span>
                    </div>
                </div>
                
                <div class="material-section">
                    <h3>法线贴图</h3>
                    <div class="slider-row">
                        <label>法线强度</label>
                        <input type="range" id="mat-normalscale" min="0" max="2" step="0.01" value="1">
                        <span class="slider-value" id="mat-normalscale-val">1.00</span>
                    </div>
                </div>
                
                <div class="material-actions">
                    <button id="mat-apply-all">应用到选中物体所有图元</button>
                    <button id="mat-clone">复制材质</button>
                    <button id="mat-reset">重置</button>
                </div>
            </div>
        `;
        
        this._cacheElements();
        this._bindEvents();
    }

    _cacheElements() {
        this.emptyState = this.container.querySelector('#material-empty');
        this.content = this.container.querySelector('#material-content');
        
        this.presetsSelect = this.container.querySelector('#material-presets');
        
        this.nameInput = this.container.querySelector('#mat-name');
        this.baseColorInput = this.container.querySelector('#mat-basecolor');
        this.opacityInput = this.container.querySelector('#mat-opacity');
        
        this.metallicSlider = this.container.querySelector('#mat-metallic');
        this.metallicValue = this.container.querySelector('#mat-metallic-val');
        this.roughnessSlider = this.container.querySelector('#mat-roughness');
        this.roughnessValue = this.container.querySelector('#mat-roughness-val');
        
        this.emissiveInput = this.container.querySelector('#mat-emissive');
        this.emissiveStrengthInput = this.container.querySelector('#mat-emissive-strength');
        
        this.doubleSidedInput = this.container.querySelector('#mat-doublesided');
        this.wireframeInput = this.container.querySelector('#mat-wireframe');
        this.alphaModeSelect = this.container.querySelector('#mat-alphamode');
        this.alphaCutoffRow = this.container.querySelector('#mat-alphacutoff-row');
        this.alphaCutoffSlider = this.container.querySelector('#mat-alphacutoff');
        this.alphaCutoffValue = this.container.querySelector('#mat-alphacutoff-val');
        
        this.normalScaleSlider = this.container.querySelector('#mat-normalscale');
        this.normalScaleValue = this.container.querySelector('#mat-normalscale-val');
        
        this.applyAllBtn = this.container.querySelector('#mat-apply-all');
        this.cloneBtn = this.container.querySelector('#mat-clone');
        this.resetBtn = this.container.querySelector('#mat-reset');
    }

    _bindEvents() {
        this.presetsSelect.addEventListener('change', (e) => this._applyPreset(e.target.value));
        
        this.nameInput.addEventListener('input', (e) => this._updateName(e.target.value));
        this.baseColorInput.addEventListener('input', (e) => this._updateBaseColor(e.target.value));
        this.opacityInput.addEventListener('input', (e) => this._updateOpacity(parseFloat(e.target.value)));
        
        this.metallicSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            this.metallicValue.textContent = val.toFixed(2);
            this._updateMetallic(val);
        });
        
        this.roughnessSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            this.roughnessValue.textContent = val.toFixed(2);
            this._updateRoughness(val);
        });
        
        this.emissiveInput.addEventListener('input', (e) => this._updateEmissive(e.target.value));
        this.emissiveStrengthInput.addEventListener('input', (e) => this._updateEmissiveStrength(parseFloat(e.target.value)));
        
        this.doubleSidedInput.addEventListener('change', (e) => this._updateDoubleSided(e.target.checked));
        this.wireframeInput.addEventListener('change', (e) => this._updateWireframe(e.target.checked));
        
        this.alphaModeSelect.addEventListener('change', (e) => {
            this._updateAlphaMode(e.target.value);
            this.alphaCutoffRow.style.display = e.target.value === 'MASK' ? 'flex' : 'none';
        });
        
        this.alphaCutoffSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            this.alphaCutoffValue.textContent = val.toFixed(2);
            this._updateAlphaCutoff(val);
        });
        
        this.normalScaleSlider.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            this.normalScaleValue.textContent = val.toFixed(2);
            this._updateNormalScale(val);
        });
        
        this.applyAllBtn.addEventListener('click', () => this._applyToAllPrimitives());
        this.cloneBtn.addEventListener('click', () => this._cloneMaterial());
        this.resetBtn.addEventListener('click', () => this._resetMaterial());
    }

    _applyPreset(presetName) {
        if (!presetName || !this.currentMaterial || !Material.Presets[presetName]) return;
        
        const preset = Material.Presets[presetName]();
        this.currentMaterial.baseColorFactor = [...preset.baseColorFactor];
        this.currentMaterial.metallicFactor = preset.metallicFactor;
        this.currentMaterial.roughnessFactor = preset.roughnessFactor;
        this.currentMaterial.alphaMode = preset.alphaMode || 'OPAQUE';
        
        this._refreshUI();
        this._notifyChanged();
        this.presetsSelect.value = '';
    }

    _updateName(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.name = value;
        this._notifyChanged();
    }

    _updateBaseColor(hexColor) {
        if (!this.currentMaterial) return;
        const rgb = this._hexToRgb(hexColor);
        this.currentMaterial.baseColorFactor[0] = rgb.r;
        this.currentMaterial.baseColorFactor[1] = rgb.g;
        this.currentMaterial.baseColorFactor[2] = rgb.b;
        this._notifyChanged();
    }

    _updateOpacity(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.baseColorFactor[3] = value;
        this._notifyChanged();
    }

    _updateMetallic(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.metallicFactor = value;
        this._notifyChanged();
    }

    _updateRoughness(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.roughnessFactor = value;
        this._notifyChanged();
    }

    _updateEmissive(hexColor) {
        if (!this.currentMaterial) return;
        const rgb = this._hexToRgb(hexColor);
        this.currentMaterial.emissiveFactor = [rgb.r, rgb.g, rgb.b];
        this._notifyChanged();
    }

    _updateEmissiveStrength(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.emissiveStrength = value;
        this._notifyChanged();
    }

    _updateDoubleSided(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.doubleSided = value;
        this._notifyChanged();
    }

    _updateWireframe(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.wireframe = value;
        this._notifyChanged();
    }

    _updateAlphaMode(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.alphaMode = value;
        this._notifyChanged();
    }

    _updateAlphaCutoff(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.alphaCutoff = value;
        this._notifyChanged();
    }

    _updateNormalScale(value) {
        if (!this.currentMaterial) return;
        this.currentMaterial.normalScale = value;
        this._notifyChanged();
    }

    _applyToAllPrimitives() {
        if (!this.currentNode || !this.currentMaterial) return;
        
        for (const mesh of this.currentNode.meshes) {
            for (const primitive of mesh.primitives) {
                if (primitive.material !== this.currentMaterial) {
                    primitive.material = this.currentMaterial;
                }
            }
        }
        this._notifyChanged();
    }

    _cloneMaterial() {
        if (!this.currentMaterial) return;
        
        const newMaterial = this.currentMaterial.clone();
        this.setMaterial(newMaterial, this.currentNode, this.currentPrimitive);
        
        if (this.currentNode && this.currentNode.meshes.length > 0 && this.currentPrimitive) {
            for (const mesh of this.currentNode.meshes) {
                for (let i = 0; i < mesh.primitives.length; i++) {
                    if (mesh.primitives[i] === this.currentPrimitive) {
                        mesh.primitives[i].material = newMaterial;
                    }
                }
            }
        }
        
        this._notifyChanged();
    }

    _resetMaterial() {
        if (!this.currentMaterial) return;
        
        const defaultMat = new Material();
        this.currentMaterial.baseColorFactor = [...defaultMat.baseColorFactor];
        this.currentMaterial.metallicFactor = defaultMat.metallicFactor;
        this.currentMaterial.roughnessFactor = defaultMat.roughnessFactor;
        this.currentMaterial.emissiveFactor = [...defaultMat.emissiveFactor];
        this.currentMaterial.doubleSided = defaultMat.doubleSided;
        this.currentMaterial.wireframe = defaultMat.wireframe;
        this.currentMaterial.alphaMode = defaultMat.alphaMode;
        this.currentMaterial.alphaCutoff = defaultMat.alphaCutoff;
        this.currentMaterial.normalScale = defaultMat.normalScale;
        this.currentMaterial.emissiveStrength = defaultMat.emissiveStrength;
        
        this._refreshUI();
        this._notifyChanged();
    }

    _hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16) / 255,
            g: parseInt(result[2], 16) / 255,
            b: parseInt(result[3], 16) / 255
        } : { r: 1, g: 1, b: 1 };
    }

    _rgbToHex(r, g, b) {
        const toHex = (c) => {
            const hex = Math.round(MathUtils.clamp(c, 0, 1) * 255).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        };
        return '#' + toHex(r) + toHex(g) + toHex(b);
    }

    _notifyChanged() {
        if (this.currentMaterial) {
            this.currentMaterial._notifyChanged();
        }
        if (this.onMaterialChanged) {
            this.onMaterialChanged(this.currentMaterial, this.currentNode);
        }
    }

    _refreshUI() {
        if (!this.currentMaterial) return;
        
        const m = this.currentMaterial;
        
        this.nameInput.value = m.name;
        this.baseColorInput.value = this._rgbToHex(m.baseColorFactor[0], m.baseColorFactor[1], m.baseColorFactor[2]);
        this.opacityInput.value = m.baseColorFactor[3];
        
        this.metallicSlider.value = m.metallicFactor;
        this.metallicValue.textContent = m.metallicFactor.toFixed(2);
        this.roughnessSlider.value = m.roughnessFactor;
        this.roughnessValue.textContent = m.roughnessFactor.toFixed(2);
        
        this.emissiveInput.value = this._rgbToHex(m.emissiveFactor[0], m.emissiveFactor[1], m.emissiveFactor[2]);
        this.emissiveStrengthInput.value = m.emissiveStrength;
        
        this.doubleSidedInput.checked = m.doubleSided;
        this.wireframeInput.checked = m.wireframe;
        this.alphaModeSelect.value = m.alphaMode;
        this.alphaCutoffRow.style.display = m.alphaMode === 'MASK' ? 'flex' : 'none';
        this.alphaCutoffSlider.value = m.alphaCutoff;
        this.alphaCutoffValue.textContent = m.alphaCutoff.toFixed(2);
        
        this.normalScaleSlider.value = m.normalScale;
        this.normalScaleValue.textContent = m.normalScale.toFixed(2);
    }

    setMaterial(material, node = null, primitive = null) {
        this.currentMaterial = material;
        this.currentNode = node;
        this.currentPrimitive = primitive;
        
        if (material) {
            this.emptyState.style.display = 'none';
            this.content.style.display = 'block';
            this._refreshUI();
        } else {
            this.emptyState.style.display = 'flex';
            this.content.style.display = 'none';
        }
    }

    setMaterialFromNode(node) {
        if (!node || node.meshes.length === 0) {
            this.setMaterial(null);
            return;
        }
        
        const firstPrimitive = node.meshes[0].primitives[0];
        this.setMaterial(firstPrimitive.material, node, firstPrimitive);
    }

    clear() {
        this.setMaterial(null);
    }
}

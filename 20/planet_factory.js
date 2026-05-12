const PlanetFactory = (function() {
    const loadingPromises = [];
    const planetInfo = {
        '太阳': {
            type: '恒星',
            description: '太阳系的中心天体，由氢和氦组成的巨大等离子体球，通过核聚变反应释放能量。',
            facts: [
                '质量：约 1.989 × 10³⁰ kg（占太阳系总质量的 99.86%）',
                '直径：约 1,392,700 km（是地球的 109 倍）',
                '表面温度：约 5,500 °C',
                '核心温度：约 1500 万 °C',
                '年龄：约 46 亿年'
            ],
            color: '#FFA500'
        },
        '水星': {
            type: '行星',
            description: '太阳系中最小且距离太阳最近的行星，没有大气层，表面布满陨石坑。',
            facts: [
                '直径：约 4,879 km',
                '公转周期：约 88 地球日',
                '自转周期：约 58.6 地球日',
                '表面温度：-173 °C 至 427 °C',
                '距离太阳：约 5790 万公里'
            ],
            color: '#8C7853'
        },
        '金星': {
            type: '行星',
            description: '太阳系中最热的行星，拥有浓厚的二氧化碳大气层和强烈的温室效应。',
            facts: [
                '直径：约 12,104 km',
                '公转周期：约 225 地球日',
                '自转周期：约 243 地球日（逆向自转）',
                '表面温度：约 462 °C',
                '大气压力：约地球的 92 倍'
            ],
            color: '#DEB887'
        },
        '地球': {
            type: '行星',
            description: '太阳系中唯一已知存在生命的行星，拥有液态水和适宜的大气层。',
            facts: [
                '直径：约 12,742 km',
                '公转周期：约 365.25 天',
                '自转周期：约 24 小时',
                '表面温度：-88 °C 至 58 °C',
                '卫星：1 个（月球）'
            ],
            color: '#4169E1'
        },
        '火星': {
            type: '行星',
            description: '被称为"红色星球"，因表面富含氧化铁而呈红色，是人类探索的重点目标。',
            facts: [
                '直径：约 6,779 km',
                '公转周期：约 687 地球日',
                '自转周期：约 24.6 小时',
                '表面温度：-87 °C 至 -5 °C',
                '卫星：2 个（火卫一、火卫二）'
            ],
            color: '#CD5C5C'
        },
        '木星': {
            type: '气态巨行星',
            description: '太阳系中最大的行星，是一个由氢和氦组成的气态巨行星，拥有著名的大红斑风暴。',
            facts: [
                '直径：约 139,820 km（是地球的 11 倍）',
                '公转周期：约 11.86 地球年',
                '自转周期：约 9.9 小时（太阳系最快）',
                '卫星数量：已知 95 颗',
                '大红斑：持续 350 多年的巨大风暴'
            ],
            color: '#DAA520'
        },
        '土星': {
            type: '气态巨行星',
            description: '太阳系第二大行星，拥有壮观的行星环系统，主要由冰和岩石碎片组成。',
            facts: [
                '直径：约 116,460 km',
                '公转周期：约 29.46 地球年',
                '自转周期：约 10.7 小时',
                '卫星数量：已知 146 颗（含土卫六）',
                '密度：比水还低（能漂浮在水上）'
            ],
            color: '#F4A460'
        },
        '天王星': {
            type: '冰巨星',
            description: '太阳系中最冷的行星，自转轴几乎与公转轨道平行，呈"躺着"旋转。',
            facts: [
                '直径：约 50,724 km',
                '公转周期：约 84 地球年',
                '自转周期：约 17.2 小时（逆向）',
                '自转轴倾角：约 98°',
                '表面温度：约 -224 °C'
            ],
            color: '#40E0D0'
        },
        '海王星': {
            type: '冰巨星',
            description: '太阳系中距离太阳最远的行星，拥有太阳系中最强的风暴系统。',
            facts: [
                '直径：约 49,244 km',
                '公转周期：约 164.8 地球年',
                '自转周期：约 16.1 小时',
                '风速：可达 2,100 km/h',
                '表面温度：约 -214 °C'
            ],
            color: '#4682B4'
        }
    };

    function create(scene, options) {
        const {
            name = 'Planet',
            size = 1,
            color = '#FFFFFF',
            emissiveColor = null,
            textureUrl = null,
            isStar = false,
            position = BABYLON.Vector3.Zero(),
            segments = 64,
            hasAtmosphere = false,
            atmosphereColor = '#87CEEB',
            atmosphereThickness = 0.15,
            info = null
        } = options;

        const planet = BABYLON.MeshBuilder.CreateSphere(
            name,
            {
                diameter: size * 2,
                segments: segments
            },
            scene
        );
        planet.position = position.clone();
        planet._isPickable = true;
        planet._isPlanet = true;

        const material = new BABYLON.StandardMaterial(`${name}-mat`, scene);
        material.freeze();

        const fallbackColor = hexToColor3(color);
        material.diffuseColor = fallbackColor.clone();

        if (textureUrl) {
            const texture = new BABYLON.Texture(textureUrl, scene, true, false);
            texture.uScale = 1;
            texture.vScale = 1;
            texture.coordinatesMode = BABYLON.Texture.SPHERICAL_MODE;

            const loadPromise = new Promise((resolve) => {
                texture.onLoadObservable.addOnce(() => {
                    material.unfreeze();
                    material.diffuseTexture = texture;
                    material.diffuseColor = new BABYLON.Color3(1, 1, 1);
                    material.freeze();
                    resolve(planet);
                });
                texture.onErrorObservable.addOnce(() => {
                    resolve(planet);
                });
            });

            loadingPromises.push(loadPromise);

            texture.hasAlpha = false;
        }

        if (isStar) {
            material.unfreeze();
            material.emissiveColor = emissiveColor ? hexToColor3(emissiveColor) : fallbackColor.clone();
            material.diffuseColor = new BABYLON.Color3(0, 0, 0);
            material.specularColor = new BABYLON.Color3(0, 0, 0);
            material.disableLighting = true;
            material.freeze();

            const glowLayer = new BABYLON.GlowLayer(`${name}-glow`, scene, {
                mainTextureFixedSize: 128,
                blurKernelSize: 16
            });
            glowLayer.intensity = 1.2;
        } else {
            material.unfreeze();
            material.specularColor = new BABYLON.Color3(0.3, 0.3, 0.3);
            material.specularPower = 64;

            if (emissiveColor) {
                material.emissiveColor = hexToColor3(emissiveColor);
            }
            material.freeze();
        }

        planet.material = material;

        if (hasAtmosphere && !isStar) {
            const atmosphere = BABYLON.MeshBuilder.CreateSphere(
                `${name}-atmosphere`,
                {
                    diameter: (size * 2) * (1 + atmosphereThickness),
                    segments: segments
                },
                scene
            );

            const atmosphereMaterial = new BABYLON.StandardMaterial(`${name}-atmosphere-mat`, scene);
            atmosphereMaterial.diffuseColor = hexToColor3(atmosphereColor);
            atmosphereMaterial.opacity = 0.3;
            atmosphereMaterial.alpha = 0.3;
            atmosphereMaterial.specularColor = new BABYLON.Color3(0, 0, 0);
            atmosphereMaterial.emissiveColor = hexToColor3(atmosphereColor);
            atmosphereMaterial.backFaceCulling = false;

            atmosphere.material = atmosphereMaterial;
            atmosphere.parent = planet;
            atmosphere._isPickable = false;

            planet.atmosphere = atmosphere;
        }

        planet._config = {
            name,
            size,
            color,
            emissiveColor,
            textureUrl,
            isStar,
            segments
        };

        planet._info = info || planetInfo[name] || {
            type: '天体',
            description: `${name} - 一个神秘的天体。`,
            facts: [
                '名称：' + name,
                '类型：未知'
            ],
            color: color
        };

        return planet;
    }

    function waitForAllTextures() {
        return Promise.all(loadingPromises);
    }

    function hexToColor3(hex) {
        let r = 0, g = 0, b = 0;

        if (hex.startsWith('#')) {
            hex = hex.slice(1);
        }

        if (hex.length === 3) {
            r = parseInt(hex[0] + hex[0], 16) / 255;
            g = parseInt(hex[1] + hex[1], 16) / 255;
            b = parseInt(hex[2] + hex[2], 16) / 255;
        } else if (hex.length === 6) {
            r = parseInt(hex.substring(0, 2), 16) / 255;
            g = parseInt(hex.substring(2, 4), 16) / 255;
            b = parseInt(hex.substring(4, 6), 16) / 255;
        }

        return new BABYLON.Color3(r, g, b);
    }

    function createRing(scene, planet, innerRadius, outerRadius, thickness = 0.05, color = '#C4A66A') {
        const ring = BABYLON.MeshBuilder.CreateTorus(
            `${planet.name}-ring`,
            {
                diameter: (innerRadius + outerRadius),
                thickness: thickness,
                tessellation: 128
            },
            scene
        );

        const ringMaterial = new BABYLON.StandardMaterial(`${planet.name}-ring-mat`, scene);
        ringMaterial.diffuseColor = hexToColor3(color);
        ringMaterial.specularColor = new BABYLON.Color3(0.5, 0.5, 0.5);
        ringMaterial.specularPower = 32;

        ring.material = ringMaterial;
        ring.rotation.x = Math.PI / 2;
        ring.parent = planet;
        ring.scaling.y = 0.01;
        ring._isPickable = false;

        return ring;
    }

    function getPlanetInfo(name) {
        return planetInfo[name];
    }

    function setHighlight(mesh, highlight = true) {
        if (!mesh || !mesh.material) return;

        if (highlight) {
            if (!mesh._originalEmissive) {
                mesh._originalEmissive = mesh.material.emissiveColor ? 
                    mesh.material.emissiveColor.clone() : 
                    new BABYLON.Color3(0, 0, 0);
            }
            mesh._highlighted = true;
        } else {
            if (mesh._originalEmissive) {
                mesh.material.emissiveColor = mesh._originalEmissive;
                mesh._originalEmissive = null;
            }
            mesh._highlighted = false;
        }
    }

    return {
        create,
        createRing,
        hexToColor3,
        waitForAllTextures,
        getPlanetInfo,
        setHighlight,
        planetInfo
    };
})();

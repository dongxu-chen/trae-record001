const SceneSetup = (function() {
    let engine = null;
    let scene = null;
    let camera = null;
    let sunlight = null;
    let ambientLight = null;
    let canvas = null;
    let pickedMesh = null;
    let hoverMesh = null;
    const onPickCallbacks = [];
    const onHoverCallbacks = [];

    function init(canvasElement) {
        canvas = canvasElement;
        engine = new BABYLON.Engine(canvas, true, {
            preserveDrawingBuffer: true,
            stencil: true,
            disableWebGL2Support: false,
            antialias: true,
            adaptToDeviceRatio: true
        });

        engine.enableOfflineSupport = false;
        engine.setHardwareScalingLevel(1);

        scene = new BABYLON.Scene(engine);
        scene.clearColor = new BABYLON.Color4(0, 0, 0.02, 1);
        scene.autoClear = true;
        scene.useRightHandedSystem = true;
        scene.fogMode = BABYLON.Scene.FOGMODE_NONE;
        scene.autoClearDepthAndStencil = true;

        engine.renderingPipeline = new BABYLON.DefaultRenderingPipeline(
            'defaultPipeline',
            true,
            scene,
            true
        );

        if (engine.renderingPipeline) {
            engine.renderingPipeline.samples = 4;
            engine.renderingPipeline.bloomEnabled = false;
            engine.renderingPipeline.fxaaEnabled = true;
            engine.renderingPipeline.sharpenEnabled = false;
        }

        camera = new BABYLON.ArcRotateCamera(
            'Camera',
            Math.PI / 4,
            Math.PI / 3,
            150,
            BABYLON.Vector3.Zero(),
            scene
        );
        camera.setTarget(BABYLON.Vector3.Zero());
        camera.attachControl(canvas, true);
        camera.lowerRadiusLimit = 20;
        camera.upperRadiusLimit = 500;
        camera.minZ = 0.1;
        camera.maxZ = 2000;
        camera.wheelPrecision = 10;
        camera.pinchPrecision = 10;
        camera.useAutoRotationBehavior = false;
        camera.checkCollisions = false;
        camera.fov = 0.8;

        camera.angularSensibilityX = 2000;
        camera.angularSensibilityY = 2000;
        camera.lowerBetaLimit = 0.1;
        camera.upperBetaLimit = Math.PI - 0.1;

        const hemiLight = new BABYLON.HemisphericLight(
            'HemiLight',
            new BABYLON.Vector3(0, 1, 0),
            scene
        );
        hemiLight.intensity = 0.2;
        hemiLight.diffuse = new BABYLON.Color3(0.5, 0.6, 0.8);
        hemiLight.groundColor = new BABYLON.Color3(0.1, 0.1, 0.2);
        ambientLight = hemiLight;

        sunlight = new BABYLON.PointLight(
            'SunLight',
            new BABYLON.Vector3(0, 0, 0),
            scene
        );
        sunlight.diffuse = new BABYLON.Color3(1, 0.95, 0.8);
        sunlight.specular = new BABYLON.Color3(1, 0.9, 0.7);
        sunlight.intensity = 2.5;
        sunlight.range = 1000;

        scene.clearColor = new BABYLON.Color4(0.001, 0.001, 0.005, 1);

        setupPicking();

        return { engine, scene, camera, sunlight, ambientLight };
    }

    function setupPicking() {
        canvas.addEventListener('pointerdown', handlePointerDown, false);
        canvas.addEventListener('pointermove', handlePointerMove, false);

        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                clearSelection();
            }
        });
    }

    function handlePointerDown(evt) {
        if (!scene || !camera) return;

        const pickResult = scene.pick(
            evt.offsetX || evt.clientX,
            evt.offsetY || evt.clientY
        );

        if (pickResult.hit && pickResult.pickedMesh) {
            const mesh = pickResult.pickedMesh;

            if (mesh._isPickable !== false) {
                pickedMesh = mesh;

                onPickCallbacks.forEach(callback => {
                    try {
                        callback(mesh, pickResult);
                    } catch (e) {
                        console.error('Pick callback error:', e);
                    }
                });
            }
        } else {
            clearSelection();
        }
    }

    function handlePointerMove(evt) {
        if (!scene || !camera) return;

        const pickResult = scene.pick(
            evt.offsetX || evt.clientX,
            evt.offsetY || evt.clientY
        );

        if (pickResult.hit && pickResult.pickedMesh) {
            const mesh = pickResult.pickedMesh;

            if (mesh._isPickable !== false && mesh !== hoverMesh) {
                hoverMesh = mesh;
                canvas.style.cursor = 'pointer';

                onHoverCallbacks.forEach(callback => {
                    try {
                        callback(mesh, true);
                    } catch (e) {
                        console.error('Hover callback error:', e);
                    }
                });
            }
        } else if (hoverMesh) {
            const prevHover = hoverMesh;
            hoverMesh = null;
            canvas.style.cursor = 'default';

            onHoverCallbacks.forEach(callback => {
                try {
                    callback(prevHover, false);
                } catch (e) {
                    console.error('Hover callback error:', e);
                }
            });
        }
    }

    function clearSelection() {
        if (pickedMesh) {
            const prevPicked = pickedMesh;
            pickedMesh = null;

            onPickCallbacks.forEach(callback => {
                try {
                    callback(null, null);
                } catch (e) {
                    console.error('Clear selection callback error:', e);
                }
            });
        }
    }

    function onPick(callback) {
        if (typeof callback === 'function') {
            onPickCallbacks.push(callback);
        }
    }

    function onHover(callback) {
        if (typeof callback === 'function') {
            onHoverCallbacks.push(callback);
        }
    }

    function getPickedMesh() {
        return pickedMesh;
    }

    function getHoverMesh() {
        return hoverMesh;
    }

    function projectToScreen(position) {
        if (!scene || !camera) return null;

        const vector3 = BABYLON.Vector3.Project(
            position,
            BABYLON.Matrix.Identity(),
            scene.getTransformMatrix(),
            camera.viewport.toGlobal(
                engine.getRenderWidth(),
                engine.getRenderHeight()
            )
        );

        return {
            x: vector3.x,
            y: vector3.y,
            z: vector3.z,
            isInFront: vector3.z >= 0 && vector3.z <= 1
        };
    }

    function makePickable(mesh, pickable = true) {
        mesh._isPickable = pickable;
    }

    function isPointVisible(position) {
        if (!scene || !camera) return false;

        const screen = projectToScreen(position);
        if (!screen) return false;

        const width = engine.getRenderWidth();
        const height = engine.getRenderHeight();

        return screen.isInFront &&
               screen.x >= 0 && screen.x <= width &&
               screen.y >= 0 && screen.y <= height;
    }

    function setSkybox(scene, size = 1000) {
        const skybox = BABYLON.MeshBuilder.CreateBox(
            'skybox',
            { size: size },
            scene
        );

        const skyboxMaterial = new BABYLON.StandardMaterial('skybox', scene);
        skyboxMaterial.backFaceCulling = false;
        skyboxMaterial.disableLighting = true;

        skyboxMaterial.reflectionTexture = new BABYLON.CubeTexture(
            '',
            scene,
            null,
            null,
            null,
            null,
            null
        );

        skyboxMaterial.reflectionTexture.coordinatesMode = BABYLON.Texture.SKYBOX_MODE;
        skyboxMaterial.diffuseColor = new BABYLON.Color3(0, 0, 0);
        skyboxMaterial.specularColor = new BABYLON.Color3(0, 0, 0);
        skybox.material = skyboxMaterial;
        skybox.infiniteDistance = true;

        return skybox;
    }

    return {
        init,
        setSkybox,
        onPick,
        onHover,
        clearSelection,
        getPickedMesh,
        getHoverMesh,
        projectToScreen,
        makePickable,
        isPointVisible
    };
})();

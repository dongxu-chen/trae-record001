const OrbitControl = (function() {
    const orbitingBodies = [];
    const orbitLines = [];
    let paused = false;
    let engine = null;
    let scene = null;
    let camera = null;

    let cruiseMode = false;
    let cruiseTargets = [];
    let currentCruiseIndex = 0;
    let cruiseStayTime = 3000;
    let cruiseTransitionSpeed = 0.02;
    let cruiseTimer = null;
    let isCruiseTransitioning = false;

    function registerOrbit(mesh, orbitRadius, orbitSpeed, orbitCenter = BABYLON.Vector3.Zero(), inclination = 0) {
        const angle = Math.random() * Math.PI * 2;

        const orbitData = {
            mesh: mesh,
            orbitRadius: orbitRadius,
            orbitSpeed: orbitSpeed,
            orbitCenter: orbitCenter.clone(),
            angle: angle,
            inclination: inclination,
            initialY: mesh.position.y
        };

        orbitingBodies.push(orbitData);

        mesh._orbitData = orbitData;

        updatePosition(orbitingBodies[orbitingBodies.length - 1]);

        return orbitingBodies.length - 1;
    }

    function createOrbitLine(name, radius, color = new BABYLON.Color3(0.2, 0.2, 0.3), segments = 256) {
        if (!scene) return null;

        const points = [];
        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            points.push(new BABYLON.Vector3(
                Math.cos(angle) * radius,
                0,
                Math.sin(angle) * radius
            ));
        }

        const orbitLine = BABYLON.MeshBuilder.CreateLines(name, {
            points: points,
            updatable: false
        }, scene);

        const lineColor = new BABYLON.Color4(color.r, color.g, color.b, 0.35);
        orbitLine.color = lineColor;
        orbitLine.alpha = 0.35;
        orbitLine.doNotSyncBoundingInfo = true;
        orbitLine._isPickable = false;

        orbitLines.push({
            mesh: orbitLine,
            radius: radius
        });

        return orbitLine;
    }

    function updatePosition(body) {
        const x = body.orbitCenter.x + body.orbitRadius * Math.cos(body.angle);
        const z = body.orbitCenter.z + body.orbitRadius * Math.sin(body.angle);
        const y = body.orbitCenter.y + body.orbitRadius * Math.sin(body.angle) * Math.sin(body.inclination);

        body.mesh.position = new BABYLON.Vector3(x, y, z);
    }

    function updateOrbits(deltaTime = null) {
        if (paused) return;

        const dt = deltaTime !== null ? deltaTime : (engine ? engine.getDeltaTime() / 1000 : 0.016);

        orbitingBodies.forEach(body => {
            body.angle += body.orbitSpeed * dt * 60;
            updatePosition(body);
        });

        updateCruiseTransition();
    }

    function removeOrbit(index) {
        if (index >= 0 && index < orbitingBodies.length) {
            orbitingBodies.splice(index, 1);
            return true;
        }
        return false;
    }

    function removeOrbitByMesh(mesh) {
        const index = orbitingBodies.findIndex(body => body.mesh === mesh);
        if (index !== -1) {
            orbitingBodies.splice(index, 1);
            return true;
        }
        return false;
    }

    function getOrbitData(mesh) {
        return orbitingBodies.find(body => body.mesh === mesh);
    }

    function togglePause() {
        paused = !paused;
        return paused;
    }

    function isPaused() {
        return paused;
    }

    function setPaused(value) {
        paused = value;
    }

    function setSpeed(mesh, newSpeed) {
        const body = orbitingBodies.find(b => b.mesh === mesh);
        if (body) {
            body.orbitSpeed = newSpeed;
        }
    }

    function setRadius(mesh, newRadius) {
        const body = orbitingBodies.find(b => b.mesh === mesh);
        if (body) {
            body.orbitRadius = newRadius;
            updatePosition(body);
        }
    }

    function clearAllOrbits() {
        orbitingBodies.length = 0;
        orbitLines.forEach(line => {
            if (line.mesh) line.mesh.dispose();
        });
        orbitLines.length = 0;
    }

    function setScene(sceneContext) {
        scene = sceneContext;
    }

    function setEngine(engineContext) {
        engine = engineContext;
    }

    function setCamera(cameraContext) {
        camera = cameraContext;
    }

    function focusOnMesh(mesh, onComplete = null) {
        if (!camera || !mesh) return;

        const size = mesh._config?.size || 1;
        const targetRadius = size * 8;

        const targetAlpha = camera.alpha;
        const targetBeta = Math.PI / 3;
        const startRadius = camera.radius;
        const startTarget = camera.target.clone();
        const endTarget = mesh.position.clone();

        let progress = 0;
        const duration = 800;
        const startTime = performance.now();

        const animate = () => {
            const elapsed = performance.now() - startTime;
            progress = Math.min(elapsed / duration, 1);

            const eased = easeInOutCubic(progress);

            camera.radius = startRadius + (targetRadius - startRadius) * eased;
            camera.target = BABYLON.Vector3.Lerp(startTarget, endTarget, eased);

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                if (onComplete) onComplete();
            }
        };

        animate();
    }

    function focusOnSolarSystem(onComplete = null) {
        if (!camera) return;

        const targetRadius = 200;
        const targetAlpha = Math.PI / 4;
        const targetBeta = Math.PI / 3;
        const endTarget = BABYLON.Vector3.Zero();

        const startRadius = camera.radius;
        const startTarget = camera.target.clone();
        const startAlpha = camera.alpha;

        let progress = 0;
        const duration = 1200;
        const startTime = performance.now();

        const animate = () => {
            const elapsed = performance.now() - startTime;
            progress = Math.min(elapsed / duration, 1);

            const eased = easeInOutCubic(progress);

            camera.radius = startRadius + (targetRadius - startRadius) * eased;
            camera.alpha = startAlpha + (targetAlpha - startAlpha) * eased;
            camera.target = BABYLON.Vector3.Lerp(startTarget, endTarget, eased);
            camera.beta = targetBeta;

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                if (onComplete) onComplete();
            }
        };

        animate();
    }

    function startCruise(targetMeshes, options = {}) {
        if (!camera || targetMeshes.length === 0) return;

        cruiseTargets = targetMeshes.slice();
        currentCruiseIndex = 0;
        cruiseMode = true;
        cruiseStayTime = options.stayTime || 3000;
        cruiseTransitionSpeed = options.transitionSpeed || 0.015;

        cruiseToCurrentTarget();
    }

    function stopCruise() {
        cruiseMode = false;
        isCruiseTransitioning = false;
        if (cruiseTimer) {
            clearTimeout(cruiseTimer);
            cruiseTimer = null;
        }
    }

    function toggleCruise(targetMeshes) {
        if (cruiseMode) {
            stopCruise();
        } else {
            startCruise(targetMeshes);
        }
        return cruiseMode;
    }

    function cruiseToCurrentTarget() {
        if (!cruiseMode || currentCruiseIndex >= cruiseTargets.length) {
            currentCruiseIndex = 0;
            if (cruiseTargets.length > 0) {
                cruiseToCurrentTarget();
            }
            return;
        }

        const target = cruiseTargets[currentCruiseIndex];

        isCruiseTransitioning = true;

        focusOnMesh(target, () => {
            isCruiseTransitioning = false;

            cruiseTimer = setTimeout(() => {
                if (cruiseMode) {
                    currentCruiseIndex++;
                    cruiseToCurrentTarget();
                }
            }, cruiseStayTime);
        });
    }

    function updateCruiseTransition() {
        if (!cruiseMode || !isCruiseTransitioning) return;

        const target = cruiseTargets[currentCruiseIndex];
        if (target) {
            const targetPos = target.position.clone();
            const currentTarget = camera.target;
            const distance = BABYLON.Vector3.Distance(currentTarget, targetPos);

            if (distance > 0.5) {
                camera.target = BABYLON.Vector3.Lerp(
                    currentTarget,
                    targetPos,
                    cruiseTransitionSpeed
                );
            }
        }
    }

    function easeInOutCubic(t) {
        return t < 0.5
            ? 4 * t * t * t
            : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function isCruising() {
        return cruiseMode;
    }

    function getCurrentCruiseTarget() {
        if (cruiseMode && currentCruiseIndex < cruiseTargets.length) {
            return cruiseTargets[currentCruiseIndex];
        }
        return null;
    }

    return {
        engine,
        scene,
        camera,
        registerOrbit,
        createOrbitLine,
        updateOrbits,
        removeOrbit,
        removeOrbitByMesh,
        getOrbitData,
        togglePause,
        isPaused,
        setPaused,
        setSpeed,
        setRadius,
        clearAllOrbits,
        setScene,
        setEngine,
        setCamera,
        focusOnMesh,
        focusOnSolarSystem,
        startCruise,
        stopCruise,
        toggleCruise,
        isCruising,
        getCurrentCruiseTarget
    };
})();

const ParticleSystem = (function() {
    let scene = null;
    const starFieldSystem = null;
    const ringMeshes = [];
    const nebulaMeshes = [];

    function init(sceneContext) {
        scene = sceneContext;
        return {
            createStarField,
            createRing,
            createNebula,
            update,
            dispose
        };
    }

    function createStarField(numStars = 800, minDistance = 100, maxDistance = 500) {
        const positions = [];
        const colors = [];

        for (let i = 0; i < numStars; i++) {
            const phi = Math.random() * Math.PI * 2;
            const costheta = Math.random() * 2 - 1;
            const u = Math.random();
            const theta = Math.acos(costheta);
            const r = minDistance + u * (maxDistance - minDistance);

            const x = r * Math.sin(theta) * Math.cos(phi);
            const y = r * Math.sin(theta) * Math.sin(phi);
            const z = r * Math.cos(theta);

            positions.push(x, y, z);

            const brightness = 0.7 + Math.random() * 0.3;
            const blueTint = 0.8 + Math.random() * 0.2;
            colors.push(brightness, brightness, brightness * blueTint, 1);
        }

        const vertexData = new BABYLON.VertexData();
        vertexData.positions = positions;
        vertexData.colors = colors;

        const starField = new BABYLON.Mesh('starField', scene);
        vertexData.applyToMesh(starField, true);

        const starFieldMaterial = new BABYLON.StandardMaterial('starFieldMat', scene);
        starFieldMaterial.disableLighting = true;
        starFieldMaterial.emissiveColor = new BABYLON.Color3(1, 1, 1);
        starFieldMaterial.pointsCloud = true;
        starFieldMaterial.pointSize = 2;

        starField.material = starFieldMaterial;
        starField.doNotSyncBoundingInfo = true;
        starField.freezeWorldMatrix();

        return starField;
    }

    function createRing(planet, innerRadius, outerRadius, height = 0.5, color = new BABYLON.Color3(1, 0.8, 0.5)) {
        const numParticles = 800;
        const positions = [];
        const colors = [];
        const indices = [];

        for (let i = 0; i < numParticles; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = innerRadius + Math.random() * (outerRadius - innerRadius);
            const y = (Math.random() - 0.5) * height;

            const size = 0.08 + Math.random() * 0.2;

            const x1 = Math.cos(angle) * radius - size * Math.sin(angle);
            const z1 = Math.sin(angle) * radius + size * Math.cos(angle);

            const x2 = Math.cos(angle) * radius + size * Math.sin(angle);
            const z2 = Math.sin(angle) * radius - size * Math.cos(angle);

            const baseIndex = i * 4;
            positions.push(x1, y - size, z1);
            positions.push(x2, y - size, z2);
            positions.push(x2, y + size, z2);
            positions.push(x1, y + size, z1);

            const brightness = 0.4 + Math.random() * 0.6;
            const r = color.r * brightness;
            const g = color.g * brightness;
            const b = color.b * brightness;
            const a = 0.5 + Math.random() * 0.5;

            for (let j = 0; j < 4; j++) {
                colors.push(r, g, b, a);
            }

            indices.push(baseIndex, baseIndex + 1, baseIndex + 2);
            indices.push(baseIndex, baseIndex + 2, baseIndex + 3);
        }

        const vertexData = new BABYLON.VertexData();
        vertexData.positions = positions;
        vertexData.colors = colors;
        vertexData.indices = indices;

        const ringMesh = new BABYLON.Mesh(`${planet.name}-ring`, scene);
        vertexData.applyToMesh(ringMesh, true);

        const ringMaterial = new BABYLON.StandardMaterial(`${planet.name}-ring-mat`, scene);
        ringMaterial.disableLighting = true;
        ringMaterial.emissiveColor = new BABYLON.Color3(1, 1, 1);
        ringMaterial.backFaceCulling = false;

        ringMesh.material = ringMaterial;
        ringMesh.parent = planet;
        ringMesh.doNotSyncBoundingInfo = true;

        ringMeshes.push({
            mesh: ringMesh,
            planet: planet,
            rotationSpeed: 0.0008
        });

        return ringMesh;
    }

    function createNebula(
        center,
        radius,
        numParticles = 200,
        color1 = new BABYLON.Color4(0.5, 0.2, 0.8, 0.3),
        color2 = new BABYLON.Color4(0.2, 0.4, 0.8, 0.2)
    ) {
        const positions = [];
        const colors = [];
        const indices = [];

        for (let i = 0; i < numParticles; i++) {
            const phi = Math.random() * Math.PI * 2;
            const u = Math.random();
            const theta = Math.acos(2 * u - 1);
            const r = Math.pow(Math.random(), 0.5) * radius;

            const x = center.x + r * Math.sin(theta) * Math.cos(phi);
            const y = center.y + r * Math.sin(theta) * Math.sin(phi) * 0.5;
            const z = center.z + r * Math.cos(theta);

            const size = 3 + Math.random() * 5;

            const baseIndex = i * 4;
            positions.push(x - size, y - size, z);
            positions.push(x + size, y - size, z);
            positions.push(x + size, y + size, z);
            positions.push(x - size, y + size, z);

            const t = Math.random();
            const rColor = color1.r * (1 - t) + color2.r * t;
            const gColor = color1.g * (1 - t) + color2.g * t;
            const bColor = color1.b * (1 - t) + color2.b * t;
            const a = (color1.a * (1 - t) + color2.a * t) * (0.5 + Math.random() * 0.5);

            for (let j = 0; j < 4; j++) {
                colors.push(rColor, gColor, bColor, a);
            }

            indices.push(baseIndex, baseIndex + 1, baseIndex + 2);
            indices.push(baseIndex, baseIndex + 2, baseIndex + 3);
        }

        const vertexData = new BABYLON.VertexData();
        vertexData.positions = positions;
        vertexData.colors = colors;
        vertexData.indices = indices;

        const nebulaMesh = new BABYLON.Mesh('nebula', scene);
        vertexData.applyToMesh(nebulaMesh, true);

        const nebulaMaterial = new BABYLON.StandardMaterial('nebulaMat', scene);
        nebulaMaterial.disableLighting = true;
        nebulaMaterial.emissiveColor = new BABYLON.Color3(1, 1, 1);
        nebulaMaterial.backFaceCulling = false;
        nebulaMaterial.useAlphaFromDiffuseTexture = false;

        nebulaMesh.material = nebulaMaterial;
        nebulaMesh.doNotSyncBoundingInfo = true;

        nebulaMeshes.push({
            mesh: nebulaMesh,
            pulsePhase: Math.random() * Math.PI * 2,
            pulseSpeed: 0.0005
        });

        return nebulaMesh;
    }

    function update() {
        ringMeshes.forEach(ring => {
            if (ring.mesh) {
                ring.mesh.rotation.y += ring.rotationSpeed;
            }
        });

        nebulaMeshes.forEach(nebula => {
            if (nebula.mesh && nebula.mesh.material) {
                nebula.pulsePhase += nebula.pulseSpeed;
                const pulse = Math.sin(nebula.pulsePhase) * 0.1 + 0.9;
            }
        });
    }

    function dispose() {
        ringMeshes.forEach(ring => {
            if (ring.mesh) ring.mesh.dispose();
        });
        ringMeshes.length = 0;

        nebulaMeshes.forEach(nebula => {
            if (nebula.mesh) nebula.mesh.dispose();
        });
        nebulaMeshes.length = 0;
    }

    return {
        init,
        createStarField,
        createRing,
        createNebula,
        update,
        dispose
    };
})();

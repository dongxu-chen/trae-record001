struct VertexInput {
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) boneIndices: vec4<f32>,
    @location(3) boneWeights: vec4<f32>,
};

struct VertexOutput {
    @builtin(position) position: vec4<f32>,
    @location(0) normal: vec3<f32>,
};

@group(0) @binding(0) var<uniform> boneMatrices: array<mat4x4<f32>, 256>;
@group(0) @binding(1) var<uniform> viewProjection: mat4x4<f32>;

fn linearToSrgb(linear: vec3<f32>) -> vec3<f32> {
    let b = linear <= vec3<f32>(0.0031308);
    return select(1.055 * pow(linear, vec3<f32>(1.0 / 2.4)) - vec3<f32>(0.055), 12.92 * linear, b);
}

@compute @workgroup_size(64)
fn computeSkinning(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let vertexIndex = global_id.x;
    let numVertices = arrayLength(&vertices);
    
    if (vertexIndex >= numVertices) {
        return;
    }

    let vertex = vertices[vertexIndex];
    
    var skinMatrix = mat4x4<f32>(0.0);
    
    let boneIndex0 = u32(vertex.boneIndices.x);
    let boneIndex1 = u32(vertex.boneIndices.y);
    let boneIndex2 = u32(vertex.boneIndices.z);
    let boneIndex3 = u32(vertex.boneIndices.w);
    
    let weight0 = vertex.boneWeights.x;
    let weight1 = vertex.boneWeights.y;
    let weight2 = vertex.boneWeights.z;
    let weight3 = vertex.boneWeights.w;
    
    skinMatrix = boneMatrices[boneIndex0] * weight0;
    skinMatrix = skinMatrix + boneMatrices[boneIndex1] * weight1;
    skinMatrix = skinMatrix + boneMatrices[boneIndex2] * weight2;
    skinMatrix = skinMatrix + boneMatrices[boneIndex3] * weight3;
    
    let skinnedPosition = skinMatrix * vec4<f32>(vertex.position, 1.0);
    let skinnedNormal = normalize((skinMatrix * vec4<f32>(vertex.normal, 0.0)).xyz);
    
    outputVertices[vertexIndex].position = viewProjection * skinnedPosition;
    outputVertices[vertexIndex].normal = skinnedNormal;
}

struct Uniforms {
    viewProjection: mat4x4<f32>,
    time: f32,
    deltaTime: f32,
};

@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(1) var<storage, read> positions: array<vec3<f32>>;
@group(0) @binding(2) var<storage, read> normals: array<vec3<f32>>;
@group(0) @binding(3) var<storage, read> boneIndices: array<vec4<u32>>;
@group(0) @binding(4) var<storage, read> boneWeights: array<vec4<f32>>;
@group(0) @binding(5) var<storage, read> boneMatrices: array<mat4x4<f32>>;
@group(0) @binding(6) var<storage, write> outputPositions: array<vec3<f32>>;
@group(0) @binding(7) var<storage, write> outputNormals: array<vec3<f32>>;

@compute @workgroup_size(256)
fn computeSkinningMain(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let vertexIndex = global_id.x;
    let numVertices = arrayLength(&positions);
    
    if (vertexIndex >= numVertices) {
        return;
    }

    let pos = positions[vertexIndex];
    let normal = normals[vertexIndex];
    let indices = boneIndices[vertexIndex];
    let weights = boneWeights[vertexIndex];
    
    var skinMatrix = mat4x4<f32>(0.0);
    
    if (weights.x > 0.0) {
        skinMatrix = skinMatrix + boneMatrices[indices.x] * weights.x;
    }
    if (weights.y > 0.0) {
        skinMatrix = skinMatrix + boneMatrices[indices.y] * weights.y;
    }
    if (weights.z > 0.0) {
        skinMatrix = skinMatrix + boneMatrices[indices.z] * weights.z;
    }
    if (weights.w > 0.0) {
        skinMatrix = skinMatrix + boneMatrices[indices.w] * weights.w;
    }
    
    let skinnedPos = skinMatrix * vec4<f32>(pos, 1.0);
    let skinnedNormal = normalize((skinMatrix * vec4<f32>(normal, 0.0)).xyz);
    
    outputPositions[vertexIndex] = skinnedPos.xyz;
    outputNormals[vertexIndex] = skinnedNormal;
}

@compute @workgroup_size(64)
fn computeMorphTargets(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let vertexIndex = global_id.x;
    let numVertices = arrayLength(&basePositions);
    
    if (vertexIndex >= numVertices) {
        return;
    }

    var finalPosition = basePositions[vertexIndex];
    var finalNormal = baseNormals[vertexIndex];
    
    for (var i: u32 = 0; i < morphTargetCount; i++) {
        let weight = morphWeights[i];
        if (weight <= 0.0) {
            continue;
        }
        
        let deltaPos = morphPositions[i][vertexIndex];
        let deltaNormal = morphNormals[i][vertexIndex];
        
        finalPosition = finalPosition + deltaPos * weight;
        finalNormal = finalNormal + deltaNormal * weight;
    }
    
    outputMorphPositions[vertexIndex] = finalPosition;
    outputMorphNormals[vertexIndex] = normalize(finalNormal);
}

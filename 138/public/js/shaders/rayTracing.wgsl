struct Ray {
    origin: vec3<f32>,
    direction: vec3<f32>,
};

struct HitInfo {
    hit: bool,
    distance: f32,
    position: vec3<f32>,
    normal: vec3<f32>,
    color: vec3<f32>,
    metallic: f32,
    roughness: f32,
};

struct Material {
    albedo: vec3<f32>,
    metallic: f32,
    roughness: f32,
    emissive: vec3<f32>,
};

struct Sphere {
    center: vec3<f32>,
    radius: f32,
    materialIndex: u32,
};

struct Plane {
    position: vec3<f32>,
    normal: vec3<f32>,
    materialIndex: u32,
};

struct Uniforms {
    cameraPosition: vec3<f32>,
    cameraDirection: vec3<f32>,
    cameraRight: vec3<f32>,
    cameraUp: vec3<f32>,
    fov: f32,
    aspectRatio: f32,
    time: f32,
    maxBounces: u32,
    samplesPerPixel: u32,
};

@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(1) var<storage, read> materials: array<Material>;
@group(0) @binding(2) var<storage, read> spheres: array<Sphere>;
@group(0) @binding(3) var<storage, read> planes: array<Plane>;
@group(0) @binding(4) var<storage, write> outputTexture: texture_storage_2d<rgba8unorm, write>;

fn random(seed: ptr<function, vec2<f32>>) -> f32 {
    *seed = vec2<f32>(
        dot(*seed, vec2<f32>(127.1, 311.7)),
        dot(*seed, vec2<f32>(269.5, 183.3))
    );
    return fract(sin(dot(*seed, vec2<f32>(12.9898, 78.233))) * 43758.5453);
}

fn randomInUnitSphere(seed: ptr<function, vec2<f32>>) -> vec3<f32> {
    var p: vec3<f32>;
    loop {
        p = vec3<f32>(random(seed), random(seed), random(seed)) * 2.0 - vec3<f32>(1.0);
        if dot(p, p) < 1.0 {
            break;
        }
    }
    return normalize(p);
}

fn intersectSphere(ray: Ray, sphere: Sphere) -> HitInfo {
    var hit: HitInfo;
    hit.hit = false;
    
    let oc = ray.origin - sphere.center;
    let a = dot(ray.direction, ray.direction);
    let b = 2.0 * dot(oc, ray.direction);
    let c = dot(oc, oc) - sphere.radius * sphere.radius;
    let discriminant = b * b - 4.0 * a * c;
    
    if discriminant < 0.0 {
        return hit;
    }
    
    let t = (-b - sqrt(discriminant)) / (2.0 * a);
    if t < 0.001 {
        return hit;
    }
    
    hit.hit = true;
    hit.distance = t;
    hit.position = ray.origin + ray.direction * t;
    hit.normal = normalize(hit.position - sphere.center);
    hit.color = materials[sphere.materialIndex].albedo;
    hit.metallic = materials[sphere.materialIndex].metallic;
    hit.roughness = materials[sphere.materialIndex].roughness;
    
    return hit;
}

fn intersectPlane(ray: Ray, plane: Plane) -> HitInfo {
    var hit: HitInfo;
    hit.hit = false;
    
    let denom = dot(plane.normal, ray.direction);
    if abs(denom) < 0.0001 {
        return hit;
    }
    
    let t = dot(plane.position - ray.origin, plane.normal) / denom;
    if t < 0.001 {
        return hit;
    }
    
    hit.hit = true;
    hit.distance = t;
    hit.position = ray.origin + ray.direction * t;
    hit.normal = plane.normal;
    hit.color = materials[plane.materialIndex].albedo;
    hit.metallic = materials[plane.materialIndex].metallic;
    hit.roughness = materials[plane.materialIndex].roughness;
    
    return hit;
}

fn castRay(ray: Ray, seed: ptr<function, vec2<f32>>) -> vec3<f32> {
    var color = vec3<f32>(0.0);
    var throughput = vec3<f32>(1.0);
    var currentRay = ray;
    
    for (var bounce: u32 = 0; bounce < uniforms.maxBounces; bounce++) {
        var closestHit: HitInfo;
        closestHit.hit = false;
        closestHit.distance = 1000000.0;
        
        for (var i: u32 = 0; i < arrayLength(&spheres); i++) {
            let hit = intersectSphere(currentRay, spheres[i]);
            if hit.hit && hit.distance < closestHit.distance {
                closestHit = hit;
            }
        }
        
        for (var i: u32 = 0; i < arrayLength(&planes); i++) {
            let hit = intersectPlane(currentRay, planes[i]);
            if hit.hit && hit.distance < closestHit.distance {
                closestHit = hit;
            }
        }
        
        if !closestHit.hit {
            let t = 0.5 * (currentRay.direction.y + 1.0);
            let skyColor = mix(vec3<f32>(1.0), vec3<f32>(0.5, 0.7, 1.0), t);
            color = color + throughput * skyColor;
            break;
        }
        
        currentRay.origin = closestHit.position;
        
        let fuzz = closestHit.roughness;
        let reflected = reflect(currentRay.direction, closestHit.normal);
        currentRay.direction = normalize(reflected + fuzz * randomInUnitSphere(seed));
        
        let fresnel = pow(1.0 - max(0.0, dot(-currentRay.direction, closestHit.normal)), 5.0);
        let metalness = mix(closestHit.metallic, 1.0, fresnel);
        
        color = color + throughput * closestHit.color * (1.0 - metalness) * 0.5;
        throughput = throughput * mix(closestHit.color, vec3<f32>(1.0), metalness);
        
        if max(max(throughput.x, throughput.y), throughput.z) < 0.001 {
            break;
        }
    }
    
    return color;
}

@compute @workgroup_size(8, 8)
fn rayTraceMain(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let dims = textureDimensions(outputTexture);
    
    if global_id.x >= dims.x || global_id.y >= dims.y {
        return;
    }
    
    let x = f32(global_id.x);
    let y = f32(global_id.y);
    let width = f32(dims.x);
    let height = f32(dims.y);
    
    var seed = vec2<f32>(
        (x + uniforms.time * 100.0) / width,
        (y + uniforms.time * 100.0) / height
    );
    
    var finalColor = vec3<f32>(0.0);
    
    for (var sample: u32 = 0; sample < uniforms.samplesPerPixel; sample++) {
        let u = (x + random(&seed)) / width * 2.0 - 1.0;
        let v = (y + random(&seed)) / height * 2.0 - 1.0;
        
        let rayDir = normalize(
            uniforms.cameraDirection
            + u * uniforms.cameraRight * tan(uniforms.fov * 0.5) * uniforms.aspectRatio
            + v * uniforms.cameraUp * tan(uniforms.fov * 0.5)
        );
        
        let ray = Ray(uniforms.cameraPosition, rayDir);
        finalColor = finalColor + castRay(ray, &seed);
    }
    
    finalColor = finalColor / f32(uniforms.samplesPerPixel);
    
    finalColor = vec3<f32>(
        pow(finalColor.x, 1.0 / 2.2),
        pow(finalColor.y, 1.0 / 2.2),
        pow(finalColor.z, 1.0 / 2.2)
    );
    
    textureStore(outputTexture, vec2<i32>(i32(global_id.x), i32(global_id.y)), 
        vec4<f32>(finalColor, 1.0));
}

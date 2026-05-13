class SpatialHashGrid {
    constructor(cellSize) {
        this.cellSize = cellSize;
        this.grid = new Map();
    }

    clear() {
        this.grid.clear();
    }

    getKey(x, y) {
        const cx = Math.floor(x / this.cellSize);
        const cy = Math.floor(y / this.cellSize);
        return `${cx},${cy}`;
    }

    insert(particle, index) {
        const key = this.getKey(particle.position.x, particle.position.y);
        if (!this.grid.has(key)) {
            this.grid.set(key, []);
        }
        this.grid.get(key).push(index);
    }

    getNeighbors(particle) {
        const neighbors = [];
        const cx = Math.floor(particle.position.x / this.cellSize);
        const cy = Math.floor(particle.position.y / this.cellSize);

        for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
                const key = `${cx + dx},${cy + dy}`;
                if (this.grid.has(key)) {
                    neighbors.push(...this.grid.get(key));
                }
            }
        }

        return neighbors;
    }
}

class ForceField {
    constructor() {
        this.forces = [];
        this.decay = 0.98;
        this.radius = 80;
    }

    add(x, y, fx, fy, strength = 1.0) {
        this.forces.push({
            x, y,
            fx, fy,
            strength,
            radius: this.radius
        });
    }

    update() {
        this.forces = this.forces.filter(f => {
            f.strength *= this.decay;
            return f.strength > 0.01;
        });
    }

    sample(x, y) {
        let totalFx = 0;
        let totalFy = 0;
        
        for (const f of this.forces) {
            const dx = x - f.x;
            const dy = y - f.y;
            const distSq = dx * dx + dy * dy;
            const dist = Math.sqrt(distSq);
            
            if (dist < f.radius && dist > 0) {
                const influence = (1 - dist / f.radius);
                const factor = influence * influence * influence * f.strength;
                totalFx += f.fx * factor;
                totalFy += f.fy * factor;
            }
        }
        
        return { x: totalFx, y: totalFy };
    }

    clear() {
        this.forces = [];
    }
}

class FluidSolver {
    constructor(params = {}) {
        this.h = params.smoothingRadius || 30;
        this.gasConstant = params.gasConstant || 300;
        this.restDensity = params.restDensity || 4.0;
        this.viscosity = params.viscosity || 10;
        this.gravity = params.gravity || { x: 0, y: 900 };
        this.damping = params.damping || 0.98;
        this.particleMass = params.particleMass || 1.0;
        this.restitution = params.restitution || 0.15;
        this.externalForceMultiplier = params.externalForceMultiplier || 8000;
        
        this.h2 = this.h * this.h;
        this.h6 = this.h * this.h * this.h;
        this.h9 = this.h6 * this.h * this.h * this.h;
        
        this.poly6Coeff = 315 / (64 * Math.PI * this.h9);
        this.spikyGradCoeff = -45 / (Math.PI * this.h6);
        this.viscCoeff = 45 / (Math.PI * this.h6);
        
        this.grid = new SpatialHashGrid(this.h);
        this.forceField = new ForceField();
    }

    addExternalForce(x, y, fx, fy, strength = 1.0) {
        this.forceField.add(x, y, fx, fy, strength);
    }

    setViscosity(value) {
        this.viscosity = value;
    }

    setGravity(x, y) {
        this.gravity = { x, y };
    }

    wPoly6(r2) {
        if (r2 > this.h2) return 0;
        const diff = this.h2 - r2;
        return this.poly6Coeff * diff * diff * diff;
    }

    gradWSpiky(r, dx, dy) {
        if (r > this.h || r === 0) return { x: 0, y: 0 };
        const diff = this.h - r;
        const factor = this.spikyGradCoeff * diff * diff / r;
        return {
            x: factor * dx,
            y: factor * dy
        };
    }

    lapWViscosity(r) {
        if (r > this.h) return 0;
        return this.viscCoeff * (this.h - r);
    }

    buildGrid(particles) {
        this.grid.clear();
        for (let i = 0; i < particles.length; i++) {
            this.grid.insert(particles[i], i);
        }
    }

    computeDensity(particles) {
        this.buildGrid(particles);
        const n = particles.length;
        
        for (let i = 0; i < n; i++) {
            const pi = particles[i];
            pi.density = 0;
            
            const neighbors = this.grid.getNeighbors(pi);
            for (let k = 0; k < neighbors.length; k++) {
                const j = neighbors[k];
                const pj = particles[j];
                const dx = pi.position.x - pj.position.x;
                const dy = pi.position.y - pj.position.y;
                const r2 = dx * dx + dy * dy;
                pi.density += this.particleMass * this.wPoly6(r2);
            }
        }
    }

    computePressure(particles) {
        for (const p of particles) {
            p.pressure = this.gasConstant * Math.max(0, p.density - this.restDensity);
        }
    }

    computeForces(particles) {
        const n = particles.length;
        
        for (let i = 0; i < n; i++) {
            const pi = particles[i];
            let pressureForce = { x: 0, y: 0 };
            let viscosityForce = { x: 0, y: 0 };

            const neighbors = this.grid.getNeighbors(pi);
            for (let k = 0; k < neighbors.length; k++) {
                const j = neighbors[k];
                if (i === j) continue;
                
                const pj = particles[j];
                const dx = pi.position.x - pj.position.x;
                const dy = pi.position.y - pj.position.y;
                const r2 = dx * dx + dy * dy;
                const r = Math.sqrt(r2);
                
                if (r < this.h && r > 0) {
                    const grad = this.gradWSpiky(r, dx, dy);
                    const pressureDensityTerm = (pi.pressure + pj.pressure) / (2 * Math.max(pj.density, 0.1));
                    pressureForce.x -= this.particleMass * pressureDensityTerm * grad.x;
                    pressureForce.y -= this.particleMass * pressureDensityTerm * grad.y;

                    const visc = this.lapWViscosity(r);
                    viscosityForce.x += (pj.velocity.x - pi.velocity.x) * visc;
                    viscosityForce.y += (pj.velocity.y - pi.velocity.y) * visc;
                }
            }

            const extForce = this.forceField.sample(pi.position.x, pi.position.y);
            
            const totalForce = {
                x: pressureForce.x + this.viscosity * viscosityForce.x + extForce.x * this.externalForceMultiplier,
                y: this.gravity.y * pi.mass + pressureForce.y + this.viscosity * viscosityForce.y + extForce.y * this.externalForceMultiplier
            };
            
            pi.applyForce(totalForce);
        }
        
        this.forceField.update();
    }

    handleBoundaryCollision(particle, bounds) {
        const margin = 5;
        
        if (particle.position.x < margin) {
            particle.position.x = margin;
            particle.velocity.x = Math.abs(particle.velocity.x) * this.restitution;
        } else if (particle.position.x > bounds.width - margin) {
            particle.position.x = bounds.width - margin;
            particle.velocity.x = -Math.abs(particle.velocity.x) * this.restitution;
        }

        if (particle.position.y < margin) {
            particle.position.y = margin;
            particle.velocity.y = Math.abs(particle.velocity.y) * this.restitution;
        } else if (particle.position.y > bounds.height - margin) {
            particle.position.y = bounds.height - margin;
            particle.velocity.y = -Math.abs(particle.velocity.y) * this.restitution;
        }
    }

    step(particles, dt, bounds) {
        this.computeDensity(particles);
        this.computePressure(particles);
        this.computeForces(particles);

        for (const p of particles) {
            p.update(dt);
            p.velocity.x *= this.damping;
            p.velocity.y *= this.damping;
            this.handleBoundaryCollision(p, bounds);
        }
    }
}

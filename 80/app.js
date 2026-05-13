class FluidSimulation {
    constructor() {
        this.width = 800;
        this.height = 600;
        this.particles = [];
        this.solver = null;
        this.renderer = null;
        this.app = null;
        this.gui = null;
        this.dragging = false;
        this.dragParticle = null;
        this.lastMousePos = null;
        this.forceStrength = 1.0;
        
        this.init();
    }

    init() {
        this.app = new PIXI.Application({
            width: this.width,
            height: this.height,
            backgroundColor: 0x1a1a2e,
            antialias: true,
            resizeTo: window
        });
        
        document.body.appendChild(this.app.view);
        
        const h = 40;
        
        this.solver = new FluidSolver({
            smoothingRadius: h,
            gasConstant: 50,
            restDensity: 8.0,
            viscosity: 30,
            gravity: { x: 0, y: 1200 },
            damping: 0.98,
            particleMass: 1.0,
            restitution: 0.1,
            externalForceMultiplier: 6000
        });
        
        this.renderer = new FluidRenderer(this.app, this.width, this.height);
        
        this.createParticles();
        this.setupUI();
        this.setupInteraction();
        this.setupGUI();
        
        this.app.ticker.add(this.update.bind(this));
    }

    createParticles() {
        this.particles = [];
        
        const startX = 150;
        const startY = 50;
        const spacing = 15;
        const cols = 12;
        const rows = 8;
        
        for (let i = 0; i < rows; i++) {
            for (let j = 0; j < cols; j++) {
                const x = startX + j * spacing;
                const y = startY + i * spacing;
                const particle = new Particle(x, y);
                
                particle.velocity.x = (Math.random() - 0.5) * 10;
                particle.velocity.y = Math.random() * 20;
                
                this.particles.push(particle);
            }
        }
        
        this.renderer.initParticles(this.particles);
    }

    setupUI() {
        const style = {
            fontFamily: 'Arial',
            fontSize: 14,
            fill: 0xffffff,
            align: 'center'
        };

        const helpText = new PIXI.Text(
            '拖拽鼠标产生流体扰动 | 点击空白添加粒子',
            style
        );
        helpText.x = 10;
        helpText.y = 10;
        this.app.stage.addChild(helpText);

        this.countText = new PIXI.Text(
            `粒子数量: ${this.particles.length}`,
            style
        );
        this.countText.x = 10;
        this.countText.y = 35;
        this.app.stage.addChild(this.countText);
    }

    setupGUI() {
        if (typeof FluidGUI !== 'undefined') {
            this.gui = new FluidGUI(this);
        }
    }

    setupInteraction() {
        this.app.stage.interactive = true;
        this.app.stage.hitArea = new PIXI.Rectangle(0, 0, this.width, this.height);

        this.app.stage.on('pointerdown', (event) => {
            const pos = event.data.global;
            this.dragging = true;
            this.lastMousePos = { x: pos.x, y: pos.y };
            
            for (const p of this.particles) {
                const dx = p.position.x - pos.x;
                const dy = p.position.y - pos.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < 30) {
                    this.dragParticle = p;
                    return;
                }
            }
            
            this.addParticle(pos.x, pos.y);
        });

        this.app.stage.on('pointermove', (event) => {
            const pos = event.data.global;
            
            if (!this.dragging) {
                this.lastMousePos = { x: pos.x, y: pos.y };
                return;
            }
            
            if (this.dragParticle) {
                this.dragParticle.position.x = pos.x;
                this.dragParticle.position.y = pos.y;
                this.dragParticle.velocity.x = 0;
                this.dragParticle.velocity.y = 0;
            } else {
                if (this.lastMousePos) {
                    const dx = pos.x - this.lastMousePos.x;
                    const dy = pos.y - this.lastMousePos.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    
                    if (dist > 1) {
                        const fx = dx / dist;
                        const fy = dy / dist;
                        
                        const midX = (pos.x + this.lastMousePos.x) / 2;
                        const midY = (pos.y + this.lastMousePos.y) / 2;
                        
                        this.solver.addExternalForce(
                            midX, midY,
                            fx, fy,
                            this.forceStrength * Math.min(dist / 10, 1.5)
                        );
                    }
                }
                
                if (Math.random() < 0.15) {
                    this.addParticle(
                        pos.x + (Math.random() - 0.5) * 15,
                        pos.y + (Math.random() - 0.5) * 15
                    );
                }
            }
            
            this.lastMousePos = { x: pos.x, y: pos.y };
        });

        this.app.stage.on('pointerup', () => {
            this.dragging = false;
            this.dragParticle = null;
            this.lastMousePos = null;
        });

        this.app.stage.on('pointerupoutside', () => {
            this.dragging = false;
            this.dragParticle = null;
            this.lastMousePos = null;
        });
    }

    addParticle(x, y) {
        if (this.particles.length >= 200) return;
        
        const particle = new Particle(x, y);
        particle.velocity.x = (Math.random() - 0.5) * 30;
        particle.velocity.y = -30;
        
        this.particles.push(particle);
        
        if (this.renderer) {
            const sprite = this.renderer.createSpriteFor(particle);
            this.renderer.particleSprites.push(sprite);
        }
        
        if (this.countText) {
            this.countText.text = `粒子数量: ${this.particles.length}`;
        }
    }

    update(delta) {
        const dt = Math.min(delta * 0.016, 0.015);
        const substeps = 2;
        const subDt = dt / substeps;

        for (let i = 0; i < substeps; i++) {
            this.solver.step(this.particles, subDt, {
                width: this.app.view.width,
                height: this.app.view.height
            });
        }

        this.renderer.update(this.particles);
    }

    resize(width, height) {
        this.width = width;
        this.height = height;
        this.renderer.resize(width, height);
    }
}

window.onload = () => {
    new FluidSimulation();
};

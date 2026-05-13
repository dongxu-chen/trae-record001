class FluidRenderer {
    constructor(application, width, height) {
        this.app = application;
        this.width = width;
        this.height = height;
        this.particleSprites = [];
        this.particleRadius = 5;
        this.useVelocityColor = true;
        this.maxSpeed = 800;
        
        this.setup();
    }

    setup() {
        this.particleTexture = this.createParticleTexture();
        
        this.particlesContainer = new PIXI.Container();
        this.particlesContainer.blendMode = PIXI.BLEND_MODES.ADD;
        this.app.stage.addChild(this.particlesContainer);
    }

    createParticleTexture() {
        const size = 32;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createRadialGradient(
            size / 2, size / 2, 0,
            size / 2, size / 2, size / 2
        );
        
        gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.3, 'rgba(220, 220, 255, 0.9)');
        gradient.addColorStop(0.6, 'rgba(150, 180, 255, 0.6)');
        gradient.addColorStop(1, 'rgba(100, 150, 255, 0)');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
        ctx.fill();
        
        return PIXI.Texture.from(canvas);
    }

    speedToColor(speed) {
        const t = Math.min(speed / this.maxSpeed, 1.0);
        
        let r, g, b;
        
        if (t < 0.25) {
            const k = t / 0.25;
            r = 0;
            g = 100 + k * 155;
            b = 255;
        } else if (t < 0.5) {
            const k = (t - 0.25) / 0.25;
            r = 0;
            g = 255;
            b = 255 - k * 255;
        } else if (t < 0.75) {
            const k = (t - 0.5) / 0.25;
            r = k * 255;
            g = 255;
            b = 0;
        } else {
            const k = (t - 0.75) / 0.25;
            r = 255;
            g = 255 - k * 100;
            b = 0;
        }
        
        return PIXI.utils.rgb2hex([r / 255, g / 255, b / 255]);
    }

    createSpriteFor(particle) {
        const sprite = new PIXI.Sprite(this.particleTexture);
        sprite.anchor.set(0.5);
        sprite.x = particle.position.x;
        sprite.y = particle.position.y;
        sprite.alpha = 0.7;
        sprite.scale.set(this.particleRadius / 16);
        sprite.blendMode = PIXI.BLEND_MODES.ADD;
        this.particlesContainer.addChild(sprite);
        return sprite;
    }

    initParticles(particles) {
        for (const sprite of this.particleSprites) {
            this.particlesContainer.removeChild(sprite);
            sprite.destroy();
        }
        this.particleSprites = [];
        
        for (const particle of particles) {
            this.particleSprites.push(this.createSpriteFor(particle));
        }
    }

    update(particles) {
        const n = Math.min(particles.length, this.particleSprites.length);
        
        for (let i = 0; i < n; i++) {
            const particle = particles[i];
            const sprite = this.particleSprites[i];
            
            sprite.x = particle.position.x;
            sprite.y = particle.position.y;
            
            const speed = Math.sqrt(
                particle.velocity.x * particle.velocity.x + 
                particle.velocity.y * particle.velocity.y
            );
            
            sprite.scale.set(this.particleRadius / 16 + Math.min(speed * 0.001, 0.3));
            sprite.alpha = 0.5 + Math.min(speed * 0.002, 0.5);
            
            if (this.useVelocityColor) {
                sprite.tint = this.speedToColor(speed);
            } else {
                sprite.tint = 0x6496FF;
            }
        }
    }

    setParticleRadius(radius) {
        this.particleRadius = radius;
        for (const sprite of this.particleSprites) {
            sprite.scale.set(this.particleRadius / 16);
        }
    }

    resize(width, height) {
        this.width = width;
        this.height = height;
    }
}

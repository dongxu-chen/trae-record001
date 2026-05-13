class FluidGUI {
    constructor(simulation) {
        this.sim = simulation;
        this.params = {
            viscosity: simulation.solver.viscosity,
            gravity: simulation.solver.gravity.y,
            particleRadius: simulation.renderer.particleRadius,
            damping: simulation.solver.damping,
            showVelocityColor: true
        };
        
        this.init();
    }

    init() {
        if (typeof dat === 'undefined' || !dat.GUI) {
            console.warn('dat.GUI not loaded, skipping GUI initialization');
            return;
        }
        
        this.gui = new dat.GUI({ width: 300 });
        this.gui.domElement.style.marginTop = '60px';
        
        const physics = this.gui.addFolder('物理参数');
        physics.open();
        
        physics.add(this.params, 'viscosity', 0, 100, 1).name('粘性系数').onChange((value) => {
            this.sim.solver.setViscosity(value);
        });
        
        physics.add(this.params, 'gravity', 0, 2000, 10).name('重力加速度').onChange((value) => {
            this.sim.solver.setGravity(0, value);
        });
        
        physics.add(this.params, 'damping', 0.9, 0.999, 0.001).name('速度阻尼').onChange((value) => {
            this.sim.solver.damping = value;
        });
        
        const rendering = this.gui.addFolder('渲染参数');
        rendering.open();
        
        rendering.add(this.params, 'particleRadius', 3, 15, 0.5).name('粒子半径').onChange((value) => {
            this.sim.renderer.setParticleRadius(value);
        });
        
        rendering.add(this.params, 'showVelocityColor').name('按速度上色').onChange((value) => {
            this.sim.renderer.useVelocityColor = value;
        });
        
        const interaction = this.gui.addFolder('交互参数');
        interaction.open();
        
        this.params.forceStrength = 1.0;
        this.params.forceRadius = 80;
        
        interaction.add(this.params, 'forceStrength', 0.1, 3.0, 0.1).name('扰动强度').onChange((value) => {
            this.sim.forceStrength = value;
        });
        
        interaction.add(this.params, 'forceRadius', 30, 150, 5).name('扰动半径').onChange((value) => {
            this.sim.solver.forceField.radius = value;
        });
    }
}

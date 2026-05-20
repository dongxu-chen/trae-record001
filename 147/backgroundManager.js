class BackgroundManager {
    constructor(avatarCanvas) {
        this.avatarCanvas = avatarCanvas;
        this.ctx = avatarCanvas.getContext('2d');
        this.currentMode = 'default';
        this.backgroundImage = null;
        this.blurRadius = 0;
        this.customImage = null;
        
        this.greenScreenColor = { r: 0, g: 255, b: 0 };
        this.blueScreenColor = { r: 0, g: 0, b: 255 };
        
        this.initDefaultBackground();
    }
    
    initDefaultBackground() {
        this.defaultGradient = this.ctx.createLinearGradient(0, 0, 0, this.avatarCanvas.height);
        this.defaultGradient.addColorStop(0, '#87CEEB');
        this.defaultGradient.addColorStop(1, '#E0F6FF');
    }
    
    setMode(mode) {
        this.currentMode = mode;
        this.log(`背景模式切换为: ${mode}`);
    }
    
    setBlur(radius) {
        this.blurRadius = Math.max(0, Math.min(50, radius));
    }
    
    async setCustomImage(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    this.customImage = img;
                    this.log('自定义背景图片已加载');
                    resolve();
                };
                img.onerror = reject;
                img.src = e.target.result;
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }
    
    async setCustomImageFromUrl(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                this.customImage = img;
                this.log('自定义背景图片已加载');
                resolve();
            };
            img.onerror = reject;
            img.src = url;
        });
    }
    
    drawBackground() {
        this.ctx.save();
        
        if (this.blurRadius > 0) {
            this.ctx.filter = `blur(${this.blurRadius}px)`;
        }
        
        switch (this.currentMode) {
            case 'green':
                this.drawSolidBackground(this.greenScreenColor);
                break;
            case 'blue':
                this.drawSolidBackground(this.blueScreenColor);
                break;
            case 'image':
                this.drawImageBackground();
                break;
            case 'default':
            default:
                this.drawDefaultBackground();
                break;
        }
        
        this.ctx.restore();
    }
    
    drawDefaultBackground() {
        this.initDefaultBackground();
        this.ctx.fillStyle = this.defaultGradient;
        this.ctx.fillRect(0, 0, this.avatarCanvas.width, this.avatarCanvas.height);
    }
    
    drawSolidBackground(color) {
        this.ctx.fillStyle = `rgb(${color.r}, ${color.g}, ${color.b})`;
        this.ctx.fillRect(0, 0, this.avatarCanvas.width, this.avatarCanvas.height);
    }
    
    drawImageBackground() {
        if (this.customImage) {
            const imgRatio = this.customImage.width / this.customImage.height;
            const canvasRatio = this.avatarCanvas.width / this.avatarCanvas.height;
            
            let drawWidth, drawHeight, offsetX, offsetY;
            
            if (imgRatio > canvasRatio) {
                drawHeight = this.avatarCanvas.height;
                drawWidth = drawHeight * imgRatio;
                offsetX = (this.avatarCanvas.width - drawWidth) / 2;
                offsetY = 0;
            } else {
                drawWidth = this.avatarCanvas.width;
                drawHeight = drawWidth / imgRatio;
                offsetX = 0;
                offsetY = (this.avatarCanvas.height - drawHeight) / 2;
            }
            
            this.ctx.drawImage(
                this.customImage,
                offsetX, offsetY,
                drawWidth, drawHeight
            );
        } else {
            this.drawDefaultBackground();
        }
    }
    
    setGreenScreenColor(r, g, b) {
        this.greenScreenColor = { r, g, b };
    }
    
    setBlueScreenColor(r, g, b) {
        this.blueScreenColor = { r, g, b };
    }
    
    applyChromaKey(videoFrame, keyColor, threshold = 0.2) {
        const imageData = this.ctx.getImageData(0, 0, this.avatarCanvas.width, this.avatarCanvas.height);
        const data = imageData.data;
        
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            
            const distance = Math.sqrt(
                Math.pow(r - keyColor.r, 2) +
                Math.pow(g - keyColor.g, 2) +
                Math.pow(b - keyColor.b, 2)
            ) / 255;
            
            if (distance < threshold) {
                data[i + 3] = 0;
            }
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }
    
    hasCustomImage() {
        return this.customImage !== null;
    }
    
    getCurrentMode() {
        return this.currentMode;
    }
    
    log(message) {
        const debugInfo = document.getElementById('debugInfo');
        if (debugInfo) {
            const timestamp = new Date().toLocaleTimeString();
            const newContent = `<div style="color: #FFA500">[${timestamp}] ${message}</div>` + debugInfo.innerHTML;
            debugInfo.innerHTML = newContent.substring(0, 3000);
        }
    }
}
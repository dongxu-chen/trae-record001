const WebGLUtils = {
    createShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error('Shader compile error:', gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }
        return shader;
    },

    createProgram(gl, vertexSource, fragmentSource) {
        const vertexShader = this.createShader(gl, gl.VERTEX_SHADER, vertexSource);
        const fragmentShader = this.createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
        
        if (!vertexShader || !fragmentShader) return null;
        
        const program = gl.createProgram();
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);
        
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            console.error('Program link error:', gl.getProgramInfoLog(program));
            return null;
        }
        
        return program;
    },

    createBuffer(gl, data, type = gl.ARRAY_BUFFER, usage = gl.STATIC_DRAW) {
        const buffer = gl.createBuffer();
        gl.bindBuffer(type, buffer);
        gl.bufferData(type, data, usage);
        return buffer;
    },

    createTexture(gl, width, height, data = null) {
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        return texture;
    },

    createFramebuffer(gl, width, height) {
        const framebuffer = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
        
        const texture = this.createTexture(gl, width, height);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
        
        const depthBuffer = gl.createRenderbuffer();
        gl.bindRenderbuffer(gl.RENDERBUFFER, depthBuffer);
        gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, width, height);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, depthBuffer);
        
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        
        return { framebuffer, texture, depthBuffer };
    },

    resizeFramebuffer(gl, fbo, width, height) {
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo.framebuffer);
        
        gl.bindTexture(gl.TEXTURE_2D, fbo.texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        
        gl.bindRenderbuffer(gl.RENDERBUFFER, fbo.depthBuffer);
        gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, width, height);
        
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    }
};
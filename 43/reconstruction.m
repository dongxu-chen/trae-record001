function [x_recon, history] = reconstruction(kspace_undersampled, mask, options)
% RECONSTRUCTION  基于 FISTA 的压缩感知 MRI 图像重建 (支持 GPU 加速)
%   [x_recon, history] = reconstruction(kspace_undersampled, mask, options)
%
%   最小化问题: 0.5*||M·F·x - y||_2^2 + lambda*||W·x||_1
%
%   GPU 加速: 自动检测输入是否为 gpuArray，若检测到 GPU 则在 GPU 上执行
%   可通过 options.use_gpu = true 强制启用 GPU（需安装 Parallel Computing Toolbox）
%
%   options 新增字段:
%       .use_gpu: 是否使用 GPU (默认自动检测)
%       .gather_output: 是否将结果传回 CPU (默认 true)
%       .pad_mode: 小波边界延拓模式 (默认 'symmetric')

if nargin < 3
    options = struct();
end

lambda = get_option(options, 'lambda', 0.01);
max_iter = get_option(options, 'max_iter', 100);
tol = get_option(options, 'tol', 1e-6);
wavelet_level = get_option(options, 'wavelet_level', 3);
verbose = get_option(options, 'verbose', true);
use_backtracking = get_option(options, 'use_backtracking', true);
L_min = get_option(options, 'L_min', 1e-3);
L_max = get_option(options, 'L_max', 1e3);
pad_mode = get_option(options, 'pad_mode', 'symmetric');
use_gpu = get_option(options, 'use_gpu', []);
gather_output = get_option(options, 'gather_output', true);

has_gpu_toolbox = license('test', 'Parallel_Toolbox');
if isempty(use_gpu)
    use_gpu = has_gpu_toolbox && isa(kspace_undersampled, 'gpuArray');
end

if use_gpu && ~has_gpu_toolbox
    warning('Parallel Computing Toolbox 不可用，将使用 CPU 计算');
    use_gpu = false;
end

if use_gpu && verbose
    gpu = gpuDevice;
    fprintf('使用 GPU: %s\n', gpu.Name);
end

y = kspace_undersampled;
[rows, cols] = size(y);

if use_gpu
    if ~isa(y, 'gpuArray')
        y = gpuArray(y);
    end
    if ~isa(mask, 'gpuArray')
        mask = gpuArray(mask);
    end
    zeros_func = @gpuArray.zeros;
else
    zeros_func = @zeros;
end

L = 1.0;

x = zeros_func(rows, cols);
x_prev = x;
t = 1.0;

history.obj = zeros(max_iter, 1);
history.error = zeros(max_iter, 1);
history.L = zeros(max_iter, 1);
history.use_gpu = use_gpu;

grad_prev = [];
x_prev2 = [];

if use_gpu && verbose
    tic;
end

for k = 1:max_iter
    
    w = x + ((t - 1) / (t + 1)) * (x - x_prev);
    
    grad = compute_gradient(w, y, mask, use_gpu);
    
    if k > 1 && ~isempty(grad_prev) && ~isempty(x_prev2)
        s = w(:) - x_prev2(:);
        y_grad = grad(:) - grad_prev(:);
        s_norm_sq = sum(abs(s).^2);
        if s_norm_sq > 1e-15
            L_bb = abs(sum(conj(y_grad) .* s)) / s_norm_sq;
            L_bb = max(L_min, min(L_max, L_bb));
            L = 0.5 * L + 0.5 * L_bb;
        end
    end
    
    if use_backtracking
        eta = 1.5;
        max_backtrack = 10;
        f_w = compute_data_fidelity(w, y, mask, use_gpu);
        grad_w = grad;
        
        for bt = 1:max_backtrack
            y_step = w - (1/L) * grad_w;
            coeff = wavelet(y_step, 'forward', wavelet_level, pad_mode);
            coeff_thresh = soft_threshold(coeff, lambda / L);
            x_candidate = wavelet(coeff_thresh, 'inverse', wavelet_level, pad_mode);
            
            f_x = compute_data_fidelity(x_candidate, y, mask, use_gpu);
            
            diff = x_candidate(:) - w(:);
            q = f_w + real(sum(conj(grad_w(:)) .* diff)) + ...
                (L/2) * sum(abs(diff).^2);
            
            if f_x <= q + 1e-10 * max(1, abs(f_w))
                break;
            end
            L = min(L_max, L * eta);
        end
        
        x_new = x_candidate;
    else
        y_step = w - (1/L) * grad;
        coeff = wavelet(y_step, 'forward', wavelet_level, pad_mode);
        coeff_thresh = soft_threshold(coeff, lambda / L);
        x_new = wavelet(coeff_thresh, 'inverse', wavelet_level, pad_mode);
    end
    
    t_new = (1 + sqrt(1 + 4*t^2)) / 2;
    
    if k > 1
        x_norm = norm(x(:));
        if x_norm > 0
            history.error(k) = gather(norm(x_new(:) - x(:)) / x_norm);
        else
            history.error(k) = gather(norm(x_new(:) - x(:)));
        end
        if history.error(k) < tol && verbose
            fprintf('Converged at iteration %d\n', k);
            break;
        end
    end
    
    x_prev2 = w;
    grad_prev = grad;
    
    x_prev = x;
    x = x_new;
    t = t_new;
    
    history.obj(k) = gather(compute_objective(x, y, mask, lambda, ...
                                wavelet_level, pad_mode, use_gpu));
    history.L(k) = L;
    
    if verbose && mod(k, 10) == 0
        fprintf('Iter %4d: Objective = %.6e, Rel. Change = %.2e, L = %.2e\n', ...
                k, history.obj(k), history.error(k), L);
    end
end

if use_gpu && verbose
    gpu_time = toc;
    fprintf('GPU 计算时间: %.2f 秒\n', gpu_time);
end

if use_gpu && gather_output
    x_recon = gather(x);
else
    x_recon = x;
end

history.obj = history.obj(1:k);
history.error = history.error(1:k);
history.L = history.L(1:k);

end

function grad = compute_gradient(x, y, mask, use_gpu)
F_x = fftshift(fft2(ifftshift(x)));
residual = mask .* F_x - y;
grad = fftshift(ifft2(ifftshift(mask .* residual)));
grad = real(grad);
end

function val = compute_data_fidelity(x, y, mask, use_gpu)
F_x = fftshift(fft2(ifftshift(x)));
val = 0.5 * sum(abs(mask(:) .* F_x(:) - y(:)).^2);
end

function val = compute_objective(x, y, mask, lambda, wavelet_level, pad_mode, use_gpu)
data_term = compute_data_fidelity(x, y, mask, use_gpu);
coeff = wavelet(x, 'forward', wavelet_level, pad_mode);
reg_term = lambda * sum(abs(coeff(:)));
val = data_term + reg_term;
end

function y = soft_threshold(x, thresh)
y = sign(x) .* max(abs(x) - thresh, 0);
end

function val = get_option(options, name, default)
if isfield(options, name)
    val = options.(name);
else
    val = default;
end
end

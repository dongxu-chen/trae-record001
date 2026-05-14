function [x_recon, history, coil_images] = parallel_recon(kspace_undersampled, mask, coil_maps, options)
% PARALLEL_RECON  多线圈并行 MRI 图像重建 (SENSE + 压缩感知 + GPU 加速)
%   [x_recon, history, coil_images] = parallel_recon(kspace_undersampled, mask, coil_maps, options)
%
%   最小化问题 (SENSE + L1 正则化):
%       min_x  0.5 * sum_c ||M·F·S_c·x - y_c||_2^2 + lambda·||W·x||_1
%   其中 S_c 是第 c 个线圈的灵敏度算子
%
%   参数:
%       kspace_undersampled: 欠采样 k-space 数据，尺寸 [rows, cols, num_coils]
%       mask: 采样掩膜 [rows, cols] (所有线圈共享)
%       coil_maps: 线圈灵敏度图，尺寸 [rows, cols, num_coils]
%       options: 参数字段
%           .lambda: L1 正则化参数 (默认 0.01)
%           .max_iter: 最大迭代次数 (默认 150)
%           .tol: 收敛阈值 (默认 1e-6)
%           .wavelet_level: 小波分解层数 (默认 3)
%           .pad_mode: 小波边界延拓 (默认 'symmetric')
%           .use_gpu: 是否使用 GPU (默认自动检测)
%           .gather_output: 是否将结果传回 CPU (默认 true)
%           .verbose: 是否显示信息 (默认 true)
%           .recon_type: 重建类型
%               'sense_cs':  SENSE + 压缩感知 (默认)
%               'sense':     仅 SENSE (无正则化)
%               'pils':      并行成像 + 小波正则化
%           .use_backtracking: 是否使用回溯线搜索 (默认 true)
%
%   返回:
%       x_recon: 重建的复合图像
%       history: 迭代历史
%       coil_images: 各线圈重建的图像 (可选)
%
%   示例:
%       % 生成模拟数据
%       img = phantom(256);
%       [coil_maps, ~] = generate_coil_maps(256, 256, 8);
%       [kspace, mask] = cartesian_simulation(img, struct('accel_factor', 4, 'pattern', 'uniform'));
%       kspace_coils = zeros(256, 256, 8);
%       for c = 1:8
%           img_coil = img .* coil_maps(:,:,c);
%           kspace_full = fftshift(fft2(ifftshift(img_coil)));
%           kspace_coils(:,:,c) = kspace_full .* mask;
%       end
%       % 并行重建
%       [x_recon, hist] = parallel_recon(kspace_coils, mask, coil_maps, struct('lambda', 0.005));

if nargin < 4
    options = struct();
end

lambda = get_opt(options, 'lambda', 0.01);
max_iter = get_opt(options, 'max_iter', 150);
tol = get_opt(options, 'tol', 1e-6);
wavelet_level = get_opt(options, 'wavelet_level', 3);
pad_mode = get_opt(options, 'pad_mode', 'symmetric');
use_gpu = get_opt(options, 'use_gpu', []);
gather_output = get_opt(options, 'gather_output', true);
verbose = get_opt(options, 'verbose', true);
recon_type = get_opt(options, 'recon_type', 'sense_cs');
use_backtracking = get_opt(options, 'use_backtracking', true);

[rows, cols, num_coils] = size(kspace_undersampled);

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
    fprintf('并行重建 - 使用 GPU: %s\n', gpu.Name);
    fprintf('线圈数量: %d, 图像尺寸: %dx%d\n', num_coils, rows, cols);
end

if strcmpi(recon_type, 'sense')
    lambda = 0;
end

if use_gpu
    if ~isa(kspace_undersampled, 'gpuArray')
        kspace_undersampled = gpuArray(kspace_undersampled);
    end
    if ~isa(mask, 'gpuArray')
        mask = gpuArray(mask);
    end
    if ~isa(coil_maps, 'gpuArray')
        coil_maps = gpuArray(coil_maps);
    end
    zeros_func = @gpuArray.zeros;
else
    zeros_func = @zeros;
end

y = kspace_undersampled;
S = coil_maps;
M = mask;

x = zeros_func(rows, cols);
x_prev = x;
t = 1.0;

L = 1.0;
L_min = 1e-3;
L_max = 1e3;

history.obj = zeros(max_iter, 1);
history.error = zeros(max_iter, 1);
history.L = zeros(max_iter, 1);
history.use_gpu = use_gpu;
history.num_coils = num_coils;

grad_prev = [];
x_prev2 = [];

if use_gpu && verbose
    tic;
end

for k = 1:max_iter
    
    w = x + ((t - 1) / (t + 1)) * (x - x_prev);
    
    grad = compute_sense_gradient(w, y, M, S, use_gpu);
    
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
    
    if use_backtracking && lambda > 0
        eta = 1.5;
        max_backtrack = 10;
        f_w = compute_sense_data_fidelity(w, y, M, S, use_gpu);
        grad_w = grad;
        
        for bt = 1:max_backtrack
            y_step = w - (1/L) * grad_w;
            coeff = wavelet(y_step, 'forward', wavelet_level, pad_mode);
            coeff_thresh = soft_threshold(coeff, lambda / L);
            x_candidate = wavelet(coeff_thresh, 'inverse', wavelet_level, pad_mode);
            
            f_x = compute_sense_data_fidelity(x_candidate, y, M, S, use_gpu);
            
            diff = x_candidate(:) - w(:);
            q = f_w + real(sum(conj(grad_w(:)) .* diff)) + ...
                (L/2) * sum(abs(diff).^2);
            
            if f_x <= q + 1e-10 * max(1, abs(f_w))
                break;
            end
            L = min(L_max, L * eta);
        end
        
        x_new = x_candidate;
    elseif lambda > 0
        y_step = w - (1/L) * grad;
        coeff = wavelet(y_step, 'forward', wavelet_level, pad_mode);
        coeff_thresh = soft_threshold(coeff, lambda / L);
        x_new = wavelet(coeff_thresh, 'inverse', wavelet_level, pad_mode);
    else
        x_new = w - (1/L) * grad;
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
    
    history.obj(k) = gather(compute_sense_objective(x, y, M, S, lambda, ...
                                wavelet_level, pad_mode, use_gpu));
    history.L(k) = L;
    
    if verbose && mod(k, 10) == 0
        fprintf('Iter %4d: Objective = %.6e, Rel. Change = %.2e, L = %.2e\n', ...
                k, history.obj(k), history.error(k), L);
    end
end

if use_gpu && verbose
    gpu_time = toc;
    fprintf('并行重建时间: %.2f 秒\n', gpu_time);
end

if nargout >= 3
    coil_images = zeros(rows, cols, num_coils);
    for c = 1:num_coils
        coil_images(:,:,c) = x .* S(:,:,c);
    end
    if use_gpu && gather_output
        coil_images = gather(coil_images);
    end
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

function grad = compute_sense_gradient(x, y, M, S, use_gpu)
[rows, cols, num_coils] = size(S);
grad = zeros(rows, cols, 'like', x);

for c = 1:num_coils
    x_coil = x .* S(:,:,c);
    F_x = fftshift(fft2(ifftshift(x_coil)));
    residual = M .* F_x - y(:,:,c);
    grad_kspace = fftshift(ifft2(ifftshift(M .* residual)));
    grad = grad + real(conj(S(:,:,c)) .* grad_kspace);
end

end

function val = compute_sense_data_fidelity(x, y, M, S, use_gpu)
[~, ~, num_coils] = size(S);
val = 0;

for c = 1:num_coils
    x_coil = x .* S(:,:,c);
    F_x = fftshift(fft2(ifftshift(x_coil)));
    val = val + 0.5 * sum(abs(M(:) .* F_x(:) - y(:,:,c)(:)).^2);
end

end

function val = compute_sense_objective(x, y, M, S, lambda, wavelet_level, pad_mode, use_gpu)
data_term = compute_sense_data_fidelity(x, y, M, S, use_gpu);

if lambda > 0
    coeff = wavelet(x, 'forward', wavelet_level, pad_mode);
    reg_term = lambda * sum(abs(coeff(:)));
else
    reg_term = 0;
end

val = data_term + reg_term;

end

function y = soft_threshold(x, thresh)
y = sign(x) .* max(abs(x) - thresh, 0);
end

function val = get_opt(options, name, default)
if isfield(options, name)
    val = options.(name);
else
    val = default;
end
end

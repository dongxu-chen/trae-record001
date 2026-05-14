function demo_parallel_gpu()
% DEMO_PARALLEL_GPU  并行成像 + GPU 加速完整演示
%
% 此脚本演示:
%   1. 笛卡尔欠采样
%   2. 多线圈并行成像 (SENSE)
%   3. GPU 加速 (如可用)
%   4. 压缩感知 + 并行成像联合重建

clc; close all; clear;

fprintf('========================================\n');
fprintf('并行成像 + GPU 加速演示\n');
fprintf('========================================\n\n');

N = 256;
num_coils = 8;
accel_factor = 4;

fprintf('参数设置:\n');
fprintf('  图像大小: %d x %d\n', N, N);
fprintf('  线圈数量: %d\n', num_coils);
fprintf('  加速倍数: R = %d\n', accel_factor);
fprintf('\n');

has_gpu = license('test', 'Parallel_Toolbox');
if has_gpu
    try
        gpu = gpuDevice;
        fprintf('检测到 GPU: %s\n', gpu.Name);
        use_gpu = true;
    catch ME
        fprintf('GPU 不可用: %s\n', ME.message);
        use_gpu = false;
    end
else
    fprintf('未检测到 Parallel Computing Toolbox\n');
    use_gpu = false;
end
fprintf('\n');

fprintf('步骤 1: 生成模拟数据...\n');
img = generate_phantom(N);
fprintf('  体模生成完成.\n');

fprintf('步骤 2: 生成线圈灵敏度图...\n');
[coil_maps, coil_pos] = generate_coil_maps(N, N, num_coils);
fprintf('  线圈位置:\n');
disp(coil_pos);

fprintf('步骤 3: 笛卡尔欠采样...\n');
cart_opt = struct();
cart_opt.accel_factor = accel_factor;
cart_opt.pattern = 'variable';
cart_opt.direction = 'phase';
cart_opt.center_fraction = 0.1;
cart_opt.seed = 42;

[kspace_demo, mask, mask_info] = cartesian_simulation(img, cart_opt);
fprintf('  实际采样率: %.2f%%\n', mask_info.sampling_ratio * 100);
fprintf('  采样模式: %s\n', mask_info.pattern);

fprintf('步骤 4: 生成多线圈 k-space 数据...\n');
kspace_coils = zeros(N, N, num_coils);
for c = 1:num_coils
    img_coil = img .* coil_maps(:,:,c);
    kspace_full = fftshift(fft2(ifftshift(img_coil)));
    kspace_coils(:,:,c) = kspace_full .* mask;
end
fprintf('  完成.\n');

fprintf('\n');
fprintf('========================================\n');
fprintf('重建 1: 单线圈压缩感知 (用于对比)\n');
fprintf('========================================\n');

opt_single = struct();
opt_single.lambda = 0.02;
opt_single.max_iter = 100;
opt_single.tol = 1e-5;
opt_single.wavelet_level = 4;
opt_single.verbose = true;
opt_single.use_gpu = use_gpu;

[x_single, hist_single] = reconstruction(kspace_demo, mask, opt_single);

fprintf('\n');
fprintf('========================================\n');
fprintf('重建 2: 多线圈 SENSE + 压缩感知\n');
fprintf('========================================\n');

opt_parallel = struct();
opt_parallel.lambda = 0.01;
opt_parallel.max_iter = 150;
opt_parallel.tol = 1e-5;
opt_parallel.wavelet_level = 4;
opt_parallel.verbose = true;
opt_parallel.use_gpu = use_gpu;
opt_parallel.recon_type = 'sense_cs';

[x_parallel, hist_parallel, coil_imgs] = parallel_recon(kspace_coils, mask, coil_maps, opt_parallel);

fprintf('\n');
fprintf('========================================\n');
fprintf('结果展示\n');
fprintf('========================================\n');

zero_fill = fftshift(ifft2(ifftshift(kspace_demo)));

rmse_zero = sqrt(mean((abs(img(:)) - abs(zero_fill(:))).^2));
rmse_single = sqrt(mean((abs(img(:)) - abs(x_single(:))).^2));
rmse_parallel = sqrt(mean((abs(img(:)) - abs(x_parallel(:))).^2));

fprintf('\n重建质量评估:\n');
fprintf('  零填充 RMSE:     %.6f\n', rmse_zero);
fprintf('  单线圈 CS RMSE:  %.6f\n', rmse_single);
fprintf('  并行成像 RMSE:   %.6f\n', rmse_parallel);

figure('Position', [100, 100, 1400, 800]);

subplot(2, 5, 1);
imagesc(abs(img)); axis image; colormap gray;
title('原始图像'); colorbar;

subplot(2, 5, 2);
imagesc(mask); axis image; colormap gray;
title(sprintf('采样掩膜 (R=%.1f)', accel_factor));

subplot(2, 5, 3);
imagesc(abs(zero_fill)); axis image; colormap gray;
title('零填充'); colorbar;

subplot(2, 5, 4);
imagesc(abs(x_single)); axis image; colormap gray;
title('单线圈 CS'); colorbar;

subplot(2, 5, 5);
imagesc(abs(x_parallel)); axis image; colormap gray;
title('SENSE + CS'); colorbar;

subplot(2, 5, 6);
montage(abs(coil_maps), 'Size', [2, 4]);
title('线圈灵敏度图');

subplot(2, 5, 7);
montage(abs(coil_imgs), 'Size', [2, 4]);
title('各线圈重建');

subplot(2, 5, [8, 9]);
semilogy(hist_single.obj, 'b-', 'LineWidth', 1.5); hold on;
semilogy(hist_parallel.obj, 'r-', 'LineWidth', 1.5);
grid on;
legend('单线圈 CS', 'SENSE + CS');
xlabel('迭代次数');
ylabel('目标函数');
title('收敛曲线');

subplot(2, 5, 10);
diff = abs(img - x_parallel);
imagesc(diff); axis image; colormap hot;
title(sprintf('并行误差 (RMSE=%.4f)', rmse_parallel));
colorbar;

sgtitle(sprintf('并行成像 R=%d 加速演示', accel_factor));

end

function phantom = generate_phantom(N)

[X, Y] = meshgrid(linspace(-1, 1, N));

ellipses = [
    1.0,    0.69,   0.92,   0.0,    0.0,    0.0;
    -0.8,   0.6624, 0.8740, 0.0,   -0.0184, 0.0;
    -0.2,   0.1100, 0.3100, 0.22,   0.0,    -18;
    -0.2,   0.1600, 0.4100, -0.22,  0.0,    18;
    0.1,    0.2100, 0.2500, 0.0,    0.35,   0.0;
    0.1,    0.0460, 0.0460, 0.0,    0.1,    0.0;
    0.1,    0.0460, 0.0460, 0.0,   -0.1,    0.0;
];

phantom = zeros(N, N);

for i = 1:size(ellipses, 1)
    A = ellipses(i, 1);
    a = ellipses(i, 2);
    b = ellipses(i, 3);
    x0 = ellipses(i, 4);
    y0 = ellipses(i, 5);
    phi = ellipses(i, 6) * pi / 180;
    
    x_rot = (X - x0) * cos(phi) + (Y - y0) * sin(phi);
    y_rot = -(X - x0) * sin(phi) + (Y - y0) * cos(phi);
    
    ellipse = ((x_rot / a).^2 + (y_rot / b).^2) <= 1;
    phantom = phantom + A * ellipse;
end

phantom = max(phantom, 0);
phantom = phantom / max(phantom(:));

end

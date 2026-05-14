function main_example()
% MAIN_EXAMPLE  压缩感知 MRI 重建完整示例
%
% 此脚本演示完整的流程:
%   1. 生成模拟 MRI 图像 (Shepp-Logan 体模)
%   2. 模拟 k-space 欠采样
%   3. 使用 FISTA 进行压缩感知重建
%   4. 显示并评估结果

clc; close all; clear;

fprintf('========================================\n');
fprintf('压缩感知 MRI 重建 - FISTA 算法演示\n');
fprintf('========================================\n\n');

N = 256;
sampling_ratio = 0.3;
pattern_type = 'variable_density';

fprintf('参数设置:\n');
fprintf('  图像大小: %d x %d\n', N, N);
fprintf('  采样率:   %.1f%%\n', sampling_ratio * 100);
fprintf('  采样模式: %s\n', pattern_type);
fprintf('\n');

fprintf('步骤 1: 生成模拟 MRI 图像...\n');
original = generate_phantom(N);
fprintf('  完成.\n\n');

fprintf('步骤 2: 模拟 k-space 欠采样...\n');
[kspace_undersampled, mask, ~] = kspace_simulation(original, sampling_ratio, pattern_type);
actual_ratio = sum(mask(:)) / numel(mask);
fprintf('  实际采样率: %.1f%%\n', actual_ratio * 100);
fprintf('  完成.\n\n');

fprintf('步骤 3: 零填充重建 (用于对比)...\n');
undersampled_recon = fftshift(ifft2(ifftshift(kspace_undersampled)));
fprintf('  完成.\n\n');

fprintf('步骤 4: FISTA 压缩感知重建...\n');
options = struct();
options.lambda = 0.05;
options.max_iter = 150;
options.tol = 1e-5;
options.wavelet_level = 4;
options.verbose = true;

[x_recon, history] = reconstruction(kspace_undersampled, mask, options);
fprintf('  完成.\n\n');

fprintf('步骤 5: 显示结果...\n');
display(original, undersampled_recon, x_recon, mask, history);

end

function phantom = generate_phantom(N)
% GENERATE_PHANTOM  生成 Shepp-Logan 体模图像

[X, Y] = meshgrid(linspace(-1, 1, N));

ellipses = [
    1.0,    0.69,   0.92,   0.0,    0.0,    0.0;
    -0.8,   0.6624, 0.8740, 0.0,   -0.0184, 0.0;
    -0.2,   0.1100, 0.3100, 0.22,   0.0,    -18;
    -0.2,   0.1600, 0.4100, -0.22,  0.0,    18;
    0.1,    0.2100, 0.2500, 0.0,    0.35,   0.0;
    0.1,    0.0460, 0.0460, 0.0,    0.1,    0.0;
    0.1,    0.0460, 0.0460, 0.0,   -0.1,    0.0;
    0.1,    0.0460, 0.0460, -0.08,  -0.605, 0.0;
    0.1,    0.0230, 0.0230, 0.0,   -0.606, 0.0;
    0.1,    0.0460, 0.0460, 0.06,  -0.605, 0.0;
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

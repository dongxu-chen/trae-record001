function [coil_maps, coil_positions] = generate_coil_maps(rows, cols, num_coils, options)
% GENERATE_COIL_MAPS  生成模拟的相控阵线圈灵敏度图
%   [coil_maps, coil_positions] = generate_coil_maps(rows, cols, num_coils, options)
%
%   使用鸟笼式或环形线圈模型生成平滑的灵敏度分布
%
%   参数:
%       rows, cols: 图像尺寸
%       num_coils: 线圈数量 (默认 8)
%       options: 参数字段
%           .coil_type: 'birdcage' (鸟笼) 或 'circular' (环形) (默认 'birdcage')
%           .radius: 线圈半径 (图像半宽的比例, 默认 0.75)
%           .coil_width: 线圈宽度 (平滑因子, 默认 0.2)
%           .fov_ratio: 视野比例 (默认 0.9)
%           .use_gpu: 是否返回 gpuArray (默认 false)
%
%   返回:
%       coil_maps: 尺寸 [rows, cols, num_coils] 的复灵敏度图
%       coil_positions: 各线圈中心位置 [num_coils, 2]
%
%   示例:
%       % 生成 8 通道鸟笼线圈灵敏度图
%       [coil_maps, pos] = generate_coil_maps(256, 256, 8);
%       figure; montage(abs(coil_maps), 'Size', [2, 4]);

if nargin < 3
    num_coils = 8;
end
if nargin < 4
    options = struct();
end

coil_type = get_opt(options, 'coil_type', 'birdcage');
radius_ratio = get_opt(options, 'radius', 0.75);
coil_width = get_opt(options, 'coil_width', 0.2);
fov_ratio = get_opt(options, 'fov_ratio', 0.9);
use_gpu = get_opt(options, 'use_gpu', false);

[Y, X] = meshgrid(linspace(-1, 1, cols), linspace(-1, 1, rows));

center_x = (cols + 1) / 2;
center_y = (rows + 1) / 2;

coil_maps = zeros(rows, cols, num_coils);
coil_positions = zeros(num_coils, 2);

radius = min(rows, cols) / 2 * radius_ratio;

for c = 1:num_coils
    
    if strcmpi(coil_type, 'birdcage')
        theta = (c - 1) * 2 * pi / num_coils;
    else
        theta = (c - 1) * 2 * pi / num_coils + pi / num_coils;
    end
    
    cx = center_x + radius * cos(theta);
    cy = center_y + radius * sin(theta);
    
    coil_positions(c, :) = [cx, cy];
    
    [Xc, Yc] = meshgrid((1:cols) - cx, (1:rows) - cy);
    
    dist = sqrt(Xc.^2 + Yc.^2);
    
    sigma = min(rows, cols) * coil_width;
    amp = exp(-dist.^2 / (2 * sigma^2));
    
    [X_fov, Y_fov] = meshgrid(linspace(-1, 1, cols), linspace(-1, 1, rows));
    R_fov = sqrt(X_fov.^2 + Y_fov.^2);
    fov_mask = exp(-(R_fov / fov_ratio).^8);
    
    phase = angle((X + 1i*Y) - (cx/cols*2 - 1 + 1i*(cy/rows*2 - 1)));
    
    coil_maps(:,:,c) = amp .* fov_mask .* exp(1i * phase);
end

total_power = sqrt(sum(abs(coil_maps).^2, 3));
total_power(total_power == 0) = 1;
for c = 1:num_coils
    coil_maps(:,:,c) = coil_maps(:,:,c) ./ total_power;
end

if use_gpu && license('test', 'Parallel_Toolbox')
    coil_maps = gpuArray(coil_maps);
end

end

function val = get_opt(options, name, default)
if isfield(options, name)
    val = options.(name);
else
    val = default;
end
end

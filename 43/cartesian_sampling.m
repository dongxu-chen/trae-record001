function [kspace_undersampled, mask, mask_pattern] = cartesian_simulation(img, options)
% CARTESIAN_SIMULATION  笛卡尔 (Cartesian) 网格 k-space 欠采样模拟
%   [kspace_undersampled, mask, mask_pattern] = cartesian_simulation(img, options)
%
%   笛卡尔采样是 MRI 最常用的采样方式，沿相位编码方向 (PE) 进行欠采样
%
%   参数:
%       img: 输入图像 (2D 矩阵)
%       options: 参数字段
%           .sampling_ratio: 整体采样率 (默认 0.3)
%           .accel_factor: 加速倍数 R (若指定则覆盖 sampling_ratio)
%           .direction: 欠采样方向 - 'phase' (行方向), 'readout' (列方向) (默认 'phase')
%           .pattern: 采样模式类型
%               'uniform':     均匀隔行采样 (标准并行成像)
%               'random':      随机相位编码线
%               'variable':    可变密度 (中心高密度)
%               'poisson_disk': 泊松圆盘采样
%           .center_fraction: 中心 k-space 全采样比例 (默认 0.08)
%           .use_gpu: 是否返回 gpuArray (默认 false)
%           .seed: 随机数种子 (默认 42)
%
%   返回:
%       kspace_undersampled: 欠采样 k-space 数据
%       mask: 采样掩膜 (1=采样, 0=未采样)
%       mask_pattern: 采样模式信息结构体
%
%   示例:
%       % 4 倍加速的均匀笛卡尔采样
%       [k_u, m] = cartesian_simulation(img, struct('accel_factor', 4, 'pattern', 'uniform'));
%       
%       % 可变密度采样用于压缩感知
%       [k_u, m] = cartesian_simulation(img, struct('sampling_ratio', 0.25, 'pattern', 'variable'));

if nargin < 2
    options = struct();
end

sampling_ratio = get_opt(options, 'sampling_ratio', 0.3);
accel_factor = get_opt(options, 'accel_factor', []);
direction = get_opt(options, 'direction', 'phase');
pattern = get_opt(options, 'pattern', 'variable');
center_fraction = get_opt(options, 'center_fraction', 0.08);
use_gpu = get_opt(options, 'use_gpu', false);
seed = get_opt(options, 'seed', 42);

[rows, cols] = size(img);

if strcmpi(direction, 'phase')
    pe_lines = rows;
    ro_lines = cols;
else
    pe_lines = cols;
    ro_lines = rows;
end

rng(seed);

if ~isempty(accel_factor)
    sampling_ratio = 1 / accel_factor;
end

mask = generate_cartesian_mask(pe_lines, ro_lines, sampling_ratio, ...
                                pattern, center_fraction, direction);

kspace_full = fftshift(fft2(ifftshift(img)));
kspace_undersampled = kspace_full .* mask;

mask_pattern = struct();
mask_pattern.type = 'cartesian';
mask_pattern.direction = direction;
mask_pattern.pattern = pattern;
mask_pattern.sampling_ratio = sum(mask(:)) / numel(mask);
mask_pattern.actual_accel = 1 / mask_pattern.sampling_ratio;
mask_pattern.center_fraction = center_fraction;

if use_gpu
    if license('test', 'Parallel_Toolbox')
        kspace_undersampled = gpuArray(kspace_undersampled);
        mask = gpuArray(mask);
    else
        warning('Parallel Computing Toolbox 不可用');
    end
end

end

function mask = generate_cartesian_mask(pe, ro, ratio, pattern_type, center_frac, direction)

full_center_pe = round(pe * center_frac);
full_center_pe = max(2, 2 * floor(full_center_pe / 2));

mask = false(pe, ro);

center_start = floor((pe - full_center_pe) / 2) + 1;
center_end = center_start + full_center_pe - 1;
mask(center_start:center_end, :) = true;

center_count = full_center_pe * ro;
total_count = pe * ro;
target_count = round(total_count * ratio);
remaining = target_count - center_count;

available_pe = [1:center_start-1, center_end+1:pe];
num_available_pe = length(available_pe);

switch pattern_type
    case 'uniform'
        R = round(1 / ratio);
        R = max(2, R);
        
        offset = randi([0, R-1]);
        for i = 1:length(available_pe)
            pe_idx = available_pe(i);
            if mod(pe_idx - 1 - offset, R) == 0
                mask(pe_idx, :) = true;
            end
        end
        
    case 'random'
        if remaining > 0 && num_available_pe > 0
            pe_to_sample = available_pe(randperm(num_available_pe));
            
            lines_needed = ceil(remaining / ro);
            lines_needed = min(lines_needed, num_available_pe);
            
            for i = 1:lines_needed
                mask(pe_to_sample(i), :) = true;
            end
        end
        
    case 'variable'
        pe_pos = available_pe - pe/2;
        pe_dist = abs(pe_pos) / (pe/2);
        
        p = 1 - pe_dist;
        p = max(p, 0.1);
        p = p / sum(p);
        
        if remaining > 0 && num_available_pe > 0
            lines_needed = ceil(remaining / ro);
            lines_needed = min(lines_needed, num_available_pe);
            
            idx = randsample(1:num_available_pe, lines_needed, true, p);
            idx = unique(idx);
            
            for i = 1:length(idx)
                mask(available_pe(idx(i)), :) = true;
            end
        end
        
    case 'poisson_disk'
        if remaining > 0 && num_available_pe > 0
            mask = poisson_disk_2d(pe, ro, ratio, center_frac);
        end
        
    otherwise
        error('Unknown Cartesian pattern type: %s', pattern_type);
end

if strcmpi(direction, 'readout')
    mask = mask.';
end

mask = double(mask);

end

function mask = poisson_disk_2d(Ny, Nx, ratio, center_frac)

mask = false(Ny, Nx);

cy = Ny / 2;
cx = Nx / 2;
r_center = min(Ny, Nx) * center_frac / 2;

[Y, X] = meshgrid(1:Ny, 1:Nx);
dist = sqrt((Y.' - cy).^2 + (X.' - cx).^2);
mask(dist <= r_center) = true;

center_count = sum(mask(:));
target_count = round(Ny * Nx * ratio);
remaining = target_count - center_count;

if remaining <= 0
    mask = double(mask);
    return;
end

r_min = sqrt(1 / (pi * ratio));
r_max = 2 * r_min;

candidates = find(~mask);
[yc, xc] = ind2sub([Ny, Nx], candidates);

accepted = [];

num_attempts = 50;
for attempt = 1:num_attempts
    if isempty(candidates)
        break;
    end
    
    idx = randi(length(candidates));
    y = yc(idx);
    x = xc(idx);
    
    is_valid = true;
    for i = 1:length(accepted)
        d = sqrt((y - accepted(i, 1))^2 + (x - accepted(i, 2))^2);
        if d < r_min
            is_valid = false;
            break;
        end
    end
    
    if is_valid
        accepted = [accepted; y, x];
        mask(y, x) = true;
        
        candidates(idx) = [];
        yc(idx) = [];
        xc(idx) = [];
        
        if length(accepted) >= remaining
            break;
        end
    end
end

mask = double(mask);

end

function val = get_opt(options, name, default)
if isfield(options, name)
    val = options.(name);
else
    val = default;
end
end

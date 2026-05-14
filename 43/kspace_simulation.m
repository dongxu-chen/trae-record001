function [kspace_undersampled, mask, kspace_full] = kspace_simulation(img, sampling_ratio, pattern_type)
% KSPACE_SIMULATION  模拟 MRI k-space 欠采样
%   [kspace_undersampled, mask, kspace_full] = kspace_simulation(img, sampling_ratio, pattern_type)
%
%   img: 输入图像 (2D 矩阵)
%   sampling_ratio: 采样比例 (0 < ratio < 1)
%   pattern_type: 采样模式 - 'random', 'radial', 'variable_density'
%
%   kspace_undersampled: 欠采样 k-space 数据
%   mask: 采样掩膜 (1=采样, 0=未采样)
%   kspace_full: 完全采样的 k-space 数据

if nargin < 3
    pattern_type = 'variable_density';
end

[rows, cols] = size(img);

kspace_full = fftshift(fft2(ifftshift(img)));

mask = generate_mask(rows, cols, sampling_ratio, pattern_type);

kspace_undersampled = kspace_full .* mask;

end

function mask = generate_mask(rows, cols, sampling_ratio, pattern_type)

rng(42);

switch pattern_type
    case 'random'
        mask = rand(rows, cols) < sampling_ratio;
        
    case 'radial'
        mask = zeros(rows, cols);
        total_samples = rows * cols;
        target_samples = round(total_samples * sampling_ratio);
        
        center_row = (rows + 1) / 2;
        center_col = (cols + 1) / 2;
        
        r = min(rows, cols) / 2;
        samples_per_spoke = 2 * floor(r) + 1;
        
        num_spokes = max(1, round(target_samples / samples_per_spoke));
        
        for k = 1:num_spokes
            theta = (k - 1) * 2 * pi / num_spokes;
            
            end_col = round(center_col + r * cos(theta));
            end_row = round(center_row + r * sin(theta));
            
            line_indices = bresenham_line(round(center_row), round(center_col), ...
                                          end_row, end_col, rows, cols);
            mask(line_indices) = 1;
            
            end_col2 = round(center_col - r * cos(theta));
            end_row2 = round(center_row - r * sin(theta));
            line_indices2 = bresenham_line(round(center_row), round(center_col), ...
                                           end_row2, end_col2, rows, cols);
            mask(line_indices2) = 1;
        end
        
    case 'variable_density'
        [X, Y] = meshgrid(linspace(-1, 1, cols), linspace(-1, 1, rows));
        R = sqrt(X.^2 + Y.^2);
        p = 1 - R;
        p = max(p, 0);
        p = p / max(p(:));
        
        target_count = round(rows * cols * sampling_ratio);
        
        mask = false(rows, cols);
        
        center_radius = min(rows, cols) * 0.08;
        center_x = round(cols/2);
        center_y = round(rows/2);
        for r = 1:rows
            for c = 1:cols
                dist = sqrt((r-center_y)^2 + (c-center_x)^2);
                if dist <= center_radius
                    mask(r, c) = true;
                end
            end
        end
        
        current_count = sum(mask(:));
        remaining = target_count - current_count;
        
        if remaining > 0
            candidates = find(~mask);
            p_candidates = p(candidates);
            p_candidates = p_candidates / sum(p_candidates);
            
            idx = randsample(candidates, min(remaining, length(candidates)), ...
                           true, p_candidates);
            mask(idx) = true;
        end
        
    otherwise
        error('Unknown pattern type');
end

mask = double(mask);

end

function indices = bresenham_line(r0, c0, r1, c1, max_r, max_c)
% BRESENHAM_LINE  使用 Bresenham 算法生成直线上的像素索引

r0 = max(1, min(max_r, r0));
c0 = max(1, min(max_c, c0));
r1 = max(1, min(max_r, r1));
c1 = max(1, min(max_c, c1));

dr = abs(r1 - r0);
dc = abs(c1 - c0);

if dr == 0 && dc == 0
    indices = sub2ind([max_r, max_c], r0, c0);
    return;
end

sr = sign(r1 - r0);
sc = sign(c1 - c0);

if dr > dc
    err = dr / 2;
else
    err = -dc / 2;
end

r = r0;
c = c0;

max_points = dr + dc + 1;
rs = zeros(max_points, 1);
cs = zeros(max_points, 1);
count = 0;

while true
    count = count + 1;
    rs(count) = r;
    cs(count) = c;
    
    if r == r1 && c == c1
        break;
    end
    
    e2 = err;
    
    if e2 > -dr
        err = err - dc;
        r = r + sr;
    end
    
    if e2 < dc
        err = err + dr;
        c = c + sc;
    end
end

rs = rs(1:count);
cs = cs(1:count);

valid = rs >= 1 & rs <= max_r & cs >= 1 & cs <= max_c;
rs = rs(valid);
cs = cs(valid);

indices = sub2ind([max_r, max_c], rs, cs);
indices = unique(indices);

end

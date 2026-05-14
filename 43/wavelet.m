function [result, meta] = wavelet(x, mode, level, pad_mode)
% WAVELET  二维 Haar 小波变换与逆变换 (支持 GPU 加速)
%   [result, meta] = wavelet(x, 'forward', level, pad_mode)
%   [result, meta] = wavelet(x, 'inverse', level, pad_mode)
%
%   自动检测输入是否为 gpuArray，在 GPU 上执行变换
%
%   参数:
%       x: 输入图像 (2D 矩阵) 或 gpuArray
%       mode: 'forward' 或 'inverse'
%       level: 分解层数 (默认 3)
%       pad_mode: 边界延拓 - 'symmetric', 'periodic', 'zero' (默认 'symmetric')
%
%   返回:
%       result: 变换结果，与输入同类型 (CPU 或 GPU)
%       meta: 包含尺寸信息的结构体

persistent global_meta;

if nargin < 3, level = 3; end
if nargin < 4, pad_mode = 'symmetric'; end

is_gpu = isa(x, 'gpuArray');

use_stored_meta = false;
stored_meta = [];

if isstruct(x)
    if isfield(x, 'coeff') && isfield(x, 'meta')
        stored_meta = x.meta;
        x = x.coeff;
        use_stored_meta = true;
    elseif isfield(x, 'data')
        x = x.data;
    end
end

if strcmpi(mode, 'forward')
    [result, meta] = wavelet_forward(x, level, pad_mode, is_gpu);
    global_meta = meta;
elseif strcmpi(mode, 'inverse')
    if use_stored_meta
        result = wavelet_inverse_with_meta(x, level, stored_meta, is_gpu);
        meta = stored_meta;
    elseif ~isempty(global_meta)
        result = wavelet_inverse_with_meta(x, level, global_meta, is_gpu);
        meta = global_meta;
    else
        result = wavelet_inverse_simple(x, level, is_gpu);
        meta = struct();
    end
else
    error('mode must be ''forward'' or ''inverse''');
end

end

function [coeff, meta] = wavelet_forward(img, level, pad_mode, is_gpu)
[rows, cols] = size(img);

if is_gpu
    img = gpuArray(double(img));
    zeros_func = @gpuArray.zeros;
else
    img = double(img);
    zeros_func = @zeros;
end

pad_rows = ceil(rows / (2^level)) * (2^level);
pad_cols = ceil(cols / (2^level)) * (2^level);

meta = struct();
meta.original_size = [rows, cols];
meta.padded_size = [pad_rows, pad_cols];
meta.pad_mode = pad_mode;
meta.level = level;
meta.is_gpu = is_gpu;

if pad_rows ~= rows || pad_cols ~= cols
    img_padded = pad_image(img, pad_rows, pad_cols, pad_mode, is_gpu);
else
    img_padded = img;
end

coeff = img_padded;

for l = 1:level
    r = floor(pad_rows / (2^(l-1)));
    c = floor(pad_cols / (2^(l-1)));
    
    block = coeff(1:r, 1:c);
    
    if mod(r, 2) == 1
        block = pad_1d(block, r + 1, c, pad_mode, 1, is_gpu);
        r = r + 1;
    end
    if mod(c, 2) == 1
        block = pad_1d(block, r, c + 1, pad_mode, 2, is_gpu);
        c = c + 1;
    end
    
    row_even = block(1:2:end, :);
    row_odd  = block(2:2:end, :);
    
    row_low  = (row_even + row_odd) / sqrt(2);
    row_high = (row_even - row_odd) / sqrt(2);
    
    col_even_low = row_low(:, 1:2:end);
    col_odd_low  = row_low(:, 2:2:end);
    col_even_high = row_high(:, 1:2:end);
    col_odd_high  = row_high(:, 2:2:end);
    
    LL = (col_even_low + col_odd_low) / sqrt(2);
    LH = (col_even_low - col_odd_low) / sqrt(2);
    HL = (col_even_high + col_odd_high) / sqrt(2);
    HH = (col_even_high - col_odd_high) / sqrt(2);
    
    r2 = size(LL, 1);
    c2 = size(LL, 2);
    
    coeff(1:r2, 1:c2) = LL;
    coeff(1:r2, c2+1:2*c2) = LH;
    coeff(r2+1:2*r2, 1:c2) = HL;
    coeff(r2+1:2*r2, c2+1:2*c2) = HH;
end

end

function img = wavelet_inverse_with_meta(coeff, level, meta, is_gpu)
rows_full = meta.padded_size(1);
cols_full = meta.padded_size(2);
original_rows = meta.original_size(1);
original_cols = meta.original_size(2);

if is_gpu
    img = gpuArray(double(coeff));
else
    img = double(coeff);
end

for l = level:-1:1
    r2 = floor(rows_full / (2^l));
    c2 = floor(cols_full / (2^l));
    
    LL = img(1:r2, 1:c2);
    LH = img(1:r2, c2+1:2*c2);
    HL = img(r2+1:2*r2, 1:c2);
    HH = img(r2+1:2*r2, c2+1:2*c2);
    
    col_even_low = (LL + LH) / sqrt(2);
    col_odd_low  = (LL - LH) / sqrt(2);
    col_even_high = (HL + HH) / sqrt(2);
    col_odd_high  = (HL - HH) / sqrt(2);
    
    row_low = zeros(2*r2, c2, 'like', LL);
    row_low(1:2:end, :) = col_even_low;
    row_low(2:2:end, :) = col_odd_low;
    
    row_high = zeros(2*r2, c2, 'like', LL);
    row_high(1:2:end, :) = col_even_high;
    row_high(2:2:end, :) = col_odd_high;
    
    row_even = (row_low + row_high) / sqrt(2);
    row_odd  = (row_low - row_high) / sqrt(2);
    
    block = zeros(2*r2, 2*c2, 'like', LL);
    block(1:2:end, :) = row_even;
    block(2:2:end, :) = row_odd;
    
    img(1:2*r2, 1:2*c2) = block;
end

if original_rows < rows_full || original_cols < cols_full
    pad_rows_before = floor((rows_full - original_rows) / 2);
    pad_cols_before = floor((cols_full - original_cols) / 2);
    img = img(pad_rows_before+(1:original_rows), pad_cols_before+(1:original_cols));
end

end

function img = wavelet_inverse_simple(coeff, level, is_gpu)
[rows_full, cols_full] = size(coeff);

if is_gpu
    img = gpuArray(double(coeff));
else
    img = double(coeff);
end

for l = level:-1:1
    r2 = floor(rows_full / (2^l));
    c2 = floor(cols_full / (2^l));
    
    LL = img(1:r2, 1:c2);
    LH = img(1:r2, c2+1:2*c2);
    HL = img(r2+1:2*r2, 1:c2);
    HH = img(r2+1:2*r2, c2+1:2*c2);
    
    col_even_low = (LL + LH) / sqrt(2);
    col_odd_low  = (LL - LH) / sqrt(2);
    col_even_high = (HL + HH) / sqrt(2);
    col_odd_high  = (HL - HH) / sqrt(2);
    
    row_low = zeros(2*r2, c2, 'like', LL);
    row_low(1:2:end, :) = col_even_low;
    row_low(2:2:end, :) = col_odd_low;
    
    row_high = zeros(2*r2, c2, 'like', LL);
    row_high(1:2:end, :) = col_even_high;
    row_high(2:2:end, :) = col_odd_high;
    
    row_even = (row_low + row_high) / sqrt(2);
    row_odd  = (row_low - row_high) / sqrt(2);
    
    block = zeros(2*r2, 2*c2, 'like', LL);
    block(1:2:end, :) = row_even;
    block(2:2:end, :) = row_odd;
    
    img(1:2*r2, 1:2*c2) = block;
end

end

function img_padded = pad_image(img, target_rows, target_cols, pad_mode, is_gpu)
[rows, cols] = size(img);

pad_rows_before = floor((target_rows - rows) / 2);
pad_rows_after = target_rows - rows - pad_rows_before;
pad_cols_before = floor((target_cols - cols) / 2);
pad_cols_after = target_cols - cols - pad_cols_before;

switch pad_mode
    case 'symmetric'
        img_padded = padarray_sym(img, pad_rows_before, pad_rows_after, ...
                                  pad_cols_before, pad_cols_after, is_gpu);
    case 'periodic'
        img_padded = padarray_per(img, pad_rows_before, pad_rows_after, ...
                                  pad_cols_before, pad_cols_after, is_gpu);
    case 'zero'
        if is_gpu
            img_padded = gpuArray.zeros(target_rows, target_cols);
        else
            img_padded = zeros(target_rows, target_cols);
        end
        img_padded(pad_rows_before+(1:rows), pad_cols_before+(1:cols)) = img;
    otherwise
        img_padded = padarray_sym(img, pad_rows_before, pad_rows_after, ...
                                  pad_cols_before, pad_cols_after, is_gpu);
end

end

function img_padded = padarray_sym(img, pre_r, post_r, pre_c, post_c, is_gpu)
[rows, cols] = size(img);

total_r = rows + pre_r + post_r;
total_c = cols + pre_c + post_c;

if is_gpu
    r_orig = gpuArray.colon(1, total_r) - pre_r;
    c_orig = gpuArray.colon(1, total_c) - pre_c;
else
    r_orig = (1:total_r) - pre_r;
    c_orig = (1:total_c) - pre_c;
end

r_idx = r_orig;
neg_mask = r_orig < 1;
r_idx(neg_mask) = 2 - r_orig(neg_mask);
pos_mask = r_orig > rows;
r_idx(pos_mask) = 2 * rows - r_orig(pos_mask) + 1;

c_idx = c_orig;
neg_mask_c = c_orig < 1;
c_idx(neg_mask_c) = 2 - c_orig(neg_mask_c);
pos_mask_c = c_orig > cols;
c_idx(pos_mask_c) = 2 * cols - c_orig(pos_mask_c) + 1;

if is_gpu
    [RR, CC] = meshgrid(gather(r_idx), gather(c_idx));
    img_cpu = gather(img);
    img_padded_cpu = img_cpu(RR, CC);
    img_padded = gpuArray(img_padded_cpu);
else
    [RR, CC] = meshgrid(r_idx, c_idx);
    img_padded = img(RR, CC);
end

end

function img_padded = padarray_per(img, pre_r, post_r, pre_c, post_c, is_gpu)
[rows, cols] = size(img);

total_r = rows + pre_r + post_r;
total_c = cols + pre_c + post_c;

if is_gpu
    r_idx = mod(gpuArray.colon(1, total_r) - pre_r - 1, rows) + 1;
    c_idx = mod(gpuArray.colon(1, total_c) - pre_c - 1, cols) + 1;
else
    r_idx = mod((1:total_r) - pre_r - 1, rows) + 1;
    c_idx = mod((1:total_c) - pre_c - 1, cols) + 1;
end

if is_gpu
    [RR, CC] = meshgrid(gather(r_idx), gather(c_idx));
    img_cpu = gather(img);
    img_padded_cpu = img_cpu(RR, CC);
    img_padded = gpuArray(img_padded_cpu);
else
    [RR, CC] = meshgrid(r_idx, c_idx);
    img_padded = img(RR, CC);
end

end

function result = pad_1d(block, target_r, target_c, pad_mode, dim, is_gpu)
if dim == 1
    [r, c] = size(block);
    pad = target_r - r;
    switch pad_mode
        case 'symmetric'
            if is_gpu
                result = [block; flip(block(end-pad+1:end, :), 1)];
            else
                result = [block; flipud(block(end-pad+1:end, :))];
            end
        case 'periodic'
            result = [block; block(1:pad, :)];
        otherwise
            if is_gpu
                result = [block; gpuArray.zeros(pad, c)];
            else
                result = [block; zeros(pad, c)];
            end
    end
else
    [r, c] = size(block);
    pad = target_c - c;
    switch pad_mode
        case 'symmetric'
            if is_gpu
                result = [block, flip(block(:, end-pad+1:end), 2)];
            else
                result = [block, fliplr(block(:, end-pad+1:end))];
            end
        case 'periodic'
            result = [block, block(:, 1:pad)];
        otherwise
            if is_gpu
                result = [block, gpuArray.zeros(r, pad)];
            else
                result = [block, zeros(r, pad)];
            end
    end
end
end

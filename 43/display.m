function display(original, undersampled, reconstructed, mask, history)
% DISPLAY  显示 MRI 压缩感知重建结果
%   display(original, undersampled, reconstructed, mask, history)
%
%   original: 原始图像
%   undersampled: 零填充重建图像 (直接逆傅里叶)
%   reconstructed: FISTA 重建图像
%   mask: 采样掩膜
%   history: 迭代历史 (可选)

figure('Position', [100, 100, 1200, 700]);

subplot(2, 4, 1);
imagesc(abs(original));
axis image; colormap gray;
title('原始图像');
colorbar;

subplot(2, 4, 2);
imagesc(mask);
axis image; colormap gray;
title(sprintf('采样掩膜 (%.1f%%)', sum(mask(:))/numel(mask)*100));
colorbar;

subplot(2, 4, 3);
imagesc(abs(undersampled));
axis image; colormap gray;
title('零填充重建');
colorbar;

subplot(2, 4, 4);
imagesc(abs(reconstructed));
axis image; colormap gray;
title('FISTA 重建');
colorbar;

subplot(2, 4, 5);
diff_undersampled = abs(original - undersampled);
imagesc(diff_undersampled);
axis image; colormap hot;
title(sprintf('零填充误差 (RMSE=%.4f)', rmse(original, undersampled)));
colorbar;

subplot(2, 4, 6);
diff_recon = abs(original - reconstructed);
imagesc(diff_recon);
axis image; colormap hot;
title(sprintf('FISTA 误差 (RMSE=%.4f)', rmse(original, reconstructed)));
colorbar;

subplot(2, 4, 7);
kspace_original = fftshift(fft2(ifftshift(original)));
imagesc(log(1 + abs(kspace_original)), []);
axis image; colormap jet;
title('原始 K-space (log)');
colorbar;

if nargin >= 5 && isfield(history, 'obj')
    subplot(2, 4, 8);
    semilogy(history.obj, 'b-', 'LineWidth', 1.5);
    grid on;
    xlabel('迭代次数');
    ylabel('目标函数值');
    title('FISTA 收敛曲线');
else
    subplot(2, 4, 8);
    kspace_undersampled = fftshift(fft2(ifftshift(undersampled)));
    imagesc(log(1 + abs(kspace_undersampled)), []);
    axis image; colormap jet;
    title('欠采样 K-space (log)');
    colorbar;
end

sgtitle('压缩感知 MRI 重建结果');

fprintf('========================================\n');
fprintf('重建质量评估:\n');
fprintf('----------------------------------------\n');
fprintf('零填充 RMSE:  %.6f\n', rmse(original, undersampled));
fprintf('FISTA   RMSE:  %.6f\n', rmse(original, reconstructed));
fprintf('零填充 PSNR:  %.2f dB\n', psnr_calc(original, undersampled));
fprintf('FISTA   PSNR:  %.2f dB\n', psnr_calc(original, reconstructed));
fprintf('========================================\n');

end

function e = rmse(x, y)
e = sqrt(mean((abs(x(:)) - abs(y(:))).^2));
end

function p = psnr_calc(x, y)
max_val = max(abs(x(:)));
mse_val = mean((abs(x(:)) - abs(y(:))).^2);
if mse_val == 0
    p = Inf;
else
    p = 20 * log10(max_val / sqrt(mse_val));
end
end

using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Windows.Forms;

namespace ImageBatchTool;

public static class Watermark
{
    public static Image AddWatermark(Image image, WatermarkOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.Text))
        {
            return image;
        }

        var bitmap = new Bitmap(image);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
        graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
        graphics.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;

        var fontSize = Math.Max(12, Math.Min(72, bitmap.Width / 20));
        using var font = new Font("Microsoft YaHei", fontSize, FontStyle.Bold, GraphicsUnit.Pixel);

        var textSize = TextRenderer.MeasureText(graphics, options.Text, font);

        var position = CalculatePosition(bitmap.Size, textSize, options.Position);

        var opacity = Math.Clamp(options.Opacity, 10, 100) / 100.0;
        var alpha = (int)(255 * opacity);
        var textColor = Color.FromArgb(alpha, Color.White);
        var shadowColor = Color.FromArgb(alpha / 2, Color.Black);

        var shadowOffset = Math.Max(2, (int)fontSize / 12);

        TextRenderer.DrawText(
            graphics,
            options.Text,
            font,
            new Point((int)position.X + shadowOffset, (int)position.Y + shadowOffset),
            shadowColor,
            TextFormatFlags.Left | TextFormatFlags.Top | TextFormatFlags.NoPrefix
        );

        TextRenderer.DrawText(
            graphics,
            options.Text,
            font,
            new Point((int)position.X, (int)position.Y),
            textColor,
            TextFormatFlags.Left | TextFormatFlags.Top | TextFormatFlags.NoPrefix
        );

        return bitmap;
    }

    private static PointF CalculatePosition(Size imageSize, SizeF textSize, WatermarkPosition position)
    {
        const int margin = 20;

        return position switch
        {
            WatermarkPosition.TopLeft => new PointF(margin, margin),
            WatermarkPosition.TopRight => new PointF(imageSize.Width - textSize.Width - margin, margin),
            WatermarkPosition.BottomLeft => new PointF(margin, imageSize.Height - textSize.Height - margin),
            WatermarkPosition.BottomRight => new PointF(imageSize.Width - textSize.Width - margin, imageSize.Height - textSize.Height - margin),
            WatermarkPosition.Center => new PointF((imageSize.Width - textSize.Width) / 2, (imageSize.Height - textSize.Height) / 2),
            _ => new PointF(imageSize.Width - textSize.Width - margin, imageSize.Height - textSize.Height - margin)
        };
    }

    public static Image AddImageWatermark(Image image, string watermarkImagePath, WatermarkPosition position, int opacity)
    {
        if (!File.Exists(watermarkImagePath))
        {
            return image;
        }

        using var watermarkImage = Image.FromFile(watermarkImagePath);
        var bitmap = new Bitmap(image);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
        graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

        var watermarkWidth = Math.Min(watermarkImage.Width, bitmap.Width / 4);
        var ratio = (double)watermarkWidth / watermarkImage.Width;
        var watermarkHeight = (int)(watermarkImage.Height * ratio);

        var watermarkSize = new SizeF(watermarkWidth, watermarkHeight);
        var pos = CalculatePosition(bitmap.Size, watermarkSize, position);

        var alpha = Math.Clamp(opacity, 10, 100);
        var attributes = new ImageAttributes();
        var colorMatrix = new ColorMatrix
        {
            Matrix33 = alpha / 100.0f
        };
        attributes.SetColorMatrix(colorMatrix, ColorMatrixFlag.Default, ColorAdjustType.Bitmap);

        graphics.DrawImage(
            watermarkImage,
            new Rectangle((int)pos.X, (int)pos.Y, watermarkWidth, watermarkHeight),
            0, 0, watermarkImage.Width, watermarkImage.Height,
            GraphicsUnit.Pixel,
            attributes
        );

        return bitmap;
    }
}

using System.Drawing.Drawing2D;

namespace ImageBatchTool;

public static class ResizeWorker
{
    public static Image Resize(Image image, ResizeOptions options)
    {
        int newWidth = options.Width;
        int newHeight = options.Height;

        if (options.KeepAspectRatio)
        {
            var ratioX = (double)options.Width / image.Width;
            var ratioY = (double)options.Height / image.Height;
            var ratio = Math.Min(ratioX, ratioY);

            newWidth = Math.Max(1, (int)Math.Round(image.Width * ratio));
            newHeight = Math.Max(1, (int)Math.Round(image.Height * ratio));
        }
        else
        {
            newWidth = Math.Max(1, newWidth);
            newHeight = Math.Max(1, newHeight);
        }

        var destRect = new Rectangle(0, 0, newWidth, newHeight);
        var destImage = new Bitmap(newWidth, newHeight);

        destImage.SetResolution(image.HorizontalResolution, image.VerticalResolution);

        using var graphics = Graphics.FromImage(destImage);
        graphics.CompositingMode = CompositingMode.SourceCopy;
        graphics.CompositingQuality = CompositingQuality.HighQuality;
        graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
        graphics.SmoothingMode = SmoothingMode.HighQuality;
        graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

        using var wrapMode = new System.Drawing.Imaging.ImageAttributes();
        wrapMode.SetWrapMode(WrapMode.TileFlipXY);
        graphics.DrawImage(image, destRect, 0, 0, image.Width, image.Height, GraphicsUnit.Pixel, wrapMode);

        return destImage;
    }

    public static Image ResizeByPercentage(Image image, double percentage)
    {
        if (percentage <= 0)
        {
            throw new ArgumentException("百分比必须大于0", nameof(percentage));
        }

        var newWidth = Math.Max(1, (int)Math.Round(image.Width * percentage / 100));
        var newHeight = Math.Max(1, (int)Math.Round(image.Height * percentage / 100));

        return Resize(image, new ResizeOptions
        {
            Width = newWidth,
            Height = newHeight,
            KeepAspectRatio = true
        });
    }

    public static Image ResizeByWidth(Image image, int width)
    {
        if (width <= 0)
        {
            throw new ArgumentException("宽度必须大于0", nameof(width));
        }

        width = Math.Max(1, width);
        var ratio = (double)width / image.Width;
        var newHeight = Math.Max(1, (int)Math.Round(image.Height * ratio));

        return Resize(image, new ResizeOptions
        {
            Width = width,
            Height = newHeight,
            KeepAspectRatio = true
        });
    }

    public static Image ResizeByHeight(Image image, int height)
    {
        if (height <= 0)
        {
            throw new ArgumentException("高度必须大于0", nameof(height));
        }

        height = Math.Max(1, height);
        var ratio = (double)height / image.Height;
        var newWidth = Math.Max(1, (int)Math.Round(image.Width * ratio));

        return Resize(image, new ResizeOptions
        {
            Width = newWidth,
            Height = height,
            KeepAspectRatio = true
        });
    }
}

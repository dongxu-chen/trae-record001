using System.Drawing.Imaging;
using System.IO;
using System.Reflection;

namespace ImageBatchTool;

public static class FormatConverter
{
    private static Assembly? _magickAssembly;
    private static Type? _magickImageType;
    private static MethodInfo? _magickWriteMethod;
    private static MethodInfo? _magickSetQualityMethod;
    private static MethodInfo? _magickDisposeMethod;
    private static bool _magickChecked = false;
    private static bool _magickAvailable = false;

    public static readonly HashSet<string> SupportedExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".ico", ".webp"
    };

    public static readonly HashSet<string> NativeGdiFormats = new(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".ico"
    };

    public static bool HasMagickNet
    {
        get
        {
            if (!_magickChecked)
            {
                TryLoadMagick();
            }
            return _magickAvailable;
        }
    }

    private static void TryLoadMagick()
    {
        try
        {
            _magickAssembly = Assembly.Load("Magick.NET-Q16-AnyCPU");
        }
        catch
        {
            try
            {
                _magickAssembly = Assembly.Load("Magick.NET-Q16-x64");
            }
            catch
            {
                try
                {
                    _magickAssembly = Assembly.Load("Magick.NET-Q16-x86");
                }
                catch
                {
                    _magickAssembly = null;
                }
            }
        }

        if (_magickAssembly != null)
        {
            _magickImageType = _magickAssembly.GetType("ImageMagick.MagickImage");
            if (_magickImageType != null)
            {
                _magickWriteMethod = _magickImageType.GetMethod("Write", new[] { typeof(string) });
                _magickSetQualityMethod = _magickImageType.GetProperty("Quality")?.SetMethod;
                _magickDisposeMethod = _magickImageType.GetMethod("Dispose", Type.EmptyTypes);

                _magickAvailable = _magickWriteMethod != null;
            }
        }

        _magickChecked = true;
    }

    public static void Convert(string inputPath, string outputPath, ImageFormat targetFormat)
    {
        var inputExt = Path.GetExtension(inputPath).ToLower();
        var outputExt = Path.GetExtension(outputPath).ToLower();
        var isAnimatedGif = inputExt == ".gif" && IsAnimatedGif(inputPath);

        if (isAnimatedGif && outputExt == ".gif")
        {
            File.Copy(inputPath, outputPath, true);
            return;
        }

        if (RequiresMagick(inputExt, outputExt))
        {
            if (HasMagickNet)
            {
                ConvertWithMagick(inputPath, outputPath, 90);
                return;
            }
            throw new NotSupportedException("WebP 格式转换需要安装 Magick.NET 库");
        }

        using var image = Image.FromFile(inputPath);
        Convert(image, outputPath, targetFormat);
    }

    public static void Convert(Image image, string outputPath, ImageFormat targetFormat)
    {
        var encoder = GetEncoder(targetFormat);
        var encoderParameters = GetEncoderParameters(targetFormat);

        image.Save(outputPath, encoder, encoderParameters);
    }

    public static void ConvertWithQuality(string inputPath, string outputPath, ImageFormat targetFormat, long quality)
    {
        var inputExt = Path.GetExtension(inputPath).ToLower();
        var outputExt = Path.GetExtension(outputPath).ToLower();
        var isAnimatedGif = inputExt == ".gif" && IsAnimatedGif(inputPath);

        if (isAnimatedGif && outputExt == ".gif")
        {
            File.Copy(inputPath, outputPath, true);
            return;
        }

        if (RequiresMagick(inputExt, outputExt))
        {
            if (HasMagickNet)
            {
                ConvertWithMagick(inputPath, outputPath, quality);
                return;
            }
            throw new NotSupportedException("WebP 格式转换需要安装 Magick.NET 库");
        }

        using var image = Image.FromFile(inputPath);
        ConvertWithQuality(image, outputPath, targetFormat, quality);
    }

    public static void ConvertWithQuality(Image image, string outputPath, ImageFormat targetFormat, long quality)
    {
        var encoder = GetEncoder(targetFormat);
        var encoderParameters = new EncoderParameters(1);
        encoderParameters.Param[0] = new EncoderParameter(Encoder.Quality, quality);

        image.Save(outputPath, encoder, encoderParameters);
    }

    public static void ConvertWithMagick(string inputPath, string outputPath, long quality = 90)
    {
        if (!HasMagickNet || _magickImageType == null || _magickWriteMethod == null)
        {
            throw new NotSupportedException("WebP 格式转换需要安装 Magick.NET 库");
        }

        object? image = null;
        try
        {
            image = Activator.CreateInstance(_magickImageType, inputPath);
            if (image == null)
            {
                throw new InvalidOperationException("无法创建 MagickImage 实例");
            }

            _magickSetQualityMethod?.Invoke(image, new object[] { (int)quality });
            _magickWriteMethod.Invoke(image, new object[] { outputPath });
        }
        finally
        {
            _magickDisposeMethod?.Invoke(image, null);
        }
    }

    public static bool IsAnimatedGif(string imagePath)
    {
        try
        {
            using var image = Image.FromFile(imagePath);
            return IsAnimatedGif(image);
        }
        catch
        {
            return false;
        }
    }

    public static bool IsAnimatedGif(Image image)
    {
        try
        {
            var frameDimension = new FrameDimension(image.FrameDimensionsList[0]);
            var frameCount = image.GetFrameCount(frameDimension);
            return frameCount > 1;
        }
        catch
        {
            return false;
        }
    }

    public static int GetFrameCount(Image image)
    {
        try
        {
            var frameDimension = new FrameDimension(image.FrameDimensionsList[0]);
            return image.GetFrameCount(frameDimension);
        }
        catch
        {
            return 1;
        }
    }

    private static bool RequiresMagick(string inputExt, string outputExt)
    {
        return inputExt == ".webp" || outputExt == ".webp";
    }

    private static ImageCodecInfo GetEncoder(ImageFormat format)
    {
        var codecs = ImageCodecInfo.GetImageEncoders();

        foreach (var codec in codecs)
        {
            if (codec.FormatID == format.Guid)
            {
                return codec;
            }
        }

        throw new ArgumentException($"不支持的图片格式: {format}", nameof(format));
    }

    private static EncoderParameters GetEncoderParameters(ImageFormat format)
    {
        var parameters = new EncoderParameters(1);

        if (format == ImageFormat.Jpeg)
        {
            parameters.Param[0] = new EncoderParameter(Encoder.Quality, 90L);
        }
        else if (format == ImageFormat.Png)
        {
            parameters.Param[0] = new EncoderParameter(Encoder.Compression, (long)EncoderValue.CompressionLZW);
        }
        else if (format == ImageFormat.Tiff)
        {
            parameters.Param[0] = new EncoderParameter(Encoder.Compression, (long)EncoderValue.CompressionLZW);
        }
        else
        {
            parameters.Param[0] = new EncoderParameter(Encoder.Quality, 100L);
        }

        return parameters;
    }

    public static string GetFileExtension(ImageFormat format)
    {
        if (format == ImageFormat.Jpeg) return ".jpg";
        if (format == ImageFormat.Png) return ".png";
        if (format == ImageFormat.Bmp) return ".bmp";
        if (format == ImageFormat.Gif) return ".gif";
        if (format == ImageFormat.Tiff) return ".tiff";
        if (format == ImageFormat.Icon) return ".ico";
        if (format == ImageFormat.Exif) return ".jpg";
        if (format == ImageFormat.MemoryBmp) return ".bmp";
        return ".jpg";
    }

    public static ImageFormat ParseFormat(string formatName)
    {
        return formatName.ToLower() switch
        {
            "jpg" or "jpeg" => ImageFormat.Jpeg,
            "png" => ImageFormat.Png,
            "bmp" => ImageFormat.Bmp,
            "gif" => ImageFormat.Gif,
            "tiff" or "tif" => ImageFormat.Tiff,
            "ico" or "icon" => ImageFormat.Icon,
            "webp" => throw new NotSupportedException("WebP 格式需要使用扩展名字符串处理"),
            _ => throw new ArgumentException($"不支持的格式名称: {formatName}", nameof(formatName))
        };
    }

    public static string ParseFormatExtension(string formatName)
    {
        return formatName.ToLower() switch
        {
            "jpg" or "jpeg" => ".jpg",
            "png" => ".png",
            "bmp" => ".bmp",
            "gif" => ".gif",
            "tiff" or "tif" => ".tiff",
            "ico" or "icon" => ".ico",
            "webp" => ".webp",
            _ => throw new ArgumentException($"不支持的格式名称: {formatName}", nameof(formatName))
        };
    }

    public static bool IsSupportedFormat(string extension)
    {
        return SupportedExtensions.Contains(extension);
    }
}

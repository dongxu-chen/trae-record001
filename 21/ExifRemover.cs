using System.Reflection;

namespace ImageBatchTool;

public class ExifRemoveOptions
{
    public bool RemoveAllExif { get; set; } = true;
    public bool RemoveIptc { get; set; } = true;
    public bool RemoveXmp { get; set; } = true;
    public bool RemoveColorProfile { get; set; } = false;
    public bool RemoveThumbnail { get; set; } = true;
    public bool KeepOrientation { get; set; } = true;
}

public static class ExifRemover
{
    private static Assembly? _magickAssembly;
    private static Type? _magickImageType;
    private static MethodInfo? _magickStripMethod;
    private static MethodInfo? _magickWriteMethod;
    private static MethodInfo? _magickRemoveProfileMethod;
    private static MethodInfo? _magickGetExifProfileMethod;
    private static PropertyInfo? _magickHasValuesProperty;
    private static PropertyInfo? _magickValuesProperty;
    private static MethodInfo? _magickImageDisposeMethod;
    private static bool _magickChecked = false;
    private static bool _magickAvailable = false;

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
                _magickStripMethod = _magickImageType.GetMethod("Strip", Type.EmptyTypes);
                _magickWriteMethod = _magickImageType.GetMethod("Write", new[] { typeof(string) });
                _magickRemoveProfileMethod = _magickImageType.GetMethod("RemoveProfile", new[] { typeof(string) });
                _magickGetExifProfileMethod = _magickImageType.GetMethod("GetExifProfile", Type.EmptyTypes);
                _magickImageDisposeMethod = _magickImageType.GetMethod("Dispose", Type.EmptyTypes);

                var exifProfileType = _magickAssembly.GetType("ImageMagick.ExifProfile");
                if (exifProfileType != null)
                {
                    _magickHasValuesProperty = exifProfileType.GetProperty("HasValues");
                    _magickValuesProperty = exifProfileType.GetProperty("Values");
                }

                _magickAvailable = _magickStripMethod != null && _magickWriteMethod != null;
            }
        }

        _magickChecked = true;
    }

    public static void RemoveExif(string inputPath, string outputPath, ExifRemoveOptions? options = null)
    {
        options ??= new ExifRemoveOptions();

        if (HasMagickNet)
        {
            RemoveExifWithMagick(inputPath, outputPath, options);
        }
        else
        {
            RemoveExifWithGdi(inputPath, outputPath, options);
        }
    }

    private static void RemoveExifWithMagick(string inputPath, string outputPath, ExifRemoveOptions options)
    {
        if (_magickImageType == null || _magickWriteMethod == null)
        {
            RemoveExifWithGdi(inputPath, outputPath, options);
            return;
        }

        object? image = null;
        try
        {
            image = Activator.CreateInstance(_magickImageType, inputPath);
            if (image == null)
            {
                RemoveExifWithGdi(inputPath, outputPath, options);
                return;
            }

            if (options.RemoveAllExif)
            {
                _magickStripMethod?.Invoke(image, null);
            }
            else
            {
                if (options.RemoveIptc)
                {
                    _magickRemoveProfileMethod?.Invoke(image, new object[] { "iptc" });
                }
                if (options.RemoveXmp)
                {
                    _magickRemoveProfileMethod?.Invoke(image, new object[] { "xmp" });
                }
                if (options.RemoveThumbnail)
                {
                    _magickRemoveProfileMethod?.Invoke(image, new object[] { "8bim" });
                }
                if (options.RemoveColorProfile)
                {
                    _magickRemoveProfileMethod?.Invoke(image, new object[] { "icc" });
                }
            }

            _magickWriteMethod.Invoke(image, new object[] { outputPath });
        }
        catch
        {
            RemoveExifWithGdi(inputPath, outputPath, options);
        }
        finally
        {
            _magickImageDisposeMethod?.Invoke(image, null);
        }
    }

    public static void RemoveExifWithGdi(string inputPath, string outputPath, ExifRemoveOptions options)
    {
        using var original = Image.FromFile(inputPath);
        var bitmap = new Bitmap(original.Width, original.Height);

        bitmap.SetResolution(original.HorizontalResolution, original.VerticalResolution);

        using var graphics = Graphics.FromImage(bitmap);
        graphics.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
        graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.HighQuality;
        graphics.PixelOffsetMode = System.Drawing.Drawing2D.PixelOffsetMode.HighQuality;

        graphics.DrawImage(original, new Rectangle(0, 0, bitmap.Width, bitmap.Height));

        var ext = Path.GetExtension(outputPath).ToLower();
        var format = ext switch
        {
            ".jpg" or ".jpeg" => System.Drawing.Imaging.ImageFormat.Jpeg,
            ".png" => System.Drawing.Imaging.ImageFormat.Png,
            ".tiff" or ".tif" => System.Drawing.Imaging.ImageFormat.Tiff,
            ".bmp" => System.Drawing.Imaging.ImageFormat.Bmp,
            ".gif" => System.Drawing.Imaging.ImageFormat.Gif,
            _ => System.Drawing.Imaging.ImageFormat.Jpeg
        };

        bitmap.Save(outputPath, format);
    }

    public static Dictionary<string, string> ReadExifData(string inputPath)
    {
        var result = new Dictionary<string, string>();

        if (HasMagickNet)
        {
            try
            {
                if (_magickImageType != null && _magickGetExifProfileMethod != null)
                {
                    object? image = null;
                    try
                    {
                        image = Activator.CreateInstance(_magickImageType, inputPath);
                        var profile = _magickGetExifProfileMethod.Invoke(image, null);
                        if (profile != null && _magickHasValuesProperty != null)
                        {
                            var hasValues = (bool)(_magickHasValuesProperty.GetValue(profile) ?? false);
                            if (hasValues && _magickValuesProperty != null)
                            {
                                var values = _magickValuesProperty.GetValue(profile) as System.Collections.IEnumerable;
                                if (values != null)
                                {
                                    foreach (var value in values)
                                    {
                                        var name = value.GetType().GetProperty("Tag")?.GetValue(value)?.ToString() ?? "Unknown";
                                        var data = value.ToString() ?? string.Empty;
                                        if (!string.IsNullOrEmpty(data))
                                        {
                                            result[name] = data;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    finally
                    {
                        _magickImageDisposeMethod?.Invoke(image, null);
                    }
                }
            }
            catch
            {
            }
        }

        if (result.Count == 0)
        {
            try
            {
                using var image = Image.FromFile(inputPath);
                foreach (var prop in image.PropertyItems)
                {
                    var id = prop.Id.ToString();
                    var value = GetPropertyValue(prop);
                    if (!string.IsNullOrEmpty(value))
                    {
                        result[id] = value;
                    }
                }
            }
            catch
            {
            }
        }

        return result;
    }

    private static string GetPropertyValue(System.Drawing.Imaging.PropertyItem prop)
    {
        try
        {
            var value = prop.Value ?? Array.Empty<byte>();
            return prop.Type switch
            {
                1 => BitConverter.ToString(value),
                2 => System.Text.Encoding.ASCII.GetString(value).TrimEnd('\0'),
                3 => value.Length >= 2 ? BitConverter.ToInt16(value, 0).ToString() : string.Empty,
                4 => value.Length >= 4 ? BitConverter.ToInt32(value, 0).ToString() : string.Empty,
                5 or 10 => FormatRational(value),
                7 => System.Text.Encoding.ASCII.GetString(value).TrimEnd('\0'),
                _ => BitConverter.ToString(value)
            };
        }
        catch
        {
            return string.Empty;
        }
    }

    private static string FormatRational(byte[] value)
    {
        if (value.Length < 8) return string.Empty;

        var numerator = BitConverter.ToInt32(value, 0);
        var denominator = BitConverter.ToInt32(value, 4);

        if (denominator == 0) return numerator.ToString();

        return $"{numerator}/{denominator}";
    }

    public static bool HasExifData(string inputPath)
    {
        return GetExifDataCount(inputPath) > 0;
    }

    public static int GetExifDataCount(string inputPath)
    {
        if (HasMagickNet)
        {
            try
            {
                if (_magickImageType != null && _magickGetExifProfileMethod != null)
                {
                    object? image = null;
                    try
                    {
                        image = Activator.CreateInstance(_magickImageType, inputPath);
                        var profile = _magickGetExifProfileMethod.Invoke(image, null);
                        if (profile != null && _magickValuesProperty != null)
                        {
                            var values = _magickValuesProperty.GetValue(profile) as System.Collections.ICollection;
                            return values?.Count ?? 0;
                        }
                        return 0;
                    }
                    finally
                    {
                        _magickImageDisposeMethod?.Invoke(image, null);
                    }
                }
            }
            catch
            {
            }
        }

        try
        {
            using var image = Image.FromFile(inputPath);
            return image.PropertyItems.Length;
        }
        catch
        {
            return 0;
        }
    }
}

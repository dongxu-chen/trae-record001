using System.Text.RegularExpressions;

namespace ImageBatchTool;

public class RenameOptions
{
    public string Prefix { get; set; } = string.Empty;
    public string Suffix { get; set; } = string.Empty;
    public bool UseNumbering { get; set; }
    public int StartNumber { get; set; } = 1;
    public int NumberPadding { get; set; } = 3;
    public bool UseRegex { get; set; }
    public string RegexPattern { get; set; } = string.Empty;
    public string RegexReplacement { get; set; } = string.Empty;
    public bool KeepOriginalExtension { get; set; } = true;
    public string NewExtension { get; set; } = string.Empty;
}

public static class RenameWorker
{
    public static List<(string OriginalPath, string NewPath)> GenerateNewNames(
        List<string> files,
        RenameOptions options)
    {
        var result = new List<(string, string)>();
        var number = options.StartNumber;

        for (int i = 0; i < files.Count; i++)
        {
            var originalPath = files[i];
            var directory = Path.GetDirectoryName(originalPath) ?? string.Empty;
            var fileName = Path.GetFileNameWithoutExtension(originalPath);
            var extension = Path.GetExtension(originalPath);

            var newFileName = fileName;

            if (options.UseRegex && !string.IsNullOrWhiteSpace(options.RegexPattern))
            {
                try
                {
                    newFileName = Regex.Replace(
                        newFileName,
                        options.RegexPattern,
                        options.RegexReplacement ?? string.Empty,
                        RegexOptions.IgnoreCase
                    );
                }
                catch (ArgumentException ex)
                {
                    throw new ArgumentException($"正则表达式错误: {ex.Message}", ex);
                }
            }

            if (options.UseNumbering)
            {
                var numStr = number.ToString().PadLeft(options.NumberPadding, '0');
                newFileName = $"{options.Prefix}{numStr}{options.Suffix}";
                number++;
            }
            else
            {
                newFileName = $"{options.Prefix}{newFileName}{options.Suffix}";
            }

            var newExtension = options.KeepOriginalExtension
                ? extension
                : options.NewExtension.StartsWith(".") ? options.NewExtension : $".{options.NewExtension}";

            if (string.IsNullOrWhiteSpace(newExtension))
            {
                newExtension = extension;
            }

            var newFileNameWithExt = $"{newFileName}{newExtension}";
            var newPath = Path.Combine(directory, newFileNameWithExt);

            int counter = 1;
            while (File.Exists(newPath) && !string.Equals(originalPath, newPath, StringComparison.OrdinalIgnoreCase))
            {
                newFileNameWithExt = $"{newFileName}_{counter}{newExtension}";
                newPath = Path.Combine(directory, newFileNameWithExt);
                counter++;
            }

            result.Add((originalPath, newPath));
        }

        return result;
    }

    public static (string OriginalPath, string NewPath) GenerateSingleName(
        string filePath,
        int index,
        RenameOptions options)
    {
        var directory = Path.GetDirectoryName(filePath) ?? string.Empty;
        var fileName = Path.GetFileNameWithoutExtension(filePath);
        var extension = Path.GetExtension(filePath);

        var newFileName = fileName;

        if (options.UseRegex && !string.IsNullOrWhiteSpace(options.RegexPattern))
        {
            try
            {
                newFileName = Regex.Replace(
                    newFileName,
                    options.RegexPattern,
                    options.RegexReplacement ?? string.Empty,
                    RegexOptions.IgnoreCase
                );
            }
            catch (ArgumentException ex)
            {
                throw new ArgumentException($"正则表达式错误: {ex.Message}", ex);
            }
        }

        if (options.UseNumbering)
        {
            var numStr = (options.StartNumber + index).ToString().PadLeft(options.NumberPadding, '0');
            newFileName = $"{options.Prefix}{numStr}{options.Suffix}";
        }
        else
        {
            newFileName = $"{options.Prefix}{newFileName}{options.Suffix}";
        }

        var newExtension = options.KeepOriginalExtension
            ? extension
            : options.NewExtension.StartsWith(".") ? options.NewExtension : $".{options.NewExtension}";

        if (string.IsNullOrWhiteSpace(newExtension))
        {
            newExtension = extension;
        }

        var newFileNameWithExt = $"{newFileName}{newExtension}";
        var newPath = Path.Combine(directory, newFileNameWithExt);

        return (filePath, newPath);
    }

    public static void Rename(string oldPath, string newPath, bool overwrite = false)
    {
        if (string.Equals(oldPath, newPath, StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        if (File.Exists(newPath))
        {
            if (overwrite)
            {
                File.Delete(newPath);
            }
            else
            {
                throw new IOException($"目标文件已存在: {newPath}");
            }
        }

        File.Move(oldPath, newPath);
    }

    public static void RenameToNewFolder(
        List<string> files,
        string outputFolder,
        RenameOptions options,
        bool overwrite = false)
    {
        if (!Directory.Exists(outputFolder))
        {
            Directory.CreateDirectory(outputFolder);
        }

        var number = options.StartNumber;

        for (int i = 0; i < files.Count; i++)
        {
            var originalPath = files[i];
            var fileName = Path.GetFileNameWithoutExtension(originalPath);
            var extension = Path.GetExtension(originalPath);

            var newFileName = fileName;

            if (options.UseRegex && !string.IsNullOrWhiteSpace(options.RegexPattern))
            {
                newFileName = Regex.Replace(
                    newFileName,
                    options.RegexPattern,
                    options.RegexReplacement ?? string.Empty,
                    RegexOptions.IgnoreCase
                );
            }

            if (options.UseNumbering)
            {
                var numStr = number.ToString().PadLeft(options.NumberPadding, '0');
                newFileName = $"{options.Prefix}{numStr}{options.Suffix}";
                number++;
            }
            else
            {
                newFileName = $"{options.Prefix}{newFileName}{options.Suffix}";
            }

            var newExtension = options.KeepOriginalExtension
                ? extension
                : options.NewExtension.StartsWith(".") ? options.NewExtension : $".{options.NewExtension}";

            if (string.IsNullOrWhiteSpace(newExtension))
            {
                newExtension = extension;
            }

            var newFileNameWithExt = $"{newFileName}{newExtension}";
            var newPath = Path.Combine(outputFolder, newFileNameWithExt);

            int counter = 1;
            while (File.Exists(newPath))
            {
                if (overwrite)
                {
                    break;
                }
                newFileNameWithExt = $"{newFileName}_{counter}{newExtension}";
                newPath = Path.Combine(outputFolder, newFileNameWithExt);
                counter++;
            }

            File.Copy(originalPath, newPath, overwrite);
        }
    }

    public static string RemoveInvalidChars(string fileName)
    {
        var invalidChars = Path.GetInvalidFileNameChars();
        foreach (var c in invalidChars)
        {
            fileName = fileName.Replace(c, '_');
        }
        return fileName;
    }

    public static bool IsValidRegex(string pattern)
    {
        if (string.IsNullOrWhiteSpace(pattern))
        {
            return false;
        }

        try
        {
            _ = Regex.Match(string.Empty, pattern);
            return true;
        }
        catch (ArgumentException)
        {
            return false;
        }
    }
}

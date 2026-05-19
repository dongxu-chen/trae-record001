#include "disk_cleaner.h"

namespace SystemOptimizer
{
    private ref class PathSecurity
    {
    public:
        static array<String^>^ GetProtectedPaths()
        {
            return gcnew array<String^> {
                Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\Downloads",
                Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\Documents",
                Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\Pictures",
                Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\Music",
                Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\Videos",
                Environment::GetFolderPath(Environment::SpecialFolder::Desktop),
                Environment::GetFolderPath(Environment::SpecialFolder::System),
                Environment::GetFolderPath(Environment::SpecialFolder::Windows),
                Environment::GetFolderPath(Environment::SpecialFolder::ProgramFiles),
                Environment::GetFolderPath(Environment::SpecialFolder::ProgramFilesX86),
                Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData),
                Environment::GetFolderPath(Environment::SpecialFolder::LocalApplicationData)
            };
        }

        static bool IsProtectedPath(String^ path)
        {
            for each (String^ protectedPath in GetProtectedPaths())
            {
                if (path->StartsWith(protectedPath, StringComparison::OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            return false;
        }
    };

    DiskCleaner::DiskCleaner()
    {
    }

    List<TempFile^>^ DiskCleaner::ScanTempFiles()
    {
        auto results = gcnew List<TempFile^>();

        try
        {
            String^ tempPath = System::IO::Path::GetTempPath();
            ScanDirectory(tempPath, results);

            array<String^>^ otherPaths = {
                Environment::GetFolderPath(Environment::SpecialFolder::InternetCache),
                Environment::GetFolderPath(Environment::SpecialFolder::History),
                Environment::GetFolderPath(Environment::SpecialFolder::Cookies),
                Environment::ExpandEnvironmentVariables(L"%windir%\\Temp"),
                Environment::ExpandEnvironmentVariables(L"%windir%\\Prefetch"),
                Environment::ExpandEnvironmentVariables(L"%localappdata%\\Microsoft\\Windows\\INetCache"),
                Environment::ExpandEnvironmentVariables(L"%localappdata%\\Temp")
            };

            for each (String^ path in otherPaths)
            {
                try
                {
                    if (System::IO::Directory::Exists(path))
                    {
                        ScanDirectory(path, results);
                    }
                }
                catch (...) {}
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }

        return results;
    }

    void DiskCleaner::ScanDirectory(String^ path, List<TempFile^>^ results)
    {
        try
        {
            if (!System::IO::Directory::Exists(path))
            {
                return;
            }

            if (PathSecurity::IsProtectedPath(path))
            {
                return;
            }

            auto files = System::IO::Directory::GetFiles(path);
            for each (String^ file in files)
            {
                try
                {
                    if (PathSecurity::IsProtectedPath(file))
                    {
                        continue;
                    }

                    if (IsTempFile(file))
                    {
                        auto fileInfo = gcnew System::IO::FileInfo(file);
                        auto tempFile = gcnew TempFile();
                        tempFile->Path = file;
                        tempFile->Size = fileInfo->Length;
                        results->Add(tempFile);
                    }
                }
                catch (...) {}
            }

            auto dirs = System::IO::Directory::GetDirectories(path);
            for each (String^ dir in dirs)
            {
                try
                {
                    ScanDirectory(dir, results);
                }
                catch (...) {}
            }
        }
        catch (...) {}
    }

    bool DiskCleaner::IsTempFile(String^ path)
    {
        try
        {
            String^ ext = System::IO::Path::GetExtension(path)->ToLower();

            array<String^>^ tempExtensions = {
                L".tmp", L".temp", L".log", L".bak", L".old",
                L".chk", L".~mp", L".dmp", L".crash", L".cache",
                L".part", L".partial"
            };

            for each (String^ tempExt in tempExtensions)
            {
                if (ext == tempExt)
                {
                    return true;
                }
            }

            String^ fileName = System::IO::Path::GetFileName(path)->ToLower();
            if (fileName->StartsWith(L"~") || fileName->StartsWith(L"._"))
            {
                return true;
            }

            if (path->Contains(L"\\Temp\\") || path->Contains(L"\\Temporary Internet Files\\") ||
                path->Contains(L"\\INetCache\\") || path->Contains(L"\\Prefetch\\"))
            {
                return true;
            }
        }
        catch (...) {}

        return false;
    }

    bool DiskCleaner::DeleteFile(String^ path)
    {
        if (PathSecurity::IsProtectedPath(path))
        {
            System::Diagnostics::Debug::WriteLine("Cannot delete file in protected path: " + path);
            return false;
        }

        try
        {
            if (System::IO::File::Exists(path))
            {
                System::IO::File::Delete(path);
                return true;
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
        return false;
    }
}
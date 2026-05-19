#include "registry_cleaner.h"
#include <vector>

namespace SystemOptimizer
{
    private ref class RegistrySecurity
    {
    public:
        static array<String^>^ GetCriticalRegistryKeys()
        {
            return gcnew array<String^> {
                L"HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunServices",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunServicesOnce",
                L"HKLM\\SYSTEM",
                L"HKCU\\Control Panel",
                L"HKLM\\SOFTWARE\\Classes",
                L"HKLM\\SOFTWARE\\Microsoft\\Active Setup",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Shell Extensions",
                L"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies",
                L"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies"
            };
        }

        static array<String^>^ GetBlacklistedRegistryKeys()
        {
            return gcnew array<String^> {
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Browser Helper Objects",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\ShellServiceObjectDelayLoad",
                L"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StartupApproved",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StartupApproved",
                L"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
                L"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer\\Run",
                L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer\\Run"
            };
        }

        static bool IsCriticalKey(String^ path)
        {
            for each (String^ criticalKey in GetCriticalRegistryKeys())
            {
                if (path->StartsWith(criticalKey, StringComparison::OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            return false;
        }

        static bool IsBlacklistedKey(String^ path)
        {
            for each (String^ blacklistedKey in GetBlacklistedRegistryKeys())
            {
                if (path->StartsWith(blacklistedKey, StringComparison::OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            return false;
        }
    };

    RegistryCleaner::RegistryCleaner()
    {
    }

    List<RegistryEntry^>^ RegistryCleaner::ScanInvalidRegistry()
    {
        auto results = gcnew List<RegistryEntry^>();

        try
        {
            auto hklm = Registry::LocalMachine;
            auto hkcu = Registry::CurrentUser;

            array<String^>^ searchKeys = {
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
                L"SOFTWARE\\Classes\\Applications",
                L"SOFTWARE\\Classes\\CLSID"
            };

            for each (String^ keyPath in searchKeys)
            {
                try
                {
                    auto key = hklm->OpenSubKey(keyPath);
                    if (key != nullptr)
                    {
                        ScanRegistryKey(key, L"HKLM\\" + keyPath, results);
                        key->Close();
                    }
                }
                catch (...) {}

                try
                {
                    auto key = hkcu->OpenSubKey(keyPath);
                    if (key != nullptr)
                    {
                        ScanRegistryKey(key, L"HKCU\\" + keyPath, results);
                        key->Close();
                    }
                }
                catch (...) {}
            }

            array<String^>^ commonPaths = {
                Environment::GetFolderPath(Environment::SpecialFolder::ProgramFiles),
                Environment::GetFolderPath(Environment::SpecialFolder::ProgramFilesX86),
                Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData),
                Environment::GetFolderPath(Environment::SpecialFolder::LocalApplicationData)
            };

            for each (String^ basePath in commonPaths)
            {
                try
                {
                    if (System::IO::Directory::Exists(basePath))
                    {
                        auto dirs = System::IO::Directory::GetDirectories(basePath);
                        for each (String^ dir in dirs)
                        {
                            try
                            {
                                auto files = System::IO::Directory::GetFiles(dir, L"*.exe", System::IO::SearchOption::TopDirectoryOnly);
                                if (files->Length == 0)
                                {
                                    auto entry = gcnew RegistryEntry();
                                    entry->Path = dir;
                                    entry->Type = RegistryEntryType::EmptyKey;
                                    results->Add(entry);
                                }
                            }
                            catch (...) {}
                        }
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

    void RegistryCleaner::ScanRegistryKey(RegistryKey^ key, String^ path, List<RegistryEntry^>^ results)
    {
        if (RegistrySecurity::IsCriticalKey(path))
        {
            return;
        }

        if (RegistrySecurity::IsBlacklistedKey(path))
        {
            auto entry = gcnew RegistryEntry();
            entry->Path = path;
            entry->Type = RegistryEntryType::Blacklisted;
            results->Add(entry);
        }

        try
        {
            for each (String^ valueName in key->GetValueNames())
            {
                try
                {
                    String^ fullValuePath = path + L"\\" + valueName;
                    if (RegistrySecurity::IsCriticalKey(fullValuePath))
                    {
                        continue;
                    }

                    if (RegistrySecurity::IsBlacklistedKey(fullValuePath))
                    {
                        auto entry = gcnew RegistryEntry();
                        entry->Path = fullValuePath;
                        entry->Type = RegistryEntryType::Blacklisted;
                        results->Add(entry);
                        continue;
                    }

                    auto value = key->GetValue(valueName);
                    if (value != nullptr && value->GetType() == String::typeid)
                    {
                        String^ strValue = dynamic_cast<String^>(value);
                        if (!String::IsNullOrEmpty(strValue))
                        {
                            if (strValue->StartsWith(L"\"") && strValue->EndsWith(L"\""))
                            {
                                strValue = strValue->Substring(1, strValue->Length - 2);
                            }

                            int exeIndex = strValue->IndexOf(L".exe", StringComparison::OrdinalIgnoreCase);
                            if (exeIndex > 0)
                            {
                                strValue = strValue->Substring(0, exeIndex + 4);
                            }

                            if (strValue->Contains(L":\\") || strValue->StartsWith(L"%"))
                            {
                                String^ expandedPath = Environment::ExpandEnvironmentVariables(strValue);
                                if (!System::IO::File::Exists(expandedPath) && !System::IO::Directory::Exists(expandedPath))
                                {
                                    auto entry = gcnew RegistryEntry();
                                    entry->Path = fullValuePath;
                                    entry->Type = RegistryEntryType::MissingFile;
                                    results->Add(entry);
                                }
                            }
                        }
                    }
                }
                catch (...) {}
            }

            for each (String^ subKeyName in key->GetSubKeyNames())
            {
                try
                {
                    String^ fullSubKeyPath = path + L"\\" + subKeyName;
                    if (RegistrySecurity::IsCriticalKey(fullSubKeyPath))
                    {
                        continue;
                    }

                    auto subKey = key->OpenSubKey(subKeyName);
                    if (subKey != nullptr)
                    {
                        if (subKey->ValueCount == 0 && subKey->SubKeyCount == 0)
                        {
                            auto entry = gcnew RegistryEntry();
                            entry->Path = fullSubKeyPath;
                            entry->Type = RegistryEntryType::EmptyKey;
                            results->Add(entry);
                        }
                        else
                        {
                            ScanRegistryKey(subKey, fullSubKeyPath, results);
                        }
                        subKey->Close();
                    }
                }
                catch (...) {}
            }
        }
        catch (...) {}
    }

    bool RegistryCleaner::RemoveRegistryEntry(String^ path)
    {
        if (RegistrySecurity::IsCriticalKey(path))
        {
            System::Diagnostics::Debug::WriteLine("Cannot delete critical registry key: " + path);
            return false;
        }

        try
        {
            RegistryKey^ rootKey = nullptr;
            String^ subPath;

            if (path->StartsWith(L"HKLM\\"))
            {
                rootKey = Registry::LocalMachine;
                subPath = path->Substring(5);
            }
            else if (path->StartsWith(L"HKCU\\"))
            {
                rootKey = Registry::CurrentUser;
                subPath = path->Substring(5);
            }
            else if (System::IO::Directory::Exists(path))
            {
                String^ downloadsPath = Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\Downloads";
                if (path->StartsWith(downloadsPath, StringComparison::OrdinalIgnoreCase))
                {
                    return false;
                }
                System::IO::Directory::Delete(path, true);
                return true;
            }
            else
            {
                return false;
            }

            int lastBackslash = subPath->LastIndexOf('\\');
            if (lastBackslash > 0)
            {
                String^ parentPath = subPath->Substring(0, lastBackslash);
                String^ valueName = subPath->Substring(lastBackslash + 1);

                auto parentKey = rootKey->OpenSubKey(parentPath, true);
                if (parentKey != nullptr)
                {
                    auto value = parentKey->GetValue(valueName);
                    if (value != nullptr)
                    {
                        parentKey->DeleteValue(valueName, false);
                        parentKey->Close();
                        return true;
                    }
                    else
                    {
                        auto targetKey = rootKey->OpenSubKey(subPath, true);
                        if (targetKey != nullptr)
                        {
                            targetKey->Close();
                            if (parentKey != nullptr)
                            {
                                parentKey->DeleteSubKeyTree(valueName, false);
                                parentKey->Close();
                                return true;
                            }
                        }
                    }
                    parentKey->Close();
                }
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
        return false;
    }

    bool RegistryCleaner::IsInvalidPath(String^ path)
    {
        return String::IsNullOrEmpty(path) || path->IndexOfAny(System::IO::Path::GetInvalidPathChars()) >= 0;
    }

    bool RegistryCleaner::IsFileMissing(String^ path)
    {
        return !System::IO::File::Exists(path);
    }
}
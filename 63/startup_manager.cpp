#include "startup_manager.h"

namespace SystemOptimizer
{
    private ref class RegistryBackup
    {
    public:
        static String^ GetBackupFilePath()
        {
            String^ backupDir = Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData) + "\\SystemOptimizer\\Backup";
            if (!System::IO::Directory::Exists(backupDir))
            {
                System::IO::Directory::CreateDirectory(backupDir);
            }
            String^ timestamp = DateTime::Now.ToString("yyyyMMdd_HHmmss");
            return backupDir + "\\StartupItems_Backup_" + timestamp + ".reg";
        }

        static bool ExportRegistryKey(String^ keyPath, String^ exportPath)
        {
            try
            {
                String^ arguments = "/e \"" + exportPath + "\" \"" + keyPath + "\"";
                auto process = gcnew System::Diagnostics::Process();
                process->StartInfo->FileName = "reg.exe";
                process->StartInfo->Arguments = arguments;
                process->StartInfo->CreateNoWindow = true;
                process->StartInfo->UseShellExecute = false;
                process->Start();
                process->WaitForExit(5000);
                return process->ExitCode == 0;
            }
            catch (Exception^ ex)
            {
                System::Diagnostics::Debug::WriteLine(ex->Message);
                return false;
            }
        }

        static bool BackupStartupItem(StartupLocation location, String^ itemName, Object^ value)
        {
            try
            {
                String^ backupDir = Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData) + "\\SystemOptimizer\\Backup\\StartupItems";
                if (!System::IO::Directory::Exists(backupDir))
                {
                    System::IO::Directory::CreateDirectory(backupDir);
                }

                String^ backupFile = backupDir + "\\" + itemName + "_" + DateTime::Now.ToString("yyyyMMdd_HHmmss") + ".bak";
                auto writer = gcnew System::IO::StreamWriter(backupFile);
                writer->WriteLine("Location: " + location.ToString());
                writer->WriteLine("Name: " + itemName);
                writer->WriteLine("Value: " + value->ToString());
                writer->WriteLine("BackupTime: " + DateTime::Now.ToString());
                writer->Close();
                return true;
            }
            catch (Exception^ ex)
            {
                System::Diagnostics::Debug::WriteLine(ex->Message);
                return false;
            }
        }
    };

    StartupManager::StartupManager()
    {
    }

    List<StartupItem^>^ StartupManager::GetStartupItems()
    {
        auto results = gcnew List<StartupItem^>();

        try
        {
            auto hklmRun = Registry::LocalMachine->OpenSubKey(
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run");
            if (hklmRun != nullptr)
            {
                ScanRegistryKey(hklmRun, StartupLocation::HKLM_Run, results);
                hklmRun->Close();
            }

            auto hkcuRun = Registry::CurrentUser->OpenSubKey(
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run");
            if (hkcuRun != nullptr)
            {
                ScanRegistryKey(hkcuRun, StartupLocation::HKCU_Run, results);
                hkcuRun->Close();
            }

            auto hklmRunOnce = Registry::LocalMachine->OpenSubKey(
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce");
            if (hklmRunOnce != nullptr)
            {
                ScanRegistryKey(hklmRunOnce, StartupLocation::HKLM_RunOnce, results);
                hklmRunOnce->Close();
            }

            auto hkcuRunOnce = Registry::CurrentUser->OpenSubKey(
                L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce");
            if (hkcuRunOnce != nullptr)
            {
                ScanRegistryKey(hkcuRunOnce, StartupLocation::HKCU_RunOnce, results);
                hkcuRunOnce->Close();
            }

            String^ startupFolder = Environment::GetFolderPath(
                Environment::SpecialFolder::Startup);
            ScanStartupFolder(startupFolder, StartupLocation::StartupFolder, results);

            String^ commonStartupFolder = Environment::GetFolderPath(
                Environment::SpecialFolder::CommonStartup);
            ScanStartupFolder(commonStartupFolder, StartupLocation::CommonStartupFolder, results);
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }

        return results;
    }

    void StartupManager::ScanRegistryKey(RegistryKey^ key, StartupLocation location, List<StartupItem^>^ results)
    {
        try
        {
            for each (String^ valueName in key->GetValueNames())
            {
                try
                {
                    auto item = gcnew StartupItem();
                    item->Name = valueName;
                    item->Path = dynamic_cast<String^>(key->GetValue(valueName));
                    item->Enabled = true;
                    item->Location = location;
                    results->Add(item);
                }
                catch (...) {}
            }
        }
        catch (...) {}
    }

    void StartupManager::ScanStartupFolder(String^ folder, StartupLocation location, List<StartupItem^>^ results)
    {
        try
        {
            if (System::IO::Directory::Exists(folder))
            {
                auto files = System::IO::Directory::GetFiles(folder, L"*.lnk");
                for each (String^ file in files)
                {
                    try
                    {
                        auto item = gcnew StartupItem();
                        item->Name = System::IO::Path::GetFileNameWithoutExtension(file);
                        item->Path = file;
                        item->Enabled = true;
                        item->Location = location;
                        results->Add(item);
                    }
                    catch (...) {}
                }

                auto exeFiles = System::IO::Directory::GetFiles(folder, L"*.exe");
                for each (String^ file in exeFiles)
                {
                    try
                    {
                        auto item = gcnew StartupItem();
                        item->Name = System::IO::Path::GetFileNameWithoutExtension(file);
                        item->Path = file;
                        item->Enabled = true;
                        item->Location = location;
                        results->Add(item);
                    }
                    catch (...) {}
                }
            }
        }
        catch (...) {}
    }

    String^ StartupManager::GetRegistryPath(StartupLocation location)
    {
        switch (location)
        {
        case StartupLocation::HKLM_Run:
        case StartupLocation::HKLM_RunOnce:
            return L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\" +
                (location == StartupLocation::HKLM_Run ? L"Run" : L"RunOnce");
        case StartupLocation::HKCU_Run:
        case StartupLocation::HKCU_RunOnce:
            return L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\" +
                (location == StartupLocation::HKCU_Run ? L"Run" : L"RunOnce");
        default:
            return String::Empty;
        }
    }

    RegistryKey^ StartupManager::GetRegistryRoot(StartupLocation location)
    {
        switch (location)
        {
        case StartupLocation::HKLM_Run:
        case StartupLocation::HKLM_RunOnce:
            return Registry::LocalMachine;
        case StartupLocation::HKCU_Run:
        case StartupLocation::HKCU_RunOnce:
            return Registry::CurrentUser;
        default:
            return nullptr;
        }
    }

    bool StartupManager::DisableStartupItem(StartupItem^ item)
    {
        if (item->Location == StartupLocation::StartupFolder ||
            item->Location == StartupLocation::CommonStartupFolder)
        {
            try
            {
                if (System::IO::File::Exists(item->Path))
                {
                    String^ backupContent = System::IO::File::ReadAllText(item->Path);
                    RegistryBackup::BackupStartupItem(item->Location, item->Name, backupContent);

                    String^ disabledPath = item->Path + L".disabled";
                    System::IO::File::Move(item->Path, disabledPath);
                    item->Enabled = false;
                    return true;
                }
            }
            catch (Exception^ ex)
            {
                System::Diagnostics::Debug::WriteLine(ex->Message);
            }
            return false;
        }

        try
        {
            auto root = GetRegistryRoot(item->Location);
            auto path = GetRegistryPath(item->Location);
            if (root != nullptr && !String::IsNullOrEmpty(path))
            {
                auto key = root->OpenSubKey(path, true);
                if (key != nullptr)
                {
                    auto value = key->GetValue(item->Name);
                    if (value != nullptr)
                    {
                        RegistryBackup::BackupStartupItem(item->Location, item->Name, value);

                        key->DeleteValue(item->Name, false);
                        key->SetValue(item->Name + L"-Disabled", value);
                        key->Close();
                        item->Enabled = false;
                        return true;
                    }
                    key->Close();
                }
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
        return false;
    }

    bool StartupManager::EnableStartupItem(StartupItem^ item)
    {
        if (item->Location == StartupLocation::StartupFolder ||
            item->Location == StartupLocation::CommonStartupFolder)
        {
            try
            {
                String^ disabledPath = item->Path + L".disabled";
                if (System::IO::File::Exists(disabledPath))
                {
                    System::IO::File::Move(disabledPath, item->Path);
                    item->Enabled = true;
                    return true;
                }
            }
            catch (Exception^ ex)
            {
                System::Diagnostics::Debug::WriteLine(ex->Message);
            }
            return false;
        }

        try
        {
            auto root = GetRegistryRoot(item->Location);
            auto path = GetRegistryPath(item->Location);
            if (root != nullptr && !String::IsNullOrEmpty(path))
            {
                auto key = root->OpenSubKey(path, true);
                if (key != nullptr)
                {
                    String^ disabledName = item->Name + L"-Disabled";
                    auto value = key->GetValue(disabledName);
                    if (value != nullptr)
                    {
                        key->DeleteValue(disabledName, false);
                        key->SetValue(item->Name, value);
                        key->Close();
                        item->Enabled = true;
                        return true;
                    }
                    key->Close();
                }
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
        return false;
    }

    bool StartupManager::DeleteStartupItem(StartupItem^ item)
    {
        if (item->Location == StartupLocation::StartupFolder ||
            item->Location == StartupLocation::CommonStartupFolder)
        {
            try
            {
                if (System::IO::File::Exists(item->Path))
                {
                    String^ backupContent = System::IO::File::ReadAllText(item->Path);
                    RegistryBackup::BackupStartupItem(item->Location, item->Name, backupContent);

                    System::IO::File::Delete(item->Path);
                    return true;
                }
            }
            catch (Exception^ ex)
            {
                System::Diagnostics::Debug::WriteLine(ex->Message);
            }
            return false;
        }

        try
        {
            auto root = GetRegistryRoot(item->Location);
            auto path = GetRegistryPath(item->Location);
            if (root != nullptr && !String::IsNullOrEmpty(path))
            {
                auto key = root->OpenSubKey(path, true);
                if (key != nullptr)
                {
                    auto value = key->GetValue(item->Name);
                    if (value != nullptr)
                    {
                        RegistryBackup::BackupStartupItem(item->Location, item->Name, value);

                        key->DeleteValue(item->Name, false);
                        key->Close();
                        return true;
                    }
                    key->Close();
                }
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
        return false;
    }
}
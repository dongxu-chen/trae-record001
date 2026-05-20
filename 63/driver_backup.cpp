#include "driver_backup.h"

namespace SystemOptimizer
{
    DriverBackup::DriverBackup()
    {
    }

    String^ DriverBackup::GetDefaultBackupPath()
    {
        String^ path = Environment::GetFolderPath(Environment::SpecialFolder::UserProfile) + "\\DriverBackups";
        if (!System::IO::Directory::Exists(path))
        {
            System::IO::Directory::CreateDirectory(path);
        }
        return path;
    }

    List<DriverInfo^>^ DriverBackup::GetInstalledDrivers()
    {
        auto results = gcnew List<DriverInfo^>();

        try
        {
            auto process = gcnew Process();
            process->StartInfo->FileName = "dism.exe";
            process->StartInfo->Arguments = "/online /get-drivers /format:table";
            process->StartInfo->CreateNoWindow = true;
            process->StartInfo->UseShellExecute = false;
            process->StartInfo->RedirectStandardOutput = true;
            process->StartInfo->StandardOutputEncoding = System::Text::Encoding::UTF8;
            process->Start();

            String^ output = process->StandardOutput->ReadToEnd();
            process->WaitForExit();

            array<String^>^ lines = output->Split(gcnew array<wchar_t> { '\n' }, StringSplitOptions::RemoveEmptyEntries);

            bool startReading = false;
            for each (String^ line in lines)
            {
                if (line->Contains("---"))
                {
                    startReading = true;
                    continue;
                }

                if (!startReading)
                {
                    continue;
                }

                if (String::IsNullOrWhiteSpace(line))
                {
                    continue;
                }

                array<String^>^ parts = line->Split(gcnew array<wchar_t> { ' ' }, StringSplitOptions::RemoveEmptyEntries);
                if (parts->Length >= 5)
                {
                    auto driver = gcnew DriverInfo();
                    driver->DriverName = parts[0];
                    driver->OriginalFileName = parts[1];
                    driver->ProviderName = parts[2];
                    driver->DriverDate = parts[3];
                    driver->DriverVersion = parts[4];
                    results->Add(driver);
                }
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }

        return results;
    }

    bool DriverBackup::BackupDrivers(String^ backupPath)
    {
        try
        {
            if (!System::IO::Directory::Exists(backupPath))
            {
                System::IO::Directory::CreateDirectory(backupPath);
            }

            String^ timestamp = DateTime::Now.ToString("yyyyMMdd_HHmmss");
            String^ fullBackupPath = System::IO::Path::Combine(backupPath, "Backup_" + timestamp);

            if (!System::IO::Directory::Exists(fullBackupPath))
            {
                System::IO::Directory::CreateDirectory(fullBackupPath);
            }

            auto process = gcnew Process();
            process->StartInfo->FileName = "dism.exe";
            process->StartInfo->Arguments = "/online /export-driver /destination:\"" + fullBackupPath + "\"";
            process->StartInfo->CreateNoWindow = true;
            process->StartInfo->UseShellExecute = false;
            process->StartInfo->RedirectStandardOutput = true;
            process->StartInfo->Verb = "runas";
            process->Start();
            process->WaitForExit();

            return process->ExitCode == 0;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }

    bool DriverBackup::RestoreDrivers(String^ backupPath)
    {
        try
        {
            if (!System::IO::Directory::Exists(backupPath))
            {
                return false;
            }

            auto process = gcnew Process();
            process->StartInfo->FileName = "pnputil.exe";
            process->StartInfo->Arguments = "/add-driver \"" + backupPath + "\\*.inf\" /install /subdirs";
            process->StartInfo->CreateNoWindow = true;
            process->StartInfo->UseShellExecute = false;
            process->StartInfo->RedirectStandardOutput = true;
            process->StartInfo->Verb = "runas";
            process->Start();
            process->WaitForExit();

            return process->ExitCode == 0;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }
}
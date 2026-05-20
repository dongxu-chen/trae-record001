#pragma once

using namespace System;
using namespace System::Collections::Generic;
using namespace System::Diagnostics;

namespace SystemOptimizer
{
    public ref class DriverInfo
    {
    public:
        property String^ DriverName;
        property String^ OriginalFileName;
        property String^ ProviderName;
        property String^ DriverVersion;
        property String^ DriverDate;
    };

    public ref class DriverBackup
    {
    public:
        DriverBackup();
        List<DriverInfo^>^ GetInstalledDrivers();
        bool BackupDrivers(String^ backupPath);
        bool RestoreDrivers(String^ backupPath);
        String^ GetDefaultBackupPath();
    };
}
#pragma once

using namespace System;
using namespace System::Collections::Generic;
using namespace Microsoft::Win32;

namespace SystemOptimizer
{
    public enum class StartupLocation
    {
        HKLM_Run,
        HKCU_Run,
        HKLM_RunOnce,
        HKCU_RunOnce,
        StartupFolder,
        CommonStartupFolder
    };

    public ref class StartupItem
    {
    public:
        property String^ Name;
        property String^ Path;
        property bool Enabled;
        property StartupLocation Location;
    };

    public ref class StartupManager
    {
    public:
        StartupManager();
        List<StartupItem^>^ GetStartupItems();
        bool DisableStartupItem(StartupItem^ item);
        bool EnableStartupItem(StartupItem^ item);
        bool DeleteStartupItem(StartupItem^ item);

    private:
        void ScanRegistryKey(RegistryKey^ key, StartupLocation location, List<StartupItem^>^ results);
        void ScanStartupFolder(String^ folder, StartupLocation location, List<StartupItem^>^ results);
        String^ GetRegistryPath(StartupLocation location);
        RegistryKey^ GetRegistryRoot(StartupLocation location);
    };
}
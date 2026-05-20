#pragma once

using namespace System;
using namespace System::Collections::Generic;
using namespace Microsoft::Win32;

namespace SystemOptimizer
{
    public enum class RegistryEntryType
    {
        InvalidPath,
        EmptyKey,
        MissingFile,
        ObsoleteEntry,
        Blacklisted
    };

    public ref class RegistryEntry
    {
    public:
        property String^ Path;
        property RegistryEntryType Type;
    };

    public ref class RegistryCleaner
    {
    public:
        RegistryCleaner();
        List<RegistryEntry^>^ ScanInvalidRegistry();
        bool RemoveRegistryEntry(String^ path);

    private:
        void ScanRegistryKey(RegistryKey^ key, String^ path, List<RegistryEntry^>^ results);
        bool IsInvalidPath(String^ path);
        bool IsFileMissing(String^ path);
    };
}
#pragma once

using namespace System;
using namespace System::Collections::Generic;

namespace SystemOptimizer
{
    public ref class TempFile
    {
    public:
        property String^ Path;
        property __int64 Size;
    };

    public ref class DiskCleaner
    {
    public:
        DiskCleaner();
        List<TempFile^>^ ScanTempFiles();
        bool DeleteFile(String^ path);

    private:
        void ScanDirectory(String^ path, List<TempFile^>^ results);
        bool IsTempFile(String^ path);
    };
}
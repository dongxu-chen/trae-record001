#pragma once

using namespace System;
using namespace System::Collections::Generic;
using namespace System::Management;

namespace SystemOptimizer
{
    public ref class RestorePointInfo
    {
    public:
        property int SequenceNumber;
        property String^ Description;
        property DateTime CreationTime;
        property String^ RestorePointType;
    };

    public ref class RestorePointManager
    {
    public:
        RestorePointManager();
        bool CreateRestorePoint(String^ description);
        List<RestorePointInfo^>^ GetRestorePoints();
        bool RestoreToPoint(int sequenceNumber);
        bool DeleteRestorePoint(int sequenceNumber);
    };
}
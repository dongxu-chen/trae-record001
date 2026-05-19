#pragma once

using namespace System;
using namespace System::Collections::Generic;
using namespace System::Threading;

namespace SystemOptimizer
{
    public enum class CleanupTaskType
    {
        RegistryCleanup,
        DiskCleanup,
        FullCleanup
    };

    public enum class ScheduleFrequency
    {
        Daily,
        Weekly,
        Monthly
    };

    public ref class ScheduledCleanupTask
    {
    public:
        property CleanupTaskType TaskType;
        property ScheduleFrequency Frequency;
        property int Hour;
        property int Minute;
        property int DayOfWeek;
        property int DayOfMonth;
        property bool Enabled;
        property DateTime LastRun;
        property DateTime NextRun;
    };

    public delegate void CleanupProgressEventHandler(String^ message, int progress);

    public ref class ScheduledTaskManager
    {
    public:
        event CleanupProgressEventHandler^ CleanupProgress;

        ScheduledTaskManager();
        ~ScheduledTaskManager();

        bool CreateScheduledTask(ScheduledCleanupTask^ task);
        bool RemoveScheduledTask();
        ScheduledCleanupTask^ GetCurrentTask();
        bool EnableTask();
        bool DisableTask();
        void RunCleanupNow(CleanupTaskType type);

    private:
        Timer^ timer;
        ScheduledCleanupTask^ currentTask;

        void TimerCallback(Object^ state);
        DateTime CalculateNextRun();
        void ExecuteCleanup(CleanupTaskType type);
        void SaveTaskToConfig();
        void LoadTaskFromConfig();
    };
}
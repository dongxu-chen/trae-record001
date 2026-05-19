#include "scheduled_task.h"
#include "registry_cleaner.h"
#include "disk_cleaner.h"

namespace SystemOptimizer
{
    ScheduledTaskManager::ScheduledTaskManager()
    {
        currentTask = nullptr;
        timer = nullptr;
        LoadTaskFromConfig();
    }

    ScheduledTaskManager::~ScheduledTaskManager()
    {
        if (timer != nullptr)
        {
            timer->Dispose();
        }
    }

    void ScheduledTaskManager::LoadTaskFromConfig()
    {
        try
        {
            String^ configPath = Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData) + "\\SystemOptimizer\\scheduled_task.config";
            if (System::IO::File::Exists(configPath))
            {
                auto lines = System::IO::File::ReadAllLines(configPath);
                currentTask = gcnew ScheduledCleanupTask();

                for each (String^ line in lines)
                {
                    array<String^>^ parts = line->Split('=');
                    if (parts->Length == 2)
                    {
                        String^ key = parts[0]->Trim();
                        String^ value = parts[1]->Trim();

                        if (key == "TaskType")
                            currentTask->TaskType = (CleanupTaskType)Enum::Parse(CleanupTaskType::typeid, value);
                        else if (key == "Frequency")
                            currentTask->Frequency = (ScheduleFrequency)Enum::Parse(ScheduleFrequency::typeid, value);
                        else if (key == "Hour")
                            currentTask->Hour = Convert::ToInt32(value);
                        else if (key == "Minute")
                            currentTask->Minute = Convert::ToInt32(value);
                        else if (key == "DayOfWeek")
                            currentTask->DayOfWeek = Convert::ToInt32(value);
                        else if (key == "DayOfMonth")
                            currentTask->DayOfMonth = Convert::ToInt32(value);
                        else if (key == "Enabled")
                            currentTask->Enabled = Convert::ToBoolean(value);
                        else if (key == "LastRun")
                            currentTask->LastRun = DateTime::Parse(value);
                    }
                }

                if (currentTask->Enabled)
                {
                    currentTask->NextRun = CalculateNextRun();
                    TimeSpan delay = currentTask->NextRun - DateTime::Now;
                    if (delay.TotalMilliseconds < 0)
                    {
                        delay = TimeSpan::FromMilliseconds(0);
                    }
                    timer = gcnew Timer(gcnew TimerCallback(this, &ScheduledTaskManager::TimerCallback), nullptr, delay, TimeSpan::FromMinutes(1));
                }
            }
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
    }

    void ScheduledTaskManager::SaveTaskToConfig()
    {
        try
        {
            String^ configDir = Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData) + "\\SystemOptimizer";
            if (!System::IO::Directory::Exists(configDir))
            {
                System::IO::Directory::CreateDirectory(configDir);
            }

            String^ configPath = configDir + "\\scheduled_task.config";
            auto lines = gcnew List<String^>();
            lines->Add("TaskType=" + currentTask->TaskType.ToString());
            lines->Add("Frequency=" + currentTask->Frequency.ToString());
            lines->Add("Hour=" + currentTask->Hour);
            lines->Add("Minute=" + currentTask->Minute);
            lines->Add("DayOfWeek=" + currentTask->DayOfWeek);
            lines->Add("DayOfMonth=" + currentTask->DayOfMonth);
            lines->Add("Enabled=" + currentTask->Enabled);
            lines->Add("LastRun=" + currentTask->LastRun.ToString("s"));

            System::IO::File::WriteAllLines(configPath, lines);
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
        }
    }

    DateTime ScheduledTaskManager::CalculateNextRun()
    {
        if (currentTask == nullptr)
            return DateTime::MaxValue;

        DateTime now = DateTime::Now;
        DateTime nextRun = DateTime(now.Year, now.Month, now.Day, currentTask->Hour, currentTask->Minute, 0);

        switch (currentTask->Frequency)
        {
        case ScheduleFrequency::Daily:
            if (nextRun <= now)
                nextRun = nextRun.AddDays(1);
            break;

        case ScheduleFrequency::Weekly:
            while ((int)nextRun.DayOfWeek != currentTask->DayOfWeek || nextRun <= now)
            {
                nextRun = nextRun.AddDays(1);
            }
            break;

        case ScheduleFrequency::Monthly:
            while (nextRun.Day != currentTask->DayOfMonth || nextRun <= now)
            {
                nextRun = nextRun.AddDays(1);
            }
            break;
        }

        return nextRun;
    }

    bool ScheduledTaskManager::CreateScheduledTask(ScheduledCleanupTask^ task)
    {
        try
        {
            currentTask = task;
            currentTask->NextRun = CalculateNextRun();
            SaveTaskToConfig();

            if (timer != nullptr)
            {
                timer->Dispose();
            }

            if (currentTask->Enabled)
            {
                TimeSpan delay = currentTask->NextRun - DateTime::Now;
                if (delay.TotalMilliseconds < 0)
                {
                    delay = TimeSpan::FromMilliseconds(0);
                }
                timer = gcnew Timer(gcnew TimerCallback(this, &ScheduledTaskManager::TimerCallback), nullptr, delay, TimeSpan::FromMinutes(1));
            }

            return true;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }

    bool ScheduledTaskManager::RemoveScheduledTask()
    {
        try
        {
            if (timer != nullptr)
            {
                timer->Dispose();
                timer = nullptr;
            }

            String^ configPath = Environment::GetFolderPath(Environment::SpecialFolder::ApplicationData) + "\\SystemOptimizer\\scheduled_task.config";
            if (System::IO::File::Exists(configPath))
            {
                System::IO::File::Delete(configPath);
            }

            currentTask = nullptr;
            return true;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }

    ScheduledCleanupTask^ ScheduledTaskManager::GetCurrentTask()
    {
        return currentTask;
    }

    bool ScheduledTaskManager::EnableTask()
    {
        if (currentTask == nullptr)
            return false;

        currentTask->Enabled = true;
        return CreateScheduledTask(currentTask);
    }

    bool ScheduledTaskManager::DisableTask()
    {
        if (currentTask == nullptr)
            return false;

        currentTask->Enabled = false;
        SaveTaskToConfig();

        if (timer != nullptr)
        {
            timer->Dispose();
            timer = nullptr;
        }

        return true;
    }

    void ScheduledTaskManager::TimerCallback(Object^ state)
    {
        if (currentTask == nullptr || !currentTask->Enabled)
            return;

        if (DateTime::Now >= currentTask->NextRun)
        {
            ExecuteCleanup(currentTask->TaskType);
            currentTask->LastRun = DateTime::Now;
            currentTask->NextRun = CalculateNextRun();
            SaveTaskToConfig();
        }
    }

    void ScheduledTaskManager::ExecuteCleanup(CleanupTaskType type)
    {
        CleanupProgress("开始执行定时清理任务...", 0);

        try
        {
            if (type == CleanupTaskType::RegistryCleanup || type == CleanupTaskType::FullCleanup)
            {
                CleanupProgress("正在清理注册表...", 25);
                auto regCleaner = gcnew RegistryCleaner();
                auto invalidEntries = regCleaner->ScanInvalidRegistry();
                int cleaned = 0;
                for each (auto entry in invalidEntries)
                {
                    if (regCleaner->RemoveRegistryEntry(entry->Path))
                        cleaned++;
                }
                CleanupProgress(String::Format("注册表清理完成，清理了 {0} 项", cleaned), 50);
            }

            if (type == CleanupTaskType::DiskCleanup || type == CleanupTaskType::FullCleanup)
            {
                CleanupProgress("正在清理磁盘临时文件...", 75);
                auto diskCleaner = gcnew DiskCleaner();
                auto tempFiles = diskCleaner->ScanTempFiles();
                int cleaned = 0;
                for each (auto file in tempFiles)
                {
                    if (diskCleaner->DeleteFile(file->Path))
                        cleaned++;
                }
                CleanupProgress(String::Format("磁盘清理完成，清理了 {0} 个文件", cleaned), 100);
            }
        }
        catch (Exception^ ex)
        {
            CleanupProgress("清理任务执行出错: " + ex->Message, 100);
        }
    }

    void ScheduledTaskManager::RunCleanupNow(CleanupTaskType type)
    {
        ExecuteCleanup(type);
    }
}
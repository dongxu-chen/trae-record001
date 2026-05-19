#include "restore_point.h"

namespace SystemOptimizer
{
    RestorePointManager::RestorePointManager()
    {
    }

    bool RestorePointManager::CreateRestorePoint(String^ description)
    {
        try
        {
            ManagementScope^ scope = gcnew ManagementScope("\\\\.\\root\\default");
            scope->Connect();

            ManagementClass^ processClass = gcnew ManagementClass(scope, gcnew ManagementPath("SystemRestore"), nullptr);
            ManagementBaseObject^ inParams = processClass->GetMethodParameters("CreateRestorePoint");

            inParams["Description"] = description;
            inParams["RestorePointType"] = 0;
            inParams["EventType"] = 100;

            ManagementBaseObject^ outParams = processClass->InvokeMethod("CreateRestorePoint", inParams, nullptr);

            return Convert::ToInt32(outParams["ReturnValue"]) == 0;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }

    List<RestorePointInfo^>^ RestorePointManager::GetRestorePoints()
    {
        auto results = gcnew List<RestorePointInfo^>();

        try
        {
            ManagementScope^ scope = gcnew ManagementScope("\\\\.\\root\\default");
            scope->Connect();

            SelectQuery^ query = gcnew SelectQuery("SELECT * FROM SystemRestore");
            ManagementObjectSearcher^ searcher = gcnew ManagementObjectSearcher(scope, query);

            for each (ManagementObject^ mo in searcher->Get())
            {
                try
                {
                    auto rp = gcnew RestorePointInfo();
                    rp->SequenceNumber = Convert::ToInt32(mo["SequenceNumber"]);
                    rp->Description = mo["Description"]->ToString();

                    String^ creationTimeStr = mo["CreationTime"]->ToString();
                    if (!String::IsNullOrEmpty(creationTimeStr) && creationTimeStr->Length >= 14)
                    {
                        int year = Convert::ToInt32(creationTimeStr->Substring(0, 4));
                        int month = Convert::ToInt32(creationTimeStr->Substring(4, 2));
                        int day = Convert::ToInt32(creationTimeStr->Substring(6, 2));
                        int hour = Convert::ToInt32(creationTimeStr->Substring(8, 2));
                        int minute = Convert::ToInt32(creationTimeStr->Substring(10, 2));
                        int second = Convert::ToInt32(creationTimeStr->Substring(12, 2));
                        rp->CreationTime = DateTime(year, month, day, hour, minute, second);
                    }

                    int restorePointType = Convert::ToInt32(mo["RestorePointType"]);
                    switch (restorePointType)
                    {
                    case 0:
                        rp->RestorePointType = "应用程序安装";
                        break;
                    case 1:
                        rp->RestorePointType = "应用程序卸载";
                        break;
                    case 6:
                        rp->RestorePointType = "恢复";
                        break;
                    case 7:
                        rp->RestorePointType = "检查点";
                        break;
                    case 10:
                        rp->RestorePointType = "设备驱动安装";
                        break;
                    case 12:
                        rp->RestorePointType = "修改设置";
                        break;
                    case 13:
                        rp->RestorePointType = "关键系统更新";
                        break;
                    default:
                        rp->RestorePointType = "未知类型";
                        break;
                    }

                    results->Add(rp);
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

    bool RestorePointManager::RestoreToPoint(int sequenceNumber)
    {
        try
        {
            ManagementScope^ scope = gcnew ManagementScope("\\\\.\\root\\default");
            scope->Connect();

            ManagementClass^ processClass = gcnew ManagementClass(scope, gcnew ManagementPath("SystemRestore"), nullptr);
            ManagementBaseObject^ inParams = processClass->GetMethodParameters("Restore");

            inParams["SequenceNumber"] = sequenceNumber;

            ManagementBaseObject^ outParams = processClass->InvokeMethod("Restore", inParams, nullptr);

            return Convert::ToInt32(outParams["ReturnValue"]) == 0;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }

    bool RestorePointManager::DeleteRestorePoint(int sequenceNumber)
    {
        try
        {
            ManagementScope^ scope = gcnew ManagementScope("\\\\.\\root\\default");
            scope->Connect();

            ManagementClass^ processClass = gcnew ManagementClass(scope, gcnew ManagementPath("SystemRestore"), nullptr);
            ManagementBaseObject^ inParams = processClass->GetMethodParameters("DeleteRestorePoint");

            inParams["SequenceNumber"] = sequenceNumber;

            ManagementBaseObject^ outParams = processClass->InvokeMethod("DeleteRestorePoint", inParams, nullptr);

            return Convert::ToInt32(outParams["ReturnValue"]) == 0;
        }
        catch (Exception^ ex)
        {
            System::Diagnostics::Debug::WriteLine(ex->Message);
            return false;
        }
    }
}
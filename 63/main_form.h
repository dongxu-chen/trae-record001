#pragma once

#include "registry_cleaner.h"
#include "startup_manager.h"
#include "disk_cleaner.h"
#include "driver_backup.h"
#include "restore_point.h"
#include "scheduled_task.h"

namespace SystemOptimizer
{
    using namespace System;
    using namespace System::ComponentModel;
    using namespace System::Collections;
    using namespace System::Windows::Forms;
    using namespace System::Data;
    using namespace System::Drawing;

    public ref class MainForm : public System::Windows::Forms::Form
    {
    public:
        MainForm(void)
        {
            InitializeComponent();
            registryCleaner = gcnew RegistryCleaner();
            startupManager = gcnew StartupManager();
            diskCleaner = gcnew DiskCleaner();
            driverBackup = gcnew DriverBackup();
            restorePointManager = gcnew RestorePointManager();
            scheduledTaskManager = gcnew ScheduledTaskManager();
        }

    protected:
        ~MainForm()
        {
            if (components)
            {
                delete components;
            }
        }

    private:
        System::Windows::Forms::TabControl^ tabControl;
        System::Windows::Forms::TabPage^ tabRegistry;
        System::Windows::Forms::TabPage^ tabStartup;
        System::Windows::Forms::TabPage^ tabDisk;
        System::Windows::Forms::TabPage^ tabDriver;
        System::Windows::Forms::TabPage^ tabRestorePoint;
        System::Windows::Forms::TabPage^ tabSchedule;
        System::Windows::Forms::ListView^ listViewRegistry;
        System::Windows::Forms::Button^ btnScanRegistry;
        System::Windows::Forms::Button^ btnCleanRegistry;
        System::Windows::Forms::CheckBox^ chkSelectAllRegistry;
        System::Windows::Forms::ListView^ listViewStartup;
        System::Windows::Forms::Button^ btnRefreshStartup;
        System::Windows::Forms::Button^ btnDisableStartup;
        System::Windows::Forms::Button^ btnEnableStartup;
        System::Windows::Forms::Button^ btnDeleteStartup;
        System::Windows::Forms::CheckedListBox^ checkedListBoxDisk;
        System::Windows::Forms::Button^ btnScanDisk;
        System::Windows::Forms::Button^ btnCleanDisk;
        System::Windows::Forms::ListView^ listViewDrivers;
        System::Windows::Forms::Button^ btnRefreshDrivers;
        System::Windows::Forms::Button^ btnBackupDrivers;
        System::Windows::Forms::TextBox^ txtBackupPath;
        System::Windows::Forms::Button^ btnBrowseBackupPath;
        System::Windows::Forms::ListView^ listViewRestorePoints;
        System::Windows::Forms::Button^ btnRefreshRestorePoints;
        System::Windows::Forms::Button^ btnCreateRestorePoint;
        System::Windows::Forms::TextBox^ txtRestorePointDesc;
        System::Windows::Forms::Button^ btnRestoreToPoint;
        System::Windows::Forms::Button^ btnDeleteRestorePoint;
        System::Windows::Forms::GroupBox^ groupBoxSchedule;
        System::Windows::Forms::RadioButton^ radioDaily;
        System::Windows::Forms::RadioButton^ radioWeekly;
        System::Windows::Forms::RadioButton^ radioMonthly;
        System::Windows::Forms::NumericUpDown^ numHour;
        System::Windows::Forms::NumericUpDown^ numMinute;
        System::Windows::Forms::ComboBox^ comboDayOfWeek;
        System::Windows::Forms::NumericUpDown^ numDayOfMonth;
        System::Windows::Forms::CheckBox^ chkEnableSchedule;
        System::Windows::Forms::Button^ btnSaveSchedule;
        System::Windows::Forms::Button^ btnRunNow;
        System::Windows::Forms::ComboBox^ comboTaskType;
        System::Windows::Forms::Label^ lblStatus;
        System::Windows::Forms::ProgressBar^ progressBar;
        System::ComponentModel::Container^ components;

        RegistryCleaner^ registryCleaner;
        StartupManager^ startupManager;
        DiskCleaner^ diskCleaner;
        DriverBackup^ driverBackup;
        RestorePointManager^ restorePointManager;
        ScheduledTaskManager^ scheduledTaskManager;

        void InitializeComponent(void)
        {
            this->tabControl = (gcnew System::Windows::Forms::TabControl());
            this->tabRegistry = (gcnew System::Windows::Forms::TabPage());
            this->chkSelectAllRegistry = (gcnew System::Windows::Forms::CheckBox());
            this->btnCleanRegistry = (gcnew System::Windows::Forms::Button());
            this->btnScanRegistry = (gcnew System::Windows::Forms::Button());
            this->listViewRegistry = (gcnew System::Windows::Forms::ListView());
            this->tabStartup = (gcnew System::Windows::Forms::TabPage());
            this->btnDeleteStartup = (gcnew System::Windows::Forms::Button());
            this->btnEnableStartup = (gcnew System::Windows::Forms::Button());
            this->btnDisableStartup = (gcnew System::Windows::Forms::Button());
            this->btnRefreshStartup = (gcnew System::Windows::Forms::Button());
            this->listViewStartup = (gcnew System::Windows::Forms::ListView());
            this->tabDisk = (gcnew System::Windows::Forms::TabPage());
            this->btnCleanDisk = (gcnew System::Windows::Forms::Button());
            this->btnScanDisk = (gcnew System::Windows::Forms::Button());
            this->checkedListBoxDisk = (gcnew System::Windows::Forms::CheckedListBox());
            this->tabDriver = (gcnew System::Windows::Forms::TabPage());
            this->btnBrowseBackupPath = (gcnew System::Windows::Forms::Button());
            this->txtBackupPath = (gcnew System::Windows::Forms::TextBox());
            this->btnBackupDrivers = (gcnew System::Windows::Forms::Button());
            this->btnRefreshDrivers = (gcnew System::Windows::Forms::Button());
            this->listViewDrivers = (gcnew System::Windows::Forms::ListView());
            this->tabRestorePoint = (gcnew System::Windows::Forms::TabPage());
            this->btnDeleteRestorePoint = (gcnew System::Windows::Forms::Button());
            this->btnRestoreToPoint = (gcnew System::Windows::Forms::Button());
            this->txtRestorePointDesc = (gcnew System::Windows::Forms::TextBox());
            this->btnCreateRestorePoint = (gcnew System::Windows::Forms::Button());
            this->btnRefreshRestorePoints = (gcnew System::Windows::Forms::Button());
            this->listViewRestorePoints = (gcnew System::Windows::Forms::ListView());
            this->tabSchedule = (gcnew System::Windows::Forms::TabPage());
            this->btnRunNow = (gcnew System::Windows::Forms::Button());
            this->btnSaveSchedule = (gcnew System::Windows::Forms::Button());
            this->comboTaskType = (gcnew System::Windows::Forms::ComboBox());
            this->numDayOfMonth = (gcnew System::Windows::Forms::NumericUpDown());
            this->comboDayOfWeek = (gcnew System::Windows::Forms::ComboBox());
            this->numMinute = (gcnew System::Windows::Forms::NumericUpDown());
            this->numHour = (gcnew System::Windows::Forms::NumericUpDown());
            this->radioMonthly = (gcnew System::Windows::Forms::RadioButton());
            this->radioWeekly = (gcnew System::Windows::Forms::RadioButton());
            this->radioDaily = (gcnew System::Windows::Forms::RadioButton());
            this->chkEnableSchedule = (gcnew System::Windows::Forms::CheckBox());
            this->groupBoxSchedule = (gcnew System::Windows::Forms::GroupBox());
            this->lblStatus = (gcnew System::Windows::Forms::Label());
            this->progressBar = (gcnew System::Windows::Forms::ProgressBar());
            this->tabControl->SuspendLayout();
            this->tabRegistry->SuspendLayout();
            this->tabStartup->SuspendLayout();
            this->tabDisk->SuspendLayout();
            this->tabDriver->SuspendLayout();
            this->tabRestorePoint->SuspendLayout();
            this->tabSchedule->SuspendLayout();
            this->groupBoxSchedule->SuspendLayout();
            (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numDayOfMonth))->BeginInit();
            (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numMinute))->BeginInit();
            (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numHour))->BeginInit();
            this->SuspendLayout();

            this->tabControl->Controls->Add(this->tabRegistry);
            this->tabControl->Controls->Add(this->tabStartup);
            this->tabControl->Controls->Add(this->tabDisk);
            this->tabControl->Controls->Add(this->tabDriver);
            this->tabControl->Controls->Add(this->tabRestorePoint);
            this->tabControl->Controls->Add(this->tabSchedule);
            this->tabControl->Location = System::Drawing::Point(12, 12);
            this->tabControl->Name = L"tabControl";
            this->tabControl->SelectedIndex = 0;
            this->tabControl->Size = System::Drawing::Size(760, 400);
            this->tabControl->TabIndex = 0;

            this->tabRegistry->Controls->Add(this->chkSelectAllRegistry);
            this->tabRegistry->Controls->Add(this->btnCleanRegistry);
            this->tabRegistry->Controls->Add(this->btnScanRegistry);
            this->tabRegistry->Controls->Add(this->listViewRegistry);
            this->tabRegistry->Location = System::Drawing::Point(4, 22);
            this->tabRegistry->Name = L"tabRegistry";
            this->tabRegistry->Padding = System::Windows::Forms::Padding(3);
            this->tabRegistry->Size = System::Drawing::Size(752, 374);
            this->tabRegistry->TabIndex = 0;
            this->tabRegistry->Text = L"注册表清理";
            this->tabRegistry->UseVisualStyleBackColor = true;

            this->chkSelectAllRegistry->AutoSize = true;
            this->chkSelectAllRegistry->Location = System::Drawing::Point(6, 348);
            this->chkSelectAllRegistry->Name = L"chkSelectAllRegistry";
            this->chkSelectAllRegistry->Size = System::Drawing::Size(48, 16);
            this->chkSelectAllRegistry->TabIndex = 3;
            this->chkSelectAllRegistry->Text = L"全选";
            this->chkSelectAllRegistry->UseVisualStyleBackColor = true;
            this->chkSelectAllRegistry->CheckedChanged += gcnew System::EventHandler(this, &MainForm::chkSelectAllRegistry_CheckedChanged);

            this->btnCleanRegistry->Location = System::Drawing::Point(662, 343);
            this->btnCleanRegistry->Name = L"btnCleanRegistry";
            this->btnCleanRegistry->Size = System::Drawing::Size(80, 25);
            this->btnCleanRegistry->TabIndex = 2;
            this->btnCleanRegistry->Text = L"清理";
            this->btnCleanRegistry->UseVisualStyleBackColor = true;
            this->btnCleanRegistry->Click += gcnew System::EventHandler(this, &MainForm::btnCleanRegistry_Click);

            this->btnScanRegistry->Location = System::Drawing::Point(576, 343);
            this->btnScanRegistry->Name = L"btnScanRegistry";
            this->btnScanRegistry->Size = System::Drawing::Size(80, 25);
            this->btnScanRegistry->TabIndex = 1;
            this->btnScanRegistry->Text = L"扫描";
            this->btnScanRegistry->UseVisualStyleBackColor = true;
            this->btnScanRegistry->Click += gcnew System::EventHandler(this, &MainForm::btnScanRegistry_Click);

            this->listViewRegistry->CheckBoxes = true;
            this->listViewRegistry->FullRowSelect = true;
            this->listViewRegistry->GridLines = true;
            this->listViewRegistry->Location = System::Drawing::Point(6, 6);
            this->listViewRegistry->Name = L"listViewRegistry";
            this->listViewRegistry->Size = System::Drawing::Size(740, 330);
            this->listViewRegistry->TabIndex = 0;
            this->listViewRegistry->UseCompatibleStateImageBehavior = false;
            this->listViewRegistry->View = System::Windows::Forms::View::Details;
            this->listViewRegistry->Columns->Add(L"注册表路径", 500);
            this->listViewRegistry->Columns->Add(L"类型", 120);
            this->listViewRegistry->Columns->Add(L"状态", 100);

            this->tabStartup->Controls->Add(this->btnDeleteStartup);
            this->tabStartup->Controls->Add(this->btnEnableStartup);
            this->tabStartup->Controls->Add(this->btnDisableStartup);
            this->tabStartup->Controls->Add(this->btnRefreshStartup);
            this->tabStartup->Controls->Add(this->listViewStartup);
            this->tabStartup->Location = System::Drawing::Point(4, 22);
            this->tabStartup->Name = L"tabStartup";
            this->tabStartup->Padding = System::Windows::Forms::Padding(3);
            this->tabStartup->Size = System::Drawing::Size(752, 374);
            this->tabStartup->TabIndex = 1;
            this->tabStartup->Text = L"启动项管理";
            this->tabStartup->UseVisualStyleBackColor = true;

            this->btnDeleteStartup->Location = System::Drawing::Point(662, 343);
            this->btnDeleteStartup->Name = L"btnDeleteStartup";
            this->btnDeleteStartup->Size = System::Drawing::Size(80, 25);
            this->btnDeleteStartup->TabIndex = 4;
            this->btnDeleteStartup->Text = L"删除";
            this->btnDeleteStartup->UseVisualStyleBackColor = true;
            this->btnDeleteStartup->Click += gcnew System::EventHandler(this, &MainForm::btnDeleteStartup_Click);

            this->btnEnableStartup->Location = System::Drawing::Point(576, 343);
            this->btnEnableStartup->Name = L"btnEnableStartup";
            this->btnEnableStartup->Size = System::Drawing::Size(80, 25);
            this->btnEnableStartup->TabIndex = 3;
            this->btnEnableStartup->Text = L"启用";
            this->btnEnableStartup->UseVisualStyleBackColor = true;
            this->btnEnableStartup->Click += gcnew System::EventHandler(this, &MainForm::btnEnableStartup_Click);

            this->btnDisableStartup->Location = System::Drawing::Point(490, 343);
            this->btnDisableStartup->Name = L"btnDisableStartup";
            this->btnDisableStartup->Size = System::Drawing::Size(80, 25);
            this->btnDisableStartup->TabIndex = 2;
            this->btnDisableStartup->Text = L"禁用";
            this->btnDisableStartup->UseVisualStyleBackColor = true;
            this->btnDisableStartup->Click += gcnew System::EventHandler(this, &MainForm::btnDisableStartup_Click);

            this->btnRefreshStartup->Location = System::Drawing::Point(404, 343);
            this->btnRefreshStartup->Name = L"btnRefreshStartup";
            this->btnRefreshStartup->Size = System::Drawing::Size(80, 25);
            this->btnRefreshStartup->TabIndex = 1;
            this->btnRefreshStartup->Text = L"刷新";
            this->btnRefreshStartup->UseVisualStyleBackColor = true;
            this->btnRefreshStartup->Click += gcnew System::EventHandler(this, &MainForm::btnRefreshStartup_Click);

            this->listViewStartup->FullRowSelect = true;
            this->listViewStartup->GridLines = true;
            this->listViewStartup->Location = System::Drawing::Point(6, 6);
            this->listViewStartup->Name = L"listViewStartup";
            this->listViewStartup->Size = System::Drawing::Size(740, 330);
            this->listViewStartup->TabIndex = 0;
            this->listViewStartup->UseCompatibleStateImageBehavior = false;
            this->listViewStartup->View = System::Windows::Forms::View::Details;
            this->listViewStartup->Columns->Add(L"名称", 150);
            this->listViewStartup->Columns->Add(L"路径", 400);
            this->listViewStartup->Columns->Add(L"状态", 80);
            this->listViewStartup->Columns->Add(L"位置", 100);

            this->tabDisk->Controls->Add(this->btnCleanDisk);
            this->tabDisk->Controls->Add(this->btnScanDisk);
            this->tabDisk->Controls->Add(this->checkedListBoxDisk);
            this->tabDisk->Location = System::Drawing::Point(4, 22);
            this->tabDisk->Name = L"tabDisk";
            this->tabDisk->Padding = System::Windows::Forms::Padding(3);
            this->tabDisk->Size = System::Drawing::Size(752, 374);
            this->tabDisk->TabIndex = 2;
            this->tabDisk->Text = L"磁盘清理";
            this->tabDisk->UseVisualStyleBackColor = true;

            this->btnCleanDisk->Location = System::Drawing::Point(662, 343);
            this->btnCleanDisk->Name = L"btnCleanDisk";
            this->btnCleanDisk->Size = System::Drawing::Size(80, 25);
            this->btnCleanDisk->TabIndex = 2;
            this->btnCleanDisk->Text = L"清理";
            this->btnCleanDisk->UseVisualStyleBackColor = true;
            this->btnCleanDisk->Click += gcnew System::EventHandler(this, &MainForm::btnCleanDisk_Click);

            this->btnScanDisk->Location = System::Drawing::Point(576, 343);
            this->btnScanDisk->Name = L"btnScanDisk";
            this->btnScanDisk->Size = System::Drawing::Size(80, 25);
            this->btnScanDisk->TabIndex = 1;
            this->btnScanDisk->Text = L"扫描";
            this->btnScanDisk->UseVisualStyleBackColor = true;
            this->btnScanDisk->Click += gcnew System::EventHandler(this, &MainForm::btnScanDisk_Click);

            this->checkedListBoxDisk->FormattingEnabled = true;
            this->checkedListBoxDisk->Location = System::Drawing::Point(6, 6);
            this->checkedListBoxDisk->Name = L"checkedListBoxDisk";
            this->checkedListBoxDisk->Size = System::Drawing::Size(740, 330);
            this->checkedListBoxDisk->TabIndex = 0;

            this->tabDriver->Controls->Add(this->btnBrowseBackupPath);
            this->tabDriver->Controls->Add(this->txtBackupPath);
            this->tabDriver->Controls->Add(this->btnBackupDrivers);
            this->tabDriver->Controls->Add(this->btnRefreshDrivers);
            this->tabDriver->Controls->Add(this->listViewDrivers);
            this->tabDriver->Location = System::Drawing::Point(4, 22);
            this->tabDriver->Name = L"tabDriver";
            this->tabDriver->Padding = System::Windows::Forms::Padding(3);
            this->tabDriver->Size = System::Drawing::Size(752, 374);
            this->tabDriver->TabIndex = 3;
            this->tabDriver->Text = L"驱动备份";
            this->tabDriver->UseVisualStyleBackColor = true;

            this->btnBrowseBackupPath->Location = System::Drawing::Point(500, 343);
            this->btnBrowseBackupPath->Name = L"btnBrowseBackupPath";
            this->btnBrowseBackupPath->Size = System::Drawing::Size(70, 25);
            this->btnBrowseBackupPath->TabIndex = 4;
            this->btnBrowseBackupPath->Text = L"浏览";
            this->btnBrowseBackupPath->UseVisualStyleBackColor = true;
            this->btnBrowseBackupPath->Click += gcnew System::EventHandler(this, &MainForm::btnBrowseBackupPath_Click);

            this->txtBackupPath->Location = System::Drawing::Point(6, 343);
            this->txtBackupPath->Name = L"txtBackupPath";
            this->txtBackupPath->Size = System::Drawing::Size(488, 21);
            this->txtBackupPath->TabIndex = 3;

            this->btnBackupDrivers->Location = System::Drawing::Point(662, 343);
            this->btnBackupDrivers->Name = L"btnBackupDrivers";
            this->btnBackupDrivers->Size = System::Drawing::Size(80, 25);
            this->btnBackupDrivers->TabIndex = 2;
            this->btnBackupDrivers->Text = L"备份";
            this->btnBackupDrivers->UseVisualStyleBackColor = true;
            this->btnBackupDrivers->Click += gcnew System::EventHandler(this, &MainForm::btnBackupDrivers_Click);

            this->btnRefreshDrivers->Location = System::Drawing::Point(576, 343);
            this->btnRefreshDrivers->Name = L"btnRefreshDrivers";
            this->btnRefreshDrivers->Size = System::Drawing::Size(80, 25);
            this->btnRefreshDrivers->TabIndex = 1;
            this->btnRefreshDrivers->Text = L"刷新";
            this->btnRefreshDrivers->UseVisualStyleBackColor = true;
            this->btnRefreshDrivers->Click += gcnew System::EventHandler(this, &MainForm::btnRefreshDrivers_Click);

            this->listViewDrivers->FullRowSelect = true;
            this->listViewDrivers->GridLines = true;
            this->listViewDrivers->Location = System::Drawing::Point(6, 6);
            this->listViewDrivers->Name = L"listViewDrivers";
            this->listViewDrivers->Size = System::Drawing::Size(740, 330);
            this->listViewDrivers->TabIndex = 0;
            this->listViewDrivers->UseCompatibleStateImageBehavior = false;
            this->listViewDrivers->View = System::Windows::Forms::View::Details;
            this->listViewDrivers->Columns->Add(L"驱动名称", 150);
            this->listViewDrivers->Columns->Add(L"原始文件名", 150);
            this->listViewDrivers->Columns->Add(L"提供商", 150);
            this->listViewDrivers->Columns->Add(L"版本", 150);
            this->listViewDrivers->Columns->Add(L"日期", 100);

            this->tabRestorePoint->Controls->Add(this->btnDeleteRestorePoint);
            this->tabRestorePoint->Controls->Add(this->btnRestoreToPoint);
            this->tabRestorePoint->Controls->Add(this->txtRestorePointDesc);
            this->tabRestorePoint->Controls->Add(this->btnCreateRestorePoint);
            this->tabRestorePoint->Controls->Add(this->btnRefreshRestorePoints);
            this->tabRestorePoint->Controls->Add(this->listViewRestorePoints);
            this->tabRestorePoint->Location = System::Drawing::Point(4, 22);
            this->tabRestorePoint->Name = L"tabRestorePoint";
            this->tabRestorePoint->Padding = System::Windows::Forms::Padding(3);
            this->tabRestorePoint->Size = System::Drawing::Size(752, 374);
            this->tabRestorePoint->TabIndex = 4;
            this->tabRestorePoint->Text = L"系统还原点";
            this->tabRestorePoint->UseVisualStyleBackColor = true;

            this->btnDeleteRestorePoint->Location = System::Drawing::Point(662, 343);
            this->btnDeleteRestorePoint->Name = L"btnDeleteRestorePoint";
            this->btnDeleteRestorePoint->Size = System::Drawing::Size(80, 25);
            this->btnDeleteRestorePoint->TabIndex = 5;
            this->btnDeleteRestorePoint->Text = L"删除";
            this->btnDeleteRestorePoint->UseVisualStyleBackColor = true;
            this->btnDeleteRestorePoint->Click += gcnew System::EventHandler(this, &MainForm::btnDeleteRestorePoint_Click);

            this->btnRestoreToPoint->Location = System::Drawing::Point(576, 343);
            this->btnRestoreToPoint->Name = L"btnRestoreToPoint";
            this->btnRestoreToPoint->Size = System::Drawing::Size(80, 25);
            this->btnRestoreToPoint->TabIndex = 4;
            this->btnRestoreToPoint->Text = L"还原";
            this->btnRestoreToPoint->UseVisualStyleBackColor = true;
            this->btnRestoreToPoint->Click += gcnew System::EventHandler(this, &MainForm::btnRestoreToPoint_Click);

            this->txtRestorePointDesc->Location = System::Drawing::Point(6, 343);
            this->txtRestorePointDesc->Name = L"txtRestorePointDesc";
            this->txtRestorePointDesc->Size = System::Drawing::Size(250, 21);
            this->txtRestorePointDesc->TabIndex = 3;
            this->txtRestorePointDesc->Text = L"系统优化工具还原点";

            this->btnCreateRestorePoint->Location = System::Drawing::Point(262, 343);
            this->btnCreateRestorePoint->Name = L"btnCreateRestorePoint";
            this->btnCreateRestorePoint->Size = System::Drawing::Size(80, 25);
            this->btnCreateRestorePoint->TabIndex = 2;
            this->btnCreateRestorePoint->Text = L"创建";
            this->btnCreateRestorePoint->UseVisualStyleBackColor = true;
            this->btnCreateRestorePoint->Click += gcnew System::EventHandler(this, &MainForm::btnCreateRestorePoint_Click);

            this->btnRefreshRestorePoints->Location = System::Drawing::Point(348, 343);
            this->btnRefreshRestorePoints->Name = L"btnRefreshRestorePoints";
            this->btnRefreshRestorePoints->Size = System::Drawing::Size(80, 25);
            this->btnRefreshRestorePoints->TabIndex = 1;
            this->btnRefreshRestorePoints->Text = L"刷新";
            this->btnRefreshRestorePoints->UseVisualStyleBackColor = true;
            this->btnRefreshRestorePoints->Click += gcnew System::EventHandler(this, &MainForm::btnRefreshRestorePoints_Click);

            this->listViewRestorePoints->FullRowSelect = true;
            this->listViewRestorePoints->GridLines = true;
            this->listViewRestorePoints->Location = System::Drawing::Point(6, 6);
            this->listViewRestorePoints->Name = L"listViewRestorePoints";
            this->listViewRestorePoints->Size = System::Drawing::Size(740, 330);
            this->listViewRestorePoints->TabIndex = 0;
            this->listViewRestorePoints->UseCompatibleStateImageBehavior = false;
            this->listViewRestorePoints->View = System::Windows::Forms::View::Details;
            this->listViewRestorePoints->Columns->Add(L"序号", 60);
            this->listViewRestorePoints->Columns->Add(L"描述", 300);
            this->listViewRestorePoints->Columns->Add(L"创建时间", 150);
            this->listViewRestorePoints->Columns->Add(L"类型", 150);

            this->tabSchedule->Controls->Add(this->btnRunNow);
            this->tabSchedule->Controls->Add(this->btnSaveSchedule);
            this->tabSchedule->Controls->Add(this->comboTaskType);
            this->tabSchedule->Controls->Add(this->numDayOfMonth);
            this->tabSchedule->Controls->Add(this->comboDayOfWeek);
            this->tabSchedule->Controls->Add(this->numMinute);
            this->tabSchedule->Controls->Add(this->numHour);
            this->tabSchedule->Controls->Add(this->radioMonthly);
            this->tabSchedule->Controls->Add(this->radioWeekly);
            this->tabSchedule->Controls->Add(this->radioDaily);
            this->tabSchedule->Controls->Add(this->chkEnableSchedule);
            this->tabSchedule->Controls->Add(this->groupBoxSchedule);
            this->tabSchedule->Location = System::Drawing::Point(4, 22);
            this->tabSchedule->Name = L"tabSchedule";
            this->tabSchedule->Padding = System::Windows::Forms::Padding(3);
            this->tabSchedule->Size = System::Drawing::Size(752, 374);
            this->tabSchedule->TabIndex = 5;
            this->tabSchedule->Text = L"定时清理";
            this->tabSchedule->UseVisualStyleBackColor = true;

            this->btnRunNow->Location = System::Drawing::Point(620, 343);
            this->btnRunNow->Name = L"btnRunNow";
            this->btnRunNow->Size = System::Drawing::Size(120, 25);
            this->btnRunNow->TabIndex = 10;
            this->btnRunNow->Text = L"立即执行清理";
            this->btnRunNow->UseVisualStyleBackColor = true;
            this->btnRunNow->Click += gcnew System::EventHandler(this, &MainForm::btnRunNow_Click);

            this->btnSaveSchedule->Location = System::Drawing::Point(494, 343);
            this->btnSaveSchedule->Name = L"btnSaveSchedule";
            this->btnSaveSchedule->Size = System::Drawing::Size(120, 25);
            this->btnSaveSchedule->TabIndex = 9;
            this->btnSaveSchedule->Text = L"保存计划任务";
            this->btnSaveSchedule->UseVisualStyleBackColor = true;
            this->btnSaveSchedule->Click += gcnew System::EventHandler(this, &MainForm::btnSaveSchedule_Click);

            this->comboTaskType->DropDownStyle = System::Windows::Forms::ComboBoxStyle::DropDownList;
            this->comboTaskType->FormattingEnabled = true;
            this->comboTaskType->Items->AddRange(gcnew cli::array< System::Object^  >(3) {L"注册表清理", L"磁盘清理", L"完整清理"});
            this->comboTaskType->Location = System::Drawing::Point(100, 30);
            this->comboTaskType->Name = L"comboTaskType";
            this->comboTaskType->Size = System::Drawing::Size(150, 20);
            this->comboTaskType->TabIndex = 8;

            this->numDayOfMonth->Location = System::Drawing::Point(400, 140);
            this->numDayOfMonth->Maximum = System::Decimal(gcnew cli::array< System::Int32^  >(4) {31, 0, 0, 0});
            this->numDayOfMonth->Minimum = System::Decimal(gcnew cli::array< System::Int32^  >(4) {1, 0, 0, 0});
            this->numDayOfMonth->Name = L"numDayOfMonth";
            this->numDayOfMonth->Size = System::Drawing::Size(80, 21);
            this->numDayOfMonth->TabIndex = 7;
            this->numDayOfMonth->Value = System::Decimal(gcnew cli::array< System::Int32^  >(4) {1, 0, 0, 0});

            this->comboDayOfWeek->DropDownStyle = System::Windows::Forms::ComboBoxStyle::DropDownList;
            this->comboDayOfWeek->FormattingEnabled = true;
            this->comboDayOfWeek->Items->AddRange(gcnew cli::array< System::Object^  >(7) {
                L"周日", L"周一", L"周二", L"周三", L"周四", L"周五", L"周六"});
            this->comboDayOfWeek->Location = System::Drawing::Point(400, 100);
            this->comboDayOfWeek->Name = L"comboDayOfWeek";
            this->comboDayOfWeek->Size = System::Drawing::Size(100, 20);
            this->comboDayOfWeek->TabIndex = 6;

            this->numMinute->Location = System::Drawing::Point(200, 100);
            this->numMinute->Maximum = System::Decimal(gcnew cli::array< System::Int32^  >(4) {59, 0, 0, 0});
            this->numMinute->Name = L"numMinute";
            this->numMinute->Size = System::Drawing::Size(80, 21);
            this->numMinute->TabIndex = 5;

            this->numHour->Location = System::Drawing::Point(100, 100);
            this->numHour->Maximum = System::Decimal(gcnew cli::array< System::Int32^  >(4) {23, 0, 0, 0});
            this->numHour->Name = L"numHour";
            this->numHour->Size = System::Drawing::Size(80, 21);
            this->numHour->TabIndex = 4;

            this->radioMonthly->AutoSize = true;
            this->radioMonthly->Location = System::Drawing::Point(300, 140);
            this->radioMonthly->Name = L"radioMonthly";
            this->radioMonthly->Size = System::Drawing::Size(47, 16);
            this->radioMonthly->TabIndex = 3;
            this->radioMonthly->Text = L"每月";
            this->radioMonthly->UseVisualStyleBackColor = true;

            this->radioWeekly->AutoSize = true;
            this->radioWeekly->Location = System::Drawing::Point(300, 100);
            this->radioWeekly->Name = L"radioWeekly";
            this->radioWeekly->Size = System::Drawing::Size(47, 16);
            this->radioWeekly->TabIndex = 2;
            this->radioWeekly->Text = L"每周";
            this->radioWeekly->UseVisualStyleBackColor = true;

            this->radioDaily->AutoSize = true;
            this->radioDaily->Checked = true;
            this->radioDaily->Location = System::Drawing::Point(100, 60);
            this->radioDaily->Name = L"radioDaily";
            this->radioDaily->Size = System::Drawing::Size(47, 16);
            this->radioDaily->TabIndex = 1;
            this->radioDaily->TabStop = true;
            this->radioDaily->Text = L"每天";
            this->radioDaily->UseVisualStyleBackColor = true;

            this->chkEnableSchedule->AutoSize = true;
            this->chkEnableSchedule->Location = System::Drawing::Point(10, 10);
            this->chkEnableSchedule->Name = L"chkEnableSchedule";
            this->chkEnableSchedule->Size = System::Drawing::Size(72, 16);
            this->chkEnableSchedule->TabIndex = 0;
            this->chkEnableSchedule->Text = L"启用计划";
            this->chkEnableSchedule->UseVisualStyleBackColor = true;

            this->groupBoxSchedule->Location = System::Drawing::Point(6, 6);
            this->groupBoxSchedule->Name = L"groupBoxSchedule";
            this->groupBoxSchedule->Size = System::Drawing::Size(500, 200);
            this->groupBoxSchedule->TabIndex = 0;
            this->groupBoxSchedule->TabStop = false;
            this->groupBoxSchedule->Text = L"计划任务设置";

            this->lblStatus->AutoSize = true;
            this->lblStatus->Location = System::Drawing::Point(12, 420);
            this->lblStatus->Name = L"lblStatus";
            this->lblStatus->Size = System::Drawing::Size(41, 12);
            this->lblStatus->TabIndex = 1;
            this->lblStatus->Text = L"就绪";

            this->progressBar->Location = System::Drawing::Point(500, 415);
            this->progressBar->Name = L"progressBar";
            this->progressBar->Size = System::Drawing::Size(272, 20);
            this->progressBar->TabIndex = 2;

            this->AutoScaleDimensions = System::Drawing::SizeF(6, 12);
            this->AutoScaleMode = System::Windows::Forms::AutoScaleMode::Font;
            this->ClientSize = System::Drawing::Size(784, 450);
            this->Controls->Add(this->progressBar);
            this->Controls->Add(this->lblStatus);
            this->Controls->Add(this->tabControl);
            this->FormBorderStyle = System::Windows::Forms::FormBorderStyle::FixedSingle;
            this->MaximizeBox = false;
            this->Name = L"MainForm";
            this->StartPosition = System::Windows::Forms::FormStartPosition::CenterScreen;
            this->Text = L"Windows 系统优化工具";
            this->Load += gcnew System::EventHandler(this, &MainForm::MainForm_Load);
            this->tabControl->ResumeLayout(false);
            this->tabRegistry->ResumeLayout(false);
            this->tabRegistry->PerformLayout();
            this->tabStartup->ResumeLayout(false);
            this->tabStartup->PerformLayout();
            this->tabDisk->ResumeLayout(false);
            this->tabDriver->ResumeLayout(false);
            this->tabDriver->PerformLayout();
            this->tabRestorePoint->ResumeLayout(false);
            this->tabRestorePoint->PerformLayout();
            this->tabSchedule->ResumeLayout(false);
            this->tabSchedule->PerformLayout();
            this->groupBoxSchedule->ResumeLayout(false);
            (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numDayOfMonth))->EndInit();
            (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numMinute))->EndInit();
            (cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numHour))->EndInit();
            this->ResumeLayout(false);
            this->PerformLayout();
        }

    private:
        System::Void MainForm_Load(System::Object^ sender, System::EventArgs^ e)
        {
            LoadStartupItems();
            txtBackupPath->Text = driverBackup->GetDefaultBackupPath();
            comboTaskType->SelectedIndex = 2;
            comboDayOfWeek->SelectedIndex = 0;
        }

        System::Void btnScanRegistry_Click(System::Object^ sender, System::EventArgs^ e)
        {
            lblStatus->Text = L"正在扫描注册表...";
            progressBar->Value = 0;
            listViewRegistry->Items->Clear();

            auto invalidEntries = registryCleaner->ScanInvalidRegistry();
            progressBar->Maximum = invalidEntries->Count;

            for each (auto entry in invalidEntries)
            {
                auto item = gcnew ListViewItem(entry->Path);
                item->SubItems->Add(entry->Type.ToString());
                item->SubItems->Add(L"无效");
                listViewRegistry->Items->Add(item);
                progressBar->Value++;
            }

            lblStatus->Text = String::Format(L"扫描完成，发现 {0} 个无效注册表项", invalidEntries->Count);
        }

        System::Void btnCleanRegistry_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (listViewRegistry->CheckedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要清理的注册表项", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto result = MessageBox::Show(String::Format(L"确定要清理选中的 {0} 个注册表项吗？", listViewRegistry->CheckedItems->Count),
                L"确认", MessageBoxButtons::YesNo, MessageBoxIcon::Warning);

            if (result == System::Windows::Forms::DialogResult::Yes)
            {
                lblStatus->Text = L"正在清理注册表...";
                progressBar->Value = 0;
                progressBar->Maximum = listViewRegistry->CheckedItems->Count;

                int cleaned = 0;
                for each (ListViewItem^ item in listViewRegistry->CheckedItems)
                {
                    if (registryCleaner->RemoveRegistryEntry(item->Text))
                    {
                        cleaned++;
                    }
                    progressBar->Value++;
                }

                listViewRegistry->Items->Clear();
                lblStatus->Text = String::Format(L"清理完成，成功清理 {0} 个注册表项", cleaned);
            }
        }

        System::Void chkSelectAllRegistry_CheckedChanged(System::Object^ sender, System::EventArgs^ e)
        {
            for each (ListViewItem^ item in listViewRegistry->Items)
            {
                item->Checked = chkSelectAllRegistry->Checked;
            }
        }

        System::Void LoadStartupItems()
        {
            listViewStartup->Items->Clear();
            auto startupItems = startupManager->GetStartupItems();

            for each (auto item in startupItems)
            {
                auto lvi = gcnew ListViewItem(item->Name);
                lvi->SubItems->Add(item->Path);
                lvi->SubItems->Add(item->Enabled ? L"启用" : L"禁用");
                lvi->SubItems->Add(item->Location.ToString());
                lvi->Tag = item;
                listViewStartup->Items->Add(lvi);
            }
        }

        System::Void btnRefreshStartup_Click(System::Object^ sender, System::EventArgs^ e)
        {
            LoadStartupItems();
            lblStatus->Text = L"启动项列表已刷新";
        }

        System::Void btnDisableStartup_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (listViewStartup->SelectedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要禁用的启动项", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto lvi = listViewStartup->SelectedItems[0];
            auto item = dynamic_cast<StartupItem^>(lvi->Tag);

            if (startupManager->DisableStartupItem(item))
            {
                LoadStartupItems();
                lblStatus->Text = String::Format(L"已禁用启动项: {0}", item->Name);
            }
        }

        System::Void btnEnableStartup_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (listViewStartup->SelectedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要启用的启动项", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto lvi = listViewStartup->SelectedItems[0];
            auto item = dynamic_cast<StartupItem^>(lvi->Tag);

            if (startupManager->EnableStartupItem(item))
            {
                LoadStartupItems();
                lblStatus->Text = String::Format(L"已启用启动项: {0}", item->Name);
            }
        }

        System::Void btnDeleteStartup_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (listViewStartup->SelectedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要删除的启动项", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto lvi = listViewStartup->SelectedItems[0];
            auto item = dynamic_cast<StartupItem^>(lvi->Tag);

            auto result = MessageBox::Show(String::Format(L"确定要删除启动项: {0} ?", item->Name),
                L"确认", MessageBoxButtons::YesNo, MessageBoxIcon::Warning);

            if (result == System::Windows::Forms::DialogResult::Yes)
            {
                if (startupManager->DeleteStartupItem(item))
                {
                    LoadStartupItems();
                    lblStatus->Text = String::Format(L"已删除启动项: {0}", item->Name);
                }
            }
        }

        System::Void btnScanDisk_Click(System::Object^ sender, System::EventArgs^ e)
        {
            lblStatus->Text = L"正在扫描临时文件...";
            progressBar->Value = 0;
            checkedListBoxDisk->Items->Clear();

            auto tempFiles = diskCleaner->ScanTempFiles();
            progressBar->Maximum = tempFiles->Count;

            __int64 totalSize = 0;
            for each (auto file in tempFiles)
            {
                checkedListBoxDisk->Items->Add(file->Path, true);
                totalSize += file->Size;
                progressBar->Value++;
            }

            double sizeMB = totalSize / (1024.0 * 1024.0);
            lblStatus->Text = String::Format(L"扫描完成，发现 {0} 个文件，共 {1:F2} MB", tempFiles->Count, sizeMB);
        }

        System::Void btnCleanDisk_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (checkedListBoxDisk->CheckedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要清理的文件", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto result = MessageBox::Show(String::Format(L"确定要清理选中的 {0} 个文件吗？", checkedListBoxDisk->CheckedItems->Count),
                L"确认", MessageBoxButtons::YesNo, MessageBoxIcon::Warning);

            if (result == System::Windows::Forms::DialogResult::Yes)
            {
                lblStatus->Text = L"正在清理临时文件...";
                progressBar->Value = 0;
                progressBar->Maximum = checkedListBoxDisk->CheckedItems->Count;

                int cleaned = 0;
                __int64 freedSize = 0;

                for each (String^ filePath in checkedListBoxDisk->CheckedItems)
                {
                    auto fileInfo = gcnew System::IO::FileInfo(filePath);
                    if (diskCleaner->DeleteFile(filePath))
                    {
                        cleaned++;
                        freedSize += fileInfo->Length;
                    }
                    progressBar->Value++;
                }

                checkedListBoxDisk->Items->Clear();
                double freedMB = freedSize / (1024.0 * 1024.0);
                lblStatus->Text = String::Format(L"清理完成，成功清理 {0} 个文件，释放 {1:F2} MB 空间", cleaned, freedMB);
            }
        }

        System::Void btnRefreshDrivers_Click(System::Object^ sender, System::EventArgs^ e)
        {
            lblStatus->Text = L"正在获取驱动列表...";
            listViewDrivers->Items->Clear();

            auto drivers = driverBackup->GetInstalledDrivers();
            progressBar->Maximum = drivers->Count;

            for each (auto driver in drivers)
            {
                auto item = gcnew ListViewItem(driver->DriverName);
                item->SubItems->Add(driver->OriginalFileName);
                item->SubItems->Add(driver->ProviderName);
                item->SubItems->Add(driver->DriverVersion);
                item->SubItems->Add(driver->DriverDate);
                listViewDrivers->Items->Add(item);
                progressBar->Value++;
            }

            lblStatus->Text = String::Format(L"获取完成，共 {0} 个驱动程序", drivers->Count);
        }

        System::Void btnBackupDrivers_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (String::IsNullOrEmpty(txtBackupPath->Text))
            {
                MessageBox::Show(L"请先选择备份路径", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            lblStatus->Text = L"正在备份驱动程序...";
            progressBar->Value = 0;

            if (driverBackup->BackupDrivers(txtBackupPath->Text))
            {
                progressBar->Value = 100;
                lblStatus->Text = L"驱动备份完成";
                MessageBox::Show(L"驱动备份完成！", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
            }
            else
            {
                lblStatus->Text = L"驱动备份失败";
                MessageBox::Show(L"驱动备份失败，请检查权限！", L"错误", MessageBoxButtons::OK, MessageBoxIcon::Error);
            }
        }

        System::Void btnBrowseBackupPath_Click(System::Object^ sender, System::EventArgs^ e)
        {
            auto dialog = gcnew FolderBrowserDialog();
            dialog->SelectedPath = txtBackupPath->Text;
            if (dialog->ShowDialog() == System::Windows::Forms::DialogResult::OK)
            {
                txtBackupPath->Text = dialog->SelectedPath;
            }
        }

        System::Void btnRefreshRestorePoints_Click(System::Object^ sender, System::EventArgs^ e)
        {
            lblStatus->Text = L"正在获取系统还原点列表...";
            listViewRestorePoints->Items->Clear();

            auto restorePoints = restorePointManager->GetRestorePoints();
            progressBar->Maximum = restorePoints->Count;

            for each (auto rp in restorePoints)
            {
                auto item = gcnew ListViewItem(rp->SequenceNumber.ToString());
                item->SubItems->Add(rp->Description);
                item->SubItems->Add(rp->CreationTime.ToString());
                item->SubItems->Add(rp->RestorePointType);
                item->Tag = rp->SequenceNumber;
                listViewRestorePoints->Items->Add(item);
                progressBar->Value++;
            }

            lblStatus->Text = String::Format(L"获取完成，共 {0} 个系统还原点", restorePoints->Count);
        }

        System::Void btnCreateRestorePoint_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (String::IsNullOrEmpty(txtRestorePointDesc->Text))
            {
                MessageBox::Show(L"请输入还原点描述", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            lblStatus->Text = L"正在创建系统还原点...";
            progressBar->Value = 0;

            if (restorePointManager->CreateRestorePoint(txtRestorePointDesc->Text))
            {
                progressBar->Value = 100;
                lblStatus->Text = L"系统还原点创建完成";
                MessageBox::Show(L"系统还原点创建成功！", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                btnRefreshRestorePoints_Click(sender, e);
            }
            else
            {
                lblStatus->Text = L"系统还原点创建失败";
                MessageBox::Show(L"系统还原点创建失败，请检查权限！", L"错误", MessageBoxButtons::OK, MessageBoxIcon::Error);
            }
        }

        System::Void btnRestoreToPoint_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (listViewRestorePoints->SelectedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要还原的还原点", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto lvi = listViewRestorePoints->SelectedItems[0];
            int sequenceNumber = (int)lvi->Tag;

            auto result = MessageBox::Show(String::Format(L"确定要还原到序号为 {0} 的还原点吗？系统将重启！", sequenceNumber),
                L"确认", MessageBoxButtons::YesNo, MessageBoxIcon::Warning);

            if (result == System::Windows::Forms::DialogResult::Yes)
            {
                lblStatus->Text = L"正在执行系统还原...";
                if (restorePointManager->RestoreToPoint(sequenceNumber))
                {
                    lblStatus->Text = L"系统还原命令已发送";
                }
                else
                {
                    lblStatus->Text = L"系统还原失败";
                    MessageBox::Show(L"系统还原失败，请检查权限！", L"错误", MessageBoxButtons::OK, MessageBoxIcon::Error);
                }
            }
        }

        System::Void btnDeleteRestorePoint_Click(System::Object^ sender, System::EventArgs^ e)
        {
            if (listViewRestorePoints->SelectedItems->Count == 0)
            {
                MessageBox::Show(L"请先选择要删除的还原点", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
                return;
            }

            auto lvi = listViewRestorePoints->SelectedItems[0];
            int sequenceNumber = (int)lvi->Tag;

            auto result = MessageBox::Show(String::Format(L"确定要删除序号为 {0} 的还原点吗？", sequenceNumber),
                L"确认", MessageBoxButtons::YesNo, MessageBoxIcon::Warning);

            if (result == System::Windows::Forms::DialogResult::Yes)
            {
                if (restorePointManager->DeleteRestorePoint(sequenceNumber))
                {
                    lblStatus->Text = String::Format(L"已删除还原点，序号: {0}", sequenceNumber);
                    btnRefreshRestorePoints_Click(sender, e);
                }
                else
                {
                    lblStatus->Text = L"删除还原点失败";
                    MessageBox::Show(L"删除还原点失败，请检查权限！", L"错误", MessageBoxButtons::OK, MessageBoxIcon::Error);
                }
            }
        }

        System::Void btnSaveSchedule_Click(System::Object^ sender, System::EventArgs^ e)
        {
            auto task = gcnew ScheduledCleanupTask();
            task->Enabled = chkEnableSchedule->Checked;
            task->TaskType = (CleanupTaskType)comboTaskType->SelectedIndex;

            if (radioDaily->Checked)
                task->Frequency = ScheduleFrequency::Daily;
            else if (radioWeekly->Checked)
                task->Frequency = ScheduleFrequency::Weekly;
            else
                task->Frequency = ScheduleFrequency::Monthly;

            task->Hour = (int)numHour->Value;
            task->Minute = (int)numMinute->Value;
            task->DayOfWeek = comboDayOfWeek->SelectedIndex;
            task->DayOfMonth = (int)numDayOfMonth->Value;

            if (scheduledTaskManager->CreateScheduledTask(task))
            {
                lblStatus->Text = L"计划任务已保存";
                MessageBox::Show(L"计划任务保存成功！", L"提示", MessageBoxButtons::OK, MessageBoxIcon::Information);
            }
            else
            {
                lblStatus->Text = L"计划任务保存失败";
                MessageBox::Show(L"计划任务保存失败！", L"错误", MessageBoxButtons::OK, MessageBoxIcon::Error);
            }
        }

        System::Void btnRunNow_Click(System::Object^ sender, System::EventArgs^ e)
        {
            auto result = MessageBox::Show(L"确定要立即执行清理任务吗？", L"确认",
                MessageBoxButtons::YesNo, MessageBoxIcon::Question);

            if (result == System::Windows::Forms::DialogResult::Yes)
            {
                lblStatus->Text = L"正在执行清理任务...";
                scheduledTaskManager->RunCleanupNow((CleanupTaskType)comboTaskType->SelectedIndex);
                lblStatus->Text = L"清理任务执行完成";
            }
        }
    };
}
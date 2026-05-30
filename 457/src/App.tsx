import { useMemo, useState } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Toolbar } from '@/components/Toolbar';
import { FieldPanel } from '@/components/FieldPanel';
import { PivotGrid } from '@/components/PivotGrid';
import { ChartPanel } from '@/components/ChartPanel';
import { DrillDownModal } from '@/components/DrillDownModal';
import { SettingsModal } from '@/components/SettingsModal';
import { usePivotDataV2 } from '@/hooks/usePivotDataV2';
import { sampleSalesData, getFieldsFromData } from '@/data/sampleData';
import { eventBus } from '@/utils/eventBus';
import { Loader2 } from 'lucide-react';

eventBus.enableDebug(true);

function App() {
  const [showSettings, setShowSettings] = useState(false);

  const {
    data,
    config,
    pivotResult,
    alertRules,
    permissions,
    drillDown,
    drillDownData,
    isLoading,
    progress,
    addRowField,
    removeRowField,
    addColField,
    removeColField,
    addValueField,
    removeValueField,
    updateAggregation,
    addCustomAggregation,
    updateCustomAggregation,
    removeCustomAggregation,
    addAlertRule,
    updateAlertRule,
    removeAlertRule,
    updatePermissions,
    openDrillDown,
    closeDrillDown,
    updateData,
  } = usePivotDataV2(sampleSalesData);

  const fields = useMemo(() => getFieldsFromData(data), [data]);

  const handleDataUpload = (newData: any[]) => {
    if (newData.length > 0) {
      updateData(newData);
    }
  };

  const handleUseSampleData = () => {
    updateData(sampleSalesData);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="h-screen flex flex-col bg-gray-50">
        <Toolbar
          pivotResult={pivotResult}
          rowFields={config.rows}
          colFields={config.cols}
          onDataUpload={handleDataUpload}
          onUseSampleData={handleUseSampleData}
          onOpenSettings={() => setShowSettings(true)}
        />

        {isLoading && (
          <div className="absolute top-0 left-0 right-0 z-50">
            <div className="h-1 bg-gray-200">
              <div
                className="h-full bg-primary-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          <div className="w-72 flex-shrink-0">
            <FieldPanel
              allFields={fields}
              rowFields={config.rows}
              colFields={config.cols}
              valueFields={config.values}
              customAggregations={config.customAggregations}
              onAddRow={addRowField}
              onRemoveRow={removeRowField}
              onAddCol={addColField}
              onRemoveCol={removeColField}
              onAddValue={addValueField}
              onRemoveValue={removeValueField}
              onUpdateAggregation={updateAggregation}
            />
          </div>

          <div className="flex-1 flex flex-col gap-4 min-w-0">
            <div className="flex-1 min-h-0 bg-white rounded-xl shadow-card p-4 overflow-hidden relative">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-100">
                <h3 className="text-lg font-semibold text-gray-800">透视表</h3>
                {isLoading && (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="animate-spin" size={16} />
                    <span>计算中... {Math.round(progress)}%</span>
                  </div>
                )}
              </div>
              <PivotGrid
                pivotResult={pivotResult}
                rowFields={config.rows}
                colFields={config.cols}
                onCellClick={(cell) => {
                  openDrillDown(
                    cell.rowFilters,
                    cell.colFilters,
                    cell.valueField,
                    cell.value
                  );
                }}
              />
            </div>

            <div className="h-80 flex-shrink-0">
              <ChartPanel pivotResult={pivotResult} />
            </div>
          </div>
        </div>

        <DrillDownModal
          isOpen={drillDown.isOpen}
          onClose={closeDrillDown}
          data={drillDownData}
          rowFilters={drillDown.rowFilters}
          colFilters={drillDown.colFilters}
          valueField={drillDown.valueField}
        />

        <SettingsModal
          isOpen={showSettings}
          onClose={() => setShowSettings(false)}
          customAggregations={config.customAggregations}
          alertRules={alertRules}
          permissions={permissions}
          data={data}
          onAddCustomAggregation={addCustomAggregation}
          onUpdateCustomAggregation={updateCustomAggregation}
          onRemoveCustomAggregation={removeCustomAggregation}
          onAddAlertRule={addAlertRule}
          onUpdateAlertRule={updateAlertRule}
          onRemoveAlertRule={removeAlertRule}
          onUpdatePermissions={updatePermissions}
        />
      </div>
    </DndProvider>
  );
}

export default App;

import React from 'react';
import { Rows, Columns, Calculator } from 'lucide-react';
import { DraggableField } from './DraggableField';
import { DropZone } from './DropZone';
import { ValueField, AggregationType, CustomAggregation } from '@/types';
import { getAggregationLabel } from '@/utils/pivotUtils';

interface FieldPanelProps {
  allFields: { name: string; type: 'dimension' | 'measure'; dataType: string }[];
  rowFields: string[];
  colFields: string[];
  valueFields: ValueField[];
  customAggregations: CustomAggregation[];
  onAddRow: (field: string) => void;
  onRemoveRow: (field: string) => void;
  onAddCol: (field: string) => void;
  onRemoveCol: (field: string) => void;
  onAddValue: (field: string, aggregation: string, customAggregationId?: string) => void;
  onRemoveValue: (field: string) => void;
  onUpdateAggregation: (field: string, aggregation: string, customAggregationId?: string) => void;
}

export const FieldPanel: React.FC<FieldPanelProps> = ({
  allFields,
  rowFields,
  colFields,
  valueFields,
  customAggregations,
  onAddRow,
  onRemoveRow,
  onAddCol,
  onRemoveCol,
  onAddValue,
  onRemoveValue,
  onUpdateAggregation,
}) => {
  const usedFields = [...rowFields, ...colFields, ...valueFields.map(v => v.field)];
  const availableFields = allFields.filter(f => !usedFields.includes(f.name));

  const handleAggregationChange = (field: string, value: string) => {
    if (value.startsWith('custom:')) {
      const customId = value.replace('custom:', '');
      onUpdateAggregation(field, 'custom', customId);
    } else {
      onUpdateAggregation(field, value);
    }
  };

  const getSelectValue = (vf: ValueField): string => {
    if (vf.aggregation === 'custom' && vf.customAggregationId) {
      return `custom:${vf.customAggregationId}`;
    }
    return vf.aggregation;
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-xl shadow-card p-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-4 pb-3 border-b border-gray-100">
        字段配置
      </h3>

      <div className="flex-1 overflow-auto mb-4">
        <h4 className="text-sm font-medium text-gray-500 mb-2">可用字段（双击快速添加）</h4>
        <div className="pr-1">
          {availableFields.map(field => (
            <DraggableField
              key={field.name}
              name={field.name}
              type={field.type}
              onDoubleClick={() => {
                if (field.type === 'dimension') {
                  if (rowFields.length === 0 || rowFields.length <= colFields.length) {
                    onAddRow(field.name);
                  } else {
                    onAddCol(field.name);
                  }
                } else {
                  onAddValue(field.name, 'sum');
                }
              }}
            />
          ))}
          {availableFields.length === 0 && (
            <div className="text-sm text-gray-400 text-center py-4">
              所有字段已使用
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-gray-100 pt-4">
        <DropZone
          title="行"
          icon={<Rows size={16} className="text-blue-500" />}
          onDrop={(item) => onAddRow(item.name)}
        >
          {rowFields.map(field => (
            <DraggableField
              key={field}
              name={field}
              type="dimension"
              showRemove
              onRemove={() => onRemoveRow(field)}
            />
          ))}
        </DropZone>

        <DropZone
          title="列"
          icon={<Columns size={16} className="text-purple-500" />}
          onDrop={(item) => onAddCol(item.name)}
        >
          {colFields.map(field => (
            <DraggableField
              key={field}
              name={field}
              type="dimension"
              showRemove
              onRemove={() => onRemoveCol(field)}
            />
          ))}
        </DropZone>

        <DropZone
          title="值"
          icon={<Calculator size={16} className="text-emerald-500" />}
          onDrop={(item) => onAddValue(item.name, 'sum')}
        >
          {valueFields.map(vf => (
            <div key={vf.field} className="flex items-center gap-2 mb-2">
              <div className="flex-1">
                <DraggableField
                  name={vf.field}
                  type="measure"
                  showRemove
                  onRemove={() => onRemoveValue(vf.field)}
                />
              </div>
              <select
                value={getSelectValue(vf)}
                onChange={(e) => handleAggregationChange(vf.field, e.target.value)}
                className="text-xs px-2 py-1.5 rounded border border-gray-200 
                  bg-white text-gray-700 focus:outline-none focus:border-primary-500
                  hover:border-gray-300 transition-colors"
              >
                {(['sum', 'avg', 'count', 'countDistinct'] as AggregationType[]).map(agg => (
                  <option key={agg} value={agg}>
                    {getAggregationLabel(agg)}
                  </option>
                ))}
                {customAggregations.length > 0 && (
                  <>
                    <option disabled>──────────</option>
                    {customAggregations.map(agg => (
                      <option key={agg.id} value={`custom:${agg.id}`}>
                        {agg.name}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </div>
          ))}
        </DropZone>
      </div>
    </div>
  );
};

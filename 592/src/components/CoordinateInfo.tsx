import React from 'react';
import { Point, FunctionConfig } from '../types';
import { formatPi, formatNumber, buildFunctionExpression, evaluateFunction } from '../utils/mathEngine';
import { Crosshair, MapPin } from 'lucide-react';

interface CoordinateInfoProps {
  mousePosition: Point | null;
  markedPoints: Point[];
  functions: FunctionConfig[];
  onClearMarkedPoints: () => void;
}

const CoordinateInfo: React.FC<CoordinateInfoProps> = ({
  mousePosition,
  markedPoints,
  functions,
  onClearMarkedPoints,
}) => {
  const getFunctionValuesAtX = (x: number): { func: FunctionConfig; value: number }[] => {
    return functions
      .filter((f) => f.visible)
      .map((func) => {
        const expr = buildFunctionExpression(func);
        const value = evaluateFunction(expr, x);
        return { func, value };
      });
  };

  return (
    <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <Crosshair className="w-5 h-5 text-blue-400" />
        <h3 className="text-lg font-semibold text-white">坐标信息</h3>
      </div>

      <div className="space-y-4">
        <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-600">
          <p className="text-xs text-gray-400 mb-2">鼠标位置</p>
          {mousePosition ? (
            <div>
              <div className="flex items-center gap-4">
                <div>
                  <span className="text-xs text-gray-500">x</span>
                  <p className="font-mono text-white text-lg">
                    {formatPi(mousePosition.x)}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">y</span>
                  <p className="font-mono text-white text-lg">
                    {formatNumber(mousePosition.y, 4)}
                  </p>
                </div>
              </div>
              <div className="mt-3 space-y-1">
                {getFunctionValuesAtX(mousePosition.x).map(({ func, value }) => (
                  <div
                    key={func.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: func.color }}
                      />
                      <span className="text-gray-400">
                        {func.type.toUpperCase()}
                      </span>
                    </span>
                    <span className="font-mono" style={{ color: func.color }}>
                      {formatNumber(value, 4)}
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                💡 点击图表可标记关键点
              </p>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">将鼠标移动到图表上</p>
          )}
        </div>

        <div className="p-4 bg-gray-900/50 rounded-lg border border-gray-600">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-red-400" />
              <p className="text-xs text-gray-400">
                已标记点 ({markedPoints.length})
              </p>
            </div>
            {markedPoints.length > 0 && (
              <button
                onClick={onClearMarkedPoints}
                className="text-xs text-gray-500 hover:text-red-400 transition-colors"
              >
                清除全部
              </button>
            )}
          </div>
          {markedPoints.length > 0 ? (
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {markedPoints.map((point, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between text-sm py-1"
                >
                  <span className="text-gray-400">#{index + 1}</span>
                  <span className="font-mono text-white">
                    ({formatPi(point.x)}, {formatNumber(point.y, 4)})
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">暂无标记点</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CoordinateInfo;

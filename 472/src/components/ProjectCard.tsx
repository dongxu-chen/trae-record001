import { Link } from 'react-router-dom';
import { Calendar, LineChart, ScatterChart, BarChart3, Edit, Trash2 } from 'lucide-react';
import type { Project } from '../types';

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
  annotationCount: number;
}

const chartTypeIcons: Record<string, any> = {
  timeSeries: LineChart,
  scatter: ScatterChart,
  bar: BarChart3,
};

const chartTypeNames: Record<string, string> = {
  timeSeries: '时序图',
  scatter: '散点图',
  bar: '柱状图',
};

export const ProjectCard = ({ project, onDelete, annotationCount }: ProjectCardProps) => {
  const ChartIcon = chartTypeIcons[project.chartType] || LineChart;

  return (
    <div className="group bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden hover:border-slate-600 transition-all hover:shadow-xl hover:shadow-black/20">
      <div className="h-32 bg-gradient-to-br from-slate-700 to-slate-800 relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center">
          <ChartIcon className="w-16 h-16 text-slate-600" strokeWidth={1} />
        </div>
        <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
          <button
            onClick={(e) => {
              e.preventDefault();
              onDelete(project.id);
            }}
            className="p-2 bg-red-600 hover:bg-red-700 rounded-lg text-white transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
        <div className="absolute bottom-4 left-4">
          <span className="px-3 py-1 bg-slate-900/80 text-slate-300 text-xs font-medium rounded-full">
            {chartTypeNames[project.chartType]}
          </span>
        </div>
      </div>

      <div className="p-5">
        <Link to={`/project/${project.id}`}>
          <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
            {project.name}
          </h3>
        </Link>
        <p className="text-sm text-slate-400 mb-4 line-clamp-2">
          {project.description}
        </p>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <div className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              <span>{new Date(project.createdAt).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center gap-1">
              <Edit className="w-4 h-4" />
              <span>{annotationCount} 标注</span>
            </div>
          </div>

          <Link
            to={`/project/${project.id}`}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            开始标注
          </Link>
        </div>
      </div>
    </div>
  );
};

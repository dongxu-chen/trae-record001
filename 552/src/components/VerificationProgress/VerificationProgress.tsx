import { FileCheck, ShieldCheck, Clock, FileCheck2, Scale, FileText, CheckCircle2 } from 'lucide-react';
import { useVerificationStore } from '@/store/verificationStore';
import { cn } from '@/lib/utils';

interface Step {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
}

const steps: Step[] = [
  { id: 'format', name: '格式检测', icon: FileCheck },
  { id: 'certificate', name: '证书链验证', icon: ShieldCheck },
  { id: 'timestamp', name: '时间戳验证', icon: Clock },
  { id: 'integrity', name: '完整性验证', icon: FileCheck2 },
  { id: 'compliance', name: '合规性检查', icon: Scale },
  { id: 'report', name: '生成报告', icon: FileText },
];

interface VerificationProgressProps {
  className?: string;
}

export default function VerificationProgress({ className }: VerificationProgressProps) {
  const { progress, currentStep, isVerifying } = useVerificationStore();

  const getStepStatus = (stepId: string, index: number) => {
    const currentIndex = steps.findIndex(s => s.id === currentStep);
    if (progress >= 100) return 'completed';
    if (currentIndex === -1) return 'pending';
    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'current';
    return 'pending';
  };

  if (!isVerifying && progress === 0) {
    return null;
  }

  return (
    <div className={cn('w-full', className)}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          验证进度
        </h3>
        <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
          {Math.round(progress)}%
        </span>
      </div>

      <div className="mb-6 h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="relative">
        <div className="absolute left-5 top-0 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
        
        <div className="space-y-4">
          {steps.map((step, index) => {
            const status = getStepStatus(step.id, index);
            const StepIcon = step.icon;
            const isCompleted = status === 'completed';
            const isCurrent = status === 'current';
            
            return (
              <div key={step.id} className="relative flex items-start gap-4 pl-2">
                <div
                  className={cn(
                    'relative z-10 flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-300',
                    isCompleted && 'border-green-500 bg-green-500',
                    isCurrent && 'border-blue-500 bg-blue-500 animate-pulse',
                    status === 'pending' && 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-800'
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-5 w-5 text-white" />
                  ) : (
                    <StepIcon
                      className={cn(
                        'h-5 w-5',
                        isCurrent && 'text-white',
                        status === 'pending' && 'text-gray-400 dark:text-gray-500'
                      )}
                    />
                  )}
                </div>
                
                <div className="flex-1 pt-1">
                  <p
                    className={cn(
                      'font-medium transition-colors duration-300',
                      isCompleted && 'text-green-600 dark:text-green-400',
                      isCurrent && 'text-blue-600 dark:text-blue-400',
                      status === 'pending' && 'text-gray-400 dark:text-gray-500'
                    )}
                  >
                    {step.name}
                  </p>
                  <p
                    className={cn(
                      'text-sm transition-colors duration-300',
                      isCompleted && 'text-green-500 dark:text-green-400/70',
                      isCurrent && 'text-blue-500 dark:text-blue-400/70',
                      status === 'pending' && 'text-gray-400 dark:text-gray-500'
                    )}
                  >
                    {isCompleted && '已完成'}
                    {isCurrent && '正在验证...'}
                    {status === 'pending' && '等待中'}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

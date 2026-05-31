import { Shield, ShieldCheck, ShieldAlert, Globe, Scale, Clock, RotateCcw } from 'lucide-react';
import { useVerificationStore } from '@/store/verificationStore';
import { cn } from '@/lib/utils';

interface VerifyOptionsProps {
  className?: string;
}

export default function VerifyOptions({ className }: VerifyOptionsProps) {
  const { verifyOptions, setVerifyOptions } = useVerificationStore();

  const verifyLevels = [
    {
      value: 'basic',
      label: '基础验证',
      description: '快速验证签名格式和基本完整性',
      icon: Shield,
      color: 'text-gray-600 dark:text-gray-400',
      bgColor: 'bg-gray-100 dark:bg-gray-800',
      borderColor: 'border-gray-300 dark:border-gray-600',
    },
    {
      value: 'standard',
      label: '标准验证',
      description: '完整验证证书链和签名有效性',
      icon: ShieldCheck,
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
      borderColor: 'border-blue-300 dark:border-blue-600',
    },
    {
      value: 'strict',
      label: '严格验证',
      description: '包含吊销检查和深度合规性验证',
      icon: ShieldAlert,
      color: 'text-green-600 dark:text-green-400',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
      borderColor: 'border-green-300 dark:border-green-600',
    },
  ] as const;

  const complianceStandards = [
    {
      value: 'cn-es',
      label: '中国电子签名法',
      description: '符合《中华人民共和国电子签名法》',
      icon: Globe,
    },
    {
      value: 'eu-eidas',
      label: '欧盟 eIDAS',
      description: '符合欧盟电子身份认证与签名法规',
      icon: Scale,
    },
    {
      value: 'us-esign',
      label: '美国 ESIGN',
      description: '符合美国全球和国家商务电子签名法案',
      icon: Scale,
    },
  ] as const;

  const toggleOptions = [
    {
      key: 'checkRevocation',
      label: '检查证书吊销',
      description: '验证签名证书是否已被吊销',
      icon: RotateCcw,
    },
    {
      key: 'checkTimestamp',
      label: '检查时间戳',
      description: '验证可信时间戳的有效性',
      icon: Clock,
    },
  ] as const;

  return (
    <div className={cn('w-full space-y-6', className)}>
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          验证级别
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {verifyLevels.map((level) => {
            const LevelIcon = level.icon;
            const isSelected = verifyOptions.verifyLevel === level.value;
            return (
              <label
                key={level.value}
                className={cn(
                  'relative flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all duration-200',
                  isSelected
                    ? cn(level.borderColor, level.bgColor)
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
                )}
              >
                <input
                  type="radio"
                  name="verifyLevel"
                  value={level.value}
                  checked={isSelected}
                  onChange={() => setVerifyOptions({ verifyLevel: level.value })}
                  className="sr-only"
                />
                <div className="flex items-center gap-3 mb-2">
                  <div className={cn('p-2 rounded-lg', level.bgColor)}>
                    <LevelIcon className={cn('w-5 h-5', level.color)} />
                  </div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {level.label}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 pl-14">
                  {level.description}
                </p>
              </label>
            );
          })}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          合规标准
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {complianceStandards.map((standard) => {
            const StandardIcon = standard.icon;
            const isSelected = verifyOptions.complianceStandard === standard.value;
            return (
              <label
                key={standard.value}
                className={cn(
                  'relative flex flex-col p-4 rounded-xl border-2 cursor-pointer transition-all duration-200',
                  isSelected
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-600'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
                )}
              >
                <input
                  type="radio"
                  name="complianceStandard"
                  value={standard.value}
                  checked={isSelected}
                  onChange={() => setVerifyOptions({ complianceStandard: standard.value })}
                  className="sr-only"
                />
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700">
                    <StandardIcon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                  </div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {standard.label}
                  </span>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 pl-14">
                  {standard.description}
                </p>
              </label>
            );
          })}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          高级选项
        </h3>
        <div className="space-y-3">
          {toggleOptions.map((option) => {
            const OptionIcon = option.icon;
            const isChecked = verifyOptions[option.key];
            return (
              <div
                key={option.key}
                className="flex items-center justify-between p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700">
                    <OptionIcon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      {option.label}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {option.description}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setVerifyOptions({ [option.key]: !isChecked })}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800',
                    isChecked ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                  )}
                >
                  <span
                    className={cn(
                      'inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-200',
                      isChecked ? 'translate-x-6' : 'translate-x-1'
                    )}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

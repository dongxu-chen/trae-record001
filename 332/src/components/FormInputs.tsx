import { motion } from 'framer-motion';
import type { QRFormData, QRCodeType } from '@/types';

interface FormInputsProps {
  type: QRCodeType;
  formData: QRFormData;
  onChange: (data: Partial<QRFormData>) => void;
}

function InputField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-2">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
      />
    </div>
  );
}

function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-2">
        {label}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none"
      />
    </div>
  );
}

export default function FormInputs({ type, formData, onChange }: FormInputsProps) {
  const variants = {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 20 },
  };

  return (
    <motion.div
      key={type}
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.2 }}
      className="space-y-4"
    >
      {type === 'text' && (
        <TextAreaField
          label="文本内容"
          value={formData.text}
          onChange={(text) => onChange({ text })}
          placeholder="输入要编码的文本内容..."
          rows={5}
        />
      )}

      {type === 'url' && (
        <InputField
          label="网址链接"
          value={formData.url}
          onChange={(url) => onChange({ url })}
          placeholder="https://example.com"
          type="url"
          required
        />
      )}

      {type === 'vcard' && (
        <div className="grid grid-cols-2 gap-4">
          <InputField
            label="名字"
            value={formData.vcard.firstName}
            onChange={(firstName) =>
              onChange({ vcard: { ...formData.vcard, firstName } })
            }
            placeholder="张三"
          />
          <InputField
            label="姓氏"
            value={formData.vcard.lastName}
            onChange={(lastName) =>
              onChange({ vcard: { ...formData.vcard, lastName } })
            }
            placeholder="李"
          />
          <InputField
            label="公司"
            value={formData.vcard.organization}
            onChange={(organization) =>
              onChange({ vcard: { ...formData.vcard, organization } })
            }
            placeholder="科技有限公司"
          />
          <InputField
            label="职位"
            value={formData.vcard.title}
            onChange={(title) =>
              onChange({ vcard: { ...formData.vcard, title } })
            }
            placeholder="产品经理"
          />
          <InputField
            label="电话"
            value={formData.vcard.phone}
            onChange={(phone) =>
              onChange({ vcard: { ...formData.vcard, phone } })
            }
            placeholder="+86 138 0000 0000"
            type="tel"
          />
          <InputField
            label="邮箱"
            value={formData.vcard.email}
            onChange={(email) =>
              onChange({ vcard: { ...formData.vcard, email } })
            }
            placeholder="name@example.com"
            type="email"
          />
          <div className="col-span-2">
            <InputField
              label="网站"
              value={formData.vcard.website}
              onChange={(website) =>
                onChange({ vcard: { ...formData.vcard, website } })
              }
              placeholder="https://example.com"
              type="url"
            />
          </div>
          <div className="col-span-2">
            <InputField
              label="地址"
              value={formData.vcard.address}
              onChange={(address) =>
                onChange({ vcard: { ...formData.vcard, address } })
              }
              placeholder="北京市朝阳区..."
            />
          </div>
        </div>
      )}

      {type === 'wifi' && (
        <div className="space-y-4">
          <InputField
            label="网络名称 (SSID)"
            value={formData.wifi.ssid}
            onChange={(ssid) => onChange({ wifi: { ...formData.wifi, ssid } })}
            placeholder="MyWiFi"
            required
          />
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              加密方式
            </label>
            <select
              value={formData.wifi.encryption}
              onChange={(e) =>
                onChange({
                  wifi: {
                    ...formData.wifi,
                    encryption: e.target.value as 'WPA' | 'WEP' | 'nopass',
                  },
                })
              }
              className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-700 text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
            >
              <option value="WPA">WPA/WPA2/WPA3</option>
              <option value="WEP">WEP</option>
              <option value="nopass">无密码</option>
            </select>
          </div>
          {formData.wifi.encryption !== 'nopass' && (
            <InputField
              label="密码"
              value={formData.wifi.password}
              onChange={(password) =>
                onChange({ wifi: { ...formData.wifi, password } })
              }
              placeholder="WiFi密码"
              type="password"
            />
          )}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="hidden-wifi"
              checked={formData.wifi.hidden}
              onChange={(e) =>
                onChange({ wifi: { ...formData.wifi, hidden: e.target.checked } })
              }
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
            />
            <label htmlFor="hidden-wifi" className="text-sm text-slate-300">
              隐藏网络
            </label>
          </div>
        </div>
      )}

      {type === 'email' && (
        <div className="space-y-4">
          <InputField
            label="收件人"
            value={formData.email.to}
            onChange={(to) => onChange({ email: { ...formData.email, to } })}
            placeholder="recipient@example.com"
            type="email"
            required
          />
          <InputField
            label="主题"
            value={formData.email.subject}
            onChange={(subject) =>
              onChange({ email: { ...formData.email, subject } })
            }
            placeholder="邮件主题"
          />
          <TextAreaField
            label="邮件正文"
            value={formData.email.body}
            onChange={(body) => onChange({ email: { ...formData.email, body } })}
            placeholder="输入邮件内容..."
            rows={5}
          />
        </div>
      )}
    </motion.div>
  );
}

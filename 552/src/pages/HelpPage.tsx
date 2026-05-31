import { useState } from 'react';
import {
  HelpCircle,
  FileQuestion,
  BookOpen,
  Scale,
  FileText,
  Clock,
  ShieldCheck,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface FAQItem {
  id: string;
  question: string;
  answer: string;
}

const faqData: FAQItem[] = [
  {
    id: '1',
    question: '什么是电子签名？',
    answer: '电子签名是指数据电文中以电子形式所含、所附用于识别签名人身份并表明签名人认可其中内容的数据。简单来说，电子签名就是通过密码技术对电子文档的电子形式的签名，并非是书面签名的数字图像化，它类似于手写签名或印章，也可以说它就是电子印章。'
  },
  {
    id: '2',
    question: '电子签名是否具有法律效力？',
    answer: '是的，在中国，根据《中华人民共和国电子签名法》，可靠的电子签名与手写签名或者盖章具有同等的法律效力。在欧盟，eIDAS法规规定合格电子签名具有手写签名同等的法律效力。在美国，ESIGN Act确认了电子签名在跨州贸易中的合法性。'
  },
  {
    id: '3',
    question: '支持哪些文件格式的验证？',
    answer: '本工具支持多种电子签名格式的验证，包括：PDF文档的PAdES签名、XML文档的XAdES签名、CMS/PKCS#7格式的CAdES签名。支持的文件扩展名包括：.pdf、.xml、.p7s、.p7m、.csr、.crt等。'
  },
  {
    id: '4',
    question: '验证结果中的"警告"状态是什么意思？',
    answer: '警告状态表示签名在数学上是有效的，但存在一些需要注意的问题。例如：证书即将过期、缺少可信时间戳、证书颁发机构不在信任列表中、签名后文档有微小修改但不影响核心内容等。建议仔细查看警告详情，根据具体情况判断是否接受该签名。'
  },
  {
    id: '5',
    question: '为什么需要时间戳？',
    answer: '可信时间戳由权威时间源签发，用于证明电子签名的确切时间。它可以防止签名者事后否认签名时间，也可以证明在证书过期或吊销之前签名已经存在。没有时间戳的签名，在证书过期后其有效性可能会受到质疑。'
  },
  {
    id: '6',
    question: '如何判断证书是否可信？',
    answer: '证书的可信性主要通过以下几点判断：1) 证书是否由受信任的证书颁发机构(CA)签发；2) 证书是否在有效期内；3) 证书是否已被吊销；4) 证书用途是否包含数字签名；5) 证书链是否完整且所有中间证书都可信。'
  }
];

const signatureFormats = [
  {
    icon: <FileText className="w-8 h-8" />,
    name: 'PAdES',
    fullName: 'PDF Advanced Electronic Signature',
    description: 'PAdES是专门为PDF文档设计的电子签名标准，由ETSI发布。它直接将签名嵌入到PDF文件中，与PDF格式深度集成。',
    features: [
      '支持多签名和并行签名',
      '签名可视化，可在PDF页面上显示签名外观',
      '支持文档安全存储(LTV)，确保证书过期后仍可验证',
      '支持时间戳和证书吊销信息嵌入',
      '广泛应用于合同、报表、法律文件等场景'
    ],
    color: 'blue'
  },
  {
    icon: <BookOpen className="w-8 h-8" />,
    name: 'XAdES',
    fullName: 'XML Advanced Electronic Signature',
    description: 'XAdES是基于XML的电子签名标准，由ETSI发布。它使用XML签名语法，支持对XML文档或任意数据进行签名。',
    features: [
      '支持 enveloped、enveloping、detached 三种签名形式',
      '可对XML文档的特定部分进行签名',
      '支持丰富的签名属性和证书信息',
      '广泛应用于电子政务、电子商务、数据交换等场景',
      '支持通过XSLT转换进行签名验证'
    ],
    color: 'green'
  },
  {
    icon: <ShieldCheck className="w-8 h-8" />,
    name: 'CAdES',
    fullName: 'CMS Advanced Electronic Signature',
    description: 'CAdES是基于CMS(PKCS#7)的电子签名标准，由ETSI发布。它是二进制格式，适合对任意类型的文件进行签名。',
    features: [
      '基于ASN.1编码的二进制格式，文件体积小',
      '支持分离式(detached)和封装式签名',
      '支持添加计数器签名、时间戳等属性',
      '常用于邮件安全(S/MIME)、代码签名、固件签名等',
      '支持多种哈希算法和加密算法'
    ],
    color: 'purple'
  }
];

const regulations = [
  {
    icon: <Scale className="w-8 h-8" />,
    name: '中国《电子签名法》',
    date: '2005年4月1日施行',
    description: '《中华人民共和国电子签名法》是中国第一部规范电子签名的法律，确立了电子签名的法律效力，规范了电子签名行为。',
    keyPoints: [
      '确立可靠电子签名与手写签名、盖章具有同等法律效力',
      '定义了可靠电子签名的四个条件：专有控制、签名后改动可发现、内容改动可发现、签名人真实意愿',
      '规范了电子认证服务提供者的资质和行为',
      '明确了电子签名各方的法律责任',
      '适用范围排除了涉及婚姻、收养、继承等人身关系的文书'
    ],
    color: 'red'
  },
  {
    icon: <Scale className="w-8 h-8" />,
    name: '欧盟 eIDAS',
    date: '2016年7月1日生效',
    description: 'eIDAS (Electronic Identification, Authentication and Trust Services) 是欧盟关于电子识别和信任服务的法规，在所有欧盟成员国直接适用。',
    keyPoints: [
      '定义了三种电子签名：普通电子签名、高级电子签名、合格电子签名',
      '合格电子签名(QES)具有与手写签名同等的法律效力',
      '建立了欧盟范围内的信任服务提供商互认机制',
      '适用于电子身份证明、电子印章、时间戳、注册服务等',
      '促进欧盟内部市场的电子化服务发展'
    ],
    color: 'blue'
  },
  {
    icon: <Scale className="w-8 h-8" />,
    name: '美国 ESIGN Act',
    date: '2000年10月1日生效',
    description: '《全球和国家商务中的电子签名法》(Electronic Signatures in Global and National Commerce Act) 确认了电子签名和电子记录在跨州贸易中的法律效力。',
    keyPoints: [
      '电子签名、电子合同、电子记录的法律效力得到确认',
      '签名不能仅因采用电子形式而被否定法律效力',
      '消费者有权选择使用电子方式或纸质方式',
      '适用于跨州贸易和商业活动',
      '某些特殊领域如遗嘱、信托、家庭法事务等除外'
    ],
    color: 'indigo'
  }
];

const verificationSteps = [
  {
    step: 1,
    icon: <FileText className="w-6 h-6" />,
    title: '文件解析',
    description: '系统首先解析上传的文件，识别文件类型和其中包含的电子签名。根据文件扩展名和内容判断签名格式（PAdES/XAdES/CAdES）。'
  },
  {
    step: 2,
    icon: <ShieldCheck className="w-6 h-6" />,
    title: '签名有效性验证',
    description: '使用公钥密码学验证签名的数学有效性。检查签名值是否与文档内容的哈希值匹配，确认签名后文档未被篡改。'
  },
  {
    step: 3,
    icon: <BookOpen className="w-6 h-6" />,
    title: '证书链验证',
    description: '验证签名证书的颁发链，从签名证书追溯到受信任的根证书。检查每一级证书的有效性、有效期和用途。'
  },
  {
    step: 4,
    icon: <Clock className="w-6 h-6" />,
    title: '证书状态检查',
    description: '通过CRL或OCSP检查证书是否已被吊销。如果有可信时间戳，验证时间戳的有效性，并确认签名时证书仍然有效。'
  },
  {
    step: 5,
    icon: <HelpCircle className="w-6 h-6" />,
    title: '合规性评估',
    description: '根据不同司法管辖区的法律法规要求，评估签名是否满足合规要求。包括中国《电子签名法》、欧盟eIDAS、美国ESIGN Act等。'
  },
  {
    step: 6,
    icon: <FileQuestion className="w-6 h-6" />,
    title: '生成验证报告',
    description: '汇总所有验证结果，生成详细的验证报告，包括每个签名的状态、证书信息、时间戳信息、合规性评估结论等。'
  }
];

const getColorClass = (color: string) => {
  switch (color) {
    case 'blue':
      return 'bg-blue-100 text-blue-600';
    case 'green':
      return 'bg-green-100 text-green-600';
    case 'purple':
      return 'bg-purple-100 text-purple-600';
    case 'red':
      return 'bg-red-100 text-red-600';
    case 'indigo':
      return 'bg-indigo-100 text-indigo-600';
    default:
      return 'bg-gray-100 text-gray-600';
  }
};

export default function HelpPage() {
  const [openFaq, setOpenFaq] = useState<string | null>('1');
  const [activeTab, setActiveTab] = useState<'formats' | 'regulations' | 'process'>('formats');

  const toggleFaq = (id: string) => {
    setOpenFaq(openFaq === id ? null : id);
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-100 rounded-full mb-6">
            <HelpCircle className="w-10 h-10 text-blue-600" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">帮助中心</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            了解电子签名的相关知识，掌握验证工具的使用方法
          </p>
        </div>

        <div className="mb-16">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
            <HelpCircle className="w-7 h-7 text-blue-600" />
            常见问题
          </h2>
          <div className="space-y-3">
            {faqData.map((item) => (
              <div
                key={item.id}
                className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm"
              >
                <button
                  onClick={() => toggleFaq(item.id)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                >
                  <span className="font-semibold text-gray-900 pr-4">{item.question}</span>
                  {openFaq === item.id ? (
                    <ChevronDown className="w-5 h-5 text-gray-500 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-500 flex-shrink-0" />
                  )}
                </button>
                {openFaq === item.id && (
                  <div className="px-6 pb-5">
                    <p className="text-gray-600 leading-relaxed">{item.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="mb-16">
          <div className="flex flex-wrap gap-2 mb-8 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('formats')}
              className={cn(
                "px-6 py-3 font-medium transition-colors border-b-2 -mb-px",
                activeTab === 'formats'
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-500 border-transparent hover:text-gray-700"
              )}
            >
              签名格式说明
            </button>
            <button
              onClick={() => setActiveTab('regulations')}
              className={cn(
                "px-6 py-3 font-medium transition-colors border-b-2 -mb-px",
                activeTab === 'regulations'
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-500 border-transparent hover:text-gray-700"
              )}
            >
              法规依据说明
            </button>
            <button
              onClick={() => setActiveTab('process')}
              className={cn(
                "px-6 py-3 font-medium transition-colors border-b-2 -mb-px",
                activeTab === 'process'
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-500 border-transparent hover:text-gray-700"
              )}
            >
              验证流程说明
            </button>
          </div>

          {activeTab === 'formats' && (
            <div className="space-y-8">
              {signatureFormats.map((format, index) => (
                <div
                  key={index}
                  className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm"
                >
                  <div className="flex items-start gap-6">
                    <div className={cn(
                      "w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0",
                      getColorClass(format.color)
                    )}>
                      {format.icon}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-2xl font-bold text-gray-900 mb-1">
                        {format.name}
                      </h3>
                      <p className="text-sm text-gray-500 mb-4">{format.fullName}</p>
                      <p className="text-gray-600 mb-6">{format.description}</p>
                      <h4 className="font-semibold text-gray-900 mb-3">主要特点：</h4>
                      <ul className="space-y-2">
                        {format.features.map((feature, idx) => (
                          <li key={idx} className="flex items-start gap-3 text-gray-600">
                            <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'regulations' && (
            <div className="space-y-8">
              {regulations.map((regulation, index) => (
                <div
                  key={index}
                  className="bg-white rounded-xl border border-gray-200 p-8 shadow-sm"
                >
                  <div className="flex items-start gap-6">
                    <div className={cn(
                      "w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0",
                      getColorClass(regulation.color)
                    )}>
                      {regulation.icon}
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-3 mb-4">
                        <h3 className="text-2xl font-bold text-gray-900">
                          {regulation.name}
                        </h3>
                        <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                          {regulation.date}
                        </span>
                      </div>
                      <p className="text-gray-600 mb-6">{regulation.description}</p>
                      <h4 className="font-semibold text-gray-900 mb-3">核心要点：</h4>
                      <ul className="space-y-2">
                        {regulation.keyPoints.map((point, idx) => (
                          <li key={idx} className="flex items-start gap-3 text-gray-600">
                            <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                            {point}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'process' && (
            <div className="relative">
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-200 hidden md:block" />
              <div className="space-y-8">
                {verificationSteps.map((step, index) => (
                  <div
                    key={index}
                    className="relative flex gap-6"
                  >
                    <div className={cn(
                      "w-16 h-16 rounded-xl flex items-center justify-center flex-shrink-0 z-10",
                      "bg-blue-100 text-blue-600"
                    )}>
                      {step.icon}
                    </div>
                    <div className="flex-1 bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                      <div className="flex items-center gap-3 mb-3">
                        <span className="inline-flex items-center justify-center w-8 h-8 bg-blue-600 text-white text-sm font-bold rounded-full">
                          {step.step}
                        </span>
                        <h3 className="text-xl font-bold text-gray-900">{step.title}</h3>
                      </div>
                      <p className="text-gray-600 ml-11">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

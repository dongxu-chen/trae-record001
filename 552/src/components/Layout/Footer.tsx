import { ShieldCheck, Github, Mail } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <div>
                <span className="text-xl font-bold text-gray-900">ESVerify</span>
                <p className="text-xs text-gray-500 -mt-1">电子签名验证</p>
              </div>
            </div>
            <p className="text-gray-600 text-sm max-w-md">
              专业的电子签名法律效力验证工具，支持PAdES、XAdES、CAdES等多种签名格式，
              为您的电子合同和文档提供权威的法律效力验证。
            </p>
            <div className="flex gap-4 mt-4">
              <a href="#" className="text-gray-400 hover:text-blue-600 transition-colors">
                <Github className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-blue-600 transition-colors">
                <Mail className="w-5 h-5" />
              </a>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-4">支持格式</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="hover:text-blue-600 cursor-pointer">PAdES (PDF签名)</li>
              <li className="hover:text-blue-600 cursor-pointer">XAdES (XML签名)</li>
              <li className="hover:text-blue-600 cursor-pointer">CAdES (CMS/PKCS#7)</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-4">合规标准</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="hover:text-blue-600 cursor-pointer">中国《电子签名法》</li>
              <li className="hover:text-blue-600 cursor-pointer">欧盟 eIDAS</li>
              <li className="hover:text-blue-600 cursor-pointer">美国 ESIGN Act</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-200 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-sm text-gray-500">
            © 2026 ESVerify. 本工具仅提供技术验证参考，不构成法律意见。
          </p>
          <div className="flex gap-6 text-sm text-gray-500">
            <a href="#" className="hover:text-blue-600">隐私政策</a>
            <a href="#" className="hover:text-blue-600">使用条款</a>
            <a href="#" className="hover:text-blue-600">免责声明</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

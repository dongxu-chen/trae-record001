import { FileText, Upload, X, Layers } from 'lucide-react';

const MultiDocInput = ({ documents, setDocuments, onClear }) => {
  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    
    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target.result;
        if (content.trim().length > 50) {
          setDocuments(prev => [
            ...prev,
            {
              id: Date.now() + Math.random(),
              name: file.name,
              content: content
            }
          ]);
        }
      };
      reader.readAsText(file);
    });
  };

  const removeDocument = (id) => {
    setDocuments(prev => prev.filter(d => d.id !== id));
  };

  return (
    <div className="bg-white rounded-2xl p-6 card-shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <Layers className="w-6 h-6 text-purple-600" />
          多文档输入
        </h3>
        {documents.length > 0 && (
          <button
            onClick={onClear}
            className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            清空全部
          </button>
        )}
      </div>

      <div className="mb-4">
        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-purple-500 hover:bg-purple-50 transition-colors">
          <div className="flex flex-col items-center justify-center">
            <Upload className="w-8 h-8 text-gray-400 mb-2" />
            <p className="text-sm text-gray-500">
              点击或拖拽上传多个 TXT 文件
            </p>
            <p className="text-xs text-gray-400 mt-1">
              至少上传 2 个文件
            </p>
          </div>
          <input
            type="file"
            accept=".txt"
            multiple
            onChange={handleFileUpload}
            className="hidden"
          />
        </label>
      </div>

      {documents.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-gray-600 mb-2">
            已上传 <span className="font-semibold text-purple-600">{documents.length}</span> 个文档
          </p>
          <div className="max-h-48 overflow-y-auto space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-purple-600" />
                  <div>
                    <p className="text-sm font-medium text-gray-700">{doc.name}</p>
                    <p className="text-xs text-gray-400">{doc.content.length} 字符</p>
                  </div>
                </div>
                <button
                  onClick={() => removeDocument(doc.id)}
                  className="p-1 hover:bg-red-100 rounded transition-colors"
                >
                  <X className="w-4 h-4 text-gray-400 hover:text-red-500" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MultiDocInput;

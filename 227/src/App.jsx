import { useState } from 'react';
import { usePDF } from './hooks/usePDF';
import { Toolbar } from './components/Toolbar';
import { Sidebar } from './components/Sidebar';
import { PDFPage } from './components/PDFPage';
import { FormFillPanel } from './components/FormFillPanel';
import { SignaturePanel } from './components/SignaturePanel';
import { MergeSplitPanel } from './components/MergeSplitPanel';

function App() {
  const [tool, setTool] = useState('select');
  const [color, setColor] = useState('#e74c3c');
  const [strokeWidth, setStrokeWidth] = useState(2);
  const [showFormFill, setShowFormFill] = useState(false);
  const [showSignature, setShowSignature] = useState(false);
  const [showMergeSplit, setShowMergeSplit] = useState(false);

  const {
    pdfDoc,
    numPages,
    currentPage,
    scale,
    baseScale,
    pageAnnotations,
    pageThumbnails,
    searchResults,
    currentSearchIndex,
    loadPDF,
    searchInPDF,
    nextSearchResult,
    prevSearchResult,
    saveAnnotations,
    addPage,
    deletePage,
    movePage,
    goToPage,
    nextPage,
    prevPage,
    zoomIn,
    zoomOut,
    transformAnnotationsForScale,
    markPageLoaded
  } = usePDF();

  return (
    <div className="app-container">
      <header className="header">
        <h1>📄 PDF在线编辑器</h1>
        <div className="header-actions">
          {pdfDoc && (
            <>
              <button 
                className="btn btn-primary" 
                style={{ background: '#9b59b6' }}
                onClick={() => setShowFormFill(true)}
              >
                📝 表单填充
              </button>
              <button 
                className="btn btn-primary" 
                style={{ background: '#27ae60' }}
                onClick={() => setShowSignature(true)}
              >
                🔐 数字签名
              </button>
              <button 
                className="btn btn-primary" 
                style={{ background: '#e67e22' }}
                onClick={() => setShowMergeSplit(true)}
              >
                📦 合并/拆分
              </button>
              <button className="btn btn-success">
                💾 保存
              </button>
            </>
          )}
        </div>
      </header>

      <div className="main-content">
        <Sidebar
          pageThumbnails={pageThumbnails}
          currentPage={currentPage}
          onPageSelect={goToPage}
          onUpload={loadPDF}
          onSearch={searchInPDF}
          searchResults={searchResults}
          currentSearchIndex={currentSearchIndex}
          onNextSearch={nextSearchResult}
          onPrevSearch={prevSearchResult}
          onDeletePage={deletePage}
          onMovePage={movePage}
          hasPDF={!!pdfDoc}
        />

        <div className="editor-container">
          {pdfDoc && (
            <Toolbar
              tool={tool}
              setTool={setTool}
              color={color}
              setColor={setColor}
              strokeWidth={strokeWidth}
              setStrokeWidth={setStrokeWidth}
              currentPage={currentPage}
              numPages={numPages}
              prevPage={prevPage}
              nextPage={nextPage}
              zoom={scale}
              zoomIn={zoomIn}
              zoomOut={zoomOut}
              addPage={addPage}
            />
          )}

          <div className="pdf-canvas-container">
            {pdfDoc ? (
              <PDFPage
                key={currentPage}
                pdfDoc={pdfDoc}
                pageNum={currentPage}
                scale={scale}
                baseScale={baseScale}
                tool={tool}
                color={color}
                strokeWidth={strokeWidth}
                onSaveAnnotations={saveAnnotations}
                savedAnnotations={pageAnnotations[currentPage] || []}
                searchResults={searchResults}
                currentSearchIndex={currentSearchIndex}
                transformAnnotationsForScale={transformAnnotationsForScale}
                onPageLoaded={markPageLoaded}
              />
            ) : (
              <div className="empty-state">
                <div style={{ fontSize: '64px', marginBottom: '16px' }}>📂</div>
                <p>请上传PDF文件开始编辑</p>
                <p style={{ fontSize: '14px', marginTop: '8px', color: '#bbb' }}>
                  支持PDF上传、文本标注、图形绘制、页面管理和内容搜索
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {showFormFill && (
        <FormFillPanel
          pdfDoc={pdfDoc}
          onClose={() => setShowFormFill(false)}
        />
      )}

      {showSignature && (
        <SignaturePanel
          pdfDoc={pdfDoc}
          onClose={() => setShowSignature(false)}
        />
      )}

      {showMergeSplit && (
        <MergeSplitPanel
          pdfDoc={pdfDoc}
          numPages={numPages}
          onClose={() => setShowMergeSplit(false)}
        />
      )}
    </div>
  );
}

export default App;

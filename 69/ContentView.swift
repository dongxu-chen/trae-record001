import SwiftUI
import UniformTypeIdentifiers
import PDFKit

struct ContentView: View {
    @State private var pdfFiles: [PDFFile] = []
    @State private var selectedFile: PDFFile?
    @State private var showAnnotationView = false
    @State private var showExportPanel = false
    @State private var dragOverIndex: Int?
    @State private var selectedDocument: PDFDocument?
    @State private var selectedPageIndex: Int = 0
    @State private var showOCRPanel = false
    @State private var isPerformingOCR = false
    @State private var ocrProgress: Double = 0
    @State private var ocrResults: [OCRWorker.OCRResult] = []
    @State private var ocrError: String?
    @State private var showOCRResults = false
    @State private var ocrRecognitionLevel: OCRWorker.RecognitionLevel = .accurate
    @State private var ocrLanguages: [String] = ["zh-Hans", "en"]
    
    var body: some View {
        NavigationSplitView {
            VStack(spacing: 0) {
                headerView
                
                if pdfFiles.isEmpty {
                    emptyStateView
                } else {
                    fileListView
                }
                
                footerView
            }
            .frame(minWidth: 300)
            .background(Color(nsColor: .controlBackgroundColor))
        } detail: {
            detailView
        }
        .navigationTitle("PDF 合并与标注工具")
        .onDrop(of: [UTType.fileURL], delegate: DropDelegate { url in
            self.handleDrop(url: url)
        })
        .onChange(of: selectedFile) { newFile in
            selectedPageIndex = 0
            if let file = newFile {
                selectedDocument = PDFDocument(url: file.url)
            } else {
                selectedDocument = nil
            }
        }
        .sheet(isPresented: $showAnnotationView) {
            if let selectedFile = selectedFile {
                AnnotationView(pdfFile: selectedFile)
            }
        }
        .sheet(isPresented: $showExportPanel) {
            ExportPanel(pdfFiles: pdfFiles)
        }
        .sheet(isPresented: $showOCRPanel) {
            if let selectedFile = selectedFile {
                ocrPanel(for: selectedFile)
            }
        }
        .sheet(isPresented: $showOCRResults) {
            ocrResultsView
        }
    }
    
    private var headerView: some View {
        VStack(spacing: 12) {
            Text("PDF 文件列表")
                .font(.headline)
                .fontWeight(.semibold)
            
            Button(action: selectFiles) {
                HStack(spacing: 8) {
                    Image(systemName: "plus.circle.fill")
                    Text("添加 PDF 文件")
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(Color.accentColor)
                .foregroundColor(.white)
                .cornerRadius(8)
            }
            .buttonStyle(.plain)
        }
        .padding()
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "doc.on.doc")
                .font(.system(size: 60))
                .foregroundColor(.secondary)
            Text("拖拽 PDF 文件到这里")
                .font(.title2)
                .foregroundColor(.secondary)
            Text("或点击上方按钮添加")
                .font(.subheadline)
                .foregroundColor(.tertiary)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onDrop(of: [UTType.fileURL], isTargeted: .constant(true)) { providers in
            providers.first?.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                if let data = item as? Data, let url = URL(dataRepresentation: data, relativeTo: nil) {
                    DispatchQueue.main.async {
                        self.handleDrop(url: url)
                    }
                }
            }
            return true
        }
    }
    
    private var fileListView: some View {
        List {
            ForEach(Array(pdfFiles.enumerated()), id: \.element.id) { index, file in
                FileRow(file: file, index: index, isSelected: selectedFile == file)
                    .onDrag {
                        NSItemProvider(object: file.id.uuidString as NSString)
                    }
                    .onDrop(of: [UTType.text], delegate: ReorderDelegate(
                        destinationFileId: file.id,
                        files: $pdfFiles,
                        dragOverIndex: $dragOverIndex
                    ))
                    .onTapGesture {
                        selectedFile = file
                    }
                    .listRowBackground(
                        selectedFile == file
                        ? Color.accentColor.opacity(0.15)
                        : Color.clear
                    )
            }
            .onDelete { indexSet in
                pdfFiles.remove(atOffsets: indexSet)
                if selectedFile != nil && !pdfFiles.contains(where: { $0 == selectedFile }) {
                    selectedFile = nil
                }
            }
        }
        .listStyle(.plain)
    }
    
    private var footerView: some View {
        VStack(spacing: 12) {
            HStack(spacing: 8) {
                Button(action: {
                    showAnnotationView = true
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: "highlighter")
                        Text("标注")
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(Color.orange.opacity(0.15))
                    .foregroundColor(.orange)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)
                .disabled(selectedFile == nil)
                
                Button(action: moveUp) {
                    Image(systemName: "chevron.up")
                        .frame(width: 32, height: 32)
                        .background(Color.secondary.opacity(0.1))
                        .cornerRadius(6)
                }
                .buttonStyle(.plain)
                .disabled(selectedFile == nil || isFirstSelected)
                
                Button(action: moveDown) {
                    Image(systemName: "chevron.down")
                        .frame(width: 32, height: 32)
                        .background(Color.secondary.opacity(0.1))
                        .cornerRadius(6)
                }
                .buttonStyle(.plain)
                .disabled(selectedFile == nil || isLastSelected)
            }
            
            Button(action: {
                showExportPanel = true
            }) {
                HStack(spacing: 8) {
                    Image(systemName: "square.and.arrow.up.fill")
                    Text("合并并导出")
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(pdfFiles.isEmpty ? Color.gray : Color.accentColor)
                .foregroundColor(.white)
                .cornerRadius(8)
            }
            .buttonStyle(.plain)
            .disabled(pdfFiles.isEmpty)
        }
        .padding()
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var detailView: some View {
        Group {
            if let file = selectedFile {
                VStack(spacing: 0) {
                    HStack {
                        Text(file.name)
                            .font(.headline)
                        Spacer()
                        
                        HStack(spacing: 8) {
                            Button(action: {
                                showOCRPanel = true
                            }) {
                                HStack(spacing: 4) {
                                    Image(systemName: "text.viewfinder")
                                    Text("OCR 识别")
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(Color.purple.opacity(0.15))
                                .foregroundColor(.purple)
                                .cornerRadius(6)
                            }
                            .buttonStyle(.plain)
                            
                            Button(action: {
                                showAnnotationView = true
                            }) {
                                HStack(spacing: 4) {
                                    Image(systemName: "highlighter")
                                    Text("打开标注")
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(Color.orange.opacity(0.15))
                                .foregroundColor(.orange)
                                .cornerRadius(6)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding()
                    .background(Color(nsColor: .windowBackgroundColor))
                    
                    Divider()
                    
                    HSplitView {
                        if let doc = selectedDocument {
                            ThumbnailView(
                                document: doc,
                                selectedPageIndex: $selectedPageIndex,
                                onPageSelected: { index in
                                    print("切换到页面: \(index + 1)")
                                }
                            )
                            .frame(minWidth: 140, idealWidth: 160, maxWidth: 200)
                        }
                        
                        PDFPageView(
                            file: file,
                            pageIndex: $selectedPageIndex,
                            document: $selectedDocument
                        )
                        .frame(minWidth: 400)
                    }
                }
            } else {
                VStack(spacing: 20) {
                    Image(systemName: "doc.text")
                        .font(.system(size: 80))
                        .foregroundColor(.tertiary)
                    Text("选择一个文件预览")
                        .font(.title2)
                        .foregroundColor(.secondary)
                    Text("从左侧列表选择文件")
                        .font(.subheadline)
                        .foregroundColor(.tertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(nsColor: .controlBackgroundColor))
            }
        }
    }
    
    private var isFirstSelected: Bool {
        guard let selected = selectedFile,
              let index = pdfFiles.firstIndex(of: selected) else {
            return true
        }
        return index == 0
    }
    
    private var isLastSelected: Bool {
        guard let selected = selectedFile,
              let index = pdfFiles.firstIndex(of: selected) else {
            return true
        }
        return index == pdfFiles.count - 1
    }
    
    private func selectFiles() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [UTType.pdf]
        panel.allowsMultipleSelection = true
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        
        if panel.runModal() == .OK {
            let files = panel.urls.map { PDFFile(url: $0) }
            pdfFiles.append(contentsOf: files)
            if selectedFile == nil && !pdfFiles.isEmpty {
                selectedFile = pdfFiles.first
            }
        }
    }
    
    private func handleDrop(url: URL) {
        if url.pathExtension.lowercased() == "pdf" {
            let file = PDFFile(url: url)
            if !pdfFiles.contains(file) {
                pdfFiles.append(file)
                if selectedFile == nil {
                    selectedFile = file
                }
            }
        }
    }
    
    private func moveUp() {
        guard let selected = selectedFile,
              let currentIndex = pdfFiles.firstIndex(of: selected),
              currentIndex > 0 else { return }
        
        let newIndex = currentIndex - 1
        pdfFiles.swapAt(currentIndex, newIndex)
    }
    
    private func moveDown() {
        guard let selected = selectedFile,
              let currentIndex = pdfFiles.firstIndex(of: selected),
              currentIndex < pdfFiles.count - 1 else { return }
        
        let newIndex = currentIndex + 1
        pdfFiles.swapAt(currentIndex, newIndex)
    }
    
    private func ocrPanel(for file: PDFFile) -> some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("OCR 文字识别")
                        .font(.headline)
                    Text(file.name)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Button(action: {
                    showOCRPanel = false
                }) {
                    Image(systemName: "xmark")
                }
                .buttonStyle(.plain)
            }
            .padding()
            .background(Color(nsColor: .windowBackgroundColor))
            
            Divider()
            
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("识别质量")
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        Picker("", selection: $ocrRecognitionLevel) {
                            Text("快速").tag(OCRWorker.RecognitionLevel.fast)
                            Text("准确").tag(OCRWorker.RecognitionLevel.accurate)
                        }
                        .pickerStyle(.segmented)
                        .labelsHidden()
                        
                        Text("快速模式识别速度快，但可能遗漏一些小文字；准确模式提供更高的识别精度，但需要更多时间。")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    
                    VStack(alignment: .leading, spacing: 12) {
                        Text("识别语言")
                            .font(.subheadline)
                            .fontWeight(.medium)
                        
                        HStack(spacing: 8) {
                            LanguageToggle(
                                title: "中文",
                                isSelected: ocrLanguages.contains("zh-Hans"),
                                onToggle: { selected in
                                    if selected {
                                        if !ocrLanguages.contains("zh-Hans") {
                                            ocrLanguages.append("zh-Hans")
                                        }
                                    } else {
                                        ocrLanguages.removeAll { $0 == "zh-Hans" }
                                    }
                                }
                            )
                            
                            LanguageToggle(
                                title: "英文",
                                isSelected: ocrLanguages.contains("en"),
                                onToggle: { selected in
                                    if selected {
                                        if !ocrLanguages.contains("en") {
                                            ocrLanguages.append("en")
                                        }
                                    } else {
                                        ocrLanguages.removeAll { $0 == "en" }
                                    }
                                }
                            )
                        }
                    }
                    
                    if isPerformingOCR {
                        VStack(spacing: 12) {
                            ProgressView(value: ocrProgress) {
                                Text("正在进行文字识别...")
                                    .font(.subheadline)
                            }
                            .progressViewStyle(.linear)
                            
                            Text("\(Int(ocrProgress * 100))%")
                                .font(.caption)
                                .monospacedDigit()
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    if let error = ocrError {
                        HStack {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.red)
                            Text(error)
                                .font(.subheadline)
                                .foregroundColor(.red)
                        }
                        .padding()
                        .background(Color.red.opacity(0.1))
                        .cornerRadius(8)
                    }
                }
                .padding()
            }
            .background(Color(nsColor: .controlBackgroundColor))
            
            Divider()
            
            HStack {
                Button(action: {
                    showOCRPanel = false
                }) {
                    Text("取消")
                        .frame(width: 80)
                }
                .buttonStyle(.bordered)
                .keyboardShortcut(.cancelAction)
                .disabled(isPerformingOCR)
                
                Spacer()
                
                Button(action: {
                    Task {
                        await performOCR(on: file)
                    }
                }) {
                    HStack(spacing: 6) {
                        Image(systemName: "text.viewfinder")
                        Text(isPerformingOCR ? "识别中..." : "开始识别")
                    }
                    .frame(width: 120)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(isPerformingOCR || ocrLanguages.isEmpty)
                
                if !ocrResults.isEmpty {
                    Button(action: {
                        showOCRPanel = false
                        showOCRResults = true
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "eye")
                            Text("查看结果")
                        }
                    }
                    .buttonStyle(.bordered)
                }
            }
            .padding()
            .background(Color(nsColor: .windowBackgroundColor))
        }
        .frame(width: 500, height: 450)
    }
    
    private var ocrResultsView: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("OCR 识别结果")
                        .font(.headline)
                    Text("\(ocrResults.count) 页已识别")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Button(action: {
                    exportOCRResults()
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: "square.and.arrow.down")
                        Text("导出文本")
                    }
                }
                .buttonStyle(.bordered)
                
                Button(action: {
                    showOCRResults = false
                }) {
                    Image(systemName: "xmark")
                }
                .buttonStyle(.plain)
            }
            .padding()
            .background(Color(nsColor: .windowBackgroundColor))
            
            Divider()
            
            TabView {
                ForEach(ocrResults, id: \.pageIndex) { result in
                    ScrollView {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Text("第 \(result.pageIndex + 1) 页")
                                    .font(.headline)
                                
                                Spacer()
                                
                                Text("\(result.recognizedText.count) 个文字块")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            
                            Divider()
                            
                            if result.text.isEmpty {
                                Text("未识别到文字")
                                    .font(.body)
                                    .foregroundColor(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .center)
                                    .padding(.vertical, 50)
                            } else {
                                Text(result.text)
                                    .font(.body)
                                    .textSelection(.enabled)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                        .padding()
                    }
                    .tabItem {
                        Text("第 \(result.pageIndex + 1) 页")
                    }
                }
            }
            .tabViewStyle(.automatic)
            .background(Color(nsColor: .controlBackgroundColor))
        }
        .frame(width: 700, height: 500)
    }
    
    private func performOCR(on file: PDFFile) async {
        isPerformingOCR = true
        ocrProgress = 0
        ocrError = nil
        ocrResults = []
        
        let worker = OCRWorker.shared
        worker.recognitionLevel = ocrRecognitionLevel
        worker.recognitionLanguages = ocrLanguages
        
        do {
            let results = try await worker.recognizeText(from: file) { progress, current, total in
                DispatchQueue.main.async {
                    self.ocrProgress = progress
                }
            }
            
            DispatchQueue.main.async {
                self.ocrResults = results
                self.isPerformingOCR = false
                self.ocrProgress = 1.0
            }
        } catch {
            DispatchQueue.main.async {
                self.ocrError = error.localizedDescription
                self.isPerformingOCR = false
            }
        }
    }
    
    private func exportOCRResults() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [UTType.plainText]
        panel.nameFieldStringValue = "OCR_Result.txt"
        
        if panel.runModal() == .OK, let url = panel.url {
            do {
                try OCRWorker.shared.exportTextResults(ocrResults, to: url)
            } catch {
                print("导出失败: \(error.localizedDescription)")
            }
        }
    }
}

struct PDFFile: Identifiable, Equatable, Hashable {
    let id = UUID()
    let url: URL
    let name: String
    let pageCount: Int
    
    init(url: URL) {
        self.url = url
        self.name = url.lastPathComponent
        self.pageCount = PDFDocument(url: url)?.pageCount ?? 0
    }
    
    static func == (lhs: PDFFile, rhs: PDFFile) -> Bool {
        lhs.id == rhs.id
    }
    
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}

struct FileRow: View {
    let file: PDFFile
    let index: Int
    let isSelected: Bool
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "doc.text.fill")
                .font(.title2)
                .foregroundColor(.red)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(file.name)
                    .font(.body)
                    .lineLimit(1)
                
                Text("\(file.pageCount) 页")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Image(systemName: "line.3.horizontal")
                .foregroundColor(.tertiary)
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 4)
        .contentShape(Rectangle())
    }
}

struct PDFKitView: NSViewRepresentable {
    let document: PDFDocument
    
    func makeNSView(context: Context) -> PDFView {
        let pdfView = PDFView()
        pdfView.document = document
        pdfView.autoScales = true
        pdfView.displayMode = .singlePageContinuous
        pdfView.displayDirection = .vertical
        return pdfView
    }
    
    func updateNSView(_ nsView: PDFView, context: Context) {
        nsView.document = document
    }
}

struct DropDelegate: DropDelegate {
    let handler: (URL) -> Void
    
    func performDrop(info: DropInfo) -> Bool {
        let item = info.itemProviders(for: [UTType.fileURL]).first
        item?.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { url, _ in
            if let data = url as? Data, let fileURL = URL(dataRepresentation: data, relativeTo: nil) {
                DispatchQueue.main.async {
                    handler(fileURL)
                }
            }
        }
        return true
    }
}

struct ReorderDelegate: DropDelegate {
    let destinationFileId: UUID
    @Binding var files: [PDFFile]
    @Binding var dragOverIndex: Int?
    
    func performDrop(info: DropInfo) -> Bool {
        dragOverIndex = nil
        
        let item = info.itemProviders(for: [UTType.text]).first
        item?.loadItem(forTypeIdentifier: UTType.text.identifier, options: nil) { idString, _ in
            guard let data = idString as? Data,
                  let uuidString = String(data: data, encoding: .utf8),
                  let draggedUUID = UUID(uuidString: uuidString) else { return }
            
            DispatchQueue.main.async {
                guard let sourceIndex = files.firstIndex(where: { $0.id == draggedUUID) else { return }
                guard let destinationIndex = files.firstIndex(where: { $0.id == self.destinationFileId) else { return }
                
                guard sourceIndex != destinationIndex else { return }
                
                let movedFile = files[sourceIndex]
                var updatedFiles = files
                updatedFiles.remove(at: sourceIndex)
                
                let insertIndex: Int
                if sourceIndex < destinationIndex {
                    insertIndex = destinationIndex - 1
                } else {
                    insertIndex = destinationIndex
                }
                
                updatedFiles.insert(movedFile, at: insertIndex)
                files = updatedFiles
            }
        }
        return true
    }
    
    func dropEntered(info: DropInfo) {
        if let index = files.firstIndex(where: { $0.id == destinationFileId) {
            dragOverIndex = index
        }
    }
    
    func dropExited(info: DropInfo) {
        dragOverIndex = nil
    }
}

struct PDFPageView: NSViewRepresentable {
    let file: PDFFile
    @Binding var pageIndex: Int
    @Binding var document: PDFDocument?
    
    func makeNSView(context: Context) -> PagePDFView {
        let view = PagePDFView()
        view.pageIndex = pageIndex
        view.pdfDocument = document
        view.onPageChanged = { newIndex in
            DispatchQueue.main.async {
                pageIndex = newIndex
            }
        }
        return view
    }
    
    func updateNSView(_ nsView: PagePDFView, context: Context) {
        nsView.pageIndex = pageIndex
        nsView.pdfDocument = document
    }
}

class PagePDFView: NSView {
    var pageIndex: Int = 0 {
        didSet {
            goToPage()
        }
    }
    
    var pdfDocument: PDFDocument? {
        didSet {
            pdfView?.document = pdfDocument
            goToPage()
        }
    }
    
    var onPageChanged: ((Int) -> Void)?
    
    private var pdfView: PDFView?
    private var observer: NSObjectProtocol?
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        setupView()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupView()
    }
    
    private func setupView() {
        wantsLayer = true
        layer?.backgroundColor = NSColor.underPageBackgroundColor.cgColor
        
        let pdfView = PDFView(frame: bounds)
        pdfView.autoresizingMask = [.width, .height]
        pdfView.autoScales = true
        pdfView.displayMode = .singlePage
        pdfView.displayDirection = .vertical
        pdfView.displaysPageBreaks = false
        addSubview(pdfView)
        self.pdfView = pdfView
        
        observer = NotificationCenter.default.addObserver(
            forName: PDFView.pageChangedNotification,
            object: pdfView,
            queue: .main
        ) { [weak self] notification in
            guard let self = self,
                  let pdfView = notification.object as? PDFView,
                  let currentPage = pdfView.currentPage,
                  let document = pdfView.document else { return }
            
            let newIndex = document.index(for: currentPage)
            self.onPageChanged?(newIndex)
        }
    }
    
    private func goToPage() {
        guard let pdfView = pdfView,
              let document = pdfDocument,
              pageIndex >= 0 && pageIndex < document.pageCount else { return }
        
        if let page = document.page(at: pageIndex) {
            pdfView.go(to: page)
        }
    }
    
    deinit {
        if let observer = observer {
            NotificationCenter.default.removeObserver(observer)
        }
    }
}

struct LanguageToggle: View {
    let title: String
    let isSelected: Bool
    let onToggle: (Bool) -> Void
    
    var body: some View {
        Button(action: {
            onToggle(!isSelected)
        }) {
            HStack(spacing: 6) {
                Image(systemName: isSelected ? "checkmark.square.fill" : "square")
                    .foregroundColor(isSelected ? .accentColor : .secondary)
                
                Text(title)
                    .font(.subheadline)
                    .foregroundColor(.primary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.accentColor.opacity(0.15) : Color.secondary.opacity(0.1))
            )
        }
        .buttonStyle(.plain)
    }
}

import SwiftUI
import PDFKit

struct AnnotationView: View {
    let pdfFile: PDFFile
    @Environment(\.dismiss) private var dismiss
    @State private var currentTool: AnnotationTool = .highlight
    @State private var selectedColor: Color = .yellow
    @State private var selectedOpacity: Double = 0.4
    @State private var selectedPageIndex: Int = 0
    @State private var isDrawing = false
    @State private var annotationStartPoint: CGPoint?
    @State private var annotationEndPoint: CGPoint?
    @State private var showColorPicker = false
    @State private var pdfDocument: PDFDocument?
    @State private var annotations: [PDFAnnotation] = []
    @State private var showSaveSuccess = false
    @State private var showSignaturePad = false
    @State private var signatureLineWidth: CGFloat = 3.0
    @State private var signatureColor: Color = .black
    
    private let availableColors: [Color] = [
        .yellow, .green, .blue, .pink, .purple, .orange
    ]
    
    private let signatureColors: [Color] = [
        .black, .red, .blue, .purple, .green
    ]
    
    var body: some View {
        VStack(spacing: 0) {
            headerBar
            
            Divider()
            
            toolbar
            
            Divider()
            
            HStack(spacing: 0) {
                pagesSidebar
                
                Divider()
                
                pdfContentView
            }
        }
        .frame(minWidth: 900, minHeight: 600)
        .onAppear {
            loadDocument()
        }
        .sheet(isPresented: $showColorPicker) {
            colorPickerSheet
        }
        .sheet(isPresented: $showSignaturePad) {
            signaturePad
        }
        .alert("保存成功", isPresented: $showSaveSuccess) {
            Button("确定") {}
        } message: {
            Text("标注已保存到文件")
        }
        .onChange(of: currentTool) { newTool in
            if newTool == .signature {
                showSignaturePad = true
            }
        }
    }
    
    private var headerBar: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("PDF 标注")
                    .font(.headline)
                Text(pdfFile.name)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            HStack(spacing: 8) {
                Button(action: undoLastAnnotation) {
                    Label("撤销", systemImage: "arrow.uturn.backward")
                }
                .disabled(annotations.isEmpty)
                
                Button(action: saveAnnotations) {
                    Label("保存", systemImage: "square.and.arrow.down")
                }
                
                Button(action: { dismiss() }) {
                    Label("关闭", systemImage: "xmark")
                }
                .keyboardShortcut(.escape)
            }
        }
        .padding()
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var toolbar: some View {
        HStack(spacing: 20) {
            HStack(spacing: 4) {
                ForEach(AnnotationTool.allCases, id: \.self) { tool in
                    ToolButton(
                        tool: tool,
                        isSelected: currentTool == tool,
                        action: { currentTool = tool }
                    )
                }
            }
            
            Divider()
                .frame(height: 30)
            
            HStack(spacing: 4) {
                ForEach(availableColors, id: \.self) { color in
                    ColorButton(
                        color: color,
                        isSelected: selectedColor == color,
                        action: { selectedColor = color }
                    )
                }
                
                Button(action: { showColorPicker = true }) {
                    Image(systemName: "eyedropper")
                        .frame(width: 28, height: 28)
                        .background(Color.secondary.opacity(0.1))
                        .cornerRadius(6)
                }
                .buttonStyle(.plain)
            }
            
            Divider()
                .frame(height: 30)
            
            HStack(spacing: 8) {
                Text("透明度")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Slider(value: $selectedOpacity, in: 0.1...1.0, step: 0.1)
                    .frame(width: 100)
                
                Text("\(Int(selectedOpacity * 100))%")
                    .font(.caption)
                    .monospacedDigit()
                    .frame(width: 35)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var pagesSidebar: some View {
        VStack(spacing: 0) {
            Text("页面")
                .font(.subheadline)
                .fontWeight(.medium)
                .padding(.vertical, 12)
            
            Divider()
            
            if let document = pdfDocument {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(0..<document.pageCount, id: \.self) { index in
                            PageThumbnail(
                                page: document.page(at: index),
                                pageNumber: index + 1,
                                isSelected: selectedPageIndex == index
                            )
                            .onTapGesture {
                                selectedPageIndex = index
                            }
                        }
                    }
                    .padding(12)
                }
            }
        }
        .frame(width: 120)
        .background(Color(nsColor: .controlBackgroundColor))
    }
    
    private var pdfContentView: some View {
        GeometryReader { geometry in
            ZStack {
                if let document = pdfDocument {
                    PDFPageView(
                        document: document,
                        pageIndex: selectedPageIndex,
                        currentTool: currentTool,
                        color: nsColor(from: selectedColor),
                        opacity: CGFloat(selectedOpacity),
                        isDrawing: $isDrawing,
                        startPoint: $annotationStartPoint,
                        endPoint: $annotationEndPoint,
                        onAnnotationCreated: { annotation in
                            annotations.append(annotation)
                        }
                    )
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    VStack {
                        Image(systemName: "doc.text")
                            .font(.system(size: 60))
                            .foregroundColor(.tertiary)
                        Text("无法加载 PDF")
                            .font(.headline)
                            .foregroundColor(.secondary)
                    }
                }
                
                if isDrawing, let start = annotationStartPoint, let end = annotationEndPoint {
                    Rectangle()
                        .stroke(currentTool == .highlight ? selectedColor : selectedColor, lineWidth: currentTool == .underline ? 3 : 2)
                        .background(
                            currentTool == .highlight
                            ? selectedColor.opacity(selectedOpacity)
                            : Color.clear
                        )
                        .frame(
                            width: abs(end.x - start.x),
                            height: currentTool == .underline ? 3 : abs(end.y - start.y)
                        )
                        .position(
                            x: (start.x + end.x) / 2,
                            y: currentTool == .underline ? max(start.y, end.y) : (start.y + end.y) / 2
                        )
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
        }
        .background(Color(nsColor: .underPageBackgroundColor))
    }
    
    private var colorPickerSheet: some View {
        VStack(spacing: 20) {
            Text("选择颜色")
                .font(.headline)
            
            ColorPicker("选择颜色", selection: $selectedColor)
                .labelsHidden()
                .scaleEffect(2)
                .padding()
            
            HStack {
                Button("取消") {
                    showColorPicker = false
                }
                .keyboardShortcut(.cancelAction)
                
                Button("确定") {
                    showColorPicker = false
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding()
        .frame(width: 300, height: 200)
    }
    
    private var signaturePad: some View {
        SignaturePadView(
            lineWidth: $signatureLineWidth,
            lineColor: $signatureColor,
            onCancel: {
                showSignaturePad = false
                currentTool = .highlight
            },
            onSave: { signatureImage in
                addSignatureToPDF(signatureImage)
                showSignaturePad = false
                currentTool = .highlight
            },
            availableColors: signatureColors
        )
    }
    
    private func addSignatureToPDF(_ image: NSImage) {
        guard let document = pdfDocument else { return }
        guard let page = document.page(at: selectedPageIndex) else { return }
        
        let pageBounds = page.bounds(for: .mediaBox)
        let imageSize = image.size
        
        let targetWidth: CGFloat = 200
        let scale = targetWidth / imageSize.width
        let targetHeight = imageSize.height * scale
        
        let signatureRect = CGRect(
            x: pageBounds.width / 2 - targetWidth / 2,
            y: 50,
            width: targetWidth,
            height: targetHeight
        )
        
        let annotation = PDFAnnotation(
            bounds: signatureRect,
            forType: .stamp,
            withProperties: nil
        )
        
        annotation.setImage(image, for: .normal)
        annotation.setValue("Signature", forAnnotationKey: .name)
        annotation.setValue(Date(), forAnnotationKey: .modificationDate)
        
        page.addAnnotation(annotation)
        annotations.append(annotation)
    }
    
    private func loadDocument() {
        pdfDocument = PDFDocument(url: pdfFile.url)
    }
    
    private func undoLastAnnotation() {
        guard !annotations.isEmpty else { return }
        
        let lastAnnotation = annotations.removeLast()
        lastAnnotation.page?.removeAnnotation(lastAnnotation)
    }
    
    private func saveAnnotations() {
        guard let document = pdfDocument else { return }
        
        let fileManager = FileManager.default
        let tempDir = fileManager.temporaryDirectory
        let tempURL = tempDir.appendingPathComponent(UUID().uuidString).appendingPathExtension("pdf")
        let backupURL = tempDir.appendingPathComponent(UUID().uuidString).appendingPathExtension("pdf")
        
        do {
            if !document.write(to: tempURL) {
                throw NSError(domain: "PDFAnnotation", code: -1, userInfo: [
                    NSLocalizedDescriptionKey: "无法写入临时文件"
                ])
            }
            
            if fileManager.fileExists(atPath: pdfFile.url.path) {
                try fileManager.moveItem(at: pdfFile.url, to: backupURL)
            }
            
            do {
                try fileManager.moveItem(at: tempURL, to: pdfFile.url)
                
                if fileManager.fileExists(atPath: backupURL.path) {
                    try? fileManager.removeItem(at: backupURL)
                }
                
                showSaveSuccess = true
            } catch {
                if fileManager.fileExists(atPath: backupURL.path) {
                    try? fileManager.moveItem(at: backupURL, to: pdfFile.url)
                }
                throw error
            }
        } catch {
            print("保存失败: \(error.localizedDescription)")
            
            if fileManager.fileExists(atPath: backupURL.path) {
                try? fileManager.removeItem(at: backupURL)
            }
            if fileManager.fileExists(atPath: tempURL.path) {
                try? fileManager.removeItem(at: tempURL)
            }
        }
    }
    
    private func nsColor(from color: Color) -> NSColor {
        return NSColor(color)
    }
}

enum AnnotationTool: String, CaseIterable, Identifiable {
    case highlight = "highlight"
    case underline = "underline"
    case strikeOut = "strikeOut"
    case signature = "signature"
    
    var id: String { rawValue }
    
    var displayName: String {
        switch self {
        case .highlight: return "高亮"
        case .underline: return "下划线"
        case .strikeOut: return "删除线"
        case .signature: return "签名"
        }
    }
    
    var icon: String {
        switch self {
        case .highlight: return "highlighter"
        case .underline: return "character.underline"
        case .strikeOut: return "character.strikethrough"
        case .signature: return "signature"
        }
    }
    
    var pdfAnnotationType: PDFAnnotationSubtype? {
        switch self {
        case .highlight: return .highlight
        case .underline: return .underline
        case .strikeOut: return .strikeOut
        case .signature: return nil
        }
    }
    
    var isAreaSelection: Bool {
        switch self {
        case .highlight, .underline, .strikeOut:
            return true
        case .signature:
            return false
        }
    }
}

struct ToolButton: View {
    let tool: AnnotationTool
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 2) {
                Image(systemName: tool.icon)
                    .font(.title3)
                Text(tool.displayName)
                    .font(.caption2)
            }
            .frame(width: 50, height: 44)
            .background(
                isSelected
                ? Color.accentColor.opacity(0.2)
                : Color.secondary.opacity(0.05)
            )
            .foregroundColor(isSelected ? .accentColor : .primary)
            .cornerRadius(8)
        }
        .buttonStyle(.plain)
    }
}

struct ColorButton: View {
    let color: Color
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Circle()
                .fill(color)
                .frame(width: 24, height: 24)
                .overlay(
                    Circle()
                        .stroke(isSelected ? Color.primary : Color.clear, lineWidth: 2)
                        .frame(width: 28, height: 28)
                )
        }
        .buttonStyle(.plain)
        .padding(4)
    }
}

struct PageThumbnail: View {
    let page: PDFPage?
    let pageNumber: Int
    let isSelected: Bool
    
    var body: some View {
        VStack(spacing: 4) {
            if let page = page {
                Image(nsImage: page.thumbnail(of: CGSize(width: 80, height: 100), for: .mediaBox))
                    .resizable()
                    .scaledToFit()
                    .frame(width: 80, height: 100)
                    .background(Color.white)
                    .cornerRadius(4)
                    .shadow(radius: 2)
            } else {
                Rectangle()
                    .fill(Color.gray.opacity(0.3))
                    .frame(width: 80, height: 100)
                    .cornerRadius(4)
            }
            
            Text("第 \(pageNumber) 页")
                .font(.caption2)
                .foregroundColor(isSelected ? .accentColor : .secondary)
        }
        .padding(6)
        .background(
            isSelected
            ? Color.accentColor.opacity(0.15)
            : Color.clear
        )
        .cornerRadius(8)
    }
}

struct PDFPageView: NSViewRepresentable {
    let document: PDFDocument
    let pageIndex: Int
    let currentTool: AnnotationTool
    let color: NSColor
    let opacity: CGFloat
    @Binding var isDrawing: Bool
    @Binding var startPoint: CGPoint?
    @Binding var endPoint: CGPoint?
    let onAnnotationCreated: (PDFAnnotation) -> Void
    
    func makeNSView(context: Context) -> PDFAnnotationView {
        let view = PDFAnnotationView()
        view.document = document
        view.pageIndex = pageIndex
        view.delegate = context.coordinator
        return view
    }
    
    func updateNSView(_ nsView: PDFAnnotationView, context: Context) {
        nsView.document = document
        nsView.pageIndex = pageIndex
        nsView.currentTool = currentTool
        nsView.color = color
        nsView.opacity = opacity
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(
            isDrawing: $isDrawing,
            startPoint: $startPoint,
            endPoint: $endPoint,
            onAnnotationCreated: onAnnotationCreated
        )
    }
    
    class Coordinator: NSObject, PDFAnnotationViewDelegate {
        @Binding var isDrawing: Bool
        @Binding var startPoint: CGPoint?
        @Binding var endPoint: CGPoint?
        let onAnnotationCreated: (PDFAnnotation) -> Void
        
        init(
            isDrawing: Binding<Bool>,
            startPoint: Binding<CGPoint?>,
            endPoint: Binding<CGPoint?>,
            onAnnotationCreated: @escaping (PDFAnnotation) -> Void
        ) {
            _isDrawing = isDrawing
            _startPoint = startPoint
            _endPoint = endPoint
            self.onAnnotationCreated = onAnnotationCreated
        }
        
        func annotationViewDidStartDrawing(_ view: PDFAnnotationView, at point: CGPoint) {
            isDrawing = true
            startPoint = point
            endPoint = point
        }
        
        func annotationViewDidUpdateDrawing(_ view: PDFAnnotationView, to point: CGPoint) {
            endPoint = point
        }
        
        func annotationViewDidFinishDrawing(_ view: PDFAnnotationView, annotation: PDFAnnotation) {
            isDrawing = false
            startPoint = nil
            endPoint = nil
            onAnnotationCreated(annotation)
        }
        
        func annotationViewDidCancelDrawing(_ view: PDFAnnotationView) {
            isDrawing = false
            startPoint = nil
            endPoint = nil
        }
    }
}

protocol PDFAnnotationViewDelegate: AnyObject {
    func annotationViewDidStartDrawing(_ view: PDFAnnotationView, at point: CGPoint)
    func annotationViewDidUpdateDrawing(_ view: PDFAnnotationView, to point: CGPoint)
    func annotationViewDidFinishDrawing(_ view: PDFAnnotationView, annotation: PDFAnnotation)
    func annotationViewDidCancelDrawing(_ view: PDFAnnotationView)
}

class PDFAnnotationView: NSView {
    var document: PDFDocument? {
        didSet {
            updatePDFView()
        }
    }
    
    var pageIndex: Int = 0 {
        didSet {
            updatePDFView()
        }
    }
    
    weak var delegate: PDFAnnotationViewDelegate?
    
    var currentTool: AnnotationTool = .highlight
    var color: NSColor = .yellow
    var opacity: CGFloat = 0.4
    
    private var pdfView: PDFView?
    private var isDragging = false
    private var dragStartPoint: CGPoint?
    private var dragCurrentPoint: CGPoint?
    private var panGesture: NSPanGestureRecognizer?
    
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
        pdfView.interpolationQuality = .high
        addSubview(pdfView)
        self.pdfView = pdfView
        
        let panGesture = NSPanGestureRecognizer(target: self, action: #selector(handlePan(_:)))
        panGesture.delegate = self
        addGestureRecognizer(panGesture)
        self.panGesture = panGesture
    }
    
    private func updatePDFView() {
        guard let document = document, pageIndex >= 0 && pageIndex < document.pageCount else {
            pdfView?.document = nil
            return
        }
        
        pdfView?.document = document
        
        if let page = document.page(at: pageIndex) {
            pdfView?.go(to: page)
        }
    }
    
    @objc private func handlePan(_ gesture: NSPanGestureRecognizer) {
        guard let document = document,
              let pdfView = pdfView,
              pageIndex >= 0 && pageIndex < document.pageCount,
              let page = document.page(at: pageIndex) else { return }
        
        let location = gesture.location(in: self)
        
        guard let documentView = pdfView.documentView else { return }
        let pdfPoint = pdfView.convert(location, to: documentView)
        
        switch gesture.state {
        case .began:
            isDragging = true
            dragStartPoint = pdfPoint
            dragCurrentPoint = pdfPoint
            delegate?.annotationViewDidStartDrawing(self, at: location)
            
        case .changed:
            dragCurrentPoint = pdfPoint
            delegate?.annotationViewDidUpdateDrawing(self, to: location)
            
        case .ended:
            isDragging = false
            if let start = dragStartPoint, let current = dragCurrentPoint {
                let distance = hypot(current.x - start.x, current.y - start.y)
                if distance > 5 {
                    let annotation = createAnnotation(from: start, to: current, on: page)
                    page.addAnnotation(annotation)
                    delegate?.annotationViewDidFinishDrawing(self, annotation: annotation)
                }
            }
            dragStartPoint = nil
            dragCurrentPoint = nil
            
        case .cancelled, .failed:
            isDragging = false
            dragStartPoint = nil
            dragCurrentPoint = nil
            delegate?.annotationViewDidCancelDrawing(self)
            
        default:
            break
        }
    }
    
    private func createAnnotation(from start: CGPoint, to end: CGPoint, on page: PDFPage) -> PDFAnnotation {
        let bounds = CGRect(
            x: min(start.x, end.x),
            y: min(start.y, end.y),
            width: max(abs(end.x - start.x), 10),
            height: max(abs(end.y - start.y), 10)
        )
        
        let annotation = PDFAnnotation(
            bounds: bounds,
            forType: currentTool.pdfAnnotationType,
            withProperties: nil
        )
        annotation.color = color.withAlphaComponent(opacity)
        
        let quadPoints = [
            NSPoint(x: bounds.minX, y: bounds.maxY),
            NSPoint(x: bounds.maxX, y: bounds.maxY),
            NSPoint(x: bounds.minX, y: bounds.minY),
            NSPoint(x: bounds.maxX, y: bounds.minY)
        ]
        
        annotation.setValue(quadPoints, forAnnotationKey: .quadPoints)
        annotation.setValue("PDF Annotation Tool", forAnnotationKey: .creator)
        
        return annotation
    }
}

extension PDFAnnotationView: NSGestureRecognizerDelegate {
    func gestureRecognizer(_ gestureRecognizer: NSGestureRecognizer, shouldRecognizeSimultaneouslyWith otherGestureRecognizer: NSGestureRecognizer) -> Bool {
        return false
    }
    
    func gestureRecognizer(_ gestureRecognizer: NSGestureRecognizer, shouldRequireFailureOf otherGestureRecognizer: NSGestureRecognizer) -> Bool {
        return false
    }
}

struct SignaturePadView: View {
    @Binding var lineWidth: CGFloat
    @Binding var lineColor: Color
    let onCancel: () -> Void
    let onSave: (NSImage) -> Void
    let availableColors: [Color]
    
    @State private var strokes: [Stroke] = []
    @State private var currentStroke: Stroke?
    
    var body: some View {
        VStack(spacing: 0) {
            headerBar
            
            Divider()
            
            HStack(spacing: 16) {
                HStack(spacing: 8) {
                    Text("颜色:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    ForEach(availableColors, id: \.self) { color in
                        ColorButton(
                            color: color,
                            isSelected: lineColor == color,
                            action: { lineColor = color }
                        )
                    }
                }
                
                Divider()
                    .frame(height: 30)
                
                HStack(spacing: 8) {
                    Text("粗细:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Slider(value: $lineWidth, in: 1...10, step: 0.5)
                        .frame(width: 100)
                    
                    Text("\(Int(lineWidth))px")
                        .font(.caption)
                        .monospacedDigit()
                        .frame(width: 40)
                }
                
                Spacer()
                
                HStack(spacing: 8) {
                    Button(action: undoLastStroke) {
                        Image(systemName: "arrow.uturn.backward")
                    }
                    .buttonStyle(.bordered)
                    .disabled(strokes.isEmpty)
                    
                    Button(action: clearAll) {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.bordered)
                    .disabled(strokes.isEmpty)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color(nsColor: .windowBackgroundColor))
            
            Divider()
            
            ZStack {
                CanvasView(
                    strokes: strokes,
                    currentStroke: currentStroke,
                    lineWidth: lineWidth,
                    lineColor: NSColor(lineColor),
                    onStrokeBegan: { point in
                        currentStroke = Stroke(points: [point], color: lineColor, lineWidth: lineWidth)
                    },
                    onStrokeChanged: { point in
                        currentStroke?.points.append(point)
                    },
                    onStrokeEnded: { _ in
                        if let stroke = currentStroke, stroke.points.count > 1 {
                            strokes.append(stroke)
                        }
                        currentStroke = nil
                    }
                )
                .background(Color.white)
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.secondary.opacity(0.3), lineWidth: 1)
                )
                .padding()
                
                if strokes.isEmpty && currentStroke == nil {
                    Text("在此处签名...")
                        .font(.largeTitle)
                        .foregroundColor(.tertiary)
                        .allowsHitTesting(false)
                }
            }
            .frame(maxHeight: .infinity)
            .background(Color(nsColor: .controlBackgroundColor))
            
            Divider()
            
            HStack {
                Text("提示：使用鼠标或触控板在上方区域书写签名")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Button(action: onCancel) {
                    Text("取消")
                        .frame(width: 80)
                }
                .buttonStyle(.bordered)
                .keyboardShortcut(.cancelAction)
                
                Button(action: saveSignature) {
                    HStack(spacing: 6) {
                        Image(systemName: "checkmark")
                        Text("使用签名")
                    }
                    .frame(width: 120)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(strokes.isEmpty)
            }
            .padding()
            .background(Color(nsColor: .windowBackgroundColor))
        }
        .frame(width: 700, height: 500)
    }
    
    private var headerBar: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("创建签名")
                    .font(.headline)
                Text("绘制您的手写签名")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Button(action: onCancel) {
                Image(systemName: "xmark")
            }
            .buttonStyle(.plain)
            .keyboardShortcut(.escape)
        }
        .padding()
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private func undoLastStroke() {
        if !strokes.isEmpty {
            strokes.removeLast()
        }
    }
    
    private func clearAll() {
        strokes.removeAll()
        currentStroke = nil
    }
    
    private func saveSignature() {
        let image = renderSignatureToImage()
        onSave(image)
    }
    
    private func renderSignatureToImage() -> NSImage {
        let size = NSSize(width: 600, height: 200)
        let image = NSImage(size: size)
        
        image.lockFocus()
        
        guard let context = NSGraphicsContext.current?.cgContext else {
            image.unlockFocus()
            return image
        }
        
        NSColor.white.setFill()
        context.fill(CGRect(origin: .zero, size: size))
        
        for stroke in strokes {
            drawStroke(stroke, in: context)
        }
        
        image.unlockFocus()
        
        return cropImageToContent(image)
    }
    
    private func drawStroke(_ stroke: Stroke, in context: CGContext) {
        guard stroke.points.count >= 2 else { return }
        
        context.setStrokeColor(NSColor(stroke.color).cgColor)
        context.setLineWidth(stroke.lineWidth)
        context.setLineCap(.round)
        context.setLineJoin(.round)
        
        context.beginPath()
        context.move(to: stroke.points[0])
        
        for i in 1..<stroke.points.count {
            context.addLine(to: stroke.points[i])
        }
        
        context.strokePath()
    }
    
    private func cropImageToContent(_ image: NSImage) -> NSImage {
        guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            return image
        }
        
        let width = cgImage.width
        let height = cgImage.height
        
        var minX = width
        var maxX = 0
        var minY = height
        var maxY = 0
        
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        let bytesPerPixel = 4
        let bytesPerRow = bytesPerPixel * width
        let bitsPerComponent = 8
        
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: bitsPerComponent,
            bytesPerRow: bytesPerRow,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return image
        }
        
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
        
        guard let data = context.data else {
            return image
        }
        
        let pixelData = data.bindMemory(to: UInt8.self, capacity: width * height * 4)
        
        for y in 0..<height {
            for x in 0..<width {
                let pixelIndex = (y * width + x) * 4
                let alpha = pixelData[pixelIndex + 3]
                
                if alpha > 0 && (pixelData[pixelIndex] < 240 || pixelData[pixelIndex + 1] < 240 || pixelData[pixelIndex + 2] < 240) {
                    minX = min(minX, x)
                    maxX = max(maxX, x)
                    minY = min(minY, y)
                    maxY = max(maxY, y)
                }
            }
        }
        
        if maxX > minX && maxY > minY {
            let padding: CGFloat = 20
            let cropRect = CGRect(
                x: CGFloat(minX) - padding,
                y: CGFloat(height - maxY - 1) - padding,
                width: CGFloat(maxX - minX) + padding * 2,
                height: CGFloat(maxY - minY) + padding * 2
            )
            
            if let croppedCgImage = cgImage.cropping(to: cropRect) {
                return NSImage(cgImage: croppedCgImage, size: cropRect.size)
            }
        }
        
        return image
    }
}

struct Stroke {
    var points: [CGPoint]
    var color: Color
    var lineWidth: CGFloat
}

struct CanvasView: NSViewRepresentable {
    let strokes: [Stroke]
    let currentStroke: Stroke?
    let lineWidth: CGFloat
    let lineColor: NSColor
    let onStrokeBegan: (CGPoint) -> Void
    let onStrokeChanged: (CGPoint) -> Void
    let onStrokeEnded: (CGPoint) -> Void
    
    func makeNSView(context: Context) -> DrawingCanvas {
        let canvas = DrawingCanvas()
        canvas.delegate = context.coordinator
        canvas.allowsMagnification = false
        return canvas
    }
    
    func updateNSView(_ nsView: DrawingCanvas, context: Context) {
        nsView.strokes = strokes
        nsView.currentStroke = currentStroke
        nsView.lineWidth = lineWidth
        nsView.lineColor = lineColor
        nsView.needsDisplay = true
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(
            onStrokeBegan: onStrokeBegan,
            onStrokeChanged: onStrokeChanged,
            onStrokeEnded: onStrokeEnded
        )
    }
    
    class Coordinator: DrawingCanvasDelegate {
        let onStrokeBegan: (CGPoint) -> Void
        let onStrokeChanged: (CGPoint) -> Void
        let onStrokeEnded: (CGPoint) -> Void
        
        init(
            onStrokeBegan: @escaping (CGPoint) -> Void,
            onStrokeChanged: @escaping (CGPoint) -> Void,
            onStrokeEnded: @escaping (CGPoint) -> Void
        ) {
            self.onStrokeBegan = onStrokeBegan
            self.onStrokeChanged = onStrokeChanged
            self.onStrokeEnded = onStrokeEnded
        }
        
        func canvasBeganStroke(at point: CGPoint) {
            onStrokeBegan(point)
        }
        
        func canvasChangedStroke(to point: CGPoint) {
            onStrokeChanged(point)
        }
        
        func canvasEndedStroke(at point: CGPoint) {
            onStrokeEnded(point)
        }
    }
}

protocol DrawingCanvasDelegate: AnyObject {
    func canvasBeganStroke(at point: CGPoint)
    func canvasChangedStroke(to point: CGPoint)
    func canvasEndedStroke(at point: CGPoint)
}

class DrawingCanvas: NSView {
    weak var delegate: DrawingCanvasDelegate?
    var strokes: [Stroke] = []
    var currentStroke: Stroke?
    var lineWidth: CGFloat = 3.0
    var lineColor: NSColor = .black
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        commonInit()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        commonInit()
    }
    
    private func commonInit() {
        wantsLayer = true
        layer?.backgroundColor = NSColor.white.cgColor
        layer?.masksToBounds = true
    }
    
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        
        guard let context = NSGraphicsContext.current?.cgContext else { return }
        
        for stroke in strokes {
            drawStroke(stroke, in: context)
        }
        
        if let current = currentStroke {
            drawStroke(current, in: context)
        }
    }
    
    private func drawStroke(_ stroke: Stroke, in context: CGContext) {
        guard stroke.points.count >= 2 else { return }
        
        context.setStrokeColor(NSColor(stroke.color).cgColor)
        context.setLineWidth(stroke.lineWidth)
        context.setLineCap(.round)
        context.setLineJoin(.round)
        context.setFlatness(0.1)
        
        context.beginPath()
        context.move(to: stroke.points[0])
        
        for i in 1..<stroke.points.count {
            let previousPoint = stroke.points[i - 1]
            let currentPoint = stroke.points[i]
            
            let midPoint = CGPoint(
                x: (previousPoint.x + currentPoint.x) / 2,
                y: (previousPoint.y + currentPoint.y) / 2
            )
            
            if i == 1 {
                context.addLine(to: midPoint)
            } else if i == stroke.points.count - 1 {
                context.addQuadCurve(to: currentPoint, control: previousPoint)
            } else {
                context.addQuadCurve(to: midPoint, control: previousPoint)
            }
        }
        
        context.strokePath()
    }
    
    override func mouseDown(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        delegate?.canvasBeganStroke(at: point)
        needsDisplay = true
    }
    
    override func mouseDragged(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        delegate?.canvasChangedStroke(to: point)
        needsDisplay = true
    }
    
    override func mouseUp(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        delegate?.canvasEndedStroke(at: point)
        needsDisplay = true
    }
    
    override var acceptsFirstResponder: Bool {
        return true
    }
    
    override func becomeFirstResponder() -> Bool {
        return true
    }
}

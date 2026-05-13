import SwiftUI
import UniformTypeIdentifiers
import PDFKit

struct ExportPanel: View {
    let pdfFiles: [PDFFile]
    @Environment(\.dismiss) private var dismiss
    @State private var outputFileName: String = "MergedDocument.pdf"
    @State private var outputDirectory: URL?
    @State private var selectedExportMode: ExportMode = .mergeAll
    @State private var pageRanges: [String: String] = [:]
    @State private var isExporting = false
    @State private var exportProgress: Double = 0
    @State private var errorMessage: String?
    @State private var showSuccess = false
    
    private let merger = PDFMerger.shared
    
    var body: some View {
        VStack(spacing: 0) {
            headerSection
            
            Divider()
            
            ScrollView {
                VStack(spacing: 20) {
                    exportModeSection
                    
                    filesListSection
                    
                    outputSettingsSection
                    
                    summarySection
                }
                .padding()
            }
            
            Divider()
            
            footerSection
        }
        .frame(width: 600, height: 550)
        .onAppear {
            initializePageRanges()
        }
        .sheet(isPresented: $showSuccess) {
            successSheet
        }
    }
    
    private var headerSection: some View {
        HStack {
            Text("合并并导出")
                .font(.headline)
            
            Spacer()
            
            Button(action: { dismiss() }) {
                Image(systemName: "xmark")
            }
            .buttonStyle(.plain)
            .keyboardShortcut(.escape)
        }
        .padding()
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var exportModeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("导出模式")
                .font(.subheadline)
                .fontWeight(.medium)
            
            Picker("", selection: $selectedExportMode) {
                Text("合并全部页面").tag(ExportMode.mergeAll)
                Text("选择页面范围").tag(ExportMode.customPages)
            }
            .pickerStyle(.radioGroup)
            .labelsHidden()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(10)
    }
    
    private var filesListSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("文件列表（按顺序合并）")
                    .font(.subheadline)
                    .fontWeight(.medium)
                
                Spacer()
                
                Text("\(pdfFiles.count) 个文件")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            VStack(spacing: 0) {
                ForEach(Array(pdfFiles.enumerated()), id: \.element.id) { index, file in
                    FileExportRow(
                        file: file,
                        index: index,
                        showPageRange: selectedExportMode == .customPages,
                        pageRange: Binding(
                            get: { pageRanges[file.id.uuidString] ?? "1-\(file.pageCount)" },
                            set: { pageRanges[file.id.uuidString] = $0 }
                        )
                    )
                    
                    if index < pdfFiles.count - 1 {
                        Divider()
                            .padding(.horizontal, 12)
                    }
                }
            }
            .background(Color(nsColor: .controlBackgroundColor))
            .cornerRadius(10)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
    
    private var outputSettingsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("输出设置")
                .font(.subheadline)
                .fontWeight(.medium)
            
            VStack(spacing: 12) {
                HStack(spacing: 12) {
                    Text("文件名:")
                        .frame(width: 70, alignment: .trailing)
                        .foregroundColor(.secondary)
                    
                    TextField("输入文件名", text: $outputFileName)
                        .textFieldStyle(.roundedBorder)
                        .onChange(of: outputFileName) { newValue in
                            if !newValue.lowercased().hasSuffix(".pdf") {
                                outputFileName = newValue + ".pdf"
                            }
                        }
                }
                
                HStack(spacing: 12) {
                    Text("输出目录:")
                        .frame(width: 70, alignment: .trailing)
                        .foregroundColor(.secondary)
                    
                    Text(outputDirectory?.path ?? "点击右侧按钮选择")
                        .font(.callout)
                        .foregroundColor(outputDirectory == nil ? .tertiary : .primary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                    
                    Button(action: selectOutputDirectory) {
                        Image(systemName: "folder")
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(10)
    }
    
    private var summarySection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("导出摘要")
                .font(.subheadline)
                .fontWeight(.medium)
            
            HStack(spacing: 20) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("文件数量")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(pdfFiles.count) 个")
                        .font(.headline)
                }
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("总页数")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(totalPages) 页")
                        .font(.headline)
                }
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("输出位置")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(outputDirectory?.lastPathComponent ?? "未选择")
                        .font(.headline)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(nsColor: .controlBackgroundColor))
        .cornerRadius(10)
    }
    
    private var footerSection: some View {
        VStack(spacing: 0) {
            if isExporting {
                VStack(spacing: 8) {
                    ProgressView(value: exportProgress) {
                        Text("正在合并 PDF...")
                            .font(.subheadline)
                    }
                    .progressViewStyle(.linear)
                }
                .padding(.horizontal)
            }
            
            if let error = errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.red)
                    Text(error)
                        .font(.subheadline)
                        .foregroundColor(.red)
                }
                .padding()
            }
            
            HStack {
                Spacer()
                
                Button(action: { dismiss() }) {
                    Text("取消")
                        .frame(width: 80)
                }
                .buttonStyle(.bordered)
                .keyboardShortcut(.cancelAction)
                .disabled(isExporting)
                
                Button(action: performExport) {
                    HStack(spacing: 6) {
                        Image(systemName: "square.and.arrow.up.fill")
                        Text(isExporting ? "导出中..." : "开始导出")
                    }
                    .frame(width: 120)
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(!canExport || isExporting)
            }
            .padding()
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }
    
    private var successSheet: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundColor(.green)
            
            Text("导出成功！")
                .font(.headline)
            
            Text(outputDirectory?.appendingPathComponent(outputFileName).path ?? "")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            HStack(spacing: 12) {
                Button("在访达中显示") {
                    if let url = outputDirectory?.appendingPathComponent(outputFileName) {
                        NSWorkspace.shared.activateFileViewerSelecting([url])
                    }
                }
                
                Button("完成") {
                    showSuccess = false
                    dismiss()
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding()
        .frame(width: 400, height: 280)
    }
    
    private var canExport: Bool {
        !pdfFiles.isEmpty && outputDirectory != nil && !outputFileName.isEmpty
    }
    
    private var totalPages: Int {
        if selectedExportMode == .mergeAll {
            return pdfFiles.reduce(0) { $0 + $1.pageCount }
        } else {
            return pdfFiles.reduce(0) { total, file in
                let rangeString = pageRanges[file.id.uuidString] ?? "1-\(file.pageCount)"
                return total + countPages(from: rangeString, maxPages: file.pageCount)
            }
        }
    }
    
    private func initializePageRanges() {
        for file in pdfFiles {
            pageRanges[file.id.uuidString] = "1-\(file.pageCount)"
        }
    }
    
    private func selectOutputDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        
        if panel.runModal() == .OK, let url = panel.url {
            outputDirectory = url
        }
    }
    
    private func performExport() {
        guard let outputDir = outputDirectory else { return }
        
        isExporting = true
        exportProgress = 0
        errorMessage = nil
        
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let outputURL = outputDir.appendingPathComponent(outputFileName)
                
                if FileManager.default.fileExists(atPath: outputURL.path) {
                    try FileManager.default.removeItem(at: outputURL)
                }
                
                DispatchQueue.main.async {
                    exportProgress = 0.2
                }
                
                if selectedExportMode == .mergeAll {
                    try self.merger.merge(pdfFiles: pdfFiles, to: outputURL)
                } else {
                    let ranges = parsePageRanges()
                    try self.merger.merge(pdfFiles: pdfFiles, pageRanges: ranges, to: outputURL)
                }
                
                DispatchQueue.main.async {
                    exportProgress = 1.0
                    isExporting = false
                    showSuccess = true
                }
            } catch {
                DispatchQueue.main.async {
                    isExporting = false
                    errorMessage = error.localizedDescription
                }
            }
        }
    }
    
    private func parsePageRanges() -> [String: ClosedRange<Int>] {
        var result: [String: ClosedRange<Int>] = [:]
        
        for file in pdfFiles {
            guard let rangeString = pageRanges[file.id.uuidString] else {
                result[file.id.uuidString] = 1...file.pageCount
                continue
            }
            
            let range = parseRange(from: rangeString, maxPages: file.pageCount)
            result[file.id.uuidString] = range
        }
        
        return result
    }
    
    private func parseRange(from string: String, maxPages: Int) -> ClosedRange<Int> {
        let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
        
        if trimmed.contains("-") {
            let parts = trimmed.split(separator: "-")
            if parts.count == 2 {
                let start = Int(parts[0].trimmingCharacters(in: .whitespaces)) ?? 1
                let end = Int(parts[1].trimmingCharacters(in: .whitespaces)) ?? maxPages
                return max(1, start)...min(maxPages, end)
            }
        }
        
        if let singlePage = Int(trimmed) {
            let page = max(1, min(maxPages, singlePage))
            return page...page
        }
        
        return 1...maxPages
    }
    
    private func countPages(from string: String, maxPages: Int) -> Int {
        let range = parseRange(from: string, maxPages: maxPages)
        return range.count
    }
}

enum ExportMode {
    case mergeAll
    case customPages
}

struct FileExportRow: View {
    let file: PDFFile
    let index: Int
    let showPageRange: Bool
    @Binding var pageRange: String
    
    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 12) {
                Text("\(index + 1)")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .frame(width: 20)
                
                Image(systemName: "doc.text.fill")
                    .foregroundColor(.red)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text(file.name)
                        .font(.body)
                        .lineLimit(1)
                    
                    Text("\(file.pageCount) 页")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
            }
            
            if showPageRange {
                HStack(spacing: 8) {
                    Text("页码范围:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .frame(width: 65, alignment: .trailing)
                    
                    TextField("例如: 1-5 或 3", text: $pageRange)
                        .textFieldStyle(.roundedBorder)
                        .font(.callout)
                    
                    Text("(共 \(file.pageCount) 页)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.leading, 32)
            }
        }
        .padding(.vertical, 10)
        .padding(.horizontal, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

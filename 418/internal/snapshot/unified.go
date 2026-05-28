package snapshot

import (
	"fmt"
	"hash/fnv"
	"io"
	"os"
	"path/filepath"
	"time"
)

type SnapshotKind string

const (
	KindNodeJSV8Snapshot SnapshotKind = "nodejs_v8_snapshot"
	KindPythonBytecode   SnapshotKind = "python_pyc"
	KindJavaAppCDS       SnapshotKind = "java_appcds"
	KindGoPlugin         SnapshotKind = "go_plugin"
	KindGenericFile      SnapshotKind = "generic_file"
)

type Language string

const (
	LangNodeJS Language = "nodejs"
	LangPython Language = "python"
	LangJava   Language = "java"
	LangGo     Language = "go"
	LangDotNet Language = "dotnet"
	LangRuby   Language = "ruby"
)

type Format struct {
	Kind       SnapshotKind `json:"kind"`
	Language   Language     `json:"language"`
	RuntimeVer string       `json:"runtime_version"`
	Tool       string       `json:"tool"`
}

type FileEntry struct {
	Path       string    `json:"path"`
	SizeBytes  int64     `json:"size_bytes"`
	Checksum   string    `json:"checksum"`
	ModifiedAt time.Time `json:"modified_at"`
}

type Snapshot interface {
	Format() Format
	Entries() []FileEntry
	TotalSize() int64
	LoadTime() time.Duration
	Save(dir string) error
}

type BaseSnapshot struct {
	Fmt        Format        `json:"format"`
	Files      []FileEntry   `json:"files"`
	EstLoad    time.Duration `json:"estimated_load_ms"`
	SourceHash string        `json:"source_hash"`
}

func (b *BaseSnapshot) Format() Format          { return b.Fmt }
func (b *BaseSnapshot) Entries() []FileEntry    { return b.Files }
func (b *BaseSnapshot) LoadTime() time.Duration { return b.EstLoad }

func (b *BaseSnapshot) TotalSize() int64 {
	var total int64
	for _, f := range b.Files {
		total += f.SizeBytes
	}
	return total
}

func (b *BaseSnapshot) Save(dir string) error {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	meta := filepath.Join(dir, "snapshot.meta")
	f, err := os.Create(meta)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = fmt.Fprintf(f, "kind=%s\nlanguage=%s\nruntime=%s\nentries=%d\n",
		b.Fmt.Kind, b.Fmt.Language, b.Fmt.RuntimeVer, len(b.Files))
	return err
}

type NodeJSSnapshot struct {
	BaseSnapshot
	BlobPath   string `json:"blob_path"`
	ScriptHash string `json:"script_hash"`
}

func NewNodeJSSnapshot(runtimeVer, sourceHash string, blobPath string, entries []FileEntry) *NodeJSSnapshot {
	return &NodeJSSnapshot{
		BaseSnapshot: BaseSnapshot{
			Fmt: Format{
				Kind:       KindNodeJSV8Snapshot,
				Language:   LangNodeJS,
				RuntimeVer: runtimeVer,
				Tool:       "mksnapshot",
			},
			Files:      entries,
			EstLoad:    time.Duration(float64(len(entries))*50) * time.Microsecond,
			SourceHash: sourceHash,
		},
		BlobPath:   blobPath,
		ScriptHash: sourceHash,
	}
}

type PythonBytecodeSnapshot struct {
	BaseSnapshot
	PycDir      string `json:"pyc_dir"`
	PyVersion   string `json:"py_version"`
	Optimize    int    `json:"optimize_level"`
}

func NewPythonBytecodeSnapshot(pyVersion string, optimize int, pycDir string, entries []FileEntry) *PythonBytecodeSnapshot {
	return &PythonBytecodeSnapshot{
		BaseSnapshot: BaseSnapshot{
			Fmt: Format{
				Kind:       KindPythonBytecode,
				Language:   LangPython,
				RuntimeVer: pyVersion,
				Tool:       "compileall",
			},
			Files:      entries,
			EstLoad:    time.Duration(float64(len(entries))*30) * time.Microsecond,
		},
		PycDir:    pycDir,
		PyVersion: pyVersion,
		Optimize:  optimize,
	}
}

type JavaCDSSnapshot struct {
	BaseSnapshot
	JSAFile   string `json:"jsa_file"`
	ClassList string `json:"class_list"`
	JDKVer    string `json:"jdk_version"`
}

func NewJavaCDSSnapshot(jdkVer, jsaFile, classList string, entries []FileEntry) *JavaCDSSnapshot {
	return &JavaCDSSnapshot{
		BaseSnapshot: BaseSnapshot{
			Fmt: Format{
				Kind:       KindJavaAppCDS,
				Language:   LangJava,
				RuntimeVer: jdkVer,
				Tool:       "java -Xshare:dump",
			},
			Files:   entries,
			EstLoad: time.Duration(float64(len(entries))*100) * time.Microsecond,
		},
		JSAFile:   jsaFile,
		ClassList: classList,
		JDKVer:    jdkVer,
	}
}

type GoPluginSnapshot struct {
	BaseSnapshot
	PluginPath string `json:"plugin_path"`
	GoVersion  string `json:"go_version"`
}

func NewGoPluginSnapshot(goVersion, pluginPath string, entries []FileEntry) *GoPluginSnapshot {
	return &GoPluginSnapshot{
		BaseSnapshot: BaseSnapshot{
			Fmt: Format{
				Kind:       KindGoPlugin,
				Language:   LangGo,
				RuntimeVer: goVersion,
				Tool:       "go build -buildmode=plugin",
			},
			Files:   entries,
			EstLoad: time.Duration(float64(len(entries))*20) * time.Microsecond,
		},
		PluginPath: pluginPath,
		GoVersion:  goVersion,
	}
}

type GenericSnapshot struct {
	BaseSnapshot
	RootDir string `json:"root_dir"`
}

func NewGenericSnapshot(lang Language, runtimeVer string, rootDir string, entries []FileEntry) *GenericSnapshot {
	return &GenericSnapshot{
		BaseSnapshot: BaseSnapshot{
			Fmt: Format{
				Kind:       KindGenericFile,
				Language:   lang,
				RuntimeVer: runtimeVer,
				Tool:       "rsync",
			},
			Files:   entries,
			EstLoad: time.Duration(float64(len(entries))*25) * time.Microsecond,
		},
		RootDir: rootDir,
	}
}

type Builder interface {
	Build(sourceDir string) (Snapshot, error)
	Detect(sourceDir string) bool
}

type UnifiedBuilder struct {
	builders map[Language]Builder
}

func NewUnifiedBuilder() *UnifiedBuilder {
	return &UnifiedBuilder{
		builders: map[Language]Builder{},
	}
}

func (u *UnifiedBuilder) Register(lang Language, b Builder) {
	u.builders[lang] = b
}

func (u *UnifiedBuilder) Build(lang Language, sourceDir string) (Snapshot, error) {
	b, ok := u.builders[lang]
	if !ok {
		return nil, fmt.Errorf("no builder registered for %s", lang)
	}
	return b.Build(sourceDir)
}

type BuildResult struct {
	ID           string        `json:"id"`
	Snapshot     Snapshot      `json:"snapshot"`
	Format       Format        `json:"format"`
	BuildTime    time.Duration `json:"build_ms"`
	TotalSize    int64         `json:"total_size_bytes"`
	OriginalSize int64         `json:"original_size_bytes"`
	Ratio        float64       `json:"ratio"`
}

func BuildForLanguage(lang Language, runtimeVer, sourceDir, cacheDir string) (*BuildResult, error) {
	entries, origSize, err := scanSource(sourceDir)
	if err != nil {
		return nil, err
	}
	var s Snapshot
	start := time.Now()
	switch lang {
	case LangNodeJS:
		s = NewNodeJSSnapshot(runtimeVer, hashString(sourceDir+runtimeVer), filepath.Join(cacheDir, "snapshot_blob.bin"), entries)
	case LangPython:
		s = NewPythonBytecodeSnapshot(runtimeVer, 2, filepath.Join(cacheDir, "__pycache__"), entries)
	case LangJava:
		s = NewJavaCDSSnapshot(runtimeVer, filepath.Join(cacheDir, "app.jsa"), filepath.Join(cacheDir, "classes.lst"), entries)
	case LangGo:
		s = NewGoPluginSnapshot(runtimeVer, filepath.Join(cacheDir, "fn.so"), entries)
	default:
		s = NewGenericSnapshot(lang, runtimeVer, cacheDir, entries)
	}
	if err := s.Save(cacheDir); err != nil {
		return nil, err
	}
	buildDur := time.Since(start)
	return &BuildResult{
		ID:           fmt.Sprintf("%s-%x", lang, hashString(sourceDir+runtimeVer)),
		Snapshot:     s,
		Format:       s.Format(),
		BuildTime:    buildDur,
		TotalSize:    s.TotalSize(),
		OriginalSize: origSize,
		Ratio:        float64(s.TotalSize()) / float64(maxInt(origSize, 1)),
	}, nil
}

func scanSource(sourceDir string) ([]FileEntry, int64, error) {
	var entries []FileEntry
	var total int64
	err := filepath.Walk(sourceDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if info.IsDir() {
			return nil
		}
		size := info.Size()
		total += size
		entries = append(entries, FileEntry{
			Path:       path,
			SizeBytes:  size,
			Checksum:   fmt.Sprintf("%x", hashString(path+fmt.Sprintf("%d", size))),
			ModifiedAt: info.ModTime(),
		})
		return nil
	})
	return entries, total, err
}

func hashString(s string) uint64 {
	h := fnv.New64a()
	io.WriteString(h, s)
	return h.Sum64()
}

func maxInt(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

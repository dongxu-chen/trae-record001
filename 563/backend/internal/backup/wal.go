package backup

import (
	"encoding/binary"
	"fmt"
	"hash/crc32"
	"io"
	"os"
	"path/filepath"
	"time"
)

const (
	WALMagic   = 0x41574C45
	WALVersion = 2

	RecordTypeSession    = 1
	RecordTypeState      = 2
	RecordTypeCRC        = 3
	RecordTypeSnapshot   = 4
	RecordTypeCommit     = 5

	PageBytes = 8 * 1024
)

type WALRecord struct {
	Type      byte
	Index     int64
	Term      int64
	Data      []byte
	Timestamp time.Time
	CRC       uint32
}

type WALHeader struct {
	Magic    uint32
	Version  uint32
	CRC      uint32
	Index    int64
	Term     int64
	Cluster  string
	CreateAt time.Time
}

type WALReader struct {
	filePath string
	file     *os.File
	decoder  *WALDecoder
}

type WALDecoder struct {
	r io.Reader
}

func NewWALReader(filePath string) *WALReader {
	return &WALReader{
		filePath: filePath,
	}
}

func NewWALDecoder(r io.Reader) *WALDecoder {
	return &WALDecoder{r: r}
}

func (r *WALReader) Open() error {
	f, err := os.Open(r.filePath)
	if err != nil {
		return fmt.Errorf("failed to open WAL file: %w", err)
	}
	r.file = f
	r.decoder = NewWALDecoder(f)
	return nil
}

func (r *WALReader) Close() error {
	if r.file != nil {
		return r.file.Close()
	}
	return nil
}

func (r *WALReader) ReadAll() ([]*WALRecord, error) {
	var records []*WALRecord

	for {
		rec, err := r.decoder.Decode()
		if err == io.EOF {
			break
		}
		if err != nil {
			if err == io.ErrUnexpectedEOF {
				break
			}
			return nil, fmt.Errorf("failed to decode WAL record: %w", err)
		}
		records = append(records, rec)
	}

	return records, nil
}

func (r *WALReader) ReadRange(startIndex, endIndex int64) ([]*WALRecord, error) {
	all, err := r.ReadAll()
	if err != nil {
		return nil, err
	}

	var filtered []*WALRecord
	for _, rec := range all {
		if rec.Index >= startIndex && rec.Index <= endIndex {
			filtered = append(filtered, rec)
		}
	}

	return filtered, nil
}

func (r *WALReader) ReadFromIndex(startIndex int64) ([]*WALRecord, error) {
	all, err := r.ReadAll()
	if err != nil {
		return nil, err
	}

	var filtered []*WALRecord
	for _, rec := range all {
		if rec.Index >= startIndex {
			filtered = append(filtered, rec)
		}
	}

	return filtered, nil
}

func (r *WALReader) ReadFromTimestamp(after time.Time) ([]*WALRecord, error) {
	all, err := r.ReadAll()
	if err != nil {
		return nil, err
	}

	var filtered []*WALRecord
	for _, rec := range all {
		if rec.Timestamp.After(after) || rec.Timestamp.Equal(after) {
			filtered = append(filtered, rec)
		}
	}

	return filtered, nil
}

func (d *WALDecoder) Decode() (*WALRecord, error) {
	var lenBuf [4]byte
	if _, err := io.ReadFull(d.r, lenBuf[:]); err != nil {
		return nil, err
	}

	padLen := int(lenBuf[0])
	if padLen > 0 {
		pad := make([]byte, padLen)
		if _, err := io.ReadFull(d.r, pad); err != nil {
			return nil, err
		}
	}

	var header [24]byte
	if _, err := io.ReadFull(d.r, header[:]); err != nil {
		return nil, err
	}

	recType := header[0]
	index := int64(binary.BigEndian.Uint64(header[1:9]))
	term := int64(binary.BigEndian.Uint64(header[9:17]))
	dataLen := int64(binary.BigEndian.Uint64(header[17:25]))

	data := make([]byte, dataLen)
	if dataLen > 0 {
		if _, err := io.ReadFull(d.r, data); err != nil {
			return nil, err
		}
	}

	var crcBuf [4]byte
	if _, err := io.ReadFull(d.r, crcBuf[:]); err != nil {
		return nil, err
	}
	crc := binary.BigEndian.Uint32(crcBuf[:])

	return &WALRecord{
		Type:      recType,
		Index:     index,
		Term:      term,
		Data:      data,
		Timestamp: time.Now(),
		CRC:       crc,
	}, nil
}

type WALWriter struct {
	filePath string
	file     *os.File
	encoder  *WALEncoder
}

type WALEncoder struct {
	w io.Writer
}

func NewWALWriter(filePath string) *WALWriter {
	return &WALWriter{
		filePath: filePath,
	}
}

func NewWALEncoder(w io.Writer) *WALEncoder {
	return &WALEncoder{w: w}
}

func (w *WALWriter) Create() error {
	dir := filepath.Dir(w.filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create WAL directory: %w", err)
	}

	f, err := os.Create(w.filePath)
	if err != nil {
		return fmt.Errorf("failed to create WAL file: %w", err)
	}

	w.file = f
	w.encoder = NewWALEncoder(f)
	return nil
}

func (w *WALWriter) Close() error {
	if w.file != nil {
		return w.file.Close()
	}
	return nil
}

func (w *WALWriter) WriteHeader(header *WALHeader) error {
	var buf [28]byte
	binary.BigEndian.PutUint32(buf[0:4], header.Magic)
	binary.BigEndian.PutUint32(buf[4:8], header.Version)
	binary.BigEndian.PutUint32(buf[8:12], header.CRC)
	binary.BigEndian.PutUint64(buf[12:20], uint64(header.Index))
	binary.BigEndian.PutUint64(buf[20:28], uint64(header.Term))

	if _, err := w.file.Write(buf[:]); err != nil {
		return fmt.Errorf("failed to write WAL header: %w", err)
	}

	return nil
}

func (w *WALWriter) WriteRecord(rec *WALRecord) error {
	return w.encoder.Encode(rec)
}

func (w *WALWriter) WriteRecords(records []*WALRecord) error {
	for _, rec := range records {
		if err := w.encoder.Encode(rec); err != nil {
			return err
		}
	}
	return nil
}

func (e *WALEncoder) Encode(rec *WALRecord) error {
	var header [24]byte
	header[0] = rec.Type
	binary.BigEndian.PutUint64(header[1:9], uint64(rec.Index))
	binary.BigEndian.PutUint64(header[9:17], uint64(rec.Term))
	binary.BigEndian.PutUint64(header[17:25], uint64(len(rec.Data)))

	padLen := PageBytes - ((4 + len(header) + len(rec.Data) + 4) % PageBytes)
	if padLen == PageBytes {
		padLen = 0
	}

	lenBuf := [1]byte{byte(padLen)}
	if _, err := e.w.Write(lenBuf[:]); err != nil {
		return err
	}

	if padLen > 0 {
		pad := make([]byte, padLen)
		if _, err := e.w.Write(pad); err != nil {
			return err
		}
	}

	if _, err := e.w.Write(header[:]); err != nil {
		return err
	}

	if len(rec.Data) > 0 {
		if _, err := e.w.Write(rec.Data); err != nil {
			return err
		}
	}

	crc := crc32.ChecksumIEEE(append(header[:], rec.Data...))
	var crcBuf [4]byte
	binary.BigEndian.PutUint32(crcBuf[:], crc)
	if _, err := e.w.Write(crcBuf[:]); err != nil {
		return err
	}

	return nil
}

type WALEntry struct {
	Index     int64
	Term      int64
	OpType    string
	Key       string
	Value     []byte
	PrevValue []byte
	Timestamp time.Time
}

type WALSegment struct {
	StartIndex int64
	EndIndex   int64
	StartTime  time.Time
	EndTime    time.Time
	Records    []*WALRecord
	Checksum   string
}

func FindWALFiles(dataDir string) ([]string, error) {
	walDir := filepath.Join(dataDir, "member", "wal")
	entries, err := os.ReadDir(walDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read WAL directory: %w", err)
	}

	var files []string
	for _, entry := range entries {
		if !entry.IsDir() && filepath.Ext(entry.Name()) == ".wal" {
			files = append(files, filepath.Join(walDir, entry.Name()))
		}
	}

	return files, nil
}

func CollectWALSegments(dataDir string, sinceIndex int64) ([]*WALSegment, error) {
	files, err := FindWALFiles(dataDir)
	if err != nil {
		return nil, err
	}

	var segments []*WALSegment
	for _, f := range files {
		reader := NewWALReader(f)
		if err := reader.Open(); err != nil {
			continue
		}

		records, err := reader.ReadFromIndex(sinceIndex)
		reader.Close()
		if err != nil {
			continue
		}

		if len(records) == 0 {
			continue
		}

		segment := &WALSegment{
			StartIndex: records[0].Index,
			EndIndex:   records[len(records)-1].Index,
			StartTime:  records[0].Timestamp,
			EndTime:    records[len(records)-1].Timestamp,
			Records:    records,
		}

		segments = append(segments, segment)
	}

	return segments, nil
}

type WALReplayer struct {
	segments []*WALSegment
}

func NewWALReplayer(segments []*WALSegment) *WALReplayer {
	return &WALReplayer{segments: segments}
}

func (r *WALReplayer) ReplayUpToIndex(targetIndex int64) []*WALRecord {
	var result []*WALRecord
	for _, seg := range r.segments {
		if seg.StartIndex > targetIndex {
			break
		}
		for _, rec := range seg.Records {
			if rec.Index <= targetIndex {
				result = append(result, rec)
			}
		}
	}
	return result
}

func (r *WALReplayer) ReplayUpToTime(targetTime time.Time) []*WALRecord {
	var result []*WALRecord
	for _, seg := range r.segments {
		if seg.StartTime.After(targetTime) {
			break
		}
		for _, rec := range seg.Records {
			if !rec.Timestamp.After(targetTime) {
				result = append(result, rec)
			}
		}
	}
	return result
}

func (r *WALReplayer) ReplayRange(startIndex, endIndex int64) []*WALRecord {
	var result []*WALRecord
	for _, seg := range r.segments {
		if seg.EndIndex < startIndex {
			continue
		}
		if seg.StartIndex > endIndex {
			break
		}
		for _, rec := range seg.Records {
			if rec.Index >= startIndex && rec.Index <= endIndex {
				result = append(result, rec)
			}
		}
	}
	return result
}

package scanner

import (
	"bufio"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
)

type PasswordEntry struct {
	Password   string   `json:"password"`
	Hash       string   `json:"hash"`
	Source     string   `json:"source"`
	Count      int      `json:"count"`
	Categories []string `json:"categories"`
	LastSeen   string   `json:"last_seen"`
}

type PasswordDB struct {
	Version     string                  `json:"version"`
	LastUpdated string                  `json:"last_updated"`
	TotalCount  int                     `json:"total_count"`
	Passwords   map[string]PasswordEntry `json:"passwords"`
	Checksum    string                  `json:"checksum"`
}

type PasswordManager struct {
	db            *PasswordDB
	cacheDir      string
	customDir     string
	mu            sync.RWMutex
	categories    map[string]bool
	loadedSources map[string]bool
}

var commonDefaultPasswords = []PasswordEntry{
	{Password: "", Source: "builtin", Count: 999999, Categories: []string{"default", "blank"}},
	{Password: "root", Source: "builtin", Count: 999999, Categories: []string{"default", "username"}},
	{Password: "password", Source: "builtin", Count: 999998, Categories: []string{"common", "default"}},
	{Password: "123456", Source: "builtin", Count: 999997, Categories: []string{"common", "numeric"}},
	{Password: "12345678", Source: "builtin", Count: 999996, Categories: []string{"common", "numeric"}},
	{Password: "admin", Source: "builtin", Count: 999995, Categories: []string{"default", "username"}},
	{Password: "mysql", Source: "builtin", Count: 999994, Categories: []string{"default", "service"}},
	{Password: "123456789", Source: "builtin", Count: 999993, Categories: []string{"common", "numeric"}},
	{Password: "qwerty", Source: "builtin", Count: 999992, Categories: []string{"common", "keyboard"}},
	{Password: "123123", Source: "builtin", Count: 999991, Categories: []string{"common", "numeric"}},
	{Password: "12345", Source: "builtin", Count: 999990, Categories: []string{"common", "numeric"}},
	{Password: "1234", Source: "builtin", Count: 999989, Categories: []string{"common", "numeric"}},
	{Password: "pass", Source: "builtin", Count: 999988, Categories: []string{"common", "short"}},
	{Password: "toor", Source: "builtin", Count: 999987, Categories: []string{"default", "reverse"}},
	{Password: "letmein", Source: "builtin", Count: 999986, Categories: []string{"common", "phrase"}},
	{Password: "welcome", Source: "builtin", Count: 999985, Categories: []string{"common", "phrase"}},
	{Password: "monkey", Source: "builtin", Count: 999984, Categories: []string{"common", "word"}},
	{Password: "dragon", Source: "builtin", Count: 999983, Categories: []string{"common", "word"}},
	{Password: "master", Source: "builtin", Count: 999982, Categories: []string{"common", "word"}},
	{Password: "killer", Source: "builtin", Count: 999981, Categories: []string{"common", "word"}},
}

var defaultServicePasswords = map[string][]string{
	"mysql":    {"root", "", "mysql", "admin", "password", "123456", "12345678", "test"},
	"redis":    {"", "foobared", "redis", "password", "123456", "admin"},
	"postgres": {"postgres", "", "admin", "password", "123456"},
	"mssql":    {"sa", "", "admin", "password", "123456"},
	"oracle":   {"sys", "system", "scott", "tiger", "oracle", "password"},
	"ssh":      {"root", "admin", "user", "test", "guest"},
	"ftp":      {"ftp", "anonymous", "root", "admin", "user"},
	"telnet":   {"root", "admin", "user", "guest"},
}

func NewPasswordManager() *PasswordManager {
	cacheDir := getPasswordCacheDir()
	customDir := filepath.Join(cacheDir, "custom")
	os.MkdirAll(customDir, 0755)

	return &PasswordManager{
		cacheDir:      cacheDir,
		customDir:     customDir,
		categories:    make(map[string]bool),
		loadedSources: make(map[string]bool),
	}
}

func getPasswordCacheDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	cacheDir := filepath.Join(home, ".portscanner", "passwords")
	os.MkdirAll(cacheDir, 0755)
	return cacheDir
}

func (pm *PasswordManager) Load() error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	dbPath := filepath.Join(pm.cacheDir, "passwords.json")

	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		return pm.initDefaultDB()
	}

	data, err := os.ReadFile(dbPath)
	if err != nil {
		return err
	}

	var db PasswordDB
	if err := json.Unmarshal(data, &db); err != nil {
		return pm.initDefaultDB()
	}

	pm.db = &db

	pm.loadCustomDictionaries()

	for _, entry := range pm.db.Passwords {
		for _, cat := range entry.Categories {
			pm.categories[cat] = true
		}
		pm.loadedSources[entry.Source] = true
	}

	return nil
}

func (pm *PasswordManager) initDefaultDB() error {
	passwords := make(map[string]PasswordEntry)
	for _, entry := range commonDefaultPasswords {
		entry.Hash = calculatePasswordHash(entry.Password)
		passwords[entry.Password] = entry
	}

	db := &PasswordDB{
		Version:     "1.0.0",
		LastUpdated: "2024-01-15",
		TotalCount:  len(passwords),
		Passwords:   passwords,
	}

	checksum := calculatePasswordDBChecksum(db)
	db.Checksum = checksum

	pm.db = db
	return pm.save()
}

func calculatePasswordHash(password string) string {
	hash := sha256.Sum256([]byte(password))
	return fmt.Sprintf("%x", hash)
}

func calculatePasswordDBChecksum(db *PasswordDB) string {
	var passwords []string
	for pwd := range db.Passwords {
		passwords = append(passwords, pwd)
	}
	sort.Strings(passwords)
	data := strings.Join(passwords, "|")
	hash := sha256.Sum256([]byte(data))
	return fmt.Sprintf("%x", hash)
}

func (pm *PasswordManager) save() error {
	dbPath := filepath.Join(pm.cacheDir, "passwords.json")
	data, err := json.MarshalIndent(pm.db, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(dbPath, data, 0644)
}

func (pm *PasswordManager) loadCustomDictionaries() error {
	files, err := os.ReadDir(pm.customDir)
	if err != nil {
		return err
	}

	for _, file := range files {
		if file.IsDir() {
			continue
		}

		ext := filepath.Ext(file.Name())
		if ext != ".txt" && ext != ".dict" {
			continue
		}

		sourceName := strings.TrimSuffix(file.Name(), ext)
		if pm.loadedSources[sourceName] {
			continue
		}

		filePath := filepath.Join(pm.customDir, file.Name())
		if err := pm.ImportDictionary(filePath, sourceName); err != nil {
			fmt.Printf("⚠️  导入字典 %s 失败: %v\n", file.Name(), err)
		}
	}

	return nil
}

func (pm *PasswordManager) ImportDictionary(filename, source string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	pm.mu.Lock()
	defer pm.mu.Unlock()

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)

	count := 0
	for scanner.Scan() {
		password := strings.TrimSpace(scanner.Text())
		if password == "" || strings.HasPrefix(password, "#") {
			continue
		}

		if _, exists := pm.db.Passwords[password]; !exists {
			entry := PasswordEntry{
				Password:   password,
				Hash:       calculatePasswordHash(password),
				Source:     source,
				Count:      1,
				Categories: []string{"custom", source},
				LastSeen:   "imported",
			}
			pm.db.Passwords[password] = entry
			count++
		} else {
			entry := pm.db.Passwords[password]
			entry.Count++
			if !containsString(entry.Categories, source) {
				entry.Categories = append(entry.Categories, source)
			}
			pm.db.Passwords[password] = entry
		}
	}

	pm.loadedSources[source] = true
	pm.db.TotalCount = len(pm.db.Passwords)
	pm.db.Checksum = calculatePasswordDBChecksum(pm.db)

	if err := pm.save(); err != nil {
		return err
	}

	fmt.Printf("✅ 从 %s 导入了 %d 个密码\n", source, count)
	return nil
}

func (pm *PasswordManager) ImportLeakDB(filename, source string, categories []string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	pm.mu.Lock()
	defer pm.mu.Unlock()

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024*1024), 1024*1024)

	count := 0
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, ":", 2)
		password := parts[0]
		countStr := "1"
		if len(parts) == 2 {
			countStr = parts[1]
		}

		if password == "" {
			continue
		}

		countVal := 1
		fmt.Sscanf(countStr, "%d", &countVal)

		if _, exists := pm.db.Passwords[password]; !exists {
			entry := PasswordEntry{
				Password:   password,
				Hash:       calculatePasswordHash(password),
				Source:     source,
				Count:      countVal,
				Categories: append(categories, "leak", source),
				LastSeen:   "imported",
			}
			pm.db.Passwords[password] = entry
			count++
		} else {
			entry := pm.db.Passwords[password]
			entry.Count += countVal
			for _, cat := range append(categories, "leak") {
				if !containsString(entry.Categories, cat) {
					entry.Categories = append(entry.Categories, cat)
				}
			}
			pm.db.Passwords[password] = entry
		}
	}

	pm.loadedSources[source] = true
	pm.db.TotalCount = len(pm.db.Passwords)
	pm.db.Checksum = calculatePasswordDBChecksum(pm.db)

	if err := pm.save(); err != nil {
		return err
	}

	fmt.Printf("✅ 从泄露库 %s 导入了 %d 个密码\n", source, count)
	return nil
}

func (pm *PasswordManager) GetPasswordsForService(service string) []string {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	if pm.db == nil {
		pm.Load()
	}

	service = strings.ToLower(service)
	var passwords []string

	if servicePasswords, ok := defaultServicePasswords[service]; ok {
		passwords = append(passwords, servicePasswords...)
	}

	sortedPasswords := pm.getSortedPasswords()
	for _, entry := range sortedPasswords {
		if !containsString(passwords, entry.Password) {
			passwords = append(passwords, entry.Password)
		}
	}

	return passwords
}

func (pm *PasswordManager) GetPasswordsByCategories(categories []string, limit int) []string {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	if pm.db == nil {
		pm.Load()
	}

	var result []string
	sortedPasswords := pm.getSortedPasswords()

	for _, entry := range sortedPasswords {
		for _, cat := range categories {
			if containsString(entry.Categories, cat) {
				if !containsString(result, entry.Password) {
					result = append(result, entry.Password)
					if len(result) >= limit && limit > 0 {
						return result
					}
				}
				break
			}
		}
	}

	return result
}

func (pm *PasswordManager) getSortedPasswords() []PasswordEntry {
	var entries []PasswordEntry
	for _, entry := range pm.db.Passwords {
		entries = append(entries, entry)
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].Count > entries[j].Count
	})

	return entries
}

func (pm *PasswordManager) AddCustomPassword(password, source string, categories []string) error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	if pm.db == nil {
		pm.Load()
	}

	entry := PasswordEntry{
		Password:   password,
		Hash:       calculatePasswordHash(password),
		Source:     source,
		Count:      1,
		Categories: categories,
		LastSeen:   "manual",
	}

	if existing, exists := pm.db.Passwords[password]; exists {
		existing.Count++
		for _, cat := range categories {
			if !containsString(existing.Categories, cat) {
				existing.Categories = append(existing.Categories, cat)
			}
		}
		pm.db.Passwords[password] = existing
	} else {
		pm.db.Passwords[password] = entry
		pm.db.TotalCount++
	}

	pm.db.Checksum = calculatePasswordDBChecksum(pm.db)
	return pm.save()
}

func (pm *PasswordManager) GetDBInfo() map[string]interface{} {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	if pm.db == nil {
		pm.Load()
	}

	sources := make(map[string]int)
	categoryCounts := make(map[string]int)

	for _, entry := range pm.db.Passwords {
		sources[entry.Source]++
		for _, cat := range entry.Categories {
			categoryCounts[cat]++
		}
	}

	return map[string]interface{}{
		"version":      pm.db.Version,
		"last_updated": pm.db.LastUpdated,
		"total_count":  pm.db.TotalCount,
		"checksum":     pm.db.Checksum,
		"sources":      sources,
		"categories":   categoryCounts,
		"loaded_files": pm.loadedSources,
	}
}

func (pm *PasswordManager) ExportPasswords(filename string, categories []string) error {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	defer writer.Flush()

	sortedPasswords := pm.getSortedPasswords()

	for _, entry := range sortedPasswords {
		if len(categories) > 0 {
			matched := false
			for _, cat := range categories {
				if containsString(entry.Categories, cat) {
					matched = true
					break
				}
			}
			if !matched {
				continue
			}
		}

		fmt.Fprintf(writer, "%s:%d\n", entry.Password, entry.Count)
	}

	return nil
}

func (pm *PasswordManager) GeneratePasswordList(targetService string, minLength, maxLength, limit int) []string {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	if pm.db == nil {
		pm.Load()
	}

	var result []string
	seen := make(map[string]bool)

	servicePasswords := pm.GetPasswordsForService(targetService)
	for _, pwd := range servicePasswords {
		if len(pwd) >= minLength && len(pwd) <= maxLength && !seen[pwd] {
			result = append(result, pwd)
			seen[pwd] = true
			if len(result) >= limit {
				return result
			}
		}
	}

	if len(result) < limit {
		sortedPasswords := pm.getSortedPasswords()
		for _, entry := range sortedPasswords {
			pwd := entry.Password
			if len(pwd) >= minLength && len(pwd) <= maxLength && !seen[pwd] {
				result = append(result, pwd)
				seen[pwd] = true
				if len(result) >= limit {
					break
				}
			}
		}
	}

	return result
}

func (pm *PasswordManager) SearchPasswords(query string, limit int) []PasswordEntry {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	if pm.db == nil {
		pm.Load()
	}

	var results []PasswordEntry
	query = strings.ToLower(query)

	sortedPasswords := pm.getSortedPasswords()

	for _, entry := range sortedPasswords {
		if strings.Contains(strings.ToLower(entry.Password), query) {
			results = append(results, entry)
			if len(results) >= limit {
				break
			}
		}
	}

	return results
}

func containsString(slice []string, str string) bool {
	for _, s := range slice {
		if s == str {
			return true
		}
	}
	return false
}

func (pm *PasswordManager) ClearAll() error {
	pm.mu.Lock()
	defer pm.mu.Unlock()

	pm.initDefaultDB()

	pm.loadedSources = map[string]bool{"builtin": true}

	return nil
}

func (pm *PasswordManager) GetCustomDir() string {
	return pm.customDir
}

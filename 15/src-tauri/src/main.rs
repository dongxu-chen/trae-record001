#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

const PREVIEW_LINE_COUNT: usize = 3;
const PREVIEW_MAX_CHARS: usize = 200;
const MAX_SEARCH_RESULTS: usize = 100;

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Note {
    title: String,
    content: String,
    file_path: String,
    modified: String,
    preview: String,
    tags: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct IndexEntry {
    file_path: String,
    title: String,
    tags: Vec<String>,
    modified: String,
    preview: String,
    search_text: String,
}

#[derive(Debug, Serialize, Deserialize, Clone, Default)]
struct SearchIndex {
    entries: HashMap<String, IndexEntry>,
    tags_count: HashMap<String, usize>,
    last_updated: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct SearchResult {
    note: Note,
    score: f64,
    matched_fields: Vec<String>,
}

fn get_notes_directory() -> Result<PathBuf, String> {
    if let Some(document_dir) = dirs::document_dir() {
        let notes_dir = document_dir.join("MarkdownNotes");
        if !notes_dir.exists() {
            fs::create_dir_all(&notes_dir).map_err(|e| e.to_string())?;
        }
        Ok(notes_dir)
    } else {
        Err("无法找到文档目录".to_string())
    }
}

fn get_index_directory() -> Result<PathBuf, String> {
    let notes_dir = get_notes_directory()?;
    let index_dir = notes_dir.join(".index");
    if !index_dir.exists() {
        fs::create_dir_all(&index_dir).map_err(|e| e.to_string())?;
    }
    Ok(index_dir)
}

fn get_index_path() -> Result<PathBuf, String> {
    let index_dir = get_index_directory()?;
    Ok(index_dir.join("index.json"))
}

fn parse_frontmatter(content: &str) -> (HashMap<String, String>, &str) {
    let mut metadata = HashMap::new();
    let lines: Vec<&str> = content.lines().collect();
    
    if lines.len() < 3 || !lines[0].trim().eq("---") {
        return (metadata, content);
    }
    
    let mut end_idx = 1;
    let mut found_end = false;
    
    for (i, line) in lines.iter().skip(1).enumerate() {
        if line.trim().eq("---") {
            end_idx = i + 1;
            found_end = true;
            break;
        }
    }
    
    if !found_end {
        return (metadata, content);
    }
    
    for line in &lines[1..end_idx] {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Some(colon_pos) = trimmed.find(':') {
            let key = trimmed[..colon_pos].trim().to_lowercase();
            let value = trimmed[colon_pos + 1..].trim().to_string();
            metadata.insert(key, value);
        }
    }
    
    let remaining: String = lines[end_idx + 1..].join("\n");
    (metadata, Box::leak(remaining.into_boxed_str()))
}

fn extract_tags_from_content(content: &str) -> Vec<String> {
    let mut tags = HashSet::new();
    let re = regex::Regex::new(r"#([a-zA-Z_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5]*)").unwrap();
    
    for cap in re.captures_iter(content) {
        if let Some(tag) = cap.get(1) {
            tags.insert(tag.as_str().to_lowercase());
        }
    }
    
    tags.into_iter().collect()
}

fn parse_tags_from_metadata(metadata: &HashMap<String, String>) -> Vec<String> {
    let mut tags = Vec::new();
    
    if let Some(tags_str) = metadata.get("tags") {
        for part in tags_str.split([',', ';']) {
            let tag = part.trim().trim_matches(|c| c == '[' || c == ']' || c == '"' || c == '\'').to_lowercase();
            if !tag.is_empty() {
                tags.push(tag);
            }
        }
    }
    
    if let Some(tag_str) = metadata.get("tag") {
        for part in tag_str.split([',', ';']) {
            let tag = part.trim().trim_matches(|c| c == '[' || c == ']' || c == '"' || c == '\'').to_lowercase();
            if !tag.is_empty() {
                tags.push(tag);
            }
        }
    }
    
    tags
}

fn read_preview_lines(path: &Path, max_lines: usize) -> Result<Vec<String>, String> {
    let file = File::open(path).map_err(|e| e.to_string())?;
    let reader = BufReader::new(file);
    let mut lines = Vec::new();
    
    for (i, line) in reader.lines().enumerate() {
        if i >= max_lines {
            break;
        }
        match line {
            Ok(l) => lines.push(l),
            Err(e) => return Err(e.to_string()),
        }
    }
    
    Ok(lines)
}

fn extract_title_from_lines(lines: &[String], file_stem: &str, metadata: &HashMap<String, String>) -> String {
    if let Some(title) = metadata.get("title") {
        if !title.is_empty() {
            return title.clone();
        }
    }
    
    for line in lines {
        let trimmed = line.trim();
        if !trimmed.is_empty() && !trimmed.eq("---") {
            return trimmed
                .trim_start_matches('#')
                .trim()
                .to_string();
        }
    }
    file_stem.to_string()
}

fn build_preview_from_lines(lines: &[String]) -> String {
    let mut preview = String::new();
    let mut first_content_found = false;
    let mut in_frontmatter = false;
    let mut frontmatter_end = false;
    
    for line in lines {
        let trimmed = line.trim();
        
        if trimmed.eq("---") {
            if !in_frontmatter && !frontmatter_end {
                in_frontmatter = true;
                continue;
            } else if in_frontmatter {
                in_frontmatter = false;
                frontmatter_end = true;
                continue;
            }
        }
        
        if in_frontmatter {
            continue;
        }
        
        if !trimmed.is_empty() {
            if !first_content_found && trimmed.starts_with('#') {
                first_content_found = true;
                continue;
            }
            first_content_found = true;
            if !preview.is_empty() {
                preview.push(' ');
            }
            preview.push_str(trimmed);
            if preview.len() >= PREVIEW_MAX_CHARS {
                preview = preview.chars().take(PREVIEW_MAX_CHARS).collect();
                preview.push_str("...");
                break;
            }
        }
    }
    
    if preview.is_empty() {
        "暂无内容".to_string()
    } else {
        preview
    }
}

fn load_index() -> SearchIndex {
    if let Ok(index_path) = get_index_path() {
        if index_path.exists() {
            if let Ok(content) = fs::read_to_string(&index_path) {
                if let Ok(index) = serde_json::from_str::<SearchIndex>(&content) {
                    return index;
                }
            }
        }
    }
    SearchIndex::default()
}

fn save_index(index: &SearchIndex) -> Result<(), String> {
    let index_path = get_index_path()?;
    let json = serde_json::to_string_pretty(index).map_err(|e| e.to_string())?;
    fs::write(&index_path, json).map_err(|e| e.to_string())?;
    Ok(())
}

fn build_index() -> Result<SearchIndex, String> {
    let notes_dir = get_notes_directory()?;
    let mut index = SearchIndex::default();
    let mut tags_count: HashMap<String, usize> = HashMap::new();
    
    if notes_dir.exists() {
        for entry in fs::read_dir(&notes_dir).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let path = entry.path();
            
            if path.extension().map(|ext| ext == "md").unwrap_or(false) {
                if let Ok(content) = fs::read_to_string(&path) {
                    let (metadata, _content_body) = parse_frontmatter(&content);
                    
                    let file_stem = path
                        .file_stem()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .to_string();
                    
                    let lines: Vec<String> = content.lines().take(PREVIEW_LINE_COUNT + 5).map(|s| s.to_string()).collect();
                    let title = extract_title_from_lines(&lines, &file_stem, &metadata);
                    let preview = build_preview_from_lines(&lines);
                    
                    let mut tags = parse_tags_from_metadata(&metadata);
                    tags.extend(extract_tags_from_content(&content));
                    tags.sort();
                    tags.dedup();
                    
                    for tag in &tags {
                        *tags_count.entry(tag.clone()).or_insert(0) += 1;
                    }
                    
                    let search_text = format!("{} {} {} {}", 
                        title.to_lowercase(),
                        content.to_lowercase(),
                        tags.join(" "),
                        file_stem.to_lowercase()
                    );
                    
                    let metadata = fs::metadata(&path).map_err(|e| e.to_string())?;
                    let modified = metadata
                        .modified()
                        .ok()
                        .and_then(|t| {
                            t.duration_since(std::time::UNIX_EPOCH)
                                .ok()
                                .map(|d| d.as_secs().to_string())
                        })
                        .unwrap_or_else(|| "0".to_string());
                    
                    let file_path_str = path.to_string_lossy().to_string();
                    
                    index.entries.insert(file_path_str.clone(), IndexEntry {
                        file_path: file_path_str,
                        title,
                        tags,
                        modified,
                        preview,
                        search_text,
                    });
                }
            }
        }
    }
    
    index.tags_count = tags_count;
    index.last_updated = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string());
    
    save_index(&index)?;
    Ok(index)
}

fn note_from_index_entry(entry: &IndexEntry) -> Note {
    Note {
        title: entry.title.clone(),
        content: String::new(),
        file_path: entry.file_path.clone(),
        modified: entry.modified.clone(),
        preview: entry.preview.clone(),
        tags: entry.tags.clone(),
    }
}

#[tauri::command]
async fn list_notes() -> Result<Vec<Note>, String> {
    let mut index = load_index();
    
    if index.entries.is_empty() {
        index = build_index()?;
    }
    
    let mut notes: Vec<Note> = index.entries.values()
        .map(note_from_index_entry)
        .collect();
    
    notes.sort_by(|a, b| b.modified.cmp(&a.modified));
    Ok(notes)
}

#[tauri::command]
async fn read_note(file_path: String) -> Result<Note, String> {
    let path = Path::new(&file_path);
    let content = fs::read_to_string(path).map_err(|e| e.to_string())?;
    let metadata_fs = fs::metadata(path).map_err(|e| e.to_string())?;
    let modified = metadata_fs
        .modified()
        .ok()
        .and_then(|t| {
            t.duration_since(std::time::UNIX_EPOCH)
                .ok()
                .map(|d| d.as_secs().to_string())
        })
        .unwrap_or_else(|| "0".to_string());

    let (metadata, _) = parse_frontmatter(&content);
    let lines: Vec<String> = content.lines().take(PREVIEW_LINE_COUNT + 5).map(|s| s.to_string()).collect();
    let file_stem = path
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    let title = extract_title_from_lines(&lines, &file_stem, &metadata);
    let preview = build_preview_from_lines(&lines);
    
    let mut tags = parse_tags_from_metadata(&metadata);
    tags.extend(extract_tags_from_content(&content));
    tags.sort();
    tags.dedup();

    Ok(Note {
        title: if title.is_empty() { file_stem } else { title },
        content,
        preview,
        file_path: path.to_string_lossy().to_string(),
        modified,
        tags,
    })
}

#[tauri::command]
async fn save_note(title: String, content: String, file_path: Option<String>) -> Result<Note, String> {
    let notes_dir = get_notes_directory()?;
    
    let path = if let Some(fp) = file_path {
        PathBuf::from(fp)
    } else {
        let safe_title: String = title
            .chars()
            .map(|c| {
                if c.is_alphanumeric() || c == '-' || c == '_' || c == ' ' {
                    c
                } else {
                    '-'
                }
            })
            .collect();
        let safe_title = safe_title.trim();
        let file_name = if safe_title.is_empty() {
            format!("{}.md", chrono::Local::now().format("%Y%m%d%H%M%S"))
        } else {
            format!("{}.md", safe_title)
        };
        notes_dir.join(file_name)
    };

    fs::write(&path, &content).map_err(|e| e.to_string())?;

    let metadata_fs = fs::metadata(&path).map_err(|e| e.to_string())?;
    let modified = metadata_fs
        .modified()
        .ok()
        .and_then(|t| {
            t.duration_since(std::time::UNIX_EPOCH)
                .ok()
                .map(|d| d.as_secs().to_string())
        })
        .unwrap_or_else(|| "0".to_string());

    let (metadata, _) = parse_frontmatter(&content);
    let lines: Vec<String> = content.lines().take(PREVIEW_LINE_COUNT + 5).map(|s| s.to_string()).collect();
    let file_stem = path
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    let title_extracted = extract_title_from_lines(&lines, &file_stem, &metadata);
    let preview = build_preview_from_lines(&lines);
    
    let mut tags = parse_tags_from_metadata(&metadata);
    tags.extend(extract_tags_from_content(&content));
    tags.sort();
    tags.dedup();
    
    let mut index = load_index();
    let search_text = format!("{} {} {} {}", 
        title_extracted.to_lowercase(),
        content.to_lowercase(),
        tags.join(" "),
        file_stem.to_lowercase()
    );
    
    let file_path_str = path.to_string_lossy().to_string();
    index.entries.insert(file_path_str.clone(), IndexEntry {
        file_path: file_path_str.clone(),
        title: title_extracted.clone(),
        tags: tags.clone(),
        modified: modified.clone(),
        preview: preview.clone(),
        search_text,
    });
    
    let mut tags_count: HashMap<String, usize> = HashMap::new();
    for entry in index.entries.values() {
        for tag in &entry.tags {
            *tags_count.entry(tag.clone()).or_insert(0) += 1;
        }
    }
    index.tags_count = tags_count;
    save_index(&index)?;

    Ok(Note {
        title: if title_extracted.is_empty() { file_stem } else { title_extracted },
        content,
        preview,
        file_path: path.to_string_lossy().to_string(),
        modified,
        tags,
    })
}

#[tauri::command]
async fn delete_note(file_path: String) -> Result<(), String> {
    let path = Path::new(&file_path);
    if path.exists() {
        fs::remove_file(path).map_err(|e| e.to_string())?;
        
        let mut index = load_index();
        index.entries.remove(&file_path);
        
        let mut tags_count: HashMap<String, usize> = HashMap::new();
        for entry in index.entries.values() {
            for tag in &entry.tags {
                *tags_count.entry(tag.clone()).or_insert(0) += 1;
            }
        }
        index.tags_count = tags_count;
        save_index(&index)?;
    }
    Ok(())
}

#[tauri::command]
async fn create_new_note() -> Result<Note, String> {
    let notes_dir = get_notes_directory()?;
    let timestamp = chrono::Local::now().format("%Y%m%d%H%M%S").to_string();
    let file_name = format!("note-{}.md", timestamp);
    let path = notes_dir.join(&file_name);
    
    let default_content = "---\ntags:\n---\n\n# 新笔记\n\n在这里开始编写...\n";
    fs::write(&path, default_content).map_err(|e| e.to_string())?;

    let modified = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string());

    let note = Note {
        title: "新笔记".to_string(),
        content: default_content.to_string(),
        preview: "在这里开始编写...".to_string(),
        file_path: path.to_string_lossy().to_string(),
        modified,
        tags: Vec::new(),
    };
    
    let mut index = load_index();
    let file_path_str = path.to_string_lossy().to_string();
    let search_text = format!("新笔记 {} 在这里开始编写...", timestamp);
    index.entries.insert(file_path_str.clone(), IndexEntry {
        file_path: file_path_str,
        title: "新笔记".to_string(),
        tags: Vec::new(),
        modified: modified.clone(),
        preview: "在这里开始编写...".to_string(),
        search_text,
    });
    save_index(&index)?;
    
    Ok(note)
}

#[tauri::command]
async fn rebuild_index() -> Result<SearchIndex, String> {
    build_index()
}

#[tauri::command]
async fn get_all_tags() -> Result<Vec<(String, usize)>, String> {
    let index = load_index();
    let mut tags: Vec<(String, usize)> = index.tags_count.into_iter().collect();
    tags.sort_by(|a, b| b.1.cmp(&a.1));
    Ok(tags)
}

#[tauri::command]
async fn search_notes(query: String, tags_filter: Vec<String>) -> Result<Vec<Note>, String> {
    let index = load_index();
    let query_lower = query.to_lowercase();
    let tags_lower: Vec<String> = tags_filter.iter().map(|t| t.to_lowercase()).collect();
    
    let mut results: Vec<(f64, Note)> = Vec::new();
    
    for entry in index.entries.values() {
        if !tags_lower.is_empty() {
            let note_tags: HashSet<&str> = entry.tags.iter().map(|t| t.as_str()).collect();
            let all_match = tags_lower.iter().all(|t| note_tags.contains(t.as_str()));
            if !all_match {
                continue;
            }
        }
        
        let mut score = 0.0;
        
        if query_lower.is_empty() {
            score = 1.0;
        } else {
            let query_terms: Vec<&str> = query_lower.split_whitespace().collect();
            
            for term in &query_terms {
                if entry.search_text.contains(*term) {
                    score += 1.0;
                    
                    if entry.title.to_lowercase().contains(*term) {
                        score += 2.0;
                    }
                    if entry.tags.iter().any(|t| t.contains(*term)) {
                        score += 1.5;
                    }
                }
            }
            
            if let Some(pos) = entry.search_text.find(&query_lower) {
                score += 1.0 / (pos as f64 + 1.0);
            }
        }
        
        if score > 0.0 {
            results.push((score, note_from_index_entry(entry)));
        }
    }
    
    results.sort_by(|a, b| {
        b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| b.1.modified.cmp(&a.1.modified))
    });
    
    let notes: Vec<Note> = results.into_iter()
        .take(MAX_SEARCH_RESULTS)
        .map(|(_, note)| note)
        .collect();
    
    Ok(notes)
}

#[tauri::command]
async fn get_notes_by_tags(tags: Vec<String>) -> Result<Vec<Note>, String> {
    let index = load_index();
    let tags_lower: Vec<String> = tags.iter().map(|t| t.to_lowercase()).collect();
    
    let mut notes: Vec<Note> = Vec::new();
    
    for entry in index.entries.values() {
        let note_tags: HashSet<&str> = entry.tags.iter().map(|t| t.as_str()).collect();
        let all_match = tags_lower.iter().all(|t| note_tags.contains(t.as_str()));
        
        if all_match {
            notes.push(note_from_index_entry(entry));
        }
    }
    
    notes.sort_by(|a, b| b.modified.cmp(&a.modified));
    Ok(notes)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            list_notes,
            read_note,
            save_note,
            delete_note,
            create_new_note,
            rebuild_index,
            get_all_tags,
            search_notes,
            get_notes_by_tags
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

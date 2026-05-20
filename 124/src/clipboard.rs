use crate::models::{ClipboardContent, ContentType};

pub async fn read_clipboard() -> Result<ClipboardContent, String> {
    #[cfg(feature = "cli")]
    {
        Ok(ClipboardContent {
            content_type: ContentType::Text,
            data: b"CLI clipboard not implemented".to_vec(),
            text_preview: Some("CLI clipboard".to_string()),
            file_name: None,
            file_size: None,
        })
    }
    
    #[cfg(not(feature = "cli"))]
    {
        use arboard::Clipboard;
        let mut clipboard = Clipboard::new().map_err(|e| e.to_string())?;
        
        if let Ok(text) = clipboard.get_text() {
            return Ok(ClipboardContent {
                content_type: ContentType::Text,
                data: text.as_bytes().to_vec(),
                text_preview: Some(text.chars().take(100).collect()),
                file_name: None,
                file_size: None,
            });
        }
        
        if let Ok(image) = clipboard.get_image() {
            return Ok(ClipboardContent {
                content_type: ContentType::Image,
                data: image.bytes.to_vec(),
                text_preview: Some(format!("[Image {}x{}]", image.width, image.height)),
                file_name: None,
                file_size: None,
            });
        }
        
        Err("无法读取剪贴板".to_string())
    }
}

pub async fn write_clipboard(content: ClipboardContent) -> Result<(), String> {
    #[cfg(feature = "cli")]
    {
        Ok(())
    }
    
    #[cfg(not(feature = "cli"))]
    {
        use arboard::Clipboard;
        let mut clipboard = Clipboard::new().map_err(|e| e.to_string())?;
        
        match content.content_type {
            ContentType::Text => {
                let text = String::from_utf8_lossy(&content.data).to_string();
                clipboard.set_text(text).map_err(|e| e.to_string())?;
            }
            ContentType::Image => {
                let image_data = arboard::ImageData {
                    width: 100,
                    height: 100,
                    bytes: std::borrow::Cow::Owned(content.data),
                };
                clipboard.set_image(image_data).map_err(|e| e.to_string())?;
            }
            ContentType::File => {
                return Err("文件写入剪贴板暂不支持".to_string());
            }
        }
        
        Ok(())
    }
}

import re
from bs4 import BeautifulSoup
from typing import Optional
import html


class TextCleaner:
    @staticmethod
    def extract_text_from_html(html_content: str) -> str:
        if not html_content:
            return ""
        
        if not TextCleaner._is_html(html_content):
            return html_content
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
                element.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            text = html.unescape(text)
            text = TextCleaner._clean_whitespace(text)
            
            return text
        except Exception:
            return TextCleaner._simple_html_strip(html_content)
    
    @staticmethod
    def _is_html(content: str) -> bool:
        if not content:
            return False
        
        html_patterns = [
            r'<html',
            r'<body',
            r'<div',
            r'<p>',
            r'<span',
            r'<a\s',
            r'<br\s*/?>',
            r'<table',
            r'<!DOCTYPE html',
        ]
        
        content_lower = content.lower()[:500]
        return any(re.search(pattern, content_lower, re.IGNORECASE) for pattern in html_patterns)
    
    @staticmethod
    def _simple_html_strip(content: str) -> str:
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html.unescape(text)
        text = TextCleaner._clean_whitespace(text)
        return text
    
    @staticmethod
    def _clean_whitespace(text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    @staticmethod
    def clean_email_content(subject: str, body: str, is_html: bool = False) -> str:
        cleaned_subject = TextCleaner._clean_text(subject)
        
        if is_html:
            cleaned_body = TextCleaner.extract_text_from_html(body)
        else:
            cleaned_body = TextCleaner._clean_text(body)
        
        combined_text = f"{cleaned_subject} {cleaned_body}"
        
        return TextCleaner._clean_whitespace(combined_text)
    
    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        
        text = html.unescape(text)
        text = TextCleaner._clean_whitespace(text)
        
        return text
    
    @staticmethod
    def extract_plain_text(email_data: dict) -> dict:
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        is_html = email_data.get('is_html', False)
        
        cleaned_text = TextCleaner.clean_email_content(subject, body, is_html)
        
        return {
            'original_subject': subject,
            'original_body': body,
            'cleaned_text': cleaned_text,
            'is_html': is_html,
            'text_length': len(cleaned_text)
        }

import os
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import AdamW, get_linear_schedule_with_warmup
from transformers import AutoTokenizerFast, AutoModelForTokenClassification
from sklearn.model_selection import train_test_split
import numpy as np
from tqdm import tqdm

from config import Config


class AttributeDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len, label_map):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.label_map = label_map

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        labels = self.labels[item]

        encoding = self.tokenizer(
            list(text),
            is_split_into_words=True,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        word_ids = encoding.word_ids()
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)
            else:
                label_ids.append(self.label_map[labels[word_idx]] if word_idx < len(labels) else self.label_map['O'])

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label_ids, dtype=torch.long)
        }


class AttributeExtractor:
    def __init__(self, model_path=None, use_tinybert=None, use_quantization=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_tinybert = use_tinybert if use_tinybert is not None else Config.USE_TINYBERT
        self.use_quantization = use_quantization if use_quantization is not None else Config.USE_QUANTIZATION
        
        self.model_name = Config.TINYBERT_MODEL_NAME if self.use_tinybert else Config.BERT_MODEL_NAME
        
        self.label_map = {label: i for i, label in enumerate(Config.ATTRIBUTE_LABELS)}
        self.id_map = {i: label for label, i in self.label_map.items()}
        self.num_labels = len(Config.ATTRIBUTE_LABELS)
        
        if model_path and os.path.exists(model_path):
            self.tokenizer = AutoTokenizerFast.from_pretrained(model_path)
            self.model = AutoModelForTokenClassification.from_pretrained(
                model_path,
                num_labels=self.num_labels
            )
        else:
            self.tokenizer = AutoTokenizerFast.from_pretrained(self.model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(
                self.model_name,
                num_labels=self.num_labels
            )
        
        if self.use_quantization and self.device.type == 'cpu':
            self.model = torch.quantization.quantize_dynamic(
                self.model, 
                {torch.nn.Linear}, 
                dtype=torch.qint8
            )
        
        self.model = self.model.to(self.device)
        self.model.eval()
        
        self._warmup()
        
    def _warmup(self):
        dummy_text = "warmup text for inference"
        for _ in range(3):
            with torch.no_grad():
                encoding = self.tokenizer(
                    list(dummy_text),
                    is_split_into_words=True,
                    add_special_tokens=True,
                    max_length=Config.MAX_SEQ_LENGTH,
                    padding='max_length',
                    truncation=True,
                    return_attention_mask=True,
                    return_tensors='pt',
                )
                input_ids = encoding['input_ids'].to(self.device)
                attention_mask = encoding['attention_mask'].to(self.device)
                _ = self.model(input_ids=input_ids, attention_mask=attention_mask)

    def prepare_data(self, data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        texts = [list(item['text']) for item in data]
        labels = [item['labels'] for item in data]
        
        return train_test_split(texts, labels, test_size=0.2, random_state=42)

    def create_data_loader(self, texts, labels):
        ds = AttributeDataset(
            texts=texts,
            labels=labels,
            tokenizer=self.tokenizer,
            max_len=Config.MAX_SEQ_LENGTH,
            label_map=self.label_map
        )
        return DataLoader(ds, batch_size=Config.BATCH_SIZE, shuffle=True)

    def train(self, data_path, save_path):
        train_texts, val_texts, train_labels, val_labels = self.prepare_data(data_path)
        
        train_dataloader = self.create_data_loader(train_texts, train_labels)
        val_dataloader = self.create_data_loader(val_texts, val_labels)
        
        optimizer = AdamW(self.model.parameters(), lr=Config.LEARNING_RATE, correct_bias=False)
        total_steps = len(train_dataloader) * Config.EPOCHS
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=0,
            num_training_steps=total_steps
        )
        
        best_loss = float('inf')
        
        for epoch in range(Config.EPOCHS):
            print(f'Epoch {epoch + 1}/{Config.EPOCHS}')
            print('-' * 10)
            
            train_loss = self._train_epoch(train_dataloader, optimizer, scheduler)
            print(f'Train loss: {train_loss}')
            
            val_loss = self._eval_model(val_dataloader)
            print(f'Val   loss: {val_loss}')
            
            if val_loss < best_loss:
                self.save(save_path)
                best_loss = val_loss
                print(f'Model saved with loss: {best_loss}')

    def _train_epoch(self, data_loader, optimizer, scheduler):
        self.model = self.model.train()
        losses = []
        
        for d in tqdm(data_loader):
            input_ids = d['input_ids'].to(self.device)
            attention_mask = d['attention_mask'].to(self.device)
            labels = d['labels'].to(self.device)
            
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            
            loss = outputs.loss
            losses.append(loss.item())
            
            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
        
        return np.mean(losses)

    def _eval_model(self, data_loader):
        self.model = self.model.eval()
        losses = []
        
        with torch.no_grad():
            for d in data_loader:
                input_ids = d['input_ids'].to(self.device)
                attention_mask = d['attention_mask'].to(self.device)
                labels = d['labels'].to(self.device)
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                
                losses.append(outputs.loss.item())
        
        return np.mean(losses)

    def extract(self, text, measure_time=False):
        start_time = time.time() if measure_time else None
        
        with torch.no_grad():
            encoding = self.tokenizer(
                list(text),
                is_split_into_words=True,
                add_special_tokens=True,
                max_length=Config.MAX_SEQ_LENGTH,
                padding='max_length',
                truncation=True,
                return_attention_mask=True,
                return_tensors='pt',
            )
            
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            word_ids = encoding.word_ids()
            
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            predictions = torch.argmax(logits, dim=2)
        
        attributes = {
            'brand': [],
            'category': [],
            'spec': []
        }
        
        current_entity = None
        current_type = None
        
        for idx, (word_idx, pred) in enumerate(zip(word_ids, predictions[0])):
            if word_idx is None:
                continue
                
            label = self.id_map[pred.item()]
            
            if label.startswith('B-'):
                if current_entity is not None:
                    attributes[current_type].append(''.join(current_entity))
                current_entity = [text[word_idx]]
                current_type = label[2:].lower()
            elif label.startswith('I-') and current_type == label[2:].lower():
                if current_entity is not None:
                    current_entity.append(text[word_idx])
            else:
                if current_entity is not None:
                    attributes[current_type].append(''.join(current_entity))
                    current_entity = None
                    current_type = None
        
        if current_entity is not None:
            attributes[current_type].append(''.join(current_entity))
        
        result = {
            'brands': list(set(attributes['brand'])),
            'categories': list(set(attributes['category'])),
            'specs': list(set(attributes['spec']))
        }
        
        if measure_time:
            result['inference_time_ms'] = (time.time() - start_time) * 1000
        
        return result

    def save(self, save_path):
        os.makedirs(save_path, exist_ok=True)
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)

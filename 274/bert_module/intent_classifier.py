import os
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, AdamW, get_linear_schedule_with_warmup
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import numpy as np
from tqdm import tqdm

from config import Config


class IntentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        text = str(self.texts[item])
        label = self.labels[item]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        return {
            'text': text,
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


class IntentClassifier:
    def __init__(self, model_path=None, use_tinybert=None, use_quantization=None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.use_tinybert = use_tinybert if use_tinybert is not None else Config.USE_TINYBERT
        self.use_quantization = use_quantization if use_quantization is not None else Config.USE_QUANTIZATION
        
        self.model_name = Config.TINYBERT_MODEL_NAME if self.use_tinybert else Config.BERT_MODEL_NAME
        
        self.label_map = {label: i for i, label in enumerate(Config.INTENT_LABELS)}
        self.id_map = {i: label for label, i in self.label_map.items()}
        self.num_labels = len(Config.INTENT_LABELS)
        
        if model_path and os.path.exists(model_path):
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_path,
                num_labels=self.num_labels
            )
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
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
                encoding = self.tokenizer.encode_plus(
                    dummy_text,
                    add_special_tokens=True,
                    max_length=Config.MAX_SEQ_LENGTH,
                    return_token_type_ids=False,
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
        
        texts = [item['text'] for item in data]
        labels = [self.label_map[item['intent']] for item in data]
        
        return train_test_split(texts, labels, test_size=0.2, random_state=42)

    def create_data_loader(self, texts, labels):
        ds = IntentDataset(
            texts=texts,
            labels=labels,
            tokenizer=self.tokenizer,
            max_len=Config.MAX_SEQ_LENGTH
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
        
        best_accuracy = 0
        
        for epoch in range(Config.EPOCHS):
            print(f'Epoch {epoch + 1}/{Config.EPOCHS}')
            print('-' * 10)
            
            train_acc, train_loss = self._train_epoch(train_dataloader, optimizer, scheduler)
            print(f'Train loss {train_loss} accuracy {train_acc}')
            
            val_acc, val_loss = self._eval_model(val_dataloader)
            print(f'Val   loss {val_loss} accuracy {val_acc}')
            
            if val_acc > best_accuracy:
                self.save(save_path)
                best_accuracy = val_acc
                print(f'Model saved with accuracy: {best_accuracy}')

    def _train_epoch(self, data_loader, optimizer, scheduler):
        self.model = self.model.train()
        
        losses = []
        correct_predictions = 0
        
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
            logits = outputs.logits
            
            _, preds = torch.max(logits, dim=1)
            correct_predictions += torch.sum(preds == labels)
            losses.append(loss.item())
            
            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
        
        return correct_predictions.double() / len(data_loader.dataset), np.mean(losses)

    def _eval_model(self, data_loader):
        self.model = self.model.eval()
        
        losses = []
        correct_predictions = 0
        
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
                
                loss = outputs.loss
                logits = outputs.logits
                
                _, preds = torch.max(logits, dim=1)
                correct_predictions += torch.sum(preds == labels)
                losses.append(loss.item())
        
        return correct_predictions.double() / len(data_loader.dataset), np.mean(losses)

    def predict(self, text, measure_time=False):
        start_time = time.time() if measure_time else None
        
        with torch.no_grad():
            encoding = self.tokenizer.encode_plus(
                text,
                add_special_tokens=True,
                max_length=Config.MAX_SEQ_LENGTH,
                return_token_type_ids=False,
                padding='max_length',
                truncation=True,
                return_attention_mask=True,
                return_tensors='pt',
            )
            
            input_ids = encoding['input_ids'].to(self.device)
            attention_mask = encoding['attention_mask'].to(self.device)
            
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)
            
            _, preds = torch.max(logits, dim=1)
            pred_label = self.id_map[preds.item()]
            confidence = probs[0][preds.item()].item()
        
        result = {
            'intent': pred_label,
            'confidence': confidence,
            'probabilities': {self.id_map[i]: probs[0][i].item() for i in range(self.num_labels)}
        }
        
        if measure_time:
            result['inference_time_ms'] = (time.time() - start_time) * 1000
        
        return result
    
    def predict_batch(self, texts, measure_time=False):
        start_time = time.time() if measure_time else None
        
        with torch.no_grad():
            encodings = self.tokenizer.batch_encode_plus(
                texts,
                add_special_tokens=True,
                max_length=Config.MAX_SEQ_LENGTH,
                return_token_type_ids=False,
                padding='max_length',
                truncation=True,
                return_attention_mask=True,
                return_tensors='pt',
            )
            
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
            
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)
            
            _, preds = torch.max(logits, dim=1)
            
            results = []
            for i, pred in enumerate(preds):
                pred_label = self.id_map[pred.item()]
                confidence = probs[i][pred.item()].item()
                results.append({
                    'intent': pred_label,
                    'confidence': confidence,
                    'text': texts[i]
                })
        
        if measure_time:
            total_time = (time.time() - start_time) * 1000
            return {
                'results': results,
                'total_time_ms': total_time,
                'avg_time_ms': total_time / len(texts)
            }
        
        return results

    def save(self, save_path):
        os.makedirs(save_path, exist_ok=True)
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)

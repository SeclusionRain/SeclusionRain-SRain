#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于DistilBERT的中文情感分析模型
"""

import os
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, AdamW
from torch.utils.data import DataLoader, TensorDataset
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix
import numpy as np
import json

# 设置随机种子以确保结果可复现
torch.manual_seed(42)
np.random.seed(42)

# 数据集路径
POSITIVE_DATA_PATH = "d:\BSXM\main\models\SinaDataset\积极情感数据集.xlsx"
NEGATIVE_DATA_PATH = "d:\BSXM\main\models\SinaDataset\消极情感数据集.xlsx"
MODEL_SAVE_PATH = "d:\BSXM\main\models\distilbert_sentiment_model_new"
RESULTS_SAVE_PATH = "d:\BSXM\main\models\sentiment_analysis_results.json"

# 检查是否存在GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"使用设备: {device}")

def load_and_preprocess_data():
    """加载并预处理数据集"""
    print("正在加载数据集...")
    
    try:
        # 加载积极和消极情感数据
        positive_data = pd.read_excel(POSITIVE_DATA_PATH)
        negative_data = pd.read_excel(NEGATIVE_DATA_PATH)
        
        print(f"积极情感数据样本数: {len(positive_data)}")
        print(f"消极情感数据样本数: {len(negative_data)}")
        
        # 为数据添加标签：积极情感标记为1，消极情感标记为0
        positive_data['label'] = 1
        negative_data['label'] = 0
        
        # 合并数据集
        data = pd.concat([positive_data, negative_data], ignore_index=True)
        
        # 检查数据列名并选择合适的文本列
        text_column = None
        for col in data.columns:
            if '内容' in col or '文本' in col:
                text_column = col
                break
        
        if text_column is None:
            print("警告：未找到合适的文本列，尝试使用第一列")
            text_column = data.columns[1]  # 假设第二列包含文本
        
        print(f"使用的文本列: {text_column}")
        
        # 提取文本和标签
        texts = data[text_column].values
        labels = data['label'].values
        
        print(f"总数据样本数量: {len(data)}")
        print(f"样本分布: 积极情感 {sum(labels)} 条, 消极情感 {len(labels) - sum(labels)} 条")
        
        # 检查是否有空值并处理
        non_empty_mask = ~pd.isna(texts)
        texts = texts[non_empty_mask]
        labels = labels[non_empty_mask]
        print(f"处理后数据样本数量: {len(texts)}")
        
        return texts, labels
        
    except Exception as e:
        print(f"加载数据时出错: {e}")
        raise

def tokenize_data(texts, max_length=128):
    """使用DistilBERT分词器处理文本"""
    print("正在加载分词器并处理文本...")
    
    # 加载DistilBERT分词器（多语言版本支持中文）
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-multilingual-cased")
    
    # 分词处理
    tokenized_texts = tokenizer(
        list(texts),
        max_length=max_length,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )
    
    print(f"分词完成，特征: {tokenized_texts.keys()}")
    return tokenized_texts, tokenizer

def create_dataloaders(tokenized_texts, labels, batch_size=16):
    """创建训练集和测试集的数据加载器"""
    print("正在划分数据集并创建DataLoader...")
    
    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        tokenized_texts["input_ids"], labels, test_size=0.2, random_state=42, stratify=labels
    )
    
    # 划分注意力掩码
    X_train_masks, X_test_masks = train_test_split(
        tokenized_texts["attention_mask"], test_size=0.2, random_state=42, stratify=labels
    )
    
    # 转换标签为张量
    y_train = torch.tensor(y_train)
    y_test = torch.tensor(y_test)
    
    # 创建数据集
    train_data = TensorDataset(X_train, X_train_masks, y_train)
    test_data = TensorDataset(X_test, X_test_masks, y_test)
    
    # 创建DataLoader
    train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=batch_size)
    
    print(f"训练集大小: {len(train_data)}, 测试集大小: {len(test_data)}")
    return train_loader, test_loader, X_test, X_test_masks, y_test

def train_model(train_loader, epochs=3, learning_rate=2e-5):
    """训练DistilBERT模型"""
    print("正在加载和训练模型...")
    
    # 加载DistilBERT模型，输出2个类别（积极和消极）
    model = DistilBertForSequenceClassification.from_pretrained(
        "distilbert-base-multilingual-cased", 
        num_labels=2
    )
    model.to(device)
    
    # 定义优化器
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    
    # 训练记录
    training_losses = []
    
    # 训练循环
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for step, batch in enumerate(train_loader):
            b_input_ids, b_input_mask, b_labels = tuple(t.to(device) for t in batch)
            
            # 清零梯度
            optimizer.zero_grad()
            
            # 前向传播
            outputs = model(input_ids=b_input_ids, attention_mask=b_input_mask, labels=b_labels)
            loss = outputs.loss
            total_loss += loss.item()
            
            # 反向传播
            loss.backward()
            optimizer.step()
            
            # 打印训练进度
            if (step + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}/{epochs} | Step {step + 1}/{len(train_loader)} | Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / len(train_loader)
        training_losses.append(avg_loss)
        print(f"Epoch {epoch + 1}/{epochs} 完成 | 平均Loss: {avg_loss:.4f}")
    
    # 保存模型
    if not os.path.exists(MODEL_SAVE_PATH):
        os.makedirs(MODEL_SAVE_PATH)
    
    model.save_pretrained(MODEL_SAVE_PATH)
    print(f"模型已保存至: {MODEL_SAVE_PATH}")
    
    return model, training_losses

def evaluate_model(model, test_loader, X_test, X_test_masks, y_test):
    """评估模型性能"""
    print("正在评估模型...")
    
    # 模型评估
    model.eval()
    all_predictions = []
    all_labels = []
    
    # 使用DataLoader进行批量预测
    for batch in test_loader:
        b_input_ids, b_input_mask, b_labels = tuple(t.to(device) for t in batch)
        
        with torch.no_grad():
            outputs = model(input_ids=b_input_ids, attention_mask=b_input_mask)
            predictions = torch.argmax(outputs.logits, dim=1).cpu().numpy()
        
        all_predictions.extend(predictions)
        all_labels.extend(b_labels.cpu().numpy())
    
    # 计算准确率
    accuracy = accuracy_score(all_labels, all_predictions)
    print(f"测试集准确率: {accuracy:.4f}")
    
    # 输出分类报告
    report = classification_report(all_labels, all_predictions, target_names=['消极情感', '积极情感'], output_dict=True)
    print("分类报告:")
    print(classification_report(all_labels, all_predictions, target_names=['消极情感', '积极情感']))
    
    # 绘制混淆矩阵
    cm = confusion_matrix(all_labels, all_predictions)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['消极情感', '积极情感'],
                yticklabels=['消极情感', '积极情感'])
    plt.xlabel('预测标签')
    plt.ylabel('真实标签')
    plt.title('情感分析混淆矩阵')
    plt.savefig('d:\BSXM\main\models\sentiment_confusion_matrix.png')
    print("混淆矩阵已保存至: d:\BSXM\main\models\sentiment_confusion_matrix.png")
    
    return accuracy, report

def predict_new_sentences(model, tokenizer, sentences):
    """对新句子进行情感分类预测"""
    model.eval()
    results = []
    
    for sentence in sentences:
        # 分词处理
        inputs = tokenizer(
            [sentence],
            max_length=128,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # 转换到设备
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)
        
        # 预测
        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            prediction = torch.argmax(outputs.logits, dim=1).item()
            probability = torch.nn.functional.softmax(outputs.logits, dim=1).cpu().numpy()[0]
        
        sentiment = "积极情感" if prediction == 1 else "消极情感"
        results.append({
            "sentence": sentence,
            "sentiment": sentiment,
            "label": prediction,
            "negative_prob": float(probability[0]),
            "positive_prob": float(probability[1])
        })
        
        print(f"句子: {sentence}")
        print(f"情感预测: {sentiment}")
        print(f"消极概率: {probability[0]:.4f}, 积极概率: {probability[1]:.4f}")
        print()
    
    return results

def main():
    """主函数"""
    try:
        # 1. 加载和预处理数据
        texts, labels = load_and_preprocess_data()
        
        # 2. 分词处理
        tokenized_texts, tokenizer = tokenize_data(texts)
        
        # 3. 创建数据加载器
        train_loader, test_loader, X_test, X_test_masks, y_test = create_dataloaders(tokenized_texts, labels)
        
        # 4. 训练模型
        model, training_losses = train_model(train_loader)
        
        # 5. 评估模型
        accuracy, report = evaluate_model(model, test_loader, X_test, X_test_masks, y_test)
        
        # 6. 测试新句子
        test_sentences = [
            "天气晴朗，心情很好。",
            "今天的工作很糟糕，令人沮丧。",
            "这个产品非常好用，我很喜欢。",
            "服务态度很差，下次不会再来了。",
            "这部电影太精彩了，强烈推荐！",
            "交通很拥堵，浪费了很多时间。"
        ]
        print("\n测试新句子情感分析:")
        prediction_results = predict_new_sentences(model, tokenizer, test_sentences)
        
        # 7. 保存结果
        results = {
            "accuracy": float(accuracy),
            "report": report,
            "training_losses": training_losses,
            "predictions": prediction_results,
            "model_path": MODEL_SAVE_PATH
        }
        
        with open(RESULTS_SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析结果已保存至: {RESULTS_SAVE_PATH}")
        print("\nDistilBERT情感分析模型训练和评估完成！")
        
    except Exception as e:
        print(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== DistilBERT中文情感分析模型 ===")
    main()
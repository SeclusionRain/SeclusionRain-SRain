#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
训练DistilBERT情感分析模型
"""
import os
import sys
import torch
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    get_linear_schedule_with_warmup
)
from torch.optim import AdamW
from torch.utils.data import DataLoader, TensorDataset, RandomSampler, SequentialSampler

def load_and_preprocess_data(data_file):
    """
    加载并预处理数据（从CSV文件）
    """
    print(f"正在加载数据集: {data_file}")
    
    # 加载数据
    try:
        # 使用pandas读取CSV文件
        data = pd.read_csv(data_file)
        
        print(f"总数据样本数: {len(data)}")
        
        # 查看数据结构
        print("\n数据结构:")
        print(data.columns.tolist())
        
        # 检查必要的列是否存在
        if 'label' not in data.columns:
            print("错误: 数据集中没有 'label' 列")
            sys.exit(1)
        
        if 'review' not in data.columns:
            print("错误: 数据集中没有 'review' 列")
            sys.exit(1)
        
        # 使用指定的列
        print("\n使用 'review' 列作为文本列，'label' 列作为标签列")
        texts = data['review'].astype(str).tolist()
        labels = data['label'].tolist()
        
        # 检查标签分布
        positive_count = sum(1 for label in labels if label == 1)
        negative_count = len(labels) - positive_count
        print(f"\n数据样本数: {len(texts)}")
        print(f"标签分布: 积极={positive_count}, 消极={negative_count}")
        
        # 显示一些样本
        print("\n数据样本:")
        for i in range(min(5, len(texts))):
            print(f"{i+1}. [{labels[i]}] {texts[i]}")
        
        return texts, labels
        
    except Exception as e:
        print(f"加载数据时出错: {e}")
        sys.exit(1)

def tokenize_texts(texts, tokenizer, max_length=128):
    """
    使用DistilBERT分词器处理文本
    """
    print("\n正在进行文本分词...")
    
    # 分批处理大文本列表
    batch_size = 1000
    all_input_ids = []
    all_attention_masks = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        encoded_batch = tokenizer(
            batch_texts,
            max_length=max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        all_input_ids.extend(encoded_batch['input_ids'])
        all_attention_masks.extend(encoded_batch['attention_mask'])
    
    # 转换为张量
    input_ids = torch.stack(all_input_ids)
    attention_masks = torch.stack(all_attention_masks)
    
    print(f"分词完成，输入形状: {input_ids.shape}")
    return input_ids, attention_masks

def create_dataloaders(input_ids, attention_masks, labels, batch_size=16):
    """
    创建数据加载器
    """
    print("\n正在创建数据加载器...")
    
    # 转换标签为张量
    labels = torch.tensor(labels)
    
    # 划分训练集和验证集
    train_inputs, val_inputs, train_masks, val_masks, train_labels, val_labels = train_test_split(
        input_ids, attention_masks, labels, 
        random_state=42, test_size=0.2
    )
    
    print(f"训练集大小: {len(train_inputs)}")
    print(f"验证集大小: {len(val_inputs)}")
    
    # 创建数据集
    train_dataset = TensorDataset(train_inputs, train_masks, train_labels)
    val_dataset = TensorDataset(val_inputs, val_masks, val_labels)
    
    # 创建数据加载器
    train_dataloader = DataLoader(
        train_dataset,
        sampler=RandomSampler(train_dataset),
        batch_size=batch_size
    )
    
    validation_dataloader = DataLoader(
        val_dataset,
        sampler=SequentialSampler(val_dataset),
        batch_size=batch_size
    )
    
    return train_dataloader, validation_dataloader

def train_model(model, train_dataloader, validation_dataloader, device, epochs=3, lr=2e-5):
    """
    训练模型
    """
    print("\n开始训练模型...")
    
    # 移动模型到设备
    model.to(device)
    
    # 定义优化器
    optimizer = AdamW(model.parameters(), lr=lr, eps=1e-8)
    
    # 计算总训练步数
    total_steps = len(train_dataloader) * epochs
    
    # 创建学习率调度器
    scheduler = get_linear_schedule_with_warmup(
        optimizer, 
        num_warmup_steps=0,
        num_training_steps=total_steps
    )
    
    # 记录训练历史
    training_history = {
        'train_loss': [],
        'val_loss': [],
        'val_accuracy': []
    }
    
    # 训练循环
    for epoch in range(epochs):
        print(f"\n===== Epoch {epoch+1}/{epochs} =====")
        
        # 训练阶段
        model.train()
        total_train_loss = 0
        
        for step, batch in enumerate(train_dataloader):
            if step % 100 == 0 and step > 0:
                print(f"  Batch {step}, 训练进度: {step/len(train_dataloader)*100:.1f}%")
            
            # 获取批次数据
            b_input_ids, b_input_mask, b_labels = tuple(t.to(device) for t in batch)
            
            # 清零梯度
            model.zero_grad()
            
            # 前向传播
            outputs = model(
                input_ids=b_input_ids,
                attention_mask=b_input_mask,
                labels=b_labels
            )
            
            # 计算损失
            loss = outputs.loss
            total_train_loss += loss.item()
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            # 更新参数
            optimizer.step()
            scheduler.step()
        
        # 计算平均训练损失
        avg_train_loss = total_train_loss / len(train_dataloader)
        print(f"\n  平均训练损失: {avg_train_loss:.4f}")
        
        # 记录训练损失
        training_history['train_loss'].append(avg_train_loss)
        
        # 验证阶段
        model.eval()
        total_eval_accuracy = 0
        total_eval_loss = 0
        
        for batch in validation_dataloader:
            # 获取批次数据
            b_input_ids, b_input_mask, b_labels = tuple(t.to(device) for t in batch)
            
            # 不计算梯度
            with torch.no_grad():
                # 前向传播
                outputs = model(
                    input_ids=b_input_ids,
                    attention_mask=b_input_mask,
                    labels=b_labels
                )
            
            # 计算损失
            loss = outputs.loss
            total_eval_loss += loss.item()
            
            # 获取预测结果
            logits = outputs.logits
            logits = logits.detach().cpu().numpy()
            label_ids = b_labels.to('cpu').numpy()
            
            # 计算准确率
            predictions = np.argmax(logits, axis=-1)
            total_eval_accuracy += np.sum(predictions == label_ids) / len(label_ids)
        
        # 计算平均验证损失和准确率
        avg_val_loss = total_eval_loss / len(validation_dataloader)
        avg_val_accuracy = total_eval_accuracy / len(validation_dataloader)
        
        print(f"  验证损失: {avg_val_loss:.4f}")
        print(f"  验证准确率: {avg_val_accuracy:.4f}")
        
        # 记录验证损失和准确率
        training_history['val_loss'].append(avg_val_loss)
        training_history['val_accuracy'].append(avg_val_accuracy)
    
    # 打印训练历史
    print("\n训练历史:")
    print(f"Epoch | Train Loss | Val Loss | Val Accuracy")
    print(f"----- | ---------- | -------- | -----------")
    for i in range(epochs):
        print(f"{i+1:5d} | {training_history['train_loss'][i]:10.4f} | {training_history['val_loss'][i]:8.4f} | {training_history['val_accuracy'][i]:11.4f}")
    print("\n训练完成!")
    return model

def test_model(model, validation_dataloader, device):
    """
    测试模型性能
    """
    print("\n测试模型性能...")
    
    model.eval()
    all_predictions = []
    all_labels = []
    
    for batch in validation_dataloader:
        # 获取批次数据
        b_input_ids, b_input_mask, b_labels = tuple(t.to(device) for t in batch)
        
        # 不计算梯度
        with torch.no_grad():
            # 前向传播
            outputs = model(
                input_ids=b_input_ids,
                attention_mask=b_input_mask
            )
        
        # 获取预测结果
        logits = outputs.logits
        logits = logits.detach().cpu().numpy()
        label_ids = b_labels.to('cpu').numpy()
        
        # 获取预测类别
        predictions = np.argmax(logits, axis=-1)
        
        # 收集结果
        all_predictions.extend(predictions)
        all_labels.extend(label_ids)
    
    # 计算准确率
    accuracy = np.sum(np.array(all_predictions) == np.array(all_labels)) / len(all_labels)
    print(f"\n模型准确率: {accuracy:.4f}")
    
    # 测试一些示例句子
    print("\n测试示例句子:")
    test_sentences = [
        "我真是服了呀，这狂铁有闪",
        "宝宝好帅啊。",
        "你是不是傻逼啊。",
        "我草你妈。"
    ]
    
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-multilingual-cased")
    
    for sentence in test_sentences:
        # 预处理
        inputs = tokenizer(
            sentence,
            max_length=128,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # 预测
        with torch.no_grad():
            outputs = model(
                input_ids=inputs["input_ids"].to(device),
                attention_mask=inputs["attention_mask"].to(device)
            )
            
            # 计算概率
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=1)
            
            # 获取预测类别
            prediction = torch.argmax(probabilities, dim=1).item()
            
            # 获取置信度
            confidence = probabilities[0, prediction].item()
        
        # 构建结果
        sentiment = "积极" if prediction == 1 else "消极"
        print(f"句子: {sentence}")
        print(f"  预测情感: {sentiment}")
        print(f"  置信度: {confidence:.4f}")

def save_model(model, output_dir):
    """
    保存模型
    """
    print(f"\n正在保存模型到 {output_dir}...")
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 保存模型
    model.save_pretrained(output_dir)
    
    # 保存分词器
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-multilingual-cased")
    tokenizer.save_pretrained(output_dir)
    
    print("模型保存完成!")

def main():
    """
    主函数
    """
    # 配置参数
    data_file = "d:/BSXM/main/models/SinaDataset/weibo_senti_100k.csv"
    output_dir = "d:/BSXM/main/models/distilbert2"  # 新模型名称
    batch_size = 16
    epochs = 3
    max_length = 128
    
    # 检查GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")
    
    # 1. 加载数据
    texts, labels = load_and_preprocess_data(data_file)
    
    # 2. 加载分词器
    print("\n正在加载DistilBERT分词器...")
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-multilingual-cased")
    
    # 3. 分词
    input_ids, attention_masks = tokenize_texts(texts, tokenizer, max_length)
    
    # 4. 创建数据加载器
    train_dataloader, validation_dataloader = create_dataloaders(
        input_ids, attention_masks, labels, batch_size
    )
    
    # 5. 加载模型 - 使用现有模型进行二次训练
    print("\n正在加载现有DistilBERT模型进行二次训练...")
    model = DistilBertForSequenceClassification.from_pretrained(
        "d:/BSXM/main/models/distilbert_sentiment_model_new",  # 使用现有模型
        num_labels=2,  # 二分类：积极/消极
        output_attentions=False,
        output_hidden_states=False
    )
    
    # 6. 训练模型
    model = train_model(
        model, 
        train_dataloader, 
        validation_dataloader, 
        device, 
        epochs=epochs
    )
    
    # 7. 测试模型
    test_model(model, validation_dataloader, device)
    
    # 8. 保存模型
    save_model(model, output_dir)

if __name__ == "__main__":
    main()
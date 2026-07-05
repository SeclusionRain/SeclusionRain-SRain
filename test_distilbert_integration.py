#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试DistilBERT情感分析模型与现有服务的集成
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.model_service import SentimentModelService
from services.distilbert_model_service import DistilBertModelService

def test_distilbert_model_service():
    """直接测试DistilBERT模型服务"""
    print("\n=== 测试DistilBERT模型服务 ===")
    try:
        # 创建DistilBERT模型服务实例
        distilbert_service = DistilBertModelService()
        
        # 测试句子
        test_sentences = [
            "天气晴朗，心情很好。",
            "今天的工作很糟糕，令人沮丧。",
            "我草泥马",
            "服务态度很差，不会再来了。"
        ]
        
        # 预测结果
        results = distilbert_service.batch_predict(test_sentences)
        
        # 显示结果
        for i, (sentence, result) in enumerate(zip(test_sentences, results)):
            print(f"\n句子{i+1}: {sentence}")
            print(f"  预测情感: {result['sentiment']}")
            print(f"  标签值: {result['label']}")
            print(f"  置信度: {result['probability']:.4f}")
            
    except Exception as e:
        print(f"DistilBERT模型服务测试失败: {e}")

def test_model_service_integration():
    """测试集成后的模型服务"""
    print("\n=== 测试集成后的模型服务 ===")
    try:
        # 创建模型服务实例
        model_service = SentimentModelService()
        
        # 检查是否包含DistilBERT模型
        available_models = model_service.get_all_model_info()
        print(f"可用模型: {list(available_models.keys())}")
        
        # 检查是否包含DistilBERT模型
        has_distilbert = "DistilBERT" in available_models
        print(f"DistilBERT模型是否可用: {has_distilbert}")
        
        if has_distilbert:
            # 测试集成的DistilBERT模型
            test_sentences = [
                "天气晴朗，心情很好。",
                "今天的工作很糟糕，令人沮丧。"
            ]
            
            # 使用SentimentModelService调用DistilBERT
            results = model_service.predict_sentiment("DistilBERT", test_sentences)
            
            # 显示结果
            print("\nDistilBERT预测结果:")
            for sentence, result in zip(test_sentences, results):
                print(f"句子: {sentence}")
                print(f"  情感: {result['label']}")
                print(f"  置信度: {result['score']:.4f}")
        else:
            print("无法测试集成，DistilBERT模型不可用")
            
    except Exception as e:
        print(f"集成服务测试失败: {e}")

def test_comparison_with_traditional_models():
    """比较DistilBERT与传统模型的性能"""
    print("\n=== 比较DistilBERT与传统模型 ===")
    try:
        # 创建模型服务实例
        model_service = SentimentModelService()
        
        # 测试句子集
        test_sentences = [
            "天气晴朗，心情很好。",
            "今天的工作很糟糕，令人沮丧。",
            "妈啊[裂开][裂开][裂开][裂开]这物价，刚看完香港房价，这物价我要是去了根本不能活[裂开]",
            "感觉港星在当地好爽啊，出去随便逛 没有太大压力，不担心被围，自由自在"
        ]
        
        # 获取所有可用模型
        available_models = model_service.get_all_model_info()
        
        # 对于每个可用模型进行预测
        for model_name in available_models:
            print(f"\n--- 模型: {model_name} ---")
            try:
                results = model_service.predict_sentiment(model_name, test_sentences)
                
                for sentence, result in zip(test_sentences, results):
                    print(f"句子: {sentence}")
                    print(f"  情感: {result['label']}")
                    print(f"  置信度: {result['score']:.4f}")
                    
            except Exception as e:
                print(f"模型 {model_name} 预测失败: {e}")
                
    except Exception as e:
        print(f"模型比较测试失败: {e}")

if __name__ == "__main__":
    print("开始测试DistilBERT模型集成...")
    
    # 1. 测试DistilBERT模型服务
    test_distilbert_model_service()
    
    # 2. 测试集成后的模型服务
    test_model_service_integration()
    
    # 3. 可选: 比较不同模型的性能
    # test_comparison_with_traditional_models()  # 取消注释可运行比较测试
    
    print("\n测试完成!")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试DistilBERT模型情感分析问题
用于测试模型对实际评论数据的处理能力
"""
import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.distilbert_model_service import DistilBertModelService
from services.model_service import SentimentModelService

def test_with_sample_comments():
    """测试模型对示例评论的处理能力"""
    print("=== 开始测试DistilBERT模型 ===")
    
    # 创建两个服务实例进行对比测试
    direct_service = DistilBertModelService()
    integrated_service = SentimentModelService()
    
    # 测试用例 - 包括正面、负面和中性评论
    test_comments = [
        "天气晴朗，心情很好。",
        "今天的工作很糟糕，令人沮丧。",
        "这个产品质量还不错，价格也比较合理。",
        "服务态度很差，不会再来了。",
        "非常满意这次的购物体验，下次还会再来！",
        "一般般吧，没有特别好也没有特别差。",
        # 添加一些更复杂的测试用例
        "水母可能就是喜欢脸长的吧（不是…[杀马特][杀马特][杀马特]",
        "宝剑嫂瘦了很多的样子",
        "错误的平台刷到对的人[黑脸][黑脸]",
        "两个小女孩一起拍视频就是双倍的幸福[流泪]好可爱看的人心情好好"
    ]
    
    print("\n--- 直接使用DistilBertModelService ---\n")
    # 使用直接服务测试
    for i, comment in enumerate(test_comments):
        result = direct_service.predict(comment)
        print(f"评论{i+1}: {comment}")
        print(f"  预测结果: {result['sentiment']}")
        print(f"  标签值: {result['label']}")
        print(f"  置信度: {result['probability']:.4f}")
        print()
    
    print("\n--- 使用集成后的SentimentModelService ---\n")
    # 使用集成服务测试
    if "DistilBERT" in integrated_service.get_available_models():
        results = integrated_service.predict_sentiment("DistilBERT", test_comments)
        for i, (comment, result) in enumerate(zip(test_comments, results)):
            print(f"评论{i+1}: {comment}")
            print(f"  预测结果: {'积极' if result['label'] == 'positive' else '消极'}")
            print(f"  标签值: {result['label']}")
            print(f"  置信度: {result['score']:.4f}")
            print()
    else:
        print("DistilBERT模型在集成服务中不可用")

def test_batch_behavior():
    """测试批量预测行为是否有问题"""
    print("\n=== 测试批量预测行为 ===\n")
    
    service = DistilBertModelService()
    
    # 全是正面评论
    positive_comments = [
        "太棒了！",
        "非常好的体验",
        "我很满意",
        "超级喜欢",
        "强烈推荐"
    ]
    
    # 全是负面评论
    negative_comments = [
        "很差劲",
        "非常失望",
        "质量太次了",
        "不会再买了",
        "服务态度恶劣"
    ]
    
    # 混合评论
    mixed_comments = positive_comments + negative_comments
    
    print("\n--- 批量预测正面评论 ---\n")
    results = service.batch_predict(positive_comments)
    for i, (comment, result) in enumerate(zip(positive_comments, results)):
        print(f"评论{i+1}: {comment} -> {result['sentiment']} (置信度: {result['probability']:.4f})")
    
    print("\n--- 批量预测负面评论 ---\n")
    results = service.batch_predict(negative_comments)
    for i, (comment, result) in enumerate(zip(negative_comments, results)):
        print(f"评论{i+1}: {comment} -> {result['sentiment']} (置信度: {result['probability']:.4f})")
    
    print("\n--- 批量预测混合评论 ---\n")
    results = service.batch_predict(mixed_comments)
    for i, (comment, result) in enumerate(zip(mixed_comments, results)):
        print(f"评论{i+1}: {comment} -> {result['sentiment']} (置信度: {result['probability']:.4f})")

if __name__ == "__main__":
    print("开始调试DistilBERT模型情感分析问题...\n")
    
    # 测试1: 使用示例评论
    test_with_sample_comments()
    
    # 测试2: 测试批量预测行为
    test_batch_behavior()
    
    print("\n调试完成！")
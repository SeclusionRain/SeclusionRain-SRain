"""
情感分析模型服务类
基于现有的cli_demo.py逻辑，提供Web应用的模型推理服务
"""
import os
import re
import jieba
import joblib
import numpy as np
import pandas as pd
from gensim.models import KeyedVectors
from sklearn.feature_extraction.text import CountVectorizer

# 导入DistilBERT模型服务
try:
    import importlib
    # 使用动态导入以确保在任何运行环境下都能正确导入
    distilbert_module = importlib.import_module("services.distilbert_model_service")
    distilbert_service = distilbert_module.DistilBertModelService()
    
    # 检查模型服务的实际可用性状态
    if hasattr(distilbert_service, 'available') and distilbert_service.available:
        print("成功导入并初始化DistilBERT模型服务")
    else:
        print("警告: DistilBERT模型服务初始化失败，服务不可用")
        distilbert_service = None
except Exception as e:
    print(f"警告: 无法导入或初始化DistilBERT模型服务: {e}")
    distilbert_service = None

class SentimentModelService:
    """情感分析模型服务类 """
    
    def __init__(self):
        self.models_path = os.path.join(os.path.dirname(__file__), '..', 'models')
        self.stop_words = self._load_stop_words()
        self.available_models = {
            "决策树_词袋模型": {
                "model_file": "Decision_Tree_BOW.pkl",
                "feature_file": "Decision_Tree_BOW_feature.pkl",
                "type": "bow"
            },
            "决策树_tfidf": {
                "model_file": "Decision_Tree_tfidf.pkl", 
                "feature_file": "Decision_Tree_tfidf_feature.pkl",
                "type": "tfidf"
            },
            "朴素贝叶斯_tfidf": {
                "model_file": "Naive_Bayes.pkl",
                "feature_file": "Naive_Bayes_feature.pkl", 
                "type": "tfidf"
            },
            "SVM_tfidf": {
                "model_file": "SVM_tfidf.pkl",
                "feature_file": "SVM_feature_tfidf.pkl",
                "type": "tfidf"
            },
            "SVM_word2vec": {
                "model_file": "SVM_word2vect.pkl",
                "feature_file": "word2vec.txt",
                "type": "word2vec"
            },
            "DistilBERT": {
                "type": "transformer",  
                "model_file": None,     
                "feature_file": None,
                "available": False  
            }
        }
        self._validate_models()
    
    def _load_stop_words(self):
        """加载停用词"""
        stop_words_path = os.path.join(self.models_path, 'stoplist.txt')
        try:
            with open(stop_words_path, 'r', encoding='UTF-8') as f:
                return set(f.read().split())
        except FileNotFoundError:
            print(f"警告: 停用词文件 {stop_words_path} 不存在，使用默认停用词")
            return set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'])
    
    def _validate_models(self):
        """验证模型文件是否存在"""
        valid_models = {}
        for model_name, config in self.available_models.items():
            # 特殊处理DistilBERT模型
            if model_name == "DistilBERT":
                # 检查DistilBERT模型服务是否可用
                if distilbert_service is not None and hasattr(distilbert_service, 'available') and distilbert_service.available:
                    print("DistilBERT模型服务验证通过")
                    config['available'] = True  # 更新可用状态
                    valid_models[model_name] = config
                else:
                    print(f"警告: DistilBERT模型服务不可用，当前状态: distilbert_service={distilbert_service is not None}")
                continue
            
            # 常规模型文件检查
            model_path = os.path.join(self.models_path, config["model_file"])
            feature_path = os.path.join(self.models_path, config["feature_file"])
            
            if os.path.exists(model_path) and os.path.exists(feature_path):
                valid_models[model_name] = config
            else:
                print(f"警告: 模型 {model_name} 的文件不完整，跳过")
        
        self.available_models = valid_models
    
    def get_available_models(self):
        """获取所有可用模型的名称列表"""
        available = []
        for model_name, config in self.available_models.items():
            # 特殊处理DistilBERT模型的可用性检查
            if model_name == "DistilBERT" and 'available' in config:
                if config['available']:
                    available.append(model_name)
            else:
                # 其他模型默认可用（假设文件存在检查在_validate_model中完成）
                available.append(model_name)
        return available
    
    def clean_and_segment_text(self, input_text):
        """清理和分词文本 """
        cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', str(input_text))
        words = jieba.cut(cleaned_text)
        words = filter(lambda w: w not in self.stop_words and w.strip(), words)
        return ' '.join(words)
    
    def average_word_vectors(self, words, model, vocabulary, num_features):
        """计算词向量平均值 """
        feature_vector = np.zeros((num_features,), dtype='float64')
        nwords = 0
        for word in words:
            if word in vocabulary:
                nwords += 1
                feature_vector = np.add(feature_vector, model[word])
        if nwords:
            feature_vector = np.divide(feature_vector, nwords)
        return feature_vector
    
    def averaged_word_vectorizer(self, corpus, model, num_features):
        """批量计算词向量 """
        vocabulary = set(model.index_to_key)
        features = [self.average_word_vectors(tokenized_sentence, model, vocabulary, num_features) 
                   for tokenized_sentence in corpus]
        return np.array(features)
    
    def get_word_vectors(self, data, model):
        """获取词向量特征 """
        words_art = [text.split() for text in data]
        return self.averaged_word_vectorizer(words_art, model, num_features=100)
    
    def predict_sentiment(self, model_name, texts):
        """
        预测情感
        
        Args:
            model_name: 模型名称
            texts: 文本列表
            
        Returns:
            预测结果列表，每个元素包含 {'label': str, 'score': float}
        """
        if model_name not in self.available_models:
            raise ValueError(f"模型 {model_name} 不可用")
        
        config = self.available_models[model_name]
        
        # 特殊处理DistilBERT模型
        if config["type"] == "transformer":
            try:
                # 确保distilbert_service可用
                if distilbert_service is None or (hasattr(distilbert_service, 'available') and not distilbert_service.available):
                    raise Exception("DistilBERT模型服务不可用")
                    
                # 直接使用DistilBertModelService实例进行预测
                distilbert_results = distilbert_service.batch_predict(texts)
                
                # 转换结果格式以保持一致性
                results = []
                for result in distilbert_results:
                    # 从DistilBertModelService返回的结果格式中提取信息
                    # 格式应该是: {"sentiment": "积极/消极", "label": 0/1, "probability": 0.xx}
                    if result.get('sentiment') == '积极':
                        label = 'positive'
                    else:
                        label = 'negative'
                    
                    results.append({
                        'label': label,
                        'score': result.get('probability', 0.5)
                    })
                
                return results
                
            except Exception as e:
                print(f"DistilBERT模型预测过程中出错: {e}")
                return [{'label': 'negative', 'score': 0.5} for _ in texts]
        
        # 常规模型处理逻辑
        try:
            model_path = os.path.join(self.models_path, config["model_file"])
            feature_path = os.path.join(self.models_path, config["feature_file"])
            
            # 预处理文本
            if isinstance(texts, str):
                texts = [texts]
            
            processed_texts = [self.clean_and_segment_text(text) for text in texts]
            
            # 根据模型类型进行特征提取
            if config["type"] == "bow":
                # 词袋模型
                vocabulary = joblib.load(feature_path)
                vect = CountVectorizer(decode_error="replace", vocabulary=vocabulary)
                X_test_vect = vect.transform(processed_texts)
                
            elif config["type"] == "tfidf":
                # TF-IDF模型
                vect = joblib.load(feature_path)
                X_test_vect = vect.transform(processed_texts)
                
            elif config["type"] == "word2vec":
                # Word2Vec模型
                w2v_model = KeyedVectors.load_word2vec_format(feature_path, binary=False)
                X_test_vect = self.get_word_vectors(processed_texts, w2v_model)
            
            # 加载模型并预测
            model = joblib.load(model_path)
            predictions = model.predict(X_test_vect)
            
            # 获取预测概率（如果模型支持）
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(X_test_vect)
                scores = np.max(probabilities, axis=1)
            else:
                scores = [0.8] * len(predictions)  # 默认置信度
            
            # 转换结果格式
            results = []
            for pred, score in zip(predictions, scores):
                label = 'positive' if pred == 1 else 'negative'
                results.append({
                    'label': label,
                    'score': float(score)
                })
            
            return results
            
        except Exception as e:
            print(f"预测过程中出错: {e}")
            # 返回默认结果
            return [{'label': 'negative', 'score': 0.5} for _ in texts]
    
    def get_model_info(self, model_name):
        """获取单个模型信息"""
        if model_name not in self.available_models:
            return None
        
        config = self.available_models[model_name]
        return {
            'name': model_name,
            'type': config['type'],
            'description': self._get_model_description(model_name)
        }
    
    def get_all_model_info(self):
        """获取所有模型信息"""
        model_info = {}
        for model_name in self.available_models:
            model_info[model_name] = {
                'name': model_name,
                'type': self.available_models[model_name]['type'],
                'description': self._get_model_description(model_name)
            }
        return model_info
    
    def _get_model_description(self, model_name):
        """获取模型描述"""
        descriptions = {
            "决策树_词袋模型": "基于词袋模型的决策树分类器，适合处理短文本",
            "决策树_tfidf": "基于TF-IDF特征的决策树分类器，考虑词频和逆文档频率",
            "朴素贝叶斯_tfidf": "基于TF-IDF特征的朴素贝叶斯分类器，适合文本分类任务",
            "SVM_tfidf": "基于TF-IDF特征的支持向量机，具有较好的泛化能力",
            "SVM_word2vec": "基于Word2Vec词向量的支持向量机，能够捕捉语义信息",
            "DistilBERT": "基于预训练语言模型的深度学习分类器，具有强大的语义理解能力"
        }
        return descriptions.get(model_name, "暂无描述")

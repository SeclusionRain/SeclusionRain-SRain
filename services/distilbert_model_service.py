"""
DistilBERT情感分析模型服务
用于集成到现有的Web应用中
"""
import os

# 尝试导入torch和transformers库
try:
    import torch
    from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"警告: 未安装必要的依赖库(torch/transformers): {e}")
    TORCH_AVAILABLE = False

class DistilBertModelService:
    """
    DistilBERT情感分析模型服务类
    """
    def __init__(self, model_path=None):
        """
        初始化模型服务
        
        Args:
            model_path: 模型路径，如果为None则使用默认路径或基础模型
        """
        self.available = TORCH_AVAILABLE
        
        if not self.available:
            print("警告: DistilBERT模型服务初始化失败，torch/transformers不可用")
            return
            
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model_path = "d:/BSXM/main/models/distilbert_sentiment_model_new" if model_path is None else model_path
            
            # 加载分词器 - 优先从本地路径加载
            try:
                self.tokenizer = DistilBertTokenizer.from_pretrained(self.model_path)
                print(f"成功从本地加载分词器: {self.model_path}")
            except Exception as e:
                print(f"无法从本地加载分词器，尝试使用基础分词器: {e}")
                self.tokenizer = DistilBertTokenizer.from_pretrained(
                    "distilbert-base-multilingual-cased",
                    local_files_only=True  # 强制使用本地缓存，如果没有则报错
                )
            
            # 尝试加载训练好的模型，如果失败则使用基础模型
            try:
                self.model = DistilBertForSequenceClassification.from_pretrained(self.model_path)
                print(f"成功加载模型: {self.model_path}")
            except Exception as e:
                print(f"无法加载训练好的模型，使用基础模型: {e}")
                self.model = DistilBertForSequenceClassification.from_pretrained(
                    "distilbert-base-multilingual-cased", 
                    num_labels=2
                )
            
            self.model.to(self.device)
            self.model.eval()
        except Exception as e:
            print(f"DistilBERT模型服务初始化异常: {e}")
            self.available = False
    
    def _preprocess(self, text, max_length=128):
        """
        预处理文本
        
        Args:
            text: 输入文本
            max_length: 最大序列长度
            
        Returns:
            处理后的输入张量
        """
        if not self.available:
            raise ValueError("DistilBERT模型服务不可用")
        
        # 验证和处理文本输入
        if text is None:
            text = ""
        elif not isinstance(text, str):
            text = str(text)
        
        # 显式指定text参数名，确保正确传递
        inputs = self.tokenizer(
            text=text, 
            max_length=max_length, 
            padding="max_length", 
            truncation=True, 
            return_tensors="pt"
        )
        return inputs
    
    def predict(self, text):
        """
        预测单个文本的情感
        
        Args:
            text: 输入文本
            
        Returns:
            包含预测结果的字典
        """
        if not self.available:
            return {
                "text": text,
                "sentiment": "未知",
                "label": -1,
                "probability": 0.0,
                "error": "服务不可用"
            }
            
        try:
            # 确保文本有效
            if text is None:
                return {
                    "text": text,
                    "sentiment": "未知",
                    "label": -1,
                    "probability": 0.0,
                    "error": "输入文本为None"
                }
                
            inputs = self._preprocess(text)
            
            with torch.no_grad():
                # 确保正确传递模型输入参数
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                # 显式提取并传递必要参数
                outputs = self.model(
                    input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask']
                )
                
                # 计算概率
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=1)
                
                # 获取预测类别
                prediction = torch.argmax(probabilities, dim=1).item()
                
                # 获取置信度
                confidence = probabilities[0, prediction].item()
            
            # 构建结果
            sentiment = "积极" if prediction == 1 else "消极"
            
            return {
                "text": text,
                "sentiment": sentiment,
                "label": prediction,
                "probability": confidence
            }
        except Exception as e:
            print(f"DistilBERT模型预测过程中出错: {e}")
            return {
                "text": text,
                "sentiment": "未知",
                "label": -1,
                "probability": 0.0,
                "error": str(e)
            }
    
    def batch_predict(self, texts):
        """
        批量预测文本情感
        
        Args:
            texts: 文本列表
            
        Returns:
            预测结果列表
        """
        results = []
        # 确保texts是列表
        if not isinstance(texts, list):
            texts = [texts]
            
        for text in texts:
            try:
                result = self.predict(text)
                results.append(result)
            except Exception as e:
                print(f"处理文本 '{text}' 时出错: {e}")
                results.append({
                    "text": text,
                    "sentiment": "未知",
                    "label": -1,
                    "probability": 0.0,
                    "error": str(e)
                })
        return results

# 全局模型服务实例
global_model_service = None

def init_model_service(model_path=None):
    """
    初始化全局模型服务实例
    
    Args:
        model_path: 模型路径
    """
    global global_model_service
    if global_model_service is None:
        global_model_service = DistilBertModelService(model_path)
    return global_model_service

def predict_sentiment(model_name, texts):
    """
    统一的预测接口，供web应用调用
    
    Args:
        model_name: 模型名称（用于兼容性）
        texts: 文本列表或单个文本
        
    Returns:
        预测结果列表
    """
    try:
        # 初始化全局服务实例
        service = init_model_service()
        
        # 确保输入是列表
        if isinstance(texts, str):
            texts = [texts]
            
        # 执行预测
        return service.batch_predict(texts)
    except Exception as e:
        print(f"预测过程中发生错误: {e}")
        # 返回默认结果
        if isinstance(texts, str):
            return [{
                "text": texts,
                "sentiment": "未知",
                "label": -1,
                "probability": 0.0,
                "error": str(e)
            }]
        else:
            return [{
                "text": text,
                "sentiment": "未知",
                "label": -1,
                "probability": 0.0,
                "error": str(e)
            } for text in texts]
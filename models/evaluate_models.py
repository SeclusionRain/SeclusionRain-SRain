"""
模型批量评估脚本

该脚本用于批量加载已训练好的模型，在标准测试集上评估其性能，并将结果统一保存到CSV文件中。

[重要] 前提条件:
1. 所有模型的 .pkl 文件和特征提取器 .pkl 文件必须与此脚本位于同一目录下。
2. Word2Vec 模型需要 'word2vec.txt' 文件位于同一目录下。

使用方法:
python evaluate_models.py --data_path <PATH_TO_DATA>

输出:
脚本执行完毕后，会生成一个名为 'evaluation_summary.csv' 的文件，其中包含所有模型的评估指标。
"""
import re
import jieba
import joblib
import argparse
import numpy as np
import pandas as pd
from gensim.models import KeyedVectors
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.feature_extraction.text import CountVectorizer

# --- 可配置参数 ---
# 将您希望进行批量评估的模型名称添加到此列表中
MODELS_TO_EVALUATE = [
    "决策树_词袋模型",
    "决策树_tfidf",
    "朴素贝叶斯_tfidf",
    "SVM_tfidf",
    "SVM_word2vec",
    "DistilBERT"
]

# 在程序开始时加载停用词列表
with open('./models/stoplist.txt', 'r', encoding='UTF-8') as stop_path:
    stop_words = set(stop_path.read().split())

def load_data(file_path):
    """加载CSV数据集"""
    try:
        dataset = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        dataset = pd.read_csv(file_path, encoding='gb18030')
    print(f"数据集 '{file_path}' 加载成功，共 {len(dataset)} 条记录。")
    return dataset

def clean_and_segment_text(input_text):
    """文本清洗和分词"""
    cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', str(input_text))
    words = jieba.cut(cleaned_text)
    words = filter(lambda w: w not in stop_words and w.strip(), words)
    return ' '.join(words)

# --- Word2Vec specific functions ---
def average_word_vectors(words, model, vocabulary, num_features):
    feature_vector = np.zeros((num_features,), dtype='float64')
    nwords = 0
    for word in words:
        if word in vocabulary:
            nwords += 1
            feature_vector = np.add(feature_vector, model[word])
    if nwords:
        feature_vector = np.divide(feature_vector, nwords)
    return feature_vector

def averaged_word_vectorizer(corpus, model, num_features):
    vocabulary = set(model.index_to_key)
    features = [average_word_vectors(tokenized_sentence, model, vocabulary, num_features) for tokenized_sentence in corpus]
    return np.array(features)

def get_word_vectors(data, model):
    words_art = [text.split() for text in data]
    return averaged_word_vectorizer(words_art, model, num_features=100)

def main():
    parser = argparse.ArgumentParser(description="模型批量评估脚本")
    parser.add_argument('--data_path', type=str, required=True,
                        help='用于评估的数据集文件路径 (例如: SinaDataset/weibo_senti_100k.csv)')
    args = parser.parse_args()

    # 1. 加载和预处理数据
    print("\n--- 步骤 1: 加载和预处理数据 ---")
    dataset = load_data(args.data_path)
    dataset['review_cleaned'] = dataset['review'].apply(clean_and_segment_text)

    # 2. 分割数据集
    print("\n--- 步骤 2: 分割数据集 ---")
    _, x_test, _, y_test = train_test_split(dataset['review_cleaned'], dataset['label'], test_size=0.2, random_state=7)
    print(f"测试集大小: {len(x_test)} 条记录。")

    results_list = []

    # 3. 循环评估每个模型
    for model_name in MODELS_TO_EVALUATE:
        print(f"\n--- 正在评估模型: {model_name} ---")
        x_test_vect = None
        model_path = ''

        try:
            if model_name == "决策树_词袋模型":
                model_path = 'Decision_Tree_BOW.pkl'
                vocabulary = joblib.load('Decision_Tree_BOW_feature.pkl')
                vect = CountVectorizer(decode_error="replace", vocabulary=vocabulary)
                x_test_vect = vect.transform(x_test)
            elif model_name == "决策树_tfidf":
                model_path = 'Decision_Tree_tfidf.pkl'
                vect_path = 'Decision_Tree_tfidf_feature.pkl'       
                vect = joblib.load(vect_path)
                x_test_vect = vect.transform(x_test)
            elif model_name == "朴素贝叶斯_tfidf":
                model_path = 'Naive_Bayes.pkl'
                vect_path = 'Naive_Bayes_feature.pkl'
                vect = joblib.load(vect_path)
                x_test_vect = vect.transform(x_test)
            elif model_name == "SVM_tfidf":
                model_path = 'SVM_tfidf.pkl'
                vect_path = 'SVM_feature_tfidf.pkl'
                vect = joblib.load(vect_path)
                x_test_vect = vect.transform(x_test)
            elif model_name == "SVM_word2vec":
                model_path = 'SVM_word2vect.pkl'
                print("加载 Word2Vec 模型...")
                w2v_model = KeyedVectors.load_word2vec_format("word2vec.txt", binary=False)
                x_test_vect = get_word_vectors(x_test, w2v_model)
            elif model_name == "DistilBERT":
                model_path = 'distilbert_sentiment_model_new'
                tokenizer = DistilBertTokenizer.from_pretrained(model_path)
                model = DistilBertForSequenceClassification.from_pretrained(model_path)
                model.to(device)
                model.eval()
                x_test_vect = tokenizer(list(x_test), padding=True, truncation=True, max_length=128, return_tensors='pt')
                x_test_vect = {k: v.to(device) for k, v in x_test_vect.items()}
                with torch.no_grad():
                    outputs = model(**x_test_vect)
                y_pred = torch.argmax(outputs.logits, dim=1).cpu().numpy()
            else:
                print(f"未配置模型 {model_name} 的评估。")
                continue
            
            model = joblib.load(model_path)
            y_pred = model.predict(x_test_vect)

            # 解析分类报告
            report_dict = classification_report(y_test, y_pred, target_names=['消极', '积极'], output_dict=True)
            
            results_list.append({
                'Model': model_name,
                'Accuracy': report_dict['accuracy'],
                'Precision (Positive)': report_dict['积极']['precision'],
                'Recall (Positive)': report_dict['积极']['recall'],
                'F1-Score (Positive)': report_dict['积极']['f1-score'],
                'Precision (Negative)': report_dict['消极']['precision'],
                'Recall (Negative)': report_dict['消极']['recall'],
                'F1-Score (Negative)': report_dict['消极']['f1-score'],
            })
            print(f"模型 {model_name} 评估完成。")

        except FileNotFoundError as e:
            print(f"错误: 找不到模型或特征文件 for {model_name}。请确保文件存在。 {e}")
        except Exception as e:
            print(f"评估模型 {model_name} 时发生未知错误: {e}")

    # 4. 保存结果到CSV
    if results_list:
        results_df = pd.DataFrame(results_list)
        results_df.to_csv('evaluation_summary.csv', index=False, encoding='utf_8_sig')
        print("\n--- 所有模型评估完成 ---")
        print("评估结果已保存到 'evaluation_summary.csv'")
        print(results_df.round(4))
    else:
        print("\n没有模型被成功评估。")

if __name__ == "__main__":
    main()

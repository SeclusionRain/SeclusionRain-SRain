"""
命令行情感分析工具

使用方法:
python cli_demo.py --algorithm <ALGORITHM> --input <INPUT>

参数说明:
--algorithm:  指定要使用的模型算法。
              可选值:
              - "决策树_词袋模型"
              - "决策树_tfidf"
              - "朴素贝叶斯_tfidf"
              - "SVM_tfidf"
              - "SVM_word2vec"

--input:      输入要分析的文本、URL或CSV文件路径。
              示例:
              - 单句文本: "这件衣服质量真好"
              - URL: "https://news.ifeng.com/c/8S4z2f5z1xG"
              - 文件路径: "SinaDataset/test.csv"
"""
import re
import os
import glob
import json
import jieba
import joblib
import urllib.parse
import numpy as np
import pandas as pd
import argparse
import urllib.request
from datetime import datetime
from gensim.models import KeyedVectors
from sklearn.feature_extraction.text import CountVectorizer

# 在程序开始时加载停用词列表
with open('./stoplist.txt', 'r', encoding='UTF-8') as stop_path:
    stop_words = set(stop_path.read().split())

# --- Spider Functions (from demo.py) ---
def get_lasteleven(n_url):
    return n_url[-11:]

def create_page(page, url):
    data = {
        'p': page,
        'pageSize': 20,
    }
    base_url = 'https://comment.ifeng.com/get.php?orderby=create_time&docUrl=ucms_' + url + '&format=js&job=1&'
    data_url = base_url + urllib.parse.urlencode(data)
    return data_url

def fetch_comments(url, headers):
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    html = response.read().decode('utf-8')
    json_str = html.split('=', 1)[1].strip(';')
    data = json.loads(json_str)
    return data['comments']

def convert_timestamp(timestamp):
    utc_time = datetime.utcfromtimestamp(int(timestamp))
    local_time = utc_time.strftime('%Y-%m-%d %H:%M:%S')
    return local_time

def get_unique_filename(filename):
    if os.path.exists(filename):
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename_without_ext, extension = os.path.splitext(filename)
        new_filename = f"{filename_without_ext}_{timestamp}{extension}"
        return new_filename
    return filename

def spider_main(n_url):
    print("正在获取评论数据，请稍后...\n")
    url = get_lasteleven(n_url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
    }
    all_comments = pd.DataFrame()
    page = 1
    while True:
        page_url = create_page(page, url)
        try:
            comments = fetch_comments(page_url, headers)
            if not comments:
                break
            comments_data = [{
                'uname': comment['uname'],
                'create_time': convert_timestamp(comment['create_time']),
                'comment_contents': comment['comment_contents']
            } for comment in comments]
            df = pd.DataFrame(comments_data)
            all_comments = pd.concat([all_comments, df], ignore_index=True)
            page += 1
        except Exception as e:
            print(f"抓取第 {page} 页时出错: {e}")
            break
    unique_filename = get_unique_filename('SinaDataset/crawled_comments.csv')
    all_comments.to_csv(unique_filename, index=False, encoding='utf_8_sig')
    print(f'所有评论信息已保存到CSV文件：{unique_filename}')
    return unique_filename

# --- Core Logic Functions (from demo.py) ---
def load_data(file_path):
    try:
        dataset = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        dataset = pd.read_csv(file_path, encoding='gb18030')
    return dataset

def load_model_and_predict(model_path, X_test_vect):
    model = joblib.load(model_path)
    return model.predict(X_test_vect)

def clean_and_segment_text(input_text):
    cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', str(input_text))
    words = jieba.cut(cleaned_text)
    words = filter(lambda w: w not in stop_words and w.strip(), words)
    return ' '.join(words)

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

# --- Main CLI Logic ---
def main():
    parser = argparse.ArgumentParser(description="命令行情感分析工具")
    parser.add_argument('--algorithm', type=str, required=True, 
                        choices=["决策树_词袋模型", '决策树_tfidf', "朴素贝叶斯_tfidf", 'SVM_tfidf', 'SVM_word2vec'],
                        help='选择要使用的模型算法')
    parser.add_argument('--input', type=str, required=True, 
                        help='输入要分析的文本、URL或CSV文件路径')

    args = parser.parse_args()

    # --- Input Processing ---
    input_text = args.input
    is_single_sentence = False

    if os.path.isfile(input_text):
        print(f"从文件 '{input_text}' 加载数据...")
        test_data = load_data(input_text)
        X_new_test = test_data['comment_contents']
        X_new_test_tokenized = X_new_test.apply(clean_and_segment_text)
    elif input_text.startswith('http://') or input_text.startswith('https://'):
        print(f"从URL '{input_text}' 爬取数据...")
        csv_file = spider_main(input_text)
        test_data = load_data(csv_file)
        X_new_test = test_data['comment_contents']
        X_new_test_tokenized = X_new_test.apply(clean_and_segment_text)
    else:
        print("分析单句文本...")
        is_single_sentence = True
        X_new_test_tokenized = pd.Series([clean_and_segment_text(input_text)])

    # --- Model Loading and Prediction ---
    print(f"使用模型 '{args.algorithm}' 进行预测...")
    selected_algorithm = args.algorithm
    if selected_algorithm == "朴素贝叶斯_tfidf":
        model_path = 'Naive_Bayes.pkl'
        vect_path = 'Naive_Bayes_feature.pkl'
        vect = joblib.load(vect_path)
        X_new_test_vect = vect.transform(X_new_test_tokenized)
    elif selected_algorithm == "决策树_词袋模型":
        model_path = 'Decision_Tree_BOW.pkl'
        vocabulary = joblib.load('Decision_Tree_BOW_feature.pkl')
        vect = CountVectorizer(decode_error="replace", vocabulary=vocabulary)
        X_new_test_vect = vect.transform(X_new_test_tokenized)
    elif selected_algorithm == "决策树_tfidf":
        model_path = 'Decision_Tree_tfidf.pkl'
        vect_path = 'Decision_Tree_tfidf_feature.pkl'
        vect = joblib.load(vect_path)
        X_new_test_vect = vect.transform(X_new_test_tokenized)
    elif selected_algorithm == "SVM_tfidf":
        model_path = 'SVM_tfidf.pkl'
        vect_path = 'SVM_feature_tfidf.pkl'
        vect = joblib.load(vect_path)
        X_new_test_vect = vect.transform(X_new_test_tokenized)
    elif selected_algorithm == "SVM_word2vec":
        model_path = 'SVM_word2vect.pkl'
        w2v_model = KeyedVectors.load_word2vec_format("word2vec.txt", binary=False)
        X_new_test_vect = get_word_vectors(X_new_test_tokenized, w2v_model)
    
    new_predictions = load_model_and_predict(model_path, X_new_test_vect)

    # --- Output Results ---
    print("\n--- 分析结果 ---")
    if is_single_sentence:
        sentiment = '积极' if new_predictions[0] == 1 else '消极'
        print(f"输入文本: {input_text}")
        print(f"预测情感: {sentiment}")
    else:
        test_data['predicted_sentiment'] = new_predictions
        test_data['predicted_sentiment'] = test_data['predicted_sentiment'].map({1: '积极', 0: '消极'})
        for index, row in test_data.iterrows():
            print(f"评论: {row['comment_contents']} -> 情感: {row['predicted_sentiment']}")
    print("--- 分析完成 ---")

if __name__ == "__main__":
    main()

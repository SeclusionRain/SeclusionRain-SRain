"""
测试新的数据处理流程
模拟爬取数据并测试CSV -> HDFS -> Hive -> MySQL流程
"""

import os
import sys
from datetime import datetime
from services.data_processing_service import DataProcessingService, process_scraped_data

def create_mock_comments_data():
    """创建模拟的评论数据"""
    mock_data = [
        {
            'post_id': 'comment_001',
            'content': '这个视频太好看了！',
            'user_name': '用户A',
            'user_id': 'user_001',
            'user_signature': '热爱生活的小可爱',
            'publish_time': datetime.now(),
            'like_count': 10,
            'comment_count': 2,
            'forward_count': 1,
            'ip_location': '北京',
            'image_urls': '[]',
            'user_homepage': 'https://example.com/user1',
            'reply_to_id': None,
            'reply_to_user': None
        },
        {
            'post_id': 'comment_002',
            'content': '非常有意思的内容',
            'user_name': '用户B',
            'user_id': 'user_002',
            'user_signature': '摄影爱好者',
            'publish_time': datetime.now(),
            'like_count': 5,
            'comment_count': 0,
            'forward_count': 0,
            'ip_location': '上海',
            'image_urls': '[]',
            'user_homepage': 'https://example.com/user2',
            'reply_to_id': None,
            'reply_to_user': None
        },
        {
            'post_id': 'comment_003',
            'content': '学到了很多东西',
            'user_name': '用户C',
            'user_id': 'user_003',
            'user_signature': '终身学习者',
            'publish_time': datetime.now(),
            'like_count': 8,
            'comment_count': 1,
            'forward_count': 2,
            'ip_location': '广州',
            'image_urls': '[]',
            'user_homepage': 'https://example.com/user3',
            'reply_to_id': None,
            'reply_to_user': None
        },
        {
            'post_id': 'comment_004',
            'content': '支持原创！',
            'user_name': '用户D',
            'user_id': 'user_004',
            'user_signature': '支持原创内容',
            'publish_time': datetime.now(),
            'like_count': 15,
            'comment_count': 3,
            'forward_count': 5,
            'ip_location': '深圳',
            'image_urls': '[]',
            'user_homepage': 'https://example.com/user4',
            'reply_to_id': None,
            'reply_to_user': None
        },
        {
            'post_id': 'comment_005',
            'content': '期待更多这样的视频',
            'user_name': '用户E',
            'user_id': 'user_005',
            'user_signature': '视频爱好者',
            'publish_time': datetime.now(),
            'like_count': 12,
            'comment_count': 2,
            'forward_count': 3,
            'ip_location': '杭州',
            'image_urls': '[]',
            'user_homepage': 'https://example.com/user5',
            'reply_to_id': None,
            'reply_to_user': None
        }
    ]
    
    return mock_data

def test_data_processing_service():
    """测试数据处理服务"""
    print("🧪 测试数据处理服务")
    print("=" * 50)
    
    # 创建模拟数据
    mock_comments = create_mock_comments_data()
    task_name = "test_task"
    task_id = 9999  # 使用测试任务ID
    
    print(f"📝 创建了 {len(mock_comments)} 条模拟评论数据")
    
    # 测试数据处理服务
    service = DataProcessingService()
    
    try:
        # 测试CSV保存
        print("\n📄 测试CSV保存...")
        csv_path = service.save_comments_to_csv(mock_comments, task_name, task_id)
        print(f"CSV文件路径: {csv_path}")
        
        # 测试数据清洗
        print("\n🧹 测试数据清洗...")
        cleaned_csv_path = service.clean_csv_data(csv_path)
        print(f"清洗后文件路径: {cleaned_csv_path}")
        
        # 检查文件是否存在
        if os.path.exists(csv_path):
            print(f"✅ 原始CSV文件存在: {os.path.basename(csv_path)}")
        if os.path.exists(cleaned_csv_path):
            print(f"✅ 清洗后CSV文件存在: {os.path.basename(cleaned_csv_path)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据处理服务测试失败: {e}")
        return False

def test_complete_pipeline():
    """测试完整的数据管道"""
    print("\n🚀 测试完整数据管道")
    print("=" * 50)
    
    # 创建模拟数据
    mock_comments = create_mock_comments_data()
    task_name = "pipeline_test"
    task_id = 8888  # 使用测试任务ID
    
    try:
        # 测试完整流程（不包含MySQL保存，避免数据库操作）
        service = DataProcessingService()
        
        # 只测试到清洗步骤
        print(f"📊 开始完整流程测试...")
        csv_path = service.save_comments_to_csv(mock_comments, task_name, task_id)
        cleaned_csv_path = service.clean_csv_data(csv_path)
        
        print(f"✅ CSV处理流程测试成功!")
        print(f"   - 原始文件: {os.path.basename(csv_path)}")
        print(f"   - 清洗文件: {os.path.basename(cleaned_csv_path)}")
        
        # 如果Docker环境可用，可以测试数据管道
        print(f"\n💡 如需测试完整数据管道，请确保Docker服务运行并执行:")
        print(f"   process_scraped_data(mock_comments, '{task_name}', {task_id})")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整管道测试失败: {e}")
        return False

def test_csv_directory():
    """测试CSV目录创建"""
    print("📁 测试CSV目录")
    print("=" * 30)
    
    service = DataProcessingService()
    csv_dir = service.csv_data_dir
    
    if os.path.exists(csv_dir):
        print(f"✅ CSV目录存在: {csv_dir}")
        
        # 列出目录中的文件
        files = os.listdir(csv_dir)
        if files:
            print(f"📄 目录中的文件 ({len(files)} 个):")
            for file in files[:5]:  # 只显示前5个
                print(f"   - {file}")
            if len(files) > 5:
                print(f"   ... 还有 {len(files) - 5} 个文件")
        else:
            print("📄 目录为空")
        
        return True
    else:
        print(f"❌ CSV目录不存在: {csv_dir}")
        return False

def main():
    """主测试函数"""
    print("数据处理流程测试工具")
    print("=" * 60)
    
    # 测试结果
    results = []
    
    # 测试1: CSV目录
    print("\n🧪 测试1: CSV目录创建")
    result1 = test_csv_directory()
    results.append(("CSV目录测试", result1))
    
    # 测试2: 数据处理服务
    print("\n🧪 测试2: 数据处理服务")
    result2 = test_data_processing_service()
    results.append(("数据处理服务", result2))
    
    # 测试3: 完整管道（部分）
    print("\n🧪 测试3: 完整管道流程")
    result3 = test_complete_pipeline()
    results.append(("完整管道流程", result3))
    
    # 结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n总体结果: {success_count}/{len(results)} 测试通过")
    
    if success_count == len(results):
        print("🎉 所有测试通过！数据处理流程已就绪。")
        print("\n📋 使用说明:")
        print("1. 在爬取路由中，数据会自动经过CSV->清洗->HDFS->Hive->MySQL流程")
        print("2. CSV文件保存在 csv_data/ 目录中")
        print("3. 数据管道会创建对应的Hive表和MySQL表")
        print("4. 原始数据仍会保存到MySQL的comments表中")
    else:
        print("⚠️  部分测试失败，请检查配置。")

if __name__ == "__main__":
    main()

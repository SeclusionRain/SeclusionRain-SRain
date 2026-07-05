"""
测试Docker数据管道工具类
验证utils.docker_data_pipeline的功能
"""

import pandas as pd
import os
from utils.docker_data_pipeline import DockerDataPipeline, process_csv_with_docker_pipeline

def create_sample_data():
    """创建示例数据"""
    print("创建示例数据...")
    data = {
        'user_id': [1, 2, 3, 4, 5, 6],
        'comment': ['很好用', '不错的产品', '质量一般', '非常满意', '价格合理', '推荐购买'],
        'sentiment': ['positive', 'positive', 'neutral', 'positive', 'neutral', 'positive'],
        'score': [0.85, 0.75, 0.50, 0.95, 0.60, 0.80]
    }
    df = pd.DataFrame(data)
    
    csv_path = 'test_douyin_comments.csv'
    df.to_csv(csv_path, index=False, header=False)  # Hive不需要标题
    
    print(f"✓ 示例数据已创建: {csv_path}")
    print("数据预览:")
    print(df)
    return csv_path

def test_pipeline_class():
    """测试数据管道类"""
    print("\n" + "="*60)
    print("测试DockerDataPipeline类")
    print("="*60)
    
    csv_path = create_sample_data()
    
    # 定义表结构
    hive_columns = {
        'user_id': 'INT',
        'comment': 'STRING',
        'sentiment': 'STRING',
        'score': 'DOUBLE'
    }
    
    mysql_columns = ['user_id', 'comment', 'sentiment', 'score']
    table_name = 'douyin_comments_test'
    
    try:
        with DockerDataPipeline() as pipeline:
            success = pipeline.run_complete_pipeline(
                csv_path, 
                table_name, 
                hive_columns, 
                mysql_columns
            )
            
            if success:
                print("✅ DockerDataPipeline类测试成功！")
                return True
            else:
                print("❌ DockerDataPipeline类测试失败！")
                return False
                
    except Exception as e:
        print(f"❌ DockerDataPipeline类测试异常: {e}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(csv_path):
            os.remove(csv_path)
            print(f"✓ 已清理临时文件: {csv_path}")

def test_convenience_function():
    """测试便捷函数"""
    print("\n" + "="*60)
    print("测试便捷函数")
    print("="*60)
    
    csv_path = create_sample_data()
    
    # 定义表结构
    hive_columns = {
        'user_id': 'INT',
        'comment': 'STRING', 
        'sentiment': 'STRING',
        'score': 'DOUBLE'
    }
    
    mysql_columns = ['user_id', 'comment', 'sentiment', 'score']
    table_name = 'douyin_comments_convenience'
    
    try:
        success = process_csv_with_docker_pipeline(
            csv_path,
            table_name,
            hive_columns,
            mysql_columns
        )
        
        if success:
            print("✅ 便捷函数测试成功！")
            return True
        else:
            print("❌ 便捷函数测试失败！")
            return False
            
    except Exception as e:
        print(f"❌ 便捷函数测试异常: {e}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(csv_path):
            os.remove(csv_path)
            print(f"✓ 已清理临时文件: {csv_path}")

def test_individual_methods():
    """测试单独的方法"""
    print("\n" + "="*60)
    print("测试单独方法")
    print("="*60)
    
    csv_path = create_sample_data()
    
    try:
        pipeline = DockerDataPipeline()
        
        # 测试Docker服务检查
        print("\n1. 测试Docker服务检查...")
        if pipeline.check_docker_services():
            print("✓ Docker服务正常")
        else:
            print("✗ Docker服务异常")
            return False
        
        # 测试获取容器名称
        print("\n2. 测试获取容器名称...")
        container = pipeline.get_namenode_container()
        if container:
            print(f"✓ 找到NameNode容器: {container}")
        else:
            print("✗ 未找到NameNode容器")
            return False
        
        # 测试HDFS上传
        print("\n3. 测试HDFS上传...")
        try:
            hdfs_path = pipeline.upload_csv_to_hdfs(csv_path, 'test_individual.csv')
            print(f"✓ HDFS上传成功: {hdfs_path}")
        except Exception as e:
            print(f"✗ HDFS上传失败: {e}")
            return False
        
        # 测试Hive连接
        print("\n4. 测试Hive连接...")
        if pipeline.connect_hive():
            print("✓ Hive连接成功")
        else:
            print("✗ Hive连接失败")
            return False
        
        # 测试MySQL连接
        print("\n5. 测试MySQL连接...")
        if pipeline.connect_mysql():
            print("✓ MySQL连接成功")
        else:
            print("✗ MySQL连接失败")
            return False
        
        pipeline.close_connections()
        print("✅ 单独方法测试成功！")
        return True
        
    except Exception as e:
        print(f"❌ 单独方法测试异常: {e}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(csv_path):
            os.remove(csv_path)
            print(f"✓ 已清理临时文件: {csv_path}")

def verify_mysql_data(table_name: str):
    """验证MySQL中的数据"""
    print(f"\n验证MySQL表: {table_name}")
    try:
        from utils.db_config import DatabaseConfig
        import pymysql
        
        config = DatabaseConfig.get_config()
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute(f"SHOW TABLES LIKE '{table_name}%'")
        tables = cursor.fetchall()
        
        if tables:
            for table in tables:
                table_name = table[0]
                print(f"✓ 找到表: {table_name}")
                
                # 检查数据
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - 数据行数: {count}")
                
                # 显示前3行
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print("  - 前3行数据:")
                for i, row in enumerate(rows):
                    print(f"    行{i+1}: {row}")
        else:
            print("✗ 未找到相关表")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ 验证MySQL数据失败: {e}")

def main():
    """主测试函数"""
    print("Docker数据管道工具类测试")
    print("=" * 60)
    
    test_results = []
    
    # 测试1: 单独方法测试
    print("\n🧪 测试1: 单独方法测试")
    result1 = test_individual_methods()
    test_results.append(("单独方法测试", result1))
    
    # 测试2: 完整管道类测试
    print("\n🧪 测试2: 完整管道类测试")
    result2 = test_pipeline_class()
    test_results.append(("管道类测试", result2))
    
    # 测试3: 便捷函数测试
    print("\n🧪 测试3: 便捷函数测试")
    result3 = test_convenience_function()
    test_results.append(("便捷函数测试", result3))
    
    # 验证MySQL数据
    print("\n🔍 验证MySQL数据")
    verify_mysql_data("douyin_comments")
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    success_count = 0
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n总体结果: {success_count}/{len(test_results)} 测试通过")
    
    if success_count == len(test_results):
        print("🎉 所有测试通过！Docker数据管道工具类工作正常。")
        print("\n✅ 工具类已就绪，可以在项目中使用：")
        print("   from utils.docker_data_pipeline import DockerDataPipeline")
        print("   from utils.docker_data_pipeline import process_csv_with_docker_pipeline")
    else:
        print("⚠️  部分测试失败，请检查配置和服务状态。")

if __name__ == "__main__":
    main()

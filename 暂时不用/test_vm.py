"""
VM虚拟机数据管道测试脚本
测试CSV -> HDFS -> Hive -> MySQL的完整数据流程
"""

import os
import pandas as pd
from utils.vm_data_pipeline import VMDataPipeline, process_csv_with_vm_pipeline
from utils.vm_config import VMConfig


def test_vm_config():
    """测试VM配置"""
    print("=" * 60)
    print("测试VM配置")
    print("=" * 60)
    
    vm_config = VMConfig.get_vm_config()
    print(f"VM主机: {vm_config['host']}")
    print(f"VM用户: {vm_config['user']}")
    print(f"VM名称: {vm_config['name']}")
    
    hdfs_config = VMConfig.get_hdfs_config()
    print(f"HDFS URL: {hdfs_config['url']}")
    print(f"HDFS用户: {hdfs_config['user']}")
    
    hive_config = VMConfig.get_hive_config()
    print(f"Hive主机: {hive_config['host']}")
    print(f"Hive端口: {hive_config['port']}")
    print(f"Hive数据库: {hive_config['database']}")
    
    print("✓ VM配置测试通过")
    print()


def test_vm_pipeline_basic():
    """测试VM管道基本功能"""
    print("=" * 60)
    print("测试VM管道基本功能")
    print("=" * 60)
    
    pipeline = VMDataPipeline()
    
    # 测试SSH连接
    print("测试SSH连接...")
    if pipeline.connect_ssh():
        print("✓ SSH连接成功")
        
        # 测试执行简单命令
        print("\n测试执行命令...")
        exit_code, stdout, stderr = pipeline.execute_ssh_command("whoami")
        if exit_code == 0:
            print(f"✓ 命令执行成功，当前用户: {stdout.strip()}")
        
        # 测试HDFS命令
        print("\n测试HDFS命令...")
        exit_code, stdout, stderr = pipeline.execute_ssh_command("hdfs version")
        if exit_code == 0:
            print(f"✓ HDFS可用")
            print(stdout[:200])  # 只显示前200个字符
        
        pipeline.close_connections()
        print("\n✓ VM管道基本功能测试通过")
    else:
        print("✗ SSH连接失败")
    
    print()


def test_complete_pipeline():
    """测试完整数据管道"""
    print("=" * 60)
    print("测试完整数据管道")
    print("=" * 60)
    
    # 创建测试CSV文件
    test_csv = "test_vm_pipeline_data.csv"
    test_data = {
        'user_id': [1, 2, 3, 4, 5],
        'username': ['user1', 'user2', 'user3', 'user4', 'user5'],
        'comment': ['很好', '不错', '一般', '很差', '非常好'],
        'sentiment': ['positive', 'positive', 'neutral', 'negative', 'positive']
    }
    df = pd.DataFrame(test_data)
    df.to_csv(test_csv, index=False)
    print(f"✓ 测试CSV文件已创建: {test_csv}")
    
    # 定义Hive表结构
    hive_columns = {
        'user_id': 'INT',
        'username': 'STRING',
        'comment': 'STRING',
        'sentiment': 'STRING'
    }
    
    # MySQL列名
    mysql_columns = ['user_id', 'username', 'comment', 'sentiment']
    
    # 运行完整管道
    print("\n开始运行完整数据管道...")
    success = process_csv_with_vm_pipeline(
        csv_path=test_csv,
        table_name='test_vm_pipeline',
        hive_columns=hive_columns,
        mysql_columns=mysql_columns
    )
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 完整数据管道测试成功！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ 完整数据管道测试失败")
        print("=" * 60)
    
    # 清理测试文件
    if os.path.exists(test_csv):
        os.remove(test_csv)
        print(f"✓ 测试文件已清理: {test_csv}")


def test_with_existing_csv():
    """使用现有CSV文件测试"""
    print("=" * 60)
    print("使用现有CSV文件测试")
    print("=" * 60)
    
    # 查找csv_data目录中的清洗后的CSV文件
    csv_dir = "csv_data"
    if not os.path.exists(csv_dir):
        print(f"✗ CSV目录不存在: {csv_dir}")
        return
    
    # 查找cleaned CSV文件
    csv_files = [f for f in os.listdir(csv_dir) if f.endswith('_cleaned.csv')]
    if not csv_files:
        print(f"✗ 未找到清洗后的CSV文件")
        return
    
    # 使用第一个找到的文件
    csv_file = os.path.join(csv_dir, csv_files[0])
    print(f"使用CSV文件: {csv_file}")
    
    # 读取CSV获取列信息
    df = pd.read_csv(csv_file, nrows=5)
    print(f"CSV文件包含 {len(df.columns)} 列")
    print(f"列名: {list(df.columns)}")
    
    # 自动生成Hive列定义（所有列都设为STRING类型）
    hive_columns = {col: 'STRING' for col in df.columns}
    mysql_columns = list(df.columns)
    
    # 生成表名
    table_name = os.path.basename(csv_file).replace('.csv', '').replace('_cleaned', '')
    table_name = f"douyin_{table_name}"
    
    print(f"\n表名: {table_name}")
    print("Hive列定义:")
    for col, dtype in hive_columns.items():
        print(f"  {col}: {dtype}")
    
    # 运行管道
    print("\n开始运行数据管道...")
    success = process_csv_with_vm_pipeline(
        csv_path=csv_file,
        table_name=table_name,
        hive_columns=hive_columns,
        mysql_columns=mysql_columns
    )
    
    if success:
        print("\n" + "=" * 60)
        print(f"🎉 数据管道成功处理文件: {csv_file}")
        print(f"Hive表: {table_name}")
        print(f"MySQL表: {table_name}_mysql")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"✗ 数据管道处理失败: {csv_file}")
        print("=" * 60)


if __name__ == "__main__":
    import sys
    
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "VM虚拟机数据管道测试" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 根据命令行参数选择测试
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == 'config':
            test_vm_config()
        elif test_type == 'basic':
            test_vm_pipeline_basic()
        elif test_type == 'complete':
            test_complete_pipeline()
        elif test_type == 'existing':
            test_with_existing_csv()
        else:
            print(f"未知的测试类型: {test_type}")
            print("可用选项: config, basic, complete, existing")
    else:
        # 默认运行所有测试
        print("运行所有测试...\n")
        test_vm_config()
        test_vm_pipeline_basic()
        
        # 询问是否运行完整管道测试
        response = input("\n是否运行完整数据管道测试？(y/n): ")
        if response.lower() == 'y':
            test_complete_pipeline()

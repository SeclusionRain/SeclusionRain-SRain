"""
VM环境诊断脚本
检查SSH连接、Hadoop/Hive服务状态
"""

from utils.vm_data_pipeline import VMDataPipeline
from utils.vm_config import VMConfig
import sys


def check_ssh_connection():
    """检查SSH连接"""
    print("\n" + "=" * 60)
    print("1. 检查SSH连接")
    print("=" * 60)
    
    pipeline = VMDataPipeline()
    if pipeline.connect_ssh():
        print("✓ SSH连接成功")
        
        # 测试基本命令
        exit_code, stdout, stderr = pipeline.execute_ssh_command("hostname")
        if exit_code == 0:
            print(f"✓ VM主机名: {stdout.strip()}")
        
        exit_code, stdout, stderr = pipeline.execute_ssh_command("whoami")
        if exit_code == 0:
            print(f"✓ 当前用户: {stdout.strip()}")
        
        pipeline.close_connections()
        return True
    else:
        print("✗ SSH连接失败")
        return False


def check_hadoop_services():
    """检查Hadoop服务"""
    print("\n" + "=" * 60)
    print("2. 检查Hadoop服务")
    print("=" * 60)
    
    pipeline = VMDataPipeline()
    if not pipeline.connect_ssh():
        print("✗ 无法连接SSH")
        return False
    
    # 检查Java进程
    print("\n检查Hadoop进程 (jps)...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command("jps")
    if exit_code == 0:
        print(stdout)
        
        # 检查关键进程
        if 'NameNode' in stdout:
            print("✓ NameNode正在运行")
        else:
            print("✗ NameNode未运行")
        
        if 'DataNode' in stdout:
            print("✓ DataNode正在运行")
        else:
            print("✗ DataNode未运行")
        
        if 'ResourceManager' in stdout:
            print("✓ ResourceManager正在运行")
        else:
            print("⚠ ResourceManager未运行")
    else:
        print(f"✗ 无法执行jps命令: {stderr}")
    
    # 检查HDFS状态
    print("\n检查HDFS状态...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command("hdfs dfsadmin -report")
    if exit_code == 0:
        lines = stdout.split('\n')[:10]  # 只显示前10行
        for line in lines:
            print(line)
        print("✓ HDFS运行正常")
    else:
        print(f"✗ HDFS状态检查失败: {stderr}")
    
    pipeline.close_connections()
    return True


def check_hive_services():
    """检查Hive服务"""
    print("\n" + "=" * 60)
    print("3. 检查Hive服务")
    print("=" * 60)
    
    pipeline = VMDataPipeline()
    if not pipeline.connect_ssh():
        print("✗ 无法连接SSH")
        return False
    
    # 检查Hive进程
    print("\n检查Hive进程...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command("ps aux | grep -i hive | grep -v grep")
    if exit_code == 0 and stdout.strip():
        print("✓ Hive进程正在运行:")
        for line in stdout.strip().split('\n')[:5]:  # 最多显示5行
            print(f"  {line[:100]}")  # 每行最多100字符
    else:
        print("✗ Hive进程未运行")
        print("\n建议启动Hive服务:")
        print("  # 启动Metastore")
        print("  nohup hive --service metastore &")
        print("  # 启动HiveServer2")
        print("  nohup hive --service hiveserver2 &")
    
    # 检查端口10000
    print("\n检查Hive端口10000...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command("netstat -tulpn | grep 10000")
    if exit_code == 0 and stdout.strip():
        print("✓ 端口10000正在监听:")
        print(f"  {stdout.strip()}")
    else:
        print("✗ 端口10000未监听")
        print("\nHiveServer2可能未启动或使用其他端口")
    
    # 检查Hive配置
    print("\n检查Hive配置...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command("ls -la $HIVE_HOME/conf/hive-site.xml")
    if exit_code == 0:
        print("✓ Hive配置文件存在")
    else:
        # 尝试其他常见路径
        exit_code, stdout, stderr = pipeline.execute_ssh_command("find /opt /usr -name hive-site.xml 2>/dev/null | head -1")
        if exit_code == 0 and stdout.strip():
            print(f"✓ Hive配置文件: {stdout.strip()}")
        else:
            print("⚠ 未找到Hive配置文件")
    
    pipeline.close_connections()
    return True


def check_network():
    """检查网络连通性"""
    print("\n" + "=" * 60)
    print("4. 检查网络连通性")
    print("=" * 60)
    
    config = VMConfig()
    vm_config = config.get_vm_config()
    hdfs_config = config.get_hdfs_config()
    yarn_config = config.get_yarn_config()
    
    print(f"\nVM主机: {vm_config['host']}")
    print(f"HDFS Web UI: {hdfs_config['url']}")
    print(f"YARN Web UI: {yarn_config['url']}")
    
    print("\n请在浏览器中访问以下URL验证服务:")
    print(f"  - HDFS: {hdfs_config['url']}")
    print(f"  - YARN: {yarn_config['url']}")


def check_hive_metastore():
    """检查Hive Metastore"""
    print("\n" + "=" * 60)
    print("5. 检查Hive Metastore")
    print("=" * 60)
    
    pipeline = VMDataPipeline()
    if not pipeline.connect_ssh():
        print("✗ 无法连接SSH")
        return False
    
    # 检查Metastore数据库连接
    print("\n检查Metastore配置...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command(
        "grep -A 5 'javax.jdo.option.ConnectionURL' $HIVE_HOME/conf/hive-site.xml 2>/dev/null || "
        "grep -A 5 'javax.jdo.option.ConnectionURL' /opt/*/conf/hive-site.xml 2>/dev/null | head -20"
    )
    if exit_code == 0 and stdout.strip():
        print("Metastore连接配置:")
        print(stdout[:500])  # 最多显示500字符
    else:
        print("⚠ 无法读取Metastore配置")
    
    # 检查Metastore端口
    print("\n检查Metastore端口5270...")
    exit_code, stdout, stderr = pipeline.execute_ssh_command("netstat -tulpn | grep 5270")
    if exit_code == 0 and stdout.strip():
        print("✓ Metastore端口5270正在监听:")
        print(f"  {stdout.strip()}")
    else:
        print("✗ Metastore端口5270未监听")
        print("\n建议启动Metastore:")
        print("  nohup hive --service metastore > /tmp/metastore.log 2>&1 &")
    
    pipeline.close_connections()
    return True


def suggest_fixes():
    """建议修复方案"""
    print("\n" + "=" * 60)
    print("修复建议")
    print("=" * 60)
    
    print("\n如果Hive服务未运行，请在VM上执行以下命令:")
    print("\n1. 启动Metastore:")
    print("   nohup hive --service metastore > /tmp/metastore.log 2>&1 &")
    
    print("\n2. 启动HiveServer2:")
    print("   nohup hive --service hiveserver2 > /tmp/hiveserver2.log 2>&1 &")
    
    print("\n3. 验证服务启动:")
    print("   netstat -tulpn | grep 5270   # Metastore")
    print("   netstat -tulpn | grep 5431  # HiveServer2")
    
    print("\n4. 查看日志:")
    print("   tail -f /tmp/metastore.log")
    print("   tail -f /tmp/hiveserver2.log")
    
    print("\n5. 如果端口被占用，修改配置:")
    print("   编辑 $HIVE_HOME/conf/hive-site.xml")
    print("   修改 hive.server2.thrift.port 的值")


def main():
    """主函数"""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "VM环境诊断工具" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # 显示当前配置
    print("\n当前配置:")
    config = VMConfig()
    vm_config = config.get_vm_config()
    hive_config = config.get_hive_config()
    print(f"  VM主机: {vm_config['host']}")
    print(f"  VM用户: {vm_config['user']}")
    print(f"  Hive主机: {hive_config['host']}")
    print(f"  Hive端口: {hive_config['port']}")
    
    # 运行诊断
    try:
        if not check_ssh_connection():
            print("\n⚠ SSH连接失败，无法继续诊断")
            print("请检查:")
            print("  1. VM是否启动: ping 192.168.58.13")
            print("  2. SSH服务是否运行")
            print("  3. 用户名和密码是否正确")
            return
        
        check_hadoop_services()
        check_hive_services()
        check_hive_metastore()
        check_network()
        suggest_fixes()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n诊断过程中出错: {e}")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

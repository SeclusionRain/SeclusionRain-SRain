"""
VM虚拟机环境配置文件
用于连接Hadoop/Hive虚拟机环境
"""

import os
from typing import Dict, Any


class VMConfig:
    """VM虚拟机环境配置类"""
    
    # 虚拟机基础配置
    VM_HOST = os.environ.get('VM_HOST', '192.168.58.13')
    VM_USER = os.environ.get('VM_USER', 'root')
    VM_PASSWORD = os.environ.get('VM_PASSWORD', '123456')
    VM_NAME = os.environ.get('VM_NAME', 'djh')
    
    # 版本信息
    PYTHON_VERSION = os.environ.get('PYTHON_VERSION', '2.7.5')
    HADOOP_VERSION = os.environ.get('HADOOP_VERSION', '3.3.0')
    HIVE_VERSION = os.environ.get('HIVE_VERSION', '3.1.2')
    ZOOKEEPER_VERSION = os.environ.get('ZOOKEEPER_VERSION', '3.4.8')
    
    # HDFS配置
    HDFS_URL = os.environ.get('HDFS_URL', 'http://192.168.58.13:9870/')
    HDFS_USER = os.environ.get('HDFS_USER', 'root')
    HDFS_UPLOAD_PATH = os.environ.get('HDFS_UPLOAD_PATH', '/user/hive/warehouse/')
    
    # YARN配置
    YARN_URL = os.environ.get('YARN_URL', 'http://192.168.58.13:8088/')
    
    # Hive配置
    HIVE_HOST = os.environ.get('HIVE_HOST', 'localhost')
    HIVE_PORT = int(os.environ.get('HIVE_PORT', 10000))
    HIVE_USER = os.environ.get('HIVE_USER', 'root')
    HIVE_PASSWORD = os.environ.get('HIVE_PASSWORD', '123456')
    HIVE_DATABASE = os.environ.get('HIVE_DATABASE', 'default')
    
    # SSH隧道配置（用于连接虚拟机中的Hive）
    SSH_HOST = os.environ.get('SSH_HOST', '192.168.58.13')
    SSH_PORT = int(os.environ.get('SSH_PORT', 22))
    SSH_USER = os.environ.get('SSH_USER', 'root')
    SSH_PASSWORD = os.environ.get('SSH_PASSWORD', '123456')
    SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/root/.ssh/id_rsa')
    
    @classmethod
    def get_vm_config(cls) -> Dict[str, Any]:
        """获取VM配置信息"""
        return {
            'host': cls.VM_HOST,
            'user': cls.VM_USER,
            'password': cls.VM_PASSWORD,
            'name': cls.VM_NAME,
            'python_version': cls.PYTHON_VERSION,
            'hadoop_version': cls.HADOOP_VERSION,
            'hive_version': cls.HIVE_VERSION,
            'zookeeper_version': cls.ZOOKEEPER_VERSION
        }
    
    @classmethod
    def get_hdfs_config(cls) -> Dict[str, Any]:
        """获取HDFS配置"""
        return {
            'url': cls.HDFS_URL,
            'user': cls.HDFS_USER,
            'upload_path': cls.HDFS_UPLOAD_PATH
        }
    
    @classmethod
    def get_yarn_config(cls) -> Dict[str, Any]:
        """获取YARN配置"""
        return {
            'url': cls.YARN_URL
        }
    
    @classmethod
    def get_hive_config(cls) -> Dict[str, Any]:
        """获取Hive连接配置"""
        return {
            'host': cls.HIVE_HOST,
            'port': cls.HIVE_PORT,
            'username': cls.HIVE_USER,
            'password': cls.HIVE_PASSWORD,
            'database': cls.HIVE_DATABASE
        }
    
    @classmethod
    def get_ssh_config(cls) -> Dict[str, Any]:
        """获取SSH配置"""
        return {
            'host': cls.SSH_HOST,
            'port': cls.SSH_PORT,
            'user': cls.SSH_USER,
            'password': cls.SSH_PASSWORD,
            'key_path': cls.SSH_KEY_PATH
        }
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """获取完整配置"""
        return {
            'vm': cls.get_vm_config(),
            'hdfs': cls.get_hdfs_config(),
            'yarn': cls.get_yarn_config(),
            'hive': cls.get_hive_config(),
            'ssh': cls.get_ssh_config()
        }


# 便捷访问配置字典
VM_CONFIG = VMConfig.get_vm_config()
HDFS_CONFIG = VMConfig.get_hdfs_config()
YARN_CONFIG = VMConfig.get_yarn_config()
HIVE_CONFIG = VMConfig.get_hive_config()
SSH_CONFIG = VMConfig.get_ssh_config()


if __name__ == "__main__":
    """配置测试"""
    import json
    
    print("=" * 60)
    print("VM虚拟机环境配置信息")
    print("=" * 60)
    
    all_config = VMConfig.get_all_config()
    print(json.dumps(all_config, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("配置加载成功！")
    print("=" * 60)

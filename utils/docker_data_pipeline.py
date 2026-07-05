"""
Docker环境数据管道工具类
基于成功的test_pipeline_docker_friendly.py实现
支持CSV -> HDFS -> Hive -> MySQL的完整数据流程
"""

import os
import pandas as pd
import pymysql
import subprocess
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from .db_config import DatabaseConfig

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 尝试导入Hive相关包
try:
    from pyhive import hive
    HIVE_AVAILABLE = True
    logger.info("✓ pyhive包可用")
except ImportError as e:
    HIVE_AVAILABLE = False
    logger.warning(f"pyhive包未安装，Hive功能将不可用。错误: {e}")

try:
    from sqlalchemy import create_engine
    SQLALCHEMY_AVAILABLE = True
except ImportError as e:
    SQLALCHEMY_AVAILABLE = False
    logger.warning(f"sqlalchemy包未安装，部分功能将不可用。错误: {e}")


class DockerDataPipelineConfig:
    """Docker环境数据管道配置类"""
    
    # Hive配置
    HIVE_HOST = 'localhost'
    HIVE_PORT = 10000
    HIVE_DATABASE = 'default'
    
    # HDFS路径配置
    HDFS_UPLOAD_PATH = '/user/hive/warehouse/'
    
    # MySQL配置（从DatabaseConfig获取）
    @classmethod
    def get_mysql_config(cls) -> Dict[str, Any]:
        """获取MySQL配置"""
        return DatabaseConfig.get_config()
    
    @classmethod
    def get_hive_connection_params(cls) -> Dict[str, Any]:
        """获取Hive连接参数"""
        return {
            'host': cls.HIVE_HOST,
            'port': cls.HIVE_PORT,
            'database': cls.HIVE_DATABASE
        }


class DockerDataPipeline:
    """Docker环境数据管道主类"""
    
    def __init__(self):
        self.config = DockerDataPipelineConfig()
        self.mysql_conn = None
        self.hive_conn = None
        self.namenode_container = None
        
    def _run_docker_command(self, cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """运行Docker命令，处理编码问题"""
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore',
            timeout=timeout
        )
    
    def get_namenode_container(self) -> Optional[str]:
        """获取namenode容器名称"""
        if self.namenode_container:
            return self.namenode_container
            
        try:
            result = self._run_docker_command(['docker', 'ps', '--format', '{{.Names}}'])
            if result.returncode == 0:
                containers = result.stdout.strip().split('\n')
                for container in containers:
                    if 'namenode' in container.lower():
                        self.namenode_container = container
                        logger.info(f"找到NameNode容器: {container}")
                        return container
            return None
        except Exception as e:
            logger.error(f"获取容器名称失败: {e}")
            return None
    
    def check_docker_services(self) -> bool:
        """检查Docker服务状态"""
        try:
            result = self._run_docker_command(['docker', 'ps'])
            if result.returncode == 0:
                containers = result.stdout.lower()
                namenode_found = 'namenode' in containers
                datanode_found = 'datanode' in containers
                hive_found = 'hive' in containers
                
                logger.info(f"Docker服务状态 - NameNode: {namenode_found}, DataNode: {datanode_found}, Hive: {hive_found}")
                return namenode_found and datanode_found
            return False
        except Exception as e:
            logger.error(f"检查Docker服务失败: {e}")
            return False
    
    def wait_for_services(self, max_retries: int = 30) -> bool:
        """等待Docker服务启动"""
        logger.info("等待Docker服务启动...")
        
        for i in range(max_retries):
            if self.check_docker_services():
                logger.info("✓ Docker容器已启动")
                # 额外等待服务完全初始化
                logger.info("等待服务初始化...")
                time.sleep(10)
                return True
            
            if i < max_retries - 1:
                logger.info(f"等待中... ({i+1}/{max_retries})")
                time.sleep(2)
        
        logger.error("⚠️  Docker容器启动超时")
        return False
    
    def upload_csv_to_hdfs(self, local_csv_path: str, hdfs_filename: Optional[str] = None) -> str:
        """
        通过Docker exec上传CSV文件到HDFS
        
        Args:
            local_csv_path: 本地CSV文件路径
            hdfs_filename: HDFS中的文件名，如果为None则使用原文件名
            
        Returns:
            HDFS文件路径
        """
        if not os.path.exists(local_csv_path):
            raise FileNotFoundError(f"本地文件不存在: {local_csv_path}")
        
        namenode_container = self.get_namenode_container()
        if not namenode_container:
            raise Exception("找不到namenode容器")
        
        if hdfs_filename is None:
            hdfs_filename = os.path.basename(local_csv_path)
        
        hdfs_path = os.path.join(self.config.HDFS_UPLOAD_PATH, hdfs_filename).replace('\\', '/')
        
        try:
            # 复制文件到namenode容器
            copy_cmd = ['docker', 'cp', local_csv_path, f'{namenode_container}:/tmp/']
            result = self._run_docker_command(copy_cmd)
            if result.returncode != 0:
                raise Exception(f"复制文件到容器失败: {result.stderr}")
            
            filename = os.path.basename(local_csv_path)
            logger.info(f"✓ 文件已复制到容器: /tmp/{filename}")
            
            # 在容器内创建HDFS目录
            mkdir_cmd = ['docker', 'exec', namenode_container, 'hdfs', 'dfs', '-mkdir', '-p', self.config.HDFS_UPLOAD_PATH]
            result = self._run_docker_command(mkdir_cmd)
            logger.info(f"✓ HDFS目录创建: {result.returncode == 0}")
            
            # 上传文件到HDFS
            upload_cmd = ['docker', 'exec', namenode_container, 'hdfs', 'dfs', '-put', f'/tmp/{filename}', hdfs_path]
            result = self._run_docker_command(upload_cmd)
            
            if result.returncode == 0:
                logger.info(f"✓ 文件已上传到HDFS: {hdfs_path}")
                return hdfs_path
            else:
                # 如果文件已存在，先删除再上传
                if 'File exists' in result.stderr or 'already exists' in result.stderr:
                    logger.info("文件已存在，删除后重新上传...")
                    rm_cmd = ['docker', 'exec', namenode_container, 'hdfs', 'dfs', '-rm', hdfs_path]
                    self._run_docker_command(rm_cmd)
                    
                    result = self._run_docker_command(upload_cmd)
                    if result.returncode == 0:
                        logger.info(f"✓ 文件已重新上传到HDFS: {hdfs_path}")
                        return hdfs_path
                
                raise Exception(f"HDFS上传失败: {result.stderr}")
                
        except Exception as e:
            logger.error(f"HDFS上传失败: {e}")
            raise
    
    def connect_hive(self) -> bool:
        """连接Hive"""
        if not HIVE_AVAILABLE:
            logger.error("Hive功能不可用：pyhive包未安装")
            return False
        
        max_retries = 10
        for i in range(max_retries):
            try:
                hive_params = self.config.get_hive_connection_params()
                self.hive_conn = hive.connect(**hive_params)
                logger.info("✓ Hive连接成功")
                return True
            except Exception as e:
                if i < max_retries - 1:
                    logger.info(f"等待Hive启动... ({i+1}/{max_retries}): {e}")
                    time.sleep(5)
                else:
                    logger.error(f"Hive连接失败: {e}")
                    return False
        return False
    
    def connect_mysql(self) -> bool:
        """连接MySQL"""
        try:
            mysql_config = self.config.get_mysql_config()
            self.mysql_conn = pymysql.connect(**mysql_config)
            logger.info("✓ MySQL连接成功")
            return True
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return False
    
    def create_hive_table(self, table_name: str, columns: Dict[str, str], hdfs_path: str) -> bool:
        """
        创建Hive表并加载数据
        
        Args:
            table_name: 表名
            columns: 列定义 {'column_name': 'column_type'}
            hdfs_path: HDFS文件路径
            
        Returns:
            是否成功
        """
        if not self.hive_conn:
            if not self.connect_hive():
                return False
        
        try:
            cursor = self.hive_conn.cursor()
            
            # 删除已存在的表
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"✓ 删除旧表（如果存在）: {table_name}")
            
            # 构建列定义
            column_defs = []
            for col_name, col_type in columns.items():
                column_defs.append(f"{col_name} {col_type}")
            
            # 创建表
            create_table_sql = f"""
            CREATE TABLE {table_name} (
                {', '.join(column_defs)}
            ) ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
            STORED AS TEXTFILE
            """
            cursor.execute(create_table_sql)
            logger.info(f"✓ Hive表已创建: {table_name}")
            
            # 从HDFS加载数据
            load_sql = f"LOAD DATA INPATH '{hdfs_path}' INTO TABLE {table_name}"
            cursor.execute(load_sql)
            logger.info(f"✓ 数据已加载到Hive表: {table_name}")
            
            # 验证数据
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"✓ Hive表包含 {count} 行数据")
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"创建Hive表失败: {e}")
            return False
    
    def export_hive_to_mysql(self, hive_table: str, mysql_table: str, 
                           columns: List[str]) -> bool:
        """
        从Hive导出数据到MySQL
        
        Args:
            hive_table: Hive表名
            mysql_table: MySQL表名
            columns: 列名列表
            
        Returns:
            是否成功
        """
        if not self.hive_conn:
            if not self.connect_hive():
                return False
        
        if not self.mysql_conn:
            if not self.connect_mysql():
                return False
        
        try:
            # 从Hive获取数据
            cursor = self.hive_conn.cursor()
            cursor.execute(f"SELECT * FROM {hive_table}")
            hive_data = cursor.fetchall()
            cursor.close()
            
            # 转换为DataFrame
            hive_df = pd.DataFrame(hive_data, columns=columns)
            logger.info(f"✓ 从Hive获取到 {len(hive_df)} 行数据")
            
            # 导出到MySQL
            if SQLALCHEMY_AVAILABLE:
                mysql_config = self.config.get_mysql_config()
                mysql_conn_str = f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}"
                mysql_engine = create_engine(mysql_conn_str)
                
                hive_df.to_sql(mysql_table, mysql_engine, if_exists='replace', index=False)
                logger.info(f"✓ 数据已导出到MySQL表: {mysql_table}")
                
                # 验证MySQL数据
                mysql_df = pd.read_sql(f"SELECT * FROM {mysql_table}", mysql_engine)
                logger.info(f"✓ MySQL表包含 {len(mysql_df)} 行数据")
            else:
                # 使用pymysql直接插入
                self._insert_to_mysql_direct(hive_df, mysql_table)
            
            return True
            
        except Exception as e:
            logger.error(f"导出到MySQL失败: {e}")
            return False
    
    def _insert_to_mysql_direct(self, df: pd.DataFrame, table_name: str):
        """直接使用pymysql插入数据到MySQL"""
        cursor = self.mysql_conn.cursor()
        
        # 删除已存在的表
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # 创建表结构（简化版本）
        columns_sql = []
        for col in df.columns:
            columns_sql.append(f"{col} TEXT")
        
        create_sql = f"""
        CREATE TABLE {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            {', '.join(columns_sql)},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        cursor.execute(create_sql)
        
        # 插入数据
        if len(df) > 0:
            columns_list = list(df.columns)
            placeholders = ', '.join(['%s'] * len(columns_list))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns_list)}) VALUES ({placeholders})"
            
            data_to_insert = [tuple(row) for row in df.values]
            cursor.executemany(insert_sql, data_to_insert)
            self.mysql_conn.commit()
        
        cursor.close()
        logger.info(f"✓ 数据已直接插入到MySQL表: {table_name}")
    
    def run_complete_pipeline(self, csv_path: str, table_name: str, 
                            hive_columns: Dict[str, str], 
                            mysql_columns: List[str]) -> bool:
        """
        运行完整的数据管道
        
        Args:
            csv_path: CSV文件路径
            table_name: 表名
            hive_columns: Hive列定义
            mysql_columns: MySQL列名列表
            
        Returns:
            是否成功
        """
        try:
            logger.info("开始运行完整数据管道...")
            
            # 步骤1: 等待Docker服务
            if not self.wait_for_services():
                return False
            
            # 步骤2: 上传到HDFS
            logger.info("步骤2: 上传CSV到HDFS...")
            hdfs_path = self.upload_csv_to_hdfs(csv_path)
            
            # 步骤3: 创建Hive表并加载数据
            logger.info("步骤3: 创建Hive表并加载数据...")
            if not self.create_hive_table(table_name, hive_columns, hdfs_path):
                return False
            
            # 步骤4: 导出到MySQL
            logger.info("步骤4: 从Hive导出到MySQL...")
            mysql_table = f"{table_name}_mysql"
            if not self.export_hive_to_mysql(table_name, mysql_table, mysql_columns):
                return False
            
            logger.info("🎉 完整数据管道运行成功！")
            return True
            
        except Exception as e:
            logger.error(f"数据管道运行失败: {e}")
            return False
    
    def close_connections(self):
        """关闭所有连接"""
        if self.hive_conn:
            self.hive_conn.close()
            logger.info("Hive连接已关闭")
        
        if self.mysql_conn:
            self.mysql_conn.close()
            logger.info("MySQL连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connections()


# 便捷函数
def process_csv_with_docker_pipeline(csv_path: str, table_name: str, 
                                   hive_columns: Dict[str, str], 
                                   mysql_columns: List[str]) -> bool:
    """
    使用Docker数据管道处理CSV文件的便捷函数
    
    Args:
        csv_path: CSV文件路径
        table_name: 表名
        hive_columns: Hive列定义 {'column_name': 'column_type'}
        mysql_columns: MySQL列名列表
        
    Returns:
        是否成功
    """
    with DockerDataPipeline() as pipeline:
        return pipeline.run_complete_pipeline(csv_path, table_name, hive_columns, mysql_columns)


if __name__ == "__main__":
    # 示例用法
    sample_hive_columns = {
        'user_id': 'INT',
        'product': 'STRING',
        'price': 'DOUBLE'
    }
    
    sample_mysql_columns = ['user_id', 'product', 'price']
    
    # 运行示例
    success = process_csv_with_docker_pipeline(
        'sample_data.csv',
        'test_pipeline',
        sample_hive_columns,
        sample_mysql_columns
    )
    
    if success:
        print("Docker数据管道处理完成！")
    else:
        print("Docker数据管道处理失败！")

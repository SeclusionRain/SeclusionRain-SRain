"""
VM虚拟机环境数据管道工具类
支持通过SSH连接到VM，执行CSV -> HDFS -> Hive -> MySQL的完整数据流程
"""

import os
import pandas as pd
import pymysql
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from .db_config import DatabaseConfig
from .vm_config import VMConfig

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

# 尝试导入SQLAlchemy
try:
    from sqlalchemy import create_engine
    SQLALCHEMY_AVAILABLE = True
except ImportError as e:
    SQLALCHEMY_AVAILABLE = False
    logger.warning(f"sqlalchemy包未安装，部分功能将不可用。错误: {e}")

# 尝试导入paramiko用于SSH连接
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
    logger.info("✓ paramiko包可用")
except ImportError as e:
    PARAMIKO_AVAILABLE = False
    logger.warning(f"paramiko包未安装，SSH功能将不可用。错误: {e}")

# 尝试导入sshtunnel用于SSH隧道
try:
    from sshtunnel import SSHTunnelForwarder
    SSHTUNNEL_AVAILABLE = True
    logger.info("✓ sshtunnel包可用")
except ImportError as e:
    SSHTUNNEL_AVAILABLE = False
    logger.warning(f"sshtunnel包未安装，SSH隧道功能将不可用。错误: {e}")


class VMDataPipeline:
    """VM虚拟机环境数据管道主类"""
    
    def __init__(self):
        self.config = VMConfig()
        self.mysql_conn = None
        self.hive_conn = None
        self.ssh_client = None
        self.sftp_client = None
        self.ssh_tunnel = None
        
    def connect_ssh(self) -> bool:
        """建立SSH连接到VM"""
        if not PARAMIKO_AVAILABLE:
            logger.error("SSH功能不可用：paramiko包未安装")
            return False
        
        try:
            ssh_config = self.config.get_ssh_config()
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 尝试使用密码连接
            if ssh_config['password']:
                self.ssh_client.connect(
                    hostname=ssh_config['host'],
                    port=ssh_config['port'],
                    username=ssh_config['user'],
                    password=ssh_config['password'],
                    timeout=30
                )
            # 或使用密钥文件连接
            elif ssh_config['key_path'] and os.path.exists(ssh_config['key_path']):
                self.ssh_client.connect(
                    hostname=ssh_config['host'],
                    port=ssh_config['port'],
                    username=ssh_config['user'],
                    key_filename=ssh_config['key_path'],
                    timeout=30
                )
            else:
                logger.error("SSH连接失败：未提供密码或密钥文件")
                return False
            
            # 创建SFTP客户端
            self.sftp_client = self.ssh_client.open_sftp()
            logger.info(f"✓ SSH连接成功: {ssh_config['user']}@{ssh_config['host']}")
            return True
            
        except Exception as e:
            logger.error(f"SSH连接失败: {e}")
            return False
    
    def execute_ssh_command(self, command: str, timeout: int = 60) -> Tuple[int, str, str]:
        """
        通过SSH执行命令
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            
        Returns:
            (返回码, 标准输出, 错误输出)
        """
        if not self.ssh_client:
            if not self.connect_ssh():
                return (-1, "", "SSH未连接")
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8', errors='ignore')
            stderr_data = stderr.read().decode('utf-8', errors='ignore')
            
            return (exit_code, stdout_data, stderr_data)
            
        except Exception as e:
            logger.error(f"SSH命令执行失败: {e}")
            return (-1, "", str(e))
    
    def upload_file_to_vm(self, local_path: str, remote_path: str) -> bool:
        """
        通过SFTP上传文件到VM
        
        Args:
            local_path: 本地文件路径
            remote_path: VM上的目标路径
            
        Returns:
            是否成功
        """
        if not self.sftp_client:
            if not self.connect_ssh():
                return False
        
        try:
            # 确保远程目录存在
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                # 创建远程目录
                exit_code, _, _ = self.execute_ssh_command(f"mkdir -p {remote_dir}")
            
            # 上传文件
            self.sftp_client.put(local_path, remote_path)
            logger.info(f"✓ 文件已上传到VM: {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return False
    
    def upload_csv_to_hdfs(self, local_csv_path: str, hdfs_filename: Optional[str] = None) -> str:
        """
        上传CSV文件到HDFS
        
        Args:
            local_csv_path: 本地CSV文件路径
            hdfs_filename: HDFS中的文件名，如果为None则使用原文件名
            
        Returns:
            HDFS文件路径
        """
        if not os.path.exists(local_csv_path):
            raise FileNotFoundError(f"本地文件不存在: {local_csv_path}")
        
        if hdfs_filename is None:
            hdfs_filename = os.path.basename(local_csv_path)
        
        hdfs_config = self.config.get_hdfs_config()
        hdfs_path = os.path.join(hdfs_config['upload_path'], hdfs_filename).replace('\\', '/')
        
        try:
            # 步骤1: 上传文件到VM临时目录
            vm_tmp_path = f"/tmp/{os.path.basename(local_csv_path)}"
            if not self.upload_file_to_vm(local_csv_path, vm_tmp_path):
                raise Exception("上传文件到VM失败")
            
            # 步骤2: 在VM上创建HDFS目录
            mkdir_cmd = f"hdfs dfs -mkdir -p {hdfs_config['upload_path']}"
            exit_code, stdout, stderr = self.execute_ssh_command(mkdir_cmd)
            logger.info(f"HDFS目录创建: {exit_code == 0 or 'File exists' in stderr}")
            
            # 步骤3: 从VM上传到HDFS
            # 先尝试删除已存在的文件
            rm_cmd = f"hdfs dfs -rm -f {hdfs_path}"
            self.execute_ssh_command(rm_cmd)
            
            # 上传到HDFS
            upload_cmd = f"hdfs dfs -put {vm_tmp_path} {hdfs_path}"
            exit_code, stdout, stderr = self.execute_ssh_command(upload_cmd)
            
            if exit_code == 0:
                logger.info(f"✓ 文件已上传到HDFS: {hdfs_path}")
                
                # 清理临时文件
                self.execute_ssh_command(f"rm -f {vm_tmp_path}")
                
                return hdfs_path
            else:
                raise Exception(f"HDFS上传失败: {stderr}")
                
        except Exception as e:
            logger.error(f"HDFS上传失败: {e}")
            raise
    
    def connect_hive(self) -> bool:
        """连接Hive（支持SSH隧道）"""
        if not HIVE_AVAILABLE:
            logger.error("Hive功能不可用：pyhive包未安装")
            return False
        
        hive_config = self.config.get_hive_config()
        ssh_config = self.config.get_ssh_config()
        
        max_retries = 10
        for i in range(max_retries):
            try:
                # 如果需要SSH隧道
                if SSHTUNNEL_AVAILABLE and ssh_config['host'] not in ['localhost', '127.0.0.1']:
                    # 创建SSH隧道
                    # remote_bind_address应该是VM内部地址，使用localhost而不是主机名
                    self.ssh_tunnel = SSHTunnelForwarder(
                        (ssh_config['host'], ssh_config['port']),
                        ssh_username=ssh_config['user'],
                        ssh_password=ssh_config['password'],
                        remote_bind_address=('localhost', hive_config['port'])
                    )
                    self.ssh_tunnel.start()
                    
                    logger.info(f"✓ SSH隧道已建立: localhost:{self.ssh_tunnel.local_bind_port} -> VM内部 localhost:{hive_config['port']}")
                    
                    # 通过隧道连接Hive
                    self.hive_conn = hive.connect(
                        host='localhost',
                        port=self.ssh_tunnel.local_bind_port,
                        username=hive_config['username'],
                        database=hive_config['database']
                    )
                else:
                    # 直接连接Hive
                    self.hive_conn = hive.connect(
                        host=hive_config['host'],
                        port=hive_config['port'],
                        username=hive_config['username'],
                        database=hive_config['database']
                    )
                
                logger.info("✓ Hive连接成功")
                return True
                
            except Exception as e:
                # 清理失败的SSH隧道
                if self.ssh_tunnel:
                    try:
                        self.ssh_tunnel.stop()
                    except:
                        pass
                    self.ssh_tunnel = None
                
                if i < max_retries - 1:
                    logger.info(f"等待Hive启动... ({i+1}/{max_retries}): {e}")
                    time.sleep(5)
                else:
                    logger.error(f"Hive连接失败: {e}")
                    logger.error("请检查VM上的Hive服务是否正在运行: netstat -tulpn | grep 10000")
                    return False
        return False
    
    def connect_mysql(self) -> bool:
        """连接MySQL"""
        try:
            mysql_config = DatabaseConfig.get_config()
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
            
            # 导出到MySQL - 统一使用直接插入方式，确保有id字段
            # 这样可以确保无论是否使用SQLAlchemy，都能创建带有自增id的表结构
            logger.info(f"🔧 使用直接插入方式确保表结构包含id字段")
            self._insert_to_mysql_direct(hive_df, mysql_table)
            
            return True
            
        except Exception as e:
            logger.error(f"导出到MySQL失败: {e}")
            return False
    
    def _insert_to_mysql_direct(self, df: pd.DataFrame, table_name: str):
        """直接使用pymysql插入数据到MySQL，添加NaN值处理和重复列检查"""
        cursor = self.mysql_conn.cursor()
        
        # 删除已存在的表
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # 创建表结构（避免重复的id列）
        columns_sql = []
        # 将列名转换为小写字符串列表进行检查
        lower_columns = [col.lower() for col in df.columns]
        has_id_column = 'id' in lower_columns  # 检查是否已经有id列
        
        # 为所有列创建TEXT类型定义
        for col in df.columns:
            # 跳过id列，因为我们会单独添加一个自增id作为主键
            if col.lower() == 'id':
                continue
            columns_sql.append(f"{col} TEXT")
        
        # 如果没有id列，添加一个自增id作为主键
        if not has_id_column:
            create_sql = f"""
            CREATE TABLE {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                {', '.join(columns_sql)},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        else:
            # 如果已有id列，不要重复添加，但仍然添加自增主键
            create_sql = f"""
            CREATE TABLE {table_name} (
                primary_id INT AUTO_INCREMENT PRIMARY KEY,
                {', '.join(columns_sql)},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        
        cursor.execute(create_sql)
        
        # 插入数据
        if len(df) > 0:
            # 根据是否有id列调整插入的列
            has_id_column = 'id' in lower_columns
            
            # 确定要插入的列
            columns_list = []
            for col in df.columns:
                # 如果表中已经有id列，我们需要保留它用于插入
                columns_list.append(col)
            
            placeholders = ', '.join(['%s'] * len(columns_list))
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns_list)}) VALUES ({placeholders})"
            
            # 处理NaN值，将其转换为None（MySQL可接受的NULL值）
            data_to_insert = []
            for row in df.values:
                processed_row = []
                for value in row:
                    # 使用pandas的isna函数检查NaN值，包括np.nan, None, NaN等
                    if pd.isna(value):
                        processed_row.append(None)
                    else:
                        # 确保字符串类型数据被正确处理
                        if isinstance(value, (float, int)):
                            # 如果是浮点数且能被整除，转为整数
                            if isinstance(value, float) and value.is_integer():
                                processed_row.append(int(value))
                            else:
                                processed_row.append(value)
                        else:
                            processed_row.append(str(value) if value is not None else None)
                data_to_insert.append(tuple(processed_row))
            
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
            logger.info("开始运行VM数据管道...")
            
            # 步骤1: 建立SSH连接
            logger.info("步骤1: 建立SSH连接...")
            if not self.connect_ssh():
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
            
            logger.info("🎉 VM数据管道运行成功！")
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
        
        if self.ssh_tunnel:
            self.ssh_tunnel.stop()
            logger.info("SSH隧道已关闭")
        
        if self.sftp_client:
            self.sftp_client.close()
            logger.info("SFTP连接已关闭")
        
        if self.ssh_client:
            self.ssh_client.close()
            logger.info("SSH连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connections()


# 便捷函数
def process_csv_with_vm_pipeline(csv_path: str, table_name: str, 
                                 hive_columns: Dict[str, str], 
                                 mysql_columns: List[str]) -> bool:
    """
    使用VM数据管道处理CSV文件的便捷函数
    
    Args:
        csv_path: CSV文件路径
        table_name: 表名
        hive_columns: Hive列定义 {'column_name': 'column_type'}
        mysql_columns: MySQL列名列表
        
    Returns:
        是否成功
    """
    with VMDataPipeline() as pipeline:
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
    success = process_csv_with_vm_pipeline(
        'sample_data.csv',
        'test_pipeline',
        sample_hive_columns,
        sample_mysql_columns
    )
    
    if success:
        print("VM数据管道处理完成！")
    else:
        print("VM数据管道处理失败！")

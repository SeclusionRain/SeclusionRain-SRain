# Docker数据管道工具类使用指南

## 📋 概述

`DockerDataPipeline` 是一个专为Docker环境设计的数据管道工具类，支持完整的 **CSV → HDFS → Hive → MySQL** 数据流程。

## ✅ 解决的问题

- ✅ **Windows兼容性** - 解决了hdfs3包在Windows上的编译问题
- ✅ **Docker网络问题** - 绕过WebHDFS的容器网络重定向问题
- ✅ **编码问题** - 修复了Windows下的字符编码问题
- ✅ **自动容器发现** - 自动识别Docker容器名称
- ✅ **完整错误处理** - 提供详细的错误信息和日志

## 🚀 快速开始

### 1. 基本使用

```python
from utils.docker_data_pipeline import DockerDataPipeline

# 创建数据管道实例
with DockerDataPipeline() as pipeline:
    # 定义表结构
    hive_columns = {
        'user_id': 'INT',
        'comment': 'STRING',
        'sentiment': 'STRING',
        'score': 'DOUBLE'
    }
    
    mysql_columns = ['user_id', 'comment', 'sentiment', 'score']
    
    # 运行完整管道
    success = pipeline.run_complete_pipeline(
        csv_path='data.csv',
        table_name='my_table',
        hive_columns=hive_columns,
        mysql_columns=mysql_columns
    )
    
    if success:
        print("数据管道运行成功！")
```

### 2. 便捷函数使用

```python
from utils.docker_data_pipeline import process_csv_with_docker_pipeline

# 一行代码完成整个流程
success = process_csv_with_docker_pipeline(
    csv_path='data.csv',
    table_name='my_table',
    hive_columns={'user_id': 'INT', 'comment': 'STRING'},
    mysql_columns=['user_id', 'comment']
)
```

## 🔧 详细功能

### 主要方法

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `check_docker_services()` | 检查Docker服务状态 | bool |
| `get_namenode_container()` | 获取NameNode容器名称 | str |
| `upload_csv_to_hdfs()` | 上传CSV到HDFS | str (HDFS路径) |
| `connect_hive()` | 连接Hive服务 | bool |
| `connect_mysql()` | 连接MySQL服务 | bool |
| `create_hive_table()` | 创建Hive表并加载数据 | bool |
| `export_hive_to_mysql()` | 从Hive导出到MySQL | bool |
| `run_complete_pipeline()` | 运行完整管道 | bool |

### 配置类

```python
from utils.docker_data_pipeline import DockerDataPipelineConfig

# 查看当前配置
config = DockerDataPipelineConfig()
print(f"Hive主机: {config.HIVE_HOST}")
print(f"Hive端口: {config.HIVE_PORT}")
print(f"HDFS路径: {config.HDFS_UPLOAD_PATH}")
```

## 📊 数据类型映射

### Hive数据类型

| Hive类型 | 说明 | 示例 |
|----------|------|------|
| `INT` | 整数 | 123 |
| `BIGINT` | 长整数 | 1234567890 |
| `DOUBLE` | 双精度浮点数 | 123.45 |
| `STRING` | 字符串 | "文本内容" |
| `BOOLEAN` | 布尔值 | true/false |
| `TIMESTAMP` | 时间戳 | 2023-01-01 12:00:00 |

### MySQL数据类型（自动转换）

工具类会自动将Hive数据类型转换为合适的MySQL类型。

## 🐳 Docker环境要求

### 必需的容器

- **NameNode容器** - 包含"namenode"关键词
- **DataNode容器** - 包含"datanode"关键词  
- **Hive Server容器** - 提供端口10000服务
- **MySQL服务** - 本地或容器化

### 端口映射

确保以下端口已正确映射：

```yaml
# docker-compose.yaml示例
services:
  namenode:
    ports:
      - "50070:50070"  # Hadoop 2.7.4 Web UI
      - "8020:8020"    # NameNode IPC
  
  hive-server:
    ports:
      - "10000:10000"  # Hive Server2
```

## 🧪 测试工具类

运行测试脚本验证功能：

```bash
# 测试工具类功能
python test_docker_utils.py

# 测试原始脚本（参考）
python test_pipeline_docker_friendly.py
```

## 📝 使用示例

### 处理抖音评论数据

```python
import pandas as pd
from utils.docker_data_pipeline import DockerDataPipeline

# 准备数据
data = {
    'user_id': [1, 2, 3, 4, 5],
    'comment': ['很好用', '不错', '一般', '很满意', '推荐'],
    'sentiment': ['positive', 'positive', 'neutral', 'positive', 'positive'],
    'score': [0.85, 0.75, 0.50, 0.95, 0.80]
}

df = pd.DataFrame(data)
csv_path = 'douyin_comments.csv'
df.to_csv(csv_path, index=False, header=False)  # Hive不需要标题

# 定义表结构
hive_columns = {
    'user_id': 'INT',
    'comment': 'STRING',
    'sentiment': 'STRING', 
    'score': 'DOUBLE'
}

mysql_columns = ['user_id', 'comment', 'sentiment', 'score']

# 运行数据管道
with DockerDataPipeline() as pipeline:
    success = pipeline.run_complete_pipeline(
        csv_path=csv_path,
        table_name='douyin_comments',
        hive_columns=hive_columns,
        mysql_columns=mysql_columns
    )
    
    if success:
        print("✅ 抖音评论数据处理完成！")
        print("数据已存储到:")
        print("- Hive表: douyin_comments")
        print("- MySQL表: douyin_comments_mysql")
```

## 🔍 故障排除

### 常见问题

1. **容器未找到**
   ```
   解决方案: 确保Docker容器正在运行
   检查命令: docker ps
   ```

2. **HDFS上传失败**
   ```
   解决方案: 检查NameNode和DataNode状态
   检查命令: docker logs <namenode_container>
   ```

3. **Hive连接失败**
   ```
   解决方案: 等待Hive服务完全启动
   检查命令: docker logs <hive_container>
   ```

4. **MySQL连接失败**
   ```
   解决方案: 检查MySQL服务和配置
   检查文件: utils/db_config.py
   ```

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 然后运行数据管道
```

## 📈 性能优化

- **批量处理**: 对于大文件，考虑分批处理
- **连接复用**: 使用上下文管理器自动管理连接
- **错误重试**: 内置重试机制处理临时故障
- **资源清理**: 自动清理临时文件和连接

## 🔄 版本兼容性

- **Python**: 3.8+
- **Hadoop**: 2.7.4 (Docker镜像)
- **Hive**: 2.3.2+
- **MySQL**: 5.7+

## 📚 相关文档

- [原始数据管道文档](DATA_PIPELINE_README.md)
- [数据库配置说明](utils/db_config.py)
- [Docker Compose配置](docker-compose.yaml)

---

## 🎯 总结

`DockerDataPipeline` 工具类提供了一个稳定、可靠的数据管道解决方案，特别适合：

- ✅ Windows开发环境
- ✅ Docker化的大数据环境
- ✅ 需要处理CSV数据的项目
- ✅ 抖音评论情感分析等应用场景

通过使用这个工具类，你可以轻松实现从CSV文件到MySQL数据库的完整数据流程，无需担心底层的技术复杂性。

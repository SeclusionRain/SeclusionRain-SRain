核心功能：
1. 高效爬虫系统：采用asyncio+httpx实现异步并发爬取抖音评论数据，支持多任务管理与进度监控，通过动态参数处理与签名机制规避反爬限制。
2. 多模型情感分析：集成DistilBERT等深度学习模型与传统机器学习算法（SVM/决策树），实现评论情感的精准分类与对比评估。
3. 数据可视化平台：提供时间趋势、地域分布、情感占比等多维度图表展示，支持历史数据查询与分析结果导出。
4. 用户管理系统：实现注册登录、个人中心与任务管理功能，支持评论数据的增删改查操作。
5.AI大模型调用：实现智普清言ai大模型的api调用，能够为分析数据进行预测：
用户行为：基于点赞、评论、转发等互动数据，预测用户的活跃度和参与意愿。
商业转化：用户转化意向、购买决策因素、潜在客户识别和转化优化建议。
内容传播：分析内容传播潜力、受众覆盖范围、传播路径和病毒式传播可能性。
情感传播：基于时间、互动、地域等多维度数据，预测情感的传播趋势和影响范围。


一、系统环境要求
================================================================================

1.1 硬件配置要求
- CPU: Intel Core i5 或以上（推荐 i7）
- 内存：8GB 以上（推荐 16GB，运行深度学习模型需 32GB）
- 硬盘：至少 50GB 可用空间
- GPU: 可选（运行 DistilBERT 模型建议使用 NVIDIA GPU，显存 4GB 以上）

1.2 软件环境要求
- 操作系统：Windows 10/11（64 位）或 Linux Ubuntu 18.04+
- Python 版本：Python 3.8 - 3.10（推荐 Python 3.10）
- 数据库：MySQL 8.0
- 大数据组件（可选）: Hadoop 3.3.0 + Hive 3.1.2（虚拟机部署）


二、Python 虚拟环境配置
================================================================================

2.1 安装 Miniconda（推荐）
1. 下载 Miniconda
https://blog.csdn.net/weixin_43828245/article/details/124768518
 
2. 验证安装
   conda --version
请将准备好的ML_DouYin_Comments_SentimentAnalysis_env.rar解压到miniconda3\envs文件夹中
虚拟环境下载：https://pan.baidu.com/s/1OrxuOcL-RBUOCKRckvSWTg?pwd=HWD9

2.2 创建虚拟环境

打开 Anaconda Prompt 或 PowerShell，执行以下命令：

# 创建虚拟环境（Python 3.10）
conda create -n ML_DouYin_Comments_SentimentAnalysis_env python=3.10 -y

# 激活虚拟环境
conda activate ML_DouYin_Comments_SentimentAnalysis_env


2.3 安装项目依赖

# 进入项目目录
cd D:\BSXM\main

# 升级 pip
python -m pip install --upgrade pip

# 安装所有依赖
pip install -r requirements.txt

请注意：本项目使用了distilbert模型，请自行前往魔塔社区下载。（不使用也不影响）


三、MySQL 数据库配置
================================================================================

3.1 安装 MySQL 8.0

1. 下载安装包
   - 访问 MySQL 官网：https://dev.mysql.com/downloads/mysql/
   - 下载 MySQL Installer for Windows
   - 运行安装程序，选择"Developer Default"或"Server only"

2. 配置 MySQL
   - 设置 root 用户密码：123456（或自定义）
   - 端口号：3306
   - 字符集：utf8mb4
   - 排序规则：utf8mb4_0900_ai_ci


3.2 创建数据库

-- 使用 root 用户登录 MySQL
mysql -u root -p

-- 创建数据库
CREATE DATABASE ml_douyin_comments_sentimentanalysis 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_0900_ai_ci;

-- 验证创建
SHOW DATABASES;


3.3 初始化数据库表

# 激活虚拟环境
conda activate ML_DouYin_Comments_SentimentAnalysis_env

# 进入项目目录
cd D:\BSXM\main

# 运行项目（自动创建表）
python run.py

四、大数据环境配置（可选）
================================================================================

4.1 虚拟机环境要求

配置 Hadoop 虚拟机：

- 虚拟机软件：VMware Workstation 16+ 或 VirtualBox 6+
- 操作系统：CentOS 7.9
- IP 地址：192.168.58.13（静态 IP）
- Hadoop 版本：3.3.0
- Hive 版本：3.1.2
- ZooKeeper 版本：3.4.8


4.2 配置连接信息

# Hive 连接配置
HIVE_HOST=192.168.58.13
HIVE_PORT=10000
HIVE_USER=root
HIVE_PASSWORD=123456
HIVE_DATABASE=default

# SSH 隧道配置
SSH_HOST=192.168.58.13
SSH_PORT=22
SSH_USER=root
SSH_PASSWORD=123456


4.3 验证 Hive 连接

python -c "
from pyhive import hive
conn = hive.Connection(
    host='192.168.58.13',
    port=10000,
    username='root',
    database='default'
)
cursor = conn.cursor()
cursor.execute('SHOW DATABASES')
print(cursor.fetchall())
"


五、项目启动说明
================================================================================

5.1 启动项目

# 1. 激活虚拟环境
conda activate ML_DouYin_Comments_SentimentAnalysis_env

# 2. 进入项目目录
cd D:\BSXM\main

# 3. 启动 Flask 应用
python run.py

启动成功后，终端显示：
* Running on http://0.0.0.0:5001
* Debug mode: on


5.2 访问系统

打开浏览器访问：http://localhost:5001

首次使用需要注册账户：
1. 点击"注册"按钮
2. 填写用户名、邮箱、密码
3. 点击"注册"完成账户创建
4. 使用注册的账户登录系统


六、常见问题解决
================================================================================

6.1 依赖安装问题

问题 1: hdfs3 安装失败（Python 3.10+ 兼容性问题）

# 解决方案：运行兼容性修复脚本
cd D:\BSXM\main
python fix_compatibility.py

# 或跳过 hdfs3 安装（不使用 HDFS 功能时）
pip install -r requirements.txt --no-deps
pip install pyhive thrift cryptography


问题 2: PyTorch 安装失败

# 方案 1：使用清华镜像源
pip install torch==2.2.1 transformers==4.38.2 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方案 2：仅使用 CPU 版本（无 GPU 时）
pip install torch==2.2.1+cpu -f https://download.pytorch.org/whl/torch_stable.html


6.2 数据库连接问题

问题：无法连接到 MySQL 数据库

# 解决方案 1：检查 MySQL 服务是否启动
net start MySQL80

# 解决方案 2：修改密码为配置文件中的密码
# 打开 D:\BSXM\main\数据库信息和虚拟环境.txt
# 确认 password 字段与实际 MySQL 密码一致

# 解决方案 3：允许远程连接（如果需要）
mysql -u root -p
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY '123666';
FLUSH PRIVILEGES;


6.3 智谱 AI API 问题

问题：AI 功能调用失败

# 检查 API Key 是否有效
# 打开 D:\BSXM\main\utils\GLM_AI.py
# 确认 api_key 参数与AI型号是否正确

# 验证网络连接
ping open.bigmodel.cn

# 检查 SDK 版本
pip show zai-sdk
# 应为 0.0.3 版本


七、环境检查清单
================================================================================

在提交项目前，请确认以下环境配置完成：

[ ] Miniconda 安装完成
[ ] 虚拟环境 ML_DouYin_Comments_SentimentAnalysis_env 创建成功
[ ] 所有 Python 依赖安装完成（pip list 检查）
[ ] MySQL 8.0 安装并启动
[ ] 数据库 ml_douyin_comments_sentimentanalysis 创建成功
[ ] 项目可以正常启动（python run.py）
[ ] 可以访问 http://localhost:5001
[ ] 可以成功注册和登录用户
[ ] Hadoop/Hive 虚拟机连接正常


八、快速部署命令汇总
================================================================================

# ========== 1. 环境准备 ==========
# 安装 Miniconda（手动下载安装）

# ========== 2. 创建虚拟环境 ==========
conda create -n ML_DouYin_Comments_SentimentAnalysis_env python=3.10 -y
conda activate ML_DouYin_Comments_SentimentAnalysis_env

# ========== 3. 安装依赖 ==========
cd D:\BSXM\main
python -m pip install --upgrade pip
pip install -r requirements.txt

# ========== 4. 配置数据库 ==========
# 安装 MySQL 8.0（手动安装）
# 创建数据库（MySQL 命令行）
# CREATE DATABASE ml_douyin_comments_sentimentanalysis CHARACTER SET utf8mb4;

# ========== 5. 启动项目 ==========
python run.py

# 访问：http://localhost:5001


九、技术支持
================================================================================

如遇到环境问题，请参考：
1. 项目文档：README.md
2. 配置信息：数据库信息和虚拟环境.txt
3. 依赖列表：requirements.txt

开发环境：Windows 11 + Python 3.10 + MySQL 8.0
开发工具：VS Code / PyCharm
开发时间：2025 年 11 月 - 2026 年 3 月

================================================================================

"""
抖音爬虫服务类
改造原有的爬虫脚本为可调用的服务模块
复用原有的 Douyin_getcomments_singlevideo.py 中的核心逻辑
"""
import asyncio
from datetime import datetime
from typing import Any, List, Dict
import os
import httpx
import json
from tqdm import tqdm
from .common import common

class DouyinScraperService:
    """抖音评论爬虫服务类"""
    
    def __init__(self):
        """初始化爬虫服务"""
        self.url = "https://www.douyin.com/aweme/v1/web/comment/list/"
        self.reply_url = self.url + "reply/"
        self.cookie = self._load_cookie()
    
    def _load_cookie(self) -> str:
        """加载cookie"""
        cookie_path = os.path.join(os.path.dirname(__file__), 'cookie.txt')
        try:
            with open(cookie_path, 'r') as f:
                return f.readline().strip()
        except FileNotFoundError:
            # 如果没有cookie文件，返回空字符串
            return ""
    
    async def get_comments_async(self, client: httpx.AsyncClient, aweme_id: str, cursor: str = "0", count: str = "50") -> Dict[str, Any]:
        """异步获取评论 """
        params = {"aweme_id": aweme_id, "cursor": cursor, "count": count, "item_type": 0}
        headers = {"cookie": self.cookie}
        params, headers = common(self.url, params, headers)
        response = await client.get(self.url, params=params, headers=headers)
        await asyncio.sleep(0.8)
        try:
            return response.json()
        except ValueError:
            return {}
    
    async def fetch_all_comments_async(self, aweme_id: str) -> List[Dict[str, Any]]:
        """获取所有评论 """
        async with httpx.AsyncClient(timeout=600) as client:
            cursor = 0
            all_comments = []
            has_more = 1
            with tqdm(desc="Fetching comments", unit="comment") as pbar:
                while has_more:
                    response = await self.get_comments_async(client, aweme_id, cursor=str(cursor))
                    comments = response.get("comments", [])
                    if isinstance(comments, list):
                        all_comments.extend(comments)
                        pbar.update(len(comments))
                    has_more = response.get("has_more", 0)
                    if has_more:
                        cursor = response.get("cursor", 0)
                    await asyncio.sleep(1)
            return all_comments
    
    async def get_replies_async(self, client: httpx.AsyncClient, semaphore, comment_id: str, aweme_id: str, cursor: str = "0", count: str = "50") -> Dict:
        """获取回复 """
        params = {"cursor": cursor, "count": count, "item_type": 0, "item_id": aweme_id, "comment_id": comment_id}
        headers = {"cookie": self.cookie}
        params, headers = common(self.reply_url, params, headers)
        async with semaphore:
            response = await client.get(self.reply_url, params=params, headers=headers)
            await asyncio.sleep(0.3)
            try:
                return response.json()
            except ValueError:
                return {}
    
    async def fetch_replies_for_comment(self, client: httpx.AsyncClient, semaphore, comment: Dict, aweme_id: str, pbar: tqdm) -> List:
        """获取单个评论的回复 """
        comment_id = comment["cid"]
        has_more = 1
        cursor = 0
        all_replies = []
        while has_more and comment["reply_comment_total"] > 0:
            response = await self.get_replies_async(client, semaphore, comment_id, aweme_id, cursor=str(cursor))
            replies = response.get("comments", [])
            if isinstance(replies, list):
                all_replies.extend(replies)
            has_more = response.get("has_more", 0)
            if has_more:
                cursor = response.get("cursor", 0)
            await asyncio.sleep(0.5)
        pbar.update(1)
        return all_replies
    
    async def fetch_all_replies_async(self, comments: List, aweme_id: str) -> List:
        """获取所有回复 """
        all_replies = []
        async with httpx.AsyncClient(timeout=600) as client:
            semaphore = asyncio.Semaphore(10)
            with tqdm(total=len(comments), desc="Fetching replies", unit="comment") as pbar:
                tasks = [self.fetch_replies_for_comment(client, semaphore, comment, aweme_id, pbar) for comment in comments]
                results = await asyncio.gather(*tasks)
                for result in results:
                    all_replies.extend(result)
        return all_replies
    
    def process_comments(self, comments: List[Dict[str, Any]]) -> List[Dict]:
        """处理评论数据，转换为数据库格式 """
        data = []
        for c in comments:
            image_urls = None
            if c.get('image_list'):
                image_urls = json.dumps(c['image_list'][0]['origin_url']['url_list'])
            
            # 转换时间格式
            try:
                publish_time = datetime.fromtimestamp(c['create_time'])
            except:
                publish_time = datetime.now()
            
            data.append({
                'post_id': c['cid'],
                'content': c['text'],
                'user_name': c['user']['nickname'],
                'user_id': c['user'].get('unique_id', '未知'),
                'user_signature': c['user'].get('signature', '未知'),
                'publish_time': publish_time,
                'like_count': c['digg_count'],
                'comment_count': 0,
                'forward_count': c['reply_comment_total'],
                'ip_location': c.get('ip_label', '未知'),
                'image_urls': image_urls,
                'user_homepage': f"https://www.douyin.com/user/{c['user']['sec_uid']}"
            })
        return data
    
    def process_replies(self, replies: List[Dict[str, Any]]) -> List[Dict]:
        """处理回复数据，转换为数据库格式"""
        data = []
        for c in replies:
            image_urls = None
            if c.get('image_list'):
                image_urls = json.dumps(c['image_list'][0]['origin_url']['url_list'])
            
            # 转换时间格式
            try:
                publish_time = datetime.fromtimestamp(c['create_time'])
            except:
                publish_time = datetime.now()
            
            data.append({
                'post_id': c['cid'],
                'content': c['text'],
                'user_name': c['user']['nickname'],
                'user_id': c['user'].get('unique_id', '未知'),
                'user_signature': c['user'].get('signature', '未知'),
                'publish_time': publish_time,
                'like_count': c['digg_count'],
                'comment_count': 0,
                'forward_count': 0,
                'ip_location': c.get('ip_label', '未知'),
                'image_urls': image_urls,
                'user_homepage': f"https://www.douyin.com/user/{c['user']['sec_uid']}",
                'reply_to_id': c.get('reply_id'),
                'reply_to_user': c.get('reply_to_username', '未知')
            })
        return data
    
    async def scrape_comments(self, aweme_id: str, include_replies: bool = True) -> List[Dict]:
        """
        爬取指定视频的评论
        
        Args:
            aweme_id: 抖音视频ID
            include_replies: 是否包含回复
            
        Returns:
            评论数据列表
        """
        # 获取评论
        all_comments = await self.fetch_all_comments_async(aweme_id)
        print(f"Found {len(all_comments)} comments.")
        
        comments_data = []
        if all_comments:
            comments_data = self.process_comments(all_comments)
        
        # 获取回复
        if include_replies and all_comments:
            all_replies = await self.fetch_all_replies_async(all_comments, aweme_id)
            print(f"Found {len(all_replies)} replies")
            
            replies_data = []
            if all_replies:
                replies_data = self.process_replies(all_replies)
            
            # 合并评论和回复
            comments_data.extend(replies_data)
        
        print(f"Total: {len(comments_data)} comments and replies")
        return comments_data

import asyncio
from datetime import datetime
from typing import Any
import os
import httpx
import pandas as pd
import json
from tqdm import tqdm
from common import common

url = "https://www.douyin.com/aweme/v1/web/comment/list/"
reply_url = url + "reply/"

with open('cookie.txt','r') as f:
    cookie = f.readline().strip()

aweme_id = input("Enter the aweme_id: ")


async def get_comments_async(client: httpx.AsyncClient, aweme_id: str, cursor: str = "0", count: str = "50") -> dict[
    str, Any]:
    params = {"aweme_id": aweme_id, "cursor": cursor, "count": count, "item_type": 0}
    headers = {"cookie": cookie}
    params, headers = common(url, params, headers)
    response = await client.get(url, params=params, headers=headers)
    await asyncio.sleep(0.8)
    try:
        return response.json()
    except ValueError:
        # Return an empty dictionary if the response is not valid JSON.
        # Alternatively, you could raise an exception here to indicate that the cookies might be expired or invalid.
        return {}

async def fetch_all_comments_async(aweme_id: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=600) as client:
        cursor = 0
        all_comments = []
        has_more = 1
        with tqdm(desc="Fetching comments", unit="comment") as pbar:
            while has_more:
                response = await get_comments_async(client, aweme_id, cursor=str(cursor))
                comments = response.get("comments", [])
                if isinstance(comments, list):
                    all_comments.extend(comments)
                    pbar.update(len(comments))
                has_more = response.get("has_more", 0)
                if has_more:
                    cursor = response.get("cursor", 0)
                await asyncio.sleep(1)
        return all_comments

async def get_replies_async(client: httpx.AsyncClient, semaphore, comment_id: str, cursor: str = "0",
                            count: str = "50") -> dict:
    params = {"cursor": cursor, "count": count, "item_type": 0, "item_id": aweme_id, "comment_id": comment_id}
    headers = {"cookie": cookie}
    params, headers = common(reply_url, params, headers)
    async with semaphore:
        response = await client.get(reply_url, params=params, headers=headers)
        await asyncio.sleep(0.3)
        # print(response.text)
        try:
            return response.json()
        except ValueError:
            # Return an empty dictionary if the response is not valid JSON.
            # Alternatively, you could raise an exception here to indicate that the cookies might be expired or invalid.
            return {}

async def fetch_replies_for_comment(client: httpx.AsyncClient, semaphore, comment: dict, pbar: tqdm) -> list:
    comment_id = comment["cid"]
    has_more = 1
    cursor = 0
    all_replies = []
    while has_more and comment["reply_comment_total"] > 0:
        response = await get_replies_async(client, semaphore, comment_id, cursor=str(cursor))
        replies = response.get("comments", [])
        if isinstance(replies, list):
            all_replies.extend(replies)
        has_more = response.get("has_more", 0)
        if has_more:
            cursor = response.get("cursor", 0)
        await asyncio.sleep(0.5)
    pbar.update(1)
    return all_replies

async def fetch_all_replies_async(comments: list) -> list:
    all_replies = []
    async with httpx.AsyncClient(timeout=600) as client:
        semaphore = asyncio.Semaphore(10)  # 在这里创建信号量
        with tqdm(total=len(comments), desc="Fetching replies", unit="comment") as pbar:
            tasks = [fetch_replies_for_comment(client, semaphore, comment, pbar) for comment in comments]
            results = await asyncio.gather(*tasks)
            for result in results:
                all_replies.extend(result)
    return all_replies

def process_comments(comments: list[dict[str, Any]]) -> list[dict]:
    """处理评论数据，转换为数据库格式"""
    data = []
    for c in comments:
        image_urls = None
        if c.get('image_list'):
            image_urls = json.dumps(c['image_list'][0]['origin_url']['url_list'])
        
        data.append({
            'post_id': c['cid'],
            'content': c['text'],
            'user_name': c['user']['nickname'],
            'user_id': c['user'].get('unique_id', '未知'),
            'user_signature': c['user'].get('signature', '未知'),
            'publish_time': datetime.fromtimestamp(c['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
            'like_count': c['digg_count'],
            'comment_count': 0,  # 抖音评论没有二级评论数
            'forward_count': c['reply_comment_total'],
            'ip_location': c.get('ip_label', '未知'),
            'image_urls': image_urls,
            'user_homepage': f"https://www.douyin.com/user/{c['user']['sec_uid']}"
        })
    return data

def process_replies(replies: list[dict[str, Any]]) -> list[dict]:
    """处理回复数据，转换为数据库格式"""
    data = []
    for c in replies:
        image_urls = None
        if c.get('image_list'):
            image_urls = json.dumps(c['image_list'][0]['origin_url']['url_list'])
        
        data.append({
            'post_id': c['cid'],
            'content': c['text'],
            'user_name': c['user']['nickname'],
            'user_id': c['user'].get('unique_id', '未知'),
            'user_signature': c['user'].get('signature', '未知'),
            'publish_time': datetime.fromtimestamp(c['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
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

async def main():
    # 评论部分
    all_comments = await fetch_all_comments_async(aweme_id)
    print(f"Found {len(all_comments)} comments.")
    
    comments_data = []
    if all_comments:
        comments_data = process_comments(all_comments)

    # 回复部分 如果不需要直接注释掉
    all_replies = await fetch_all_replies_async(all_comments)
    print(f"Found {len(all_replies)} replies")
    print(f"Found {len(all_replies) + len(all_comments)} in totals")
    
    replies_data = []
    if all_replies:
        replies_data = process_replies(all_replies)

    # 合并评论和回复数据并保存到CSV
    all_data = comments_data + replies_data
    if all_data:
        df = pd.DataFrame(all_data)
        # 保证列的顺序和完整性
        cols = ['post_id', 'content', 'user_name', 'user_id', 'user_signature', 
                'publish_time', 'like_count', 'comment_count', 'forward_count', 
                'ip_location', 'image_urls', 'user_homepage', 'reply_to_id', 'reply_to_user']
        df = df.reindex(columns=cols)
        
        output_filename = f"douyin_comments_{aweme_id}.csv"
        df.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print(f"成功保存 {len(all_data)} 条数据到 {output_filename}")

# 运行 main 函数
if __name__ == "__main__":
    asyncio.run(main())
    print('done!')

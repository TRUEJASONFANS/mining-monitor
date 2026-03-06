#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
矿产储量监控工具 - 巨潮资讯网API版
监控上市公司公告，发现采矿权、矿产储量相关新闻
"""

import requests
import time
import logging
import json
import os
from datetime import datetime
import hashlib

# 托盘通知
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# 配置
KEYWORDS = [
    "采矿权",
    "矿产储量", 
    "探矿权",
    "矿业权"
]

CHECK_INTERVAL = 3600  # 每小时检查
DATA_FILE = "monitored_data.json"
CNINFO_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mining_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_monitored_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_monitored_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def timestamp_to_date(ts):
    """时间戳转日期"""
    if ts:
        return datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d')
    return ''


def search_keyword(keyword):
    """搜索巨潮资讯网公告"""
    results = []
    
    try:
        data = {
            'pageNum': 1,
            'pageSize': 20,
            'tabName': 'fulltext',
            'column': 'szse',  # 深交所
            'seDate': '',
            'searchkey': keyword,
            'category': '',
            'isHLtitle': 'true'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(CNINFO_URL, data=data, headers=headers, timeout=15)
        result = response.json()
        
        announcements = result.get('announcements', [])
        
        for item in announcements:
            title = item.get('announcementTitle', '')
            # 清理HTML标签
            title = title.replace('<em>', '').replace('</em>', '')
            
            results.append({
                'title': title,
                'url': f"http://www.cninfo.com.cn/new/disclosure/stock?stockCode={item.get('secCode')}&orgId={item.get('orgId')}",
                'keyword': keyword,
                'time': timestamp_to_date(item.get('announcementTime')),
                'company': item.get('secName', '')
            })
                
    except Exception as e:
        logger.error(f"搜索出错: {keyword} - {e}")
    
    return results


def send_notification(title, message):
    logger.info(f"📢 弹窗提醒: {title}")
    
    if PLYER_AVAILABLE:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name='矿产储量监控',
                timeout=10
            )
            return
        except Exception as e:
            logger.warning(f"通知失败: {e}")
    
    print(f"\n{'='*50}")
    print(f"🔔 {title}")
    print(f"📝 {message}")
    print(f"{'='*50}\n")


def check_updates():
    logger.info("🔄 开始检查更新...")
    
    monitored = load_monitored_data()
    new_items = []
    
    for keyword in KEYWORDS:
        logger.info(f"🔍 搜索: {keyword}")
        results = search_keyword(keyword)
        
        for item in results:
            item_hash = get_hash(item['title'])
            
            if item_hash not in monitored.get('hashes', []):
                new_items.append(item)
                monitored.setdefault('hashes', []).append(item_hash)
                logger.info(f"🆕 {item['company']}: {item['title'][:40]}")
    
    save_monitored_data(monitored)
    
    if new_items:
        count = len(new_items)
        items = [f"{item['company']}: {item['title'][:25]}..." for item in new_items[:3]]
        msg = f"发现 {count} 条新公告\n" + "\n".join(items)
        if count > 3:
            msg += f"\n...还有更多"
        send_notification("🚨 矿产相关新闻更新!", msg)
    else:
        logger.info("✅ 没有新内容")
    
    return len(new_items)


def main_loop():
    logger.info("🚀 矿产储量监控已启动!")
    logger.info(f"📋 监控关键词: {KEYWORDS}")
    logger.info(f"⏱️ 检查间隔: {CHECK_INTERVAL}秒")
    logger.info("📡 数据源: 巨潮资讯网(证监会指定)")
    
    # 首次检查
    check_updates()
    
    # 定时检查
    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            check_updates()
        except Exception as e:
            logger.error(f"检查出错: {e}")


if __name__ == "__main__":
    main_loop()

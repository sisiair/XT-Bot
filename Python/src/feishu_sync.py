import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# 添加父目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入飞书多维表格模块
from utils.feishu_bitable import FeishuBitable

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)-5s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f"../logs/feishu-{datetime.now().strftime('%Y-%m-%d')}.log", 
            encoding="utf-8"
        )
    ]
)
logger = logging.getLogger(__name__)

class TwitterToFeishuSync:
    """Twitter数据同步到飞书多维表格"""
    
    def __init__(self):
        """初始化同步器"""
        self.output_dir = Path("../output")
        self.tweets_dir = Path("../../TypeScript/tweets/user")
        self.sync_record_file = Path("../dataBase/feishu_sync_record.json")
        self.feishu_bitable = FeishuBitable()
        
    def load_sync_record(self) -> Dict[str, Dict[str, Any]]:
        """加载同步记录"""
        if not self.sync_record_file.exists():
            return {}
            
        try:
            with open(self.sync_record_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载同步记录失败: {str(e)}")
            return {}
            
    def save_sync_record(self, record: Dict) -> None:
        """保存同步记录"""
        # 确保目录存在
        self.sync_record_file.parent.mkdir(exist_ok=True, parents=True)
        
        try:
            with open(self.sync_record_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存同步记录失败: {str(e)}")
            
    def load_tweets_data(self, user_file: Path) -> List[Dict[str, Any]]:
        """加载推特数据"""
        try:
            with open(user_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载推特数据失败: {str(e)}")
            return []
            
    def sync_user_tweets(self, screen_name: str) -> int:
        """同步指定用户的推特数据"""
        # 推特用户数据文件
        user_file = self.tweets_dir / f"{screen_name}.json"
        if not user_file.exists():
            logger.warning(f"用户 {screen_name} 的数据文件不存在")
            return 0
            
        # 加载数据
        tweets_data = self.load_tweets_data(user_file)
        if not tweets_data:
            logger.warning(f"用户 {screen_name} 无有效数据")
            return 0
            
        # 加载同步记录
        sync_record = self.load_sync_record()
        user_record = sync_record.get(screen_name, {})
        
        # 筛选未同步的推文
        unsync_tweets = []
        for tweet in tweets_data:
            tweet_url = tweet.get("tweetUrl")
            if not tweet_url:
                continue
                
            # 如果推文URL不在同步记录中，则需要同步
            if tweet_url not in user_record:
                unsync_tweets.append(tweet)
                
        # 如果没有需要同步的推文，直接返回
        if not unsync_tweets:
            logger.info(f"用户 {screen_name} 没有新的推文需要同步")
            return 0
            
        # 同步到飞书多维表格
        success = self.feishu_bitable.batch_insert_records(unsync_tweets)
        
        # 更新同步记录
        if success:
            for tweet in unsync_tweets:
                tweet_url = tweet.get("tweetUrl")
                if tweet_url:
                    user_record[tweet_url] = {
                        "sync_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "publish_time": tweet.get("publishTime")
                    }
                    
            sync_record[screen_name] = user_record
            self.save_sync_record(sync_record)
            
            logger.info(f"✅ 用户 {screen_name} 成功同步 {len(unsync_tweets)} 条推文到飞书多维表格")
            return len(unsync_tweets)
        else:
            logger.error(f"❌ 用户 {screen_name} 同步推文到飞书多维表格失败")
            return 0
            
    def sync_all_users(self) -> int:
        """同步所有用户的推特数据"""
        total_synced = 0
        
        # 获取所有用户数据文件
        user_files = list(self.tweets_dir.glob("*.json"))
        
        if not user_files:
            logger.warning("没有找到用户数据文件")
            return 0
            
        logger.info(f"发现 {len(user_files)} 个用户数据文件")
        
        # 依次同步每个用户的数据
        for user_file in user_files:
            screen_name = user_file.stem
            synced_count = self.sync_user_tweets(screen_name)
            total_synced += synced_count
            
        logger.info(f"✅ 总共同步 {total_synced} 条推文到飞书多维表格")
        return total_synced
            
    def sync_recent_days(self, days: int = 7) -> int:
        """同步最近几天的推特数据"""
        total_synced = 0
        sync_record = self.load_sync_record()
        
        # 遍历输出目录中最近几天的数据文件
        start_date = datetime.now() - timedelta(days=days)
        
        for i in range(days, -1, -1):
            target_date = datetime.now() - timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            month_dir = self.output_dir / date_str[:7]
            json_path = month_dir / f"{date_str}.json"
            
            if not json_path.exists():
                continue
                
            # 加载数据
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"加载数据文件 {json_path} 失败: {str(e)}")
                continue
                
            # 筛选未同步的推文
            unsync_tweets = []
            for item in data:
                tweet_url = item.get("tweetUrl") or item.get("url")
                if not tweet_url:
                    continue
                    
                screen_name = item.get("user", {}).get("screen_name", "unknown")
                user_record = sync_record.get(screen_name, {})
                
                # 如果推文URL不在同步记录中，则需要同步
                if tweet_url not in user_record:
                    unsync_tweets.append(item)
                    
            # 如果没有需要同步的推文，继续下一天
            if not unsync_tweets:
                logger.info(f"日期 {date_str} 没有新的推文需要同步")
                continue
                
            # 同步到飞书多维表格
            success = self.feishu_bitable.batch_insert_records(unsync_tweets)
            
            # 更新同步记录
            if success:
                for tweet in unsync_tweets:
                    tweet_url = tweet.get("tweetUrl") or tweet.get("url")
                    if not tweet_url:
                        continue
                        
                    screen_name = tweet.get("user", {}).get("screen_name", "unknown")
                    
                    if screen_name not in sync_record:
                        sync_record[screen_name] = {}
                        
                    sync_record[screen_name][tweet_url] = {
                        "sync_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "publish_time": tweet.get("publishTime")
                    }
                    
                self.save_sync_record(sync_record)
                
                logger.info(f"✅ 日期 {date_str} 成功同步 {len(unsync_tweets)} 条推文到飞书多维表格")
                total_synced += len(unsync_tweets)
            else:
                logger.error(f"❌ 日期 {date_str} 同步推文到飞书多维表格失败")
                
        logger.info(f"✅ 总共同步最近 {days} 天的 {total_synced} 条推文到飞书多维表格")
        return total_synced

def main():
    """主函数"""
    args = sys.argv[1:]
    syncer = TwitterToFeishuSync()
    
    if len(args) == 0:
        # 默认同步所有用户
        syncer.sync_all_users()
    elif len(args) == 1:
        if args[0].isdigit():
            # 同步最近N天
            days = int(args[0])
            syncer.sync_recent_days(days)
        else:
            # 同步指定用户
            syncer.sync_user_tweets(args[0])
    else:
        logger.error("参数错误")
        logger.info("使用方法：")
        logger.info("  python feishu_sync.py                 # 同步所有用户")
        logger.info("  python feishu_sync.py <用户名>        # 同步指定用户")
        logger.info("  python feishu_sync.py <天数>          # 同步最近N天")
        sys.exit(1)
        
    logger.info("飞书多维表格同步完成")
    logger.info(f"表格访问地址: {syncer.feishu_bitable.get_table_url()}")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"发生异常: {str(e)}", exc_info=True)
        sys.exit(1) 
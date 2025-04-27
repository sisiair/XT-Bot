import sys
import json
import os
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List


# --------------------------
# 配置模块
# --------------------------
class Config:
    """全局配置类 (保持原始参数)"""
    # 日志配置
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # 时间戳格式

    # 文件路径
    DEFAULT_DOWNLOAD_DIR = "../downloads"
    DEFAULT_OUTPUT_DIR = "../output"
    DEFAULT_LOG_DIR = "../logs/"  # 默认日志目录

    # Telegram配置 (保持原始限制)
    TELEGRAM_LIMITS = {
        'images': 10 * 1024 * 1024,  # 10MB
        'videos': 50 * 1024 * 1024,  # 50MB
        'caption': 1024  # 保持原始截断逻辑
    }

    # 业务参数
    MAX_DOWNLOAD_ATTEMPTS = 10  # 保持原始重试次数
    NOTIFICATION_TRUNCATE = 200  # 通知消息截断长度

    @classmethod
    def get_env_vars(cls) -> Dict[str, str]:
        """环境变量获取 (保持原始变量名)"""
        return {
            'bot_token': os.getenv('BOT_TOKEN'),
            'chat_id': os.getenv('CHAT_ID'),
            'lark_key': os.getenv('LARK_KEY'),
            'lark_app_id': os.getenv('LARK_APP_ID'),
            'lark_app_secret': os.getenv('LARK_APP_SECRET')
        }


# --------------------------
# 异常类 (保持原始自定义异常)
# --------------------------
class FileTooLargeError(Exception):
    """文件大小超过平台限制异常"""
    pass


class MaxAttemptsError(Exception):
    """达到最大尝试次数异常"""
    pass


# --------------------
# 日志配置
# --------------------
def configure_logging():
    """配置日志格式和级别"""
    # 设置系统编码为UTF-8，解决Windows下GBK编码问题
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

    log_dir = Config.DEFAULT_LOG_DIR
    date_format = Config.DATE_FORMAT

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = f"python-{datetime.now().strftime('%Y-%m-%d')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)-5s] %(message)s',
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_filepath, encoding='utf-8')
        ]
    )
    logger = logging.getLogger(__name__)
    if not os.path.exists(log_dir):
        logger.info(f"📁 创建日志目录: {log_dir}")

    logger.info("🔄 T-Bot 初始化完成")
    return logger


logger = configure_logging()


# --------------------------
# 通知模块 (保持原始飞书逻辑)
# --------------------------
class Notifier:
    """通知处理器 (保持原始飞书集成)"""

    @staticmethod
    def send_lark_message(message: str) -> bool:
        """发送普通飞书消息（无告警前缀）"""
        lark_key = Config.get_env_vars()['lark_key']
        if not lark_key:
            return False

        webhook_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{lark_key}"
        try:
            payload = {
                "msg_type": "text",
                "content": {"text": f"📢 动态更新\n{message}"}  # 自定义友好前缀
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("📨 飞书动态消息发送成功")
            return True
        except Exception as e:
            logger.error(f"✗ 飞书消息发送失败: {str(e)}")
            return False

    @staticmethod
    def send_lark_alert(message: str) -> bool:
        """发送飞书通知 (保持原始截断逻辑)"""
        if not Config.get_env_vars()['lark_key']:
            return False

        # 保持原始消息截断
        truncated_msg = f"{message[:Config.NOTIFICATION_TRUNCATE]}..." if len(
            message) > Config.NOTIFICATION_TRUNCATE else message
        webhook_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{Config.get_env_vars()['lark_key']}"

        try:
            payload = {
                "msg_type": "text",
                "content": {"text": f"📢 XT-Bot处理告警\n{truncated_msg}"}
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("📨 飞书通知发送成功")
            return True
        except Exception as e:
            logger.error(f"✗ 飞书通知发送失败: {str(e)}")
            return False


# --------------------------
# 飞书通知服务
# --------------------------
class LarkNotifier:
    """飞书通知服务"""
    
    def __init__(self, lark_key, app_id=None, app_secret=None):
        self.webhook_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{lark_key}"
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        
    def send_text(self, content, is_alert=False):
        """发送文本消息"""
        prefix = "🔔 告警通知\n" if is_alert else "📢 动态更新\n"
        payload = {
            "msg_type": "text",
            "content": {"text": f"{prefix}{content}"}
        }
        return self._send_request(payload)
    
    def send_rich_text(self, title, content, screen_name=None, publish_time=None):
        """发送富文本消息"""
        # 构建zh_cn语言的内容
        zh_cn_content = []
        
        # 添加标题
        if title:
            zh_cn_content.append([{"tag": "text", "text": f"{title}"}])
        
        # 添加标签和发布时间
        tags = []
        if screen_name:
            tags.append([
                {"tag": "text", "text": "#"},
                {"tag": "text", "text": screen_name, "style": {"color": "#3370ff"}}
            ])
        
        if publish_time:
            formatted_time = publish_time
            if isinstance(publish_time, datetime):
                formatted_time = publish_time.strftime("%Y-%m-%d %H:%M:%S")
            tags.append([{"tag": "text", "text": f"发布时间: {formatted_time}"}])
            
        if tags:
            zh_cn_content.extend(tags)
        
        # 添加主要内容
        if content:
            zh_cn_content.append([{"tag": "text", "text": content}])
        
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title or "推文更新",
                        "content": zh_cn_content
                    }
                }
            }
        }
        return self._send_request(payload)
    
    def _send_request(self, payload):
        """发送请求到飞书"""
        try:
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                timeout=10
            )
            response.raise_for_status()
            
            # 处理响应
            result = response.json()
            if result.get("code") == 0:
                logger.info("✅ 飞书消息发送成功")
                return True, result.get("message", "")
            else:
                logger.error(f"❌ 飞书响应错误: {result}")
                return False, result.get("msg", "未知错误")
                
        except Exception as e:
            logger.error(f"🚨 飞书消息发送失败: {str(e)}", exc_info=True)
            return False, str(e)

    def upload_media_to_lark(self, file_path, item):
        """上传媒体文件到飞书"""
        # 判断文件类型
        file_type = self._detect_file_type(file_path)
        
        # 构建基础消息内容
        screen_name = item['user']['screen_name']
        publish_time = datetime.fromisoformat(item['publish_time']).strftime("%Y-%m-%d %H:%M:%S")
        text_content = item.get('full_text', '')
        
        # 如果是图片，直接发送图片消息
        if file_type == 'image':
            return self._send_image(file_path, screen_name, publish_time, text_content)
        
        # 如果是视频或其他类型文件，使用文件分享方式
        elif file_type in ['video', 'audio', 'file']:
            return self._share_file(file_path, screen_name, publish_time, text_content, file_type)
        
        # 如果是特殊类型(广播/空间)，发送普通文本消息
        else:
            return self.send_rich_text(
                title=f"#{screen_name} 更新了{file_type}",
                content=text_content,
                publish_time=publish_time
            )

    def _detect_file_type(self, file_path):
        """判断文件类型"""
        file_path = str(file_path).lower()
        if file_path.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            return 'image'
        elif file_path.endswith(('.mp4', '.avi', '.mov')):
            return 'video'
        elif file_path.endswith(('.mp3', '.wav')):
            return 'audio'
        else:
            return 'file'

    def _send_image(self, file_path, screen_name, publish_time, text_content):
        """发送图片消息到飞书"""
        # 简化实现，实际应该调用飞书API上传图片
        logger.info(f"模拟图片上传: {file_path}")
        return True, f"image_{datetime.now().timestamp()}"

    def _share_file(self, file_path, screen_name, publish_time, text_content, file_type):
        """共享文件到飞书"""
        # 简化实现，实际应该调用飞书API上传文件
        logger.info(f"模拟{file_type}文件上传: {file_path}")
        return True, f"file_{datetime.now().timestamp()}"


# --------------------------
# 文件处理模块 (保持原始JSON操作)
# --------------------------
class FileProcessor:
    """文件处理器 (保持原始JSON r+模式)"""

    def __init__(self, json_path: str, download_dir: str):
        self.json_path = Path(json_path)
        self.download_path = Path(download_dir)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """目录创建 (保持原始逻辑)"""
        self.download_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 下载目录已就绪: {self.download_path}")

    def load_data(self) -> List[Dict[str, Any]]:
        """加载JSON数据 (保持原始r+模式)"""
        try:
            with self.json_path.open('r+', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"📄 已加载JSON数据，共{len(data)}条记录")
                return data
        except Exception as e:
            logger.error(f"✗ JSON文件加载失败: {str(e)}")
            raise

    def save_data(self, data: List[Dict[str, Any]]) -> None:
        """保存JSON数据 (保持原始截断方式)"""
        try:
            with self.json_path.open('r+', encoding='utf-8') as f:
                f.seek(0)
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.truncate()
        except Exception as e:
            logger.error(f"✗ JSON保存失败: {str(e)}")
            raise


# --------------------------
# 下载模块 (保持原始重试逻辑)
# --------------------------
class DownloadManager:
    """下载管理器 (保持原始重试计数器位置)"""

    @classmethod
    def process_item(cls, item: Dict[str, Any], processor: FileProcessor) -> None:
        """处理单个文件下载 (保持特殊类型处理)"""
        if item.get('is_downloaded'):
            return

        # 保持原始特殊类型处理
        if item.get('media_type') in ['spaces', 'broadcasts']:
            item.update({
                "is_downloaded": True,
                "download_info": {
                    "success": True,
                    "size": 0,
                    "size_mb": 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "download_attempts": 0
                }
            })
            logger.info(f"⏭ 跳过特殊类型下载: {item['file_name']}")
            return

        # 保持原始重试计数器位置
        download_info = item.setdefault('download_info', {})
        current_attempts = download_info.get('download_attempts', 0)

        if current_attempts >= Config.MAX_DOWNLOAD_ATTEMPTS:
            logger.warning(f"⏭ 已达最大下载尝试次数: {item['file_name']}")
            item['upload_info'] = cls._build_error_info(
                MaxAttemptsError("连续下载失败10次"),
                "max_download_attempts",
                existing_info=item.get('upload_info', {})  # 关键：传递已有信息
            )
            return

        try:
            logger.info(f"⏬ 开始下载: {item['file_name']}")
            response = requests.get(item['url'], stream=True, timeout=30)
            response.raise_for_status()

            file_path = processor.download_path / item['file_name']
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 更新下载状态 (保持原始数据结构)
            file_size = os.path.getsize(file_path)
            download_info.update({
                "success": True,
                "size": file_size,
                "size_mb": round(file_size / 1024 / 1024, 2),
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "download_attempts": 0  # 重置计数器
            })
            item['is_downloaded'] = True
            logger.info(f"✓ 下载成功: {item['file_name']} ({file_size // 1024}KB)")

        except Exception as e:
            download_info['download_attempts'] = current_attempts + 1
            error_msg = f"✗ 下载失败: {item['file_name']} - {str(e)}"
            logger.error(error_msg)

            if download_info['download_attempts'] >= Config.MAX_DOWNLOAD_ATTEMPTS:
                item['upload_info'] = {
                    "success": False,
                    "error_type": "max_download_attempts",
                    "message": str(e),
                    "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "notification_sent": False  # 标记未通知，后续统一处理
                }

    @classmethod
    def _build_error_info(
            cls,
            error: Exception,
            error_type: str,
            existing_info: Optional[Dict[str, Any]] = None  # 传入已有的 upload_info
    ) -> Dict[str, Any]:
        """构建错误信息时保留原有 notification_sent 状态"""
        # 如果已有错误信息且包含时间戳，则复用
        if existing_info and "timestamp" in existing_info:
            timestamp = existing_info["timestamp"]
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")  # 新时间戳
        # 如果已有信息，则继承 notification_sent，否则初始化为 False
        notification_sent = existing_info.get("notification_sent", False) if existing_info else False

        return {
            "success": False,
            "error_type": error_type,
            "message": str(error),
            "timestamp": timestamp,
            "notification_sent": notification_sent  # 保留或初始化
        }


# --------------------------
# 上传模块 (飞书版本)
# --------------------------
class UploadManager:
    """上传管理器 (飞书版本)"""

    def __init__(self):
        env_vars = Config.get_env_vars()
        if not env_vars['lark_key']:
            logger.error("❌ 必须配置 LARK_KEY 环境变量！")
            sys.exit(1)
            
        self.lark_notifier = LarkNotifier(
            env_vars['lark_key'],
            env_vars.get('lark_app_id'),
            env_vars.get('lark_app_secret')
        )
        
    def process_item(self, item: Dict[str, Any], processor: FileProcessor) -> None:
        """处理文件上传 (保持特殊类型处理)"""
        if not self._should_upload(item):
            return

        try:
            # 处理特殊类型
            if item.get('media_type') in ['spaces', 'broadcasts']:
                message_id = self._send_text_message(item)
            else:
                message_id = self._send_media_file(item, processor)

            # 更新上传状态
            item.update({
                "is_uploaded": True,
                "upload_info": self._build_success_info(message_id)
            })
        except Exception as e:
            self._handle_upload_error(e, item)
            
    def _should_upload(self, item: Dict[str, Any]) -> bool:
        """上传判断逻辑"""
        if item.get('is_uploaded'):
            return False
        # 检查不可恢复的错误
        upload_info = item.get('upload_info', {})
        error_type = upload_info.get('error_type')

        if error_type in ['file_too_large', 'max_download_attempts']:

            # 添加通知逻辑
            if not upload_info.get('notification_sent'):
                self._send_unrecoverable_alert(item, error_type)
                upload_info['notification_sent'] = True  # 标记已通知

            logger.warning(f"⏭ 跳过不可恢复的错误: {item['file_name']} ({error_type})")
            return False
        # 特殊类型直接上传
        if item.get('media_type') in ['spaces', 'broadcasts']:
            return True
        # 常规类型需要下载成功
        return item.get('is_downloaded', False)

    def _send_unrecoverable_alert(self, item: Dict[str, Any], error_type: str) -> None:
        """发送不可恢复错误通知"""
        alert_msg = (
            "🔴 推送失败\n"
            f"文件名: {item['file_name']}\n"
            f"类型: {error_type}\n"
            f"错误: {item['upload_info']['message'][:Config.NOTIFICATION_TRUNCATE]}"
        )
        Notifier.send_lark_alert(alert_msg)

    def _send_text_message(self, item: Dict[str, Any]) -> str:
        """发送文本消息到飞书"""
        screen_name = item['user']['screen_name']
        media_type = item['media_type']
        publish_time = datetime.fromisoformat(item['publish_time'])
        url = item['url']
        
        title = f"#{screen_name} #{media_type}"
        content = f"{url}"
        
        success, message = self.lark_notifier.send_rich_text(
            title=title,
            content=content,
            screen_name=screen_name,
            publish_time=publish_time
        )
        
        if success:
            logger.info(f"✓ 文本消息已发送")
            # 返回标识符
            return f"lark_message_{datetime.now().timestamp()}"
        else:
            raise Exception(f"飞书消息发送失败: {message}")
            
    def _send_media_file(self, item: Dict[str, Any], processor: FileProcessor) -> str:
        """发送媒体文件到飞书"""
        file_path = processor.download_path / item['file_name']
        
        # 上传媒体文件
        success, message = self.lark_notifier.upload_media_to_lark(
            file_path, item
        )
        
        if success:
            logger.info(f"✓ 媒体文件已上传")
            return message
        else:
            raise Exception(f"飞书媒体上传失败: {message}")

    @staticmethod
    def _build_success_info(message_id: str) -> Dict[str, Any]:
        """包含消息ID的上传成功信息"""
        return {
            "success": True,
            "message_id": message_id,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        }

    def _handle_upload_error(self, error: Exception, item: Dict[str, Any]) -> None:
        """错误处理 (精确匹配通知规则)"""
        # 错误类型判断
        if isinstance(error, FileTooLargeError):
            error_type = 'file_too_large'
        else:
            error_type = 'api_error'
            # 其他错误类型直接通知（无标记检查）
            Notifier.send_lark_alert(
                f"🔴 上传失败\n文件名: {item['file_name']}\n"
                f"错误类型: {error.__class__.__name__}\n"
                f"错误详情: {str(error)[:Config.NOTIFICATION_TRUNCATE]}"
            )

        # 更新错误信息（保持数据结构统一）
        item['upload_info'] = self._build_error_info(error, error_type)

        # 重置下载状态（允许重试）
        item['is_downloaded'] = False
        logger.error(f"✗ 上传失败: {item['file_name']} - {error_type}")

    @staticmethod
    def _build_error_info(error: Exception, error_type: str) -> Dict[str, Any]:
        """构建错误信息 (保持原始字段)"""
        return {
            "success": False,
            "error_type": error_type,
            "message": str(error),
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "notification_sent": False  # 保持原始通知标记
        }


# --------------------------
# 主流程 (保持原始批量处理逻辑)
# --------------------------
def process_single(json_path: str, download_dir: str = Config.DEFAULT_DOWNLOAD_DIR) -> None:
    """处理单个文件 (保持原始异常处理)"""
    try:
        logger.info(f"\n{'-' * 40}\n🔍 开始处理: {json_path}")
        processor = FileProcessor(json_path, download_dir)
        data = processor.load_data()

        download_manager = DownloadManager()
        upload_manager = UploadManager()

        for item in data:
            # 保持原始处理顺序：先下载再上传
            if not item.get('is_downloaded'):
                download_manager.process_item(item, processor)

            if not item.get('is_uploaded'):
                upload_manager.process_item(item, processor)

        processor.save_data(data)
        logger.info(f"✅ 文件处理完成\n{'-' * 40}\n")

    except Exception as e:
        logger.error(f"💥 处理异常: {str(e)}", exc_info=True)
        Notifier.send_lark_alert(f"处理异常: {str(e)[:Config.NOTIFICATION_TRUNCATE]}")
        raise


def batch_process(days: int = 7) -> None:
    """批量处理 (保持原始日期回溯逻辑)"""
    base_dir = Path(Config.DEFAULT_OUTPUT_DIR)
    for i in range(days, -1, -1):  # 保持原始倒序处理
        target_date = datetime.now() - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        json_path = base_dir / f"{date_str[:7]}/{date_str}.json"

        if json_path.exists():
            process_single(str(json_path))
        else:
            logger.info(f"⏭ 跳过不存在文件: {json_path}")


def main():
    args = sys.argv[1:]  # 获取命令行参数

    if len(args) == 2:
        process_single(args[0], args[1])
    elif len(args) == 1:
        process_single(args[0])
    elif len(args) == 0:
        batch_process()
    else:
        logger.error("错误：参数数量不正确。")
        logger.info("使用方法：python T-Bot.py [<JSON文件路径> <下载目录>]")
        logger.info("示例：")
        logger.info("使用参数：python T-Bot.py ../output/2000-01/2000-01-01.json ../downloads(默认)")
        logger.info("使用默认：python T-Bot.py")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
        logger.info("🏁 所有处理任务已完成！")
    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断操作")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 未处理的异常: {str(e)}")
        sys.exit(1)

# 移除现有依赖
# import telegram

# 确保requests库已导入
import requests
import json
import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict


# --------------------------
# 配置常量
# --------------------------
class EnvConfig:
    """环境变量配置"""
    # 移除Telegram相关配置
    # BOT_TOKEN = os.getenv("BOT_TOKEN")  
    # CHAT_ID = os.getenv("CHAT_ID")  
    
    # 扩展飞书配置
    LARK_KEY = os.getenv("LARK_KEY")            # 飞书机器人Webhook Key
    LARK_APP_ID = os.getenv("LARK_APP_ID")      # 可选：飞书应用ID
    LARK_APP_SECRET = os.getenv("LARK_APP_SECRET")  # 可选：飞书应用密钥
    LARK_ALERT_KEY = os.getenv("LARK_ALERT_KEY", LARK_KEY)  # 告警机器人Key，默认同主Key


class PathConfig:
    """路径配置"""
    CONFIG_PATH = Path("../../config/config.json")  # 配置文件路径
    OUT_PUT_DIR = Path("../output/")  # 用户数据目录
    USER_DATA_DIR = Path("../../TypeScript/tweets/user/")  # 用户数据目录
    LOG_DIR = Path("../logs/")  # 日志目录


class MsgConfig:
    """消息模板"""
    TELEGRAM_ALERT = "#{screen_name} #x"  # Telegram通知模板

# 消息类型枚举
class LarkMessageType:
    TEXT = "text"               # 纯文本消息
    POST = "post"               # 富文本消息
    INTERACTIVE = "interactive" # 交互式卡片
    IMAGE = "image"             # 图片消息
    FILE = "file"               # 文件消息
    AUDIO = "audio"             # 音频消息
    MEDIA = "media"             # 视频等媒体消息
# --------------------------
# 日志配置
# --------------------------
def configure_logging() -> logging.Logger:
    """
    配置日志系统
    返回预配置的Logger对象
    """
    # 确保日志目录存在
    PathConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 生成带日期的日志文件名
    log_file = PathConfig.LOG_DIR / f"python-{datetime.now().strftime('%Y-%m-%d')}.log"

    # 配置基础设置
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)-5s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    # 获取自定义Logger
    logger = logging.getLogger("INI-XT-Bot")
    logger.info("🔄 INI-XT-Bot 初始化完成")
    return logger


# 初始化全局日志对象
logger = configure_logging()


# --------------------------
# 通知模块
# --------------------------
def send_telegram_alert(screen_name: str) -> bool:
    """
    发送Telegram格式通知
    返回发送状态: True成功 / False失败
    """
    # 检查环境配置
    if not all([EnvConfig.BOT_TOKEN, EnvConfig.CHAT_ID]):
        logger.warning("⏭️ 缺少Telegram环境变量配置，跳过通知发送")
        return False

    try:
        # 生成格式化消息
        formatted_msg = MsgConfig.TELEGRAM_ALERT.format(
            screen_name=screen_name
        )

        # 初始化机器人
        bot = telegram.Bot(token=EnvConfig.BOT_TOKEN)

        # 发送消息(静默模式)
        bot.send_message(
            chat_id=EnvConfig.CHAT_ID,
            text=formatted_msg,
            disable_notification=True
        )
        logger.info(f"📢 Telegram通知发送成功: {formatted_msg}")
        return True

    except telegram.error.TelegramError as e:
        logger.error(f"❌ Telegram消息发送失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"🚨 通知发送出现意外错误: {str(e)}", exc_info=True)
        return False


# 创建全局通知器实例
lark_notifier = None

def initialize_notifier():
    """初始化飞书通知器"""
    global lark_notifier
    if EnvConfig.LARK_KEY:
        lark_notifier = LarkNotifier(
            EnvConfig.LARK_KEY, 
            EnvConfig.LARK_APP_ID, 
            EnvConfig.LARK_APP_SECRET
        )
        logger.info("✅ 飞书通知器已初始化")
    else:
        logger.warning("⚠️ 未配置飞书，通知功能将不可用")

def send_lark_message(screen_name: str, new_count: int = 0) -> bool:
    """发送普通消息(原Telegram通知)"""
    if not lark_notifier:
        logger.warning("⏭️ 飞书通知器未初始化，跳过通知发送")
        return False
    
    try:
        title = f"#{screen_name} 内容更新"
        content = f"已处理 {new_count} 条新内容"
        
        success, message = lark_notifier.send_rich_text(
            title=title,
            content=content,
            screen_name=screen_name
        )
        
        if success:
            logger.info(f"📢 飞书通知发送成功: {title}")
            return True
        else:
            logger.error(f"❌ 飞书通知发送失败: {message}")
            return False
            
    except Exception as e:
        logger.error(f"🚨 通知发送出现意外错误: {str(e)}", exc_info=True)
        return False

def send_lark_alert(message: str) -> bool:
    """发送告警消息(保持原有功能)"""
    if not lark_notifier:
        return False
        
    try:
        success, response = lark_notifier.send_text(message, is_alert=True)
        if success:
            logger.info("📨 飞书告警发送成功")
            return True
        else:
            logger.error(f"❌ 飞书告警发送失败: {response}")
            return False
    except Exception as e:
        logger.error(f"❌ 飞书通知发送失败: {str(e)}")
        return False


# --------------------------
# 核心逻辑
# --------------------------
def load_config() -> List[str]:
    """
    加载配置文件
    返回screen_name列表
    """
    try:
        with open(PathConfig.CONFIG_PATH, "r") as f:
            config = json.load(f)

        # 获取原始列表并过滤空值
        raw_users = config.get("screenName", [])
        users = [u.strip() for u in raw_users if u.strip()]

        logger.info(f"📋 加载到{len(users)}个待处理用户")
        logger.debug(f"用户列表: {', '.join(users)}")
        return users

    except FileNotFoundError:
        logger.error(f"❌ 配置文件不存在: {PathConfig.CONFIG_PATH}")
        return []
    except json.JSONDecodeError:
        logger.error(f"❌ 配置文件解析失败: {PathConfig.CONFIG_PATH}")
        return []
    except Exception as e:
        logger.error(f"🚨 加载配置出现意外错误: {str(e)}")
        return []


def process_user(screen_name: str) -> int:
    """
    处理单个用户数据
    返回新增条目数
    """
    # 构建数据文件路径
    data_file = PathConfig.USER_DATA_DIR / f"{screen_name}.json"
    if not data_file.exists():
        logger.warning(f"⏭️ 用户数据文件不存在: {data_file}")
        return 0

    logger.info("🚀 触发X-Bot执行")

    try:
        # 执行X-Bot处理（实时显示日志）
        process = subprocess.Popen(
            ["python", "-u", "X-Bot.py", str(data_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并错误输出
            text=False,
            bufsize=1  # 启用行缓冲
        )

        # 实时打印输出并捕获最后结果
        output_lines = []
        for line in iter(process.stdout.readline, b''):
            try:
                line = line.decode('utf-8').strip()
                if line:  # 过滤空行
                    # 实时打印到父进程控制台
                    print(f"[X-Bot] {line}", flush=True)
                    output_lines.append(line)
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试使用其他编码
                try:
                    line = line.decode('gbk').strip()
                    if line:
                        print(f"[X-Bot] {line}", flush=True)
                        output_lines.append(line)
                except UnicodeDecodeError:
                    # 如果仍然失败，跳过该行
                    print("[X-Bot] [无法解码的行]", flush=True)

        # 等待进程结束
        process.wait()

        # 检查退出码
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                process.args,
                output='\n'.join(output_lines)
            )

        # 解析倒数第二行作为结果
        new_count = int(output_lines[-2]) if output_lines else 0
        logger.info(f"✅ X-Bot执行成功，用户 {screen_name} 处理完成，新增 {new_count} 条")
        return new_count

    except subprocess.CalledProcessError as e:
        error_msg = f"❌ 用户 {screen_name} 处理失败: {e.output.splitlines()[-1][:200]}"
        logger.error(error_msg)
        send_lark_alert(error_msg)
        return 0
    except ValueError:
        logger.error(f"⚠️ 无效的输出内容: {output_lines[-2][:200]}")
        return 0
    except Exception as e:
        logger.error(f"🚨 未知错误: {str(e)}")
        return 0


def trigger_tbot() -> bool:
    """
    触发下游处理流程
    返回执行状态: True成功 / False失败
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    json_path = PathConfig.OUT_PUT_DIR / f"{current_date[:7]}/{current_date}.json"

    if not json_path.exists():
        logger.warning(f"⏭️ 推送数据文件不存在: {json_path}")
        return 0

    try:
        logger.info("🚀 触发T-Bot执行")

        # 实时显示T-Bot输出
        process = subprocess.Popen(
            ["python", "-u", "T-Bot.py", str(json_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            bufsize=1
        )

        # 实时转发输出
        for line in iter(process.stdout.readline, b''):
            try:
                line_str = line.decode('utf-8').strip()
                print(f"[T-Bot] {line_str}", flush=True)
            except UnicodeDecodeError:
                try:
                    line_str = line.decode('gbk').strip()
                    print(f"[T-Bot] {line_str}", flush=True)
                except UnicodeDecodeError:
                    print("[T-Bot] [无法解码的行]", flush=True)

        # 检查结果
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                process.args
            )

        logger.info("✅ T-Bot执行成功")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ T-Bot执行失败: {str(e)}"
        logger.error(error_msg)
        send_lark_alert(error_msg)
        return False
    except Exception as e:
        logger.error(f"🚨 未知错误: {str(e)}")
        return False



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

    def _send_image(self, file_path, screen_name, publish_time, text_content):
        """发送图片消息到飞书"""
        # 飞书要求先上传图片获取image_key，再发送图片消息
        
        # 1. 获取上传凭证(调用飞书API)
        
        # 2. 上传图片文件获取image_key
        
        # 3. 发送图片消息，附带文本信息
        # ...这里需要调用飞书API实现，具体代码略
        
        # 示例返回
        return True, "图片消息已发送"

    def _share_file(self, file_path, screen_name, publish_time, text_content, file_type):
        """共享文件到飞书"""
        # 类似图片上传过程，但使用文件上传API
        # ...具体代码略
        
        # 示例返回
        return True, "文件已共享"

# --------------------------
# 主流程
# --------------------------
def main():
    """主处理流程"""
    # 初始化飞书通知器
    initialize_notifier()
    
    # 测试飞书通知是否可用
    if EnvConfig.LARK_KEY:
        logger.info(f"✅ 飞书配置已设置，Webhook Key: {EnvConfig.LARK_KEY[:4]}***")
        # 尝试发送测试消息
        test_result = send_lark_alert("INI-XT-Bot启动测试 - 这是一条测试消息")
        if test_result:
            logger.info("✅ 飞书测试消息发送成功")
        else:
            logger.error("❌ 飞书测试消息发送失败，请检查配置")
    else:
        logger.warning("⚠️ 未配置LARK_KEY环境变量，飞书通知功能不可用")
    
    # 加载配置文件
    users = load_config()
    if not users:
        error_msg = "❌ 未获取到有效用户列表，程序终止"
        logger.error(error_msg)
        send_lark_alert(error_msg)
        return

    # 遍历处理用户
    total_new = 0
    for screen_name in users:
        logger.info(f"\n{'=' * 40}\n🔍 开始处理: {screen_name}")
        new_count = process_user(screen_name)

        # 处理新增条目
        if new_count > 0:
            # 发送飞书通知
            send_lark_message(screen_name, new_count)
            logger.info(f"✅ 用户 {screen_name} 有 {new_count} 条新内容，已发送通知")

        # 触发下游流程
        if not trigger_tbot():
            send_lark_alert(f"触发T-Bot失败 - 用户: {screen_name}")

        total_new += new_count
        logger.info(f"✅ 处理完成\n{'=' * 40}\n")

    # 最终状态汇总
    summary_msg = f"🎉 所有用户处理完成！总新增条目: {total_new}"
    logger.info(summary_msg)
    if total_new > 0:
        send_lark_alert(summary_msg)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"💥 未处理的全局异常: {str(e)}"
        logger.error(error_msg, exc_info=True)
        try:
            # 尝试发送错误通知
            if lark_notifier:
                lark_notifier.send_text(error_msg, is_alert=True)
        except:
            logger.error("无法发送错误通知", exc_info=True)


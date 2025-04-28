import os
import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class FeishuBitable:
    """飞书多维表格操作类"""
    
    # 飞书API基础URL
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    def __init__(self):
        """初始化飞书多维表格操作类"""
        self.app_id = os.getenv("FEISHU_APP_ID")
        self.app_secret = os.getenv("FEISHU_APP_SECRET")
        self.bitable_id = os.getenv("FEISHU_BITABLE_ID")
        self.table_id = os.getenv("FEISHU_TABLE_ID")
        
        if not all([self.app_id, self.app_secret]):
            logger.warning("⚠️ 缺少飞书应用配置，将无法使用多维表格功能")
            self.enabled = False
            return
            
        self.enabled = True
        self.access_token = None
        self.token_expire_time = 0
        
        # 表格字段定义
        self.fields = {
            "账号": "text",
            "内容": "text",
            "URL": "url",
            "图片": "text",
            "视频": "text",
            "发布时间": "datetime"
        }
    
    def get_access_token(self) -> str:
        """获取飞书访问令牌"""
        now = datetime.now().timestamp()
        
        # 如果令牌有效则直接返回
        if self.access_token and self.token_expire_time > now:
            return self.access_token
            
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload)
            data = response.json()
            
            if data.get("code") == 0:
                self.access_token = data.get("tenant_access_token")
                # 设置令牌过期时间（提前5分钟过期）
                self.token_expire_time = now + data.get("expire") - 300
                return self.access_token
            else:
                logger.error(f"获取飞书访问令牌失败: {data}")
                return None
        except Exception as e:
            logger.error(f"获取飞书访问令牌异常: {str(e)}")
            return None
    
    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> Dict:
        """发送请求到飞书API"""
        if not self.enabled:
            return {"error": "飞书多维表格功能未启用"}
            
        token = self.get_access_token()
        if not token:
            return {"error": "无法获取飞书访问令牌"}
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method.lower() == "get":
                response = requests.get(url, headers=headers)
            elif method.lower() == "post":
                response = requests.post(url, headers=headers, json=payload)
            elif method.lower() == "put":
                response = requests.put(url, headers=headers, json=payload)
            else:
                return {"error": f"不支持的请求方法: {method}"}
                
            return response.json()
        except Exception as e:
            logger.error(f"飞书API请求异常: {str(e)}")
            return {"error": str(e)}
    
    def create_bitable(self, name: str = "Twitter数据") -> Dict:
        """创建飞书多维表格"""
        if self.bitable_id:
            return {"app_token": self.bitable_id}
            
        payload = {
            "name": name,
            "folder_token": "fldbcO1UuP2iuQpB2g9JLxJvmuf" # 默认目录
        }
        
        result = self._make_request("POST", "/bitable/v1/apps", payload)
        
        if "data" in result and "app" in result["data"]:
            self.bitable_id = result["data"]["app"]["app_token"]
            logger.info(f"✅ 成功创建飞书多维表格: {self.bitable_id}")
            return {"app_token": self.bitable_id}
        else:
            logger.error(f"❌ 创建飞书多维表格失败: {result}")
            return result
    
    def create_table(self, bitable_id: str, table_name: str = "Twitter数据") -> Dict:
        """在多维表格中创建数据表"""
        if self.table_id:
            return {"table_id": self.table_id}
            
        payload = {
            "table": {
                "name": table_name
            }
        }
        
        result = self._make_request(
            "POST", 
            f"/bitable/v1/apps/{bitable_id}/tables", 
            payload
        )
        
        if "data" in result and "table" in result["data"]:
            self.table_id = result["data"]["table"]["table_id"]
            logger.info(f"✅ 成功创建数据表: {self.table_id}")
            return {"table_id": self.table_id}
        else:
            logger.error(f"❌ 创建数据表失败: {result}")
            return result
    
    def create_fields(self, bitable_id: str, table_id: str) -> bool:
        """创建表格字段"""
        success = True
        
        for field_name, field_type in self.fields.items():
            payload = {
                "field": {
                    "name": field_name,
                    "type": field_type
                }
            }
            
            result = self._make_request(
                "POST",
                f"/bitable/v1/apps/{bitable_id}/tables/{table_id}/fields",
                payload
            )
            
            if "code" in result and result["code"] != 0:
                logger.error(f"❌ 创建字段 {field_name} 失败: {result}")
                success = False
            
        return success
    
    def get_fields(self, bitable_id: str, table_id: str) -> Dict:
        """获取表格字段信息"""
        result = self._make_request(
            "GET",
            f"/bitable/v1/apps/{bitable_id}/tables/{table_id}/fields"
        )
        
        if "data" in result and "items" in result["data"]:
            fields = {}
            for item in result["data"]["items"]:
                fields[item["field"]["name"]] = item["field"]["field_id"]
            return fields
        else:
            logger.error(f"❌ 获取字段信息失败: {result}")
            return {}
    
    def batch_insert_records(self, tweets_data: List[Dict]) -> bool:
        """批量插入推特数据到飞书多维表格"""
        if not self.enabled:
            logger.warning("⚠️ 飞书多维表格功能未启用")
            return False
            
        # 确保有多维表格ID
        if not self.bitable_id:
            result = self.create_bitable()
            if "app_token" not in result:
                return False
        
        # 确保有数据表ID
        if not self.table_id:
            result = self.create_table(self.bitable_id)
            if "table_id" not in result:
                return False
                
        # 获取字段信息
        fields = self.get_fields(self.bitable_id, self.table_id)
        if not fields:
            # 如果没有字段，创建字段
            if not self.create_fields(self.bitable_id, self.table_id):
                return False
            # 重新获取字段信息
            fields = self.get_fields(self.bitable_id, self.table_id)
            
        # 准备批量插入的记录
        records = []
        for tweet in tweets_data:
            record = {
                "fields": {
                    fields["账号"]: tweet["user"].get("name", "未知"),
                    fields["内容"]: tweet.get("fullText", ""),
                    fields["URL"]: tweet.get("tweetUrl", ""),
                    fields["图片"]: json.dumps(tweet.get("images", []), ensure_ascii=False),
                    fields["视频"]: json.dumps(tweet.get("videos", []), ensure_ascii=False),
                    fields["发布时间"]: tweet.get("publishTime", "")
                }
            }
            records.append(record)
            
        # 分批插入记录（飞书API限制单次最多500条）
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            payload = {
                "records": batch
            }
            
            result = self._make_request(
                "POST",
                f"/bitable/v1/apps/{self.bitable_id}/tables/{self.table_id}/records/batch_create",
                payload
            )
            
            if "code" in result and result["code"] != 0:
                logger.error(f"❌ 批量插入记录失败: {result}")
                return False
                
        logger.info(f"✅ 成功插入 {len(records)} 条推特数据到飞书多维表格")
        return True
        
    def check_tweet_exists(self, tweet_url: str) -> bool:
        """检查推特是否已存在于多维表格"""
        # 实际实现需要查询API
        # 这里简化处理，仅作为示例
        # TODO: 实现实际检查逻辑
        return False

    def get_table_url(self) -> str:
        """获取多维表格的访问URL"""
        if self.bitable_id and self.table_id:
            return f"https://applink.feishu.cn/client/sheet/home/bitable/{self.bitable_id}?table_id={self.table_id}"
        return "未创建表格" 
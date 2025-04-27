import os
import json
import sys

def main():
    # 获取环境变量
    screen_name = os.environ.get('SCREEN_NAME', '')
    
    # 打印调试信息
    print(f"读取到的SCREEN_NAME环境变量: {screen_name}")
    
    # 如果SCREEN_NAME包含多个值（逗号分隔），则分割为列表
    screen_names = [name.strip() for name in screen_name.split(',') if name.strip()] if screen_name else []
    
    # 创建配置对象
    config = {
        "screenName": screen_names,
        "interval": 5000,
        "filterRetweets": True,
        "filterQuotes": True,
        "maxRetries": 3,
        "limit": 10
    }
    
    print(f"ℹ️ 创建配置：{json.dumps(config)}")
    
    # 确保路径正确
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 从脚本目录计算config目录的绝对路径
    config_dir = os.path.abspath(os.path.join(script_dir, '../../config'))
    config_path = os.path.join(config_dir, 'config.json')
    
    try:
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 配置文件已生成：{config_path}")
        return 0
    except Exception as e:
        print(f"错误：文件写入失败（{e}）")
        
        # 直接尝试在当前工作目录创建config文件夹
        try:
            cwd_config_dir = os.path.join(os.getcwd(), 'config')
            os.makedirs(cwd_config_dir, exist_ok=True)
            cwd_config_path = os.path.join(cwd_config_dir, 'config.json')
            
            with open(cwd_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✓ 配置文件已生成在工作目录：{cwd_config_path}")
            return 0
        except Exception as e:
            print(f"错误：在工作目录创建配置也失败（{e}）")
            
            # 最后尝试直接在根目录创建
            try:
                root_config_path = '/config/config.json'
                os.makedirs('/config', exist_ok=True)
                with open(root_config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print(f"✓ 配置文件已生成在根目录：{root_config_path}")
                return 0
            except Exception as e:
                print(f"❌ 所有尝试均失败：{e}")
                return 1

if __name__ == "__main__":
    sys.exit(main()) 
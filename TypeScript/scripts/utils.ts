import {TwitterOpenApi} from "twitter-openapi-typescript";
import axios from "axios";
import {TwitterApi} from 'twitter-api-v2';

export const _xClient = async (TOKEN: string) => {
    // 添加调试输出，确认token是否存在及其长度
    console.log(`🔄 开始创建X客户端`);
    if (!TOKEN) {
        console.error(`❌ 严重错误：未提供有效的AUTH_TOKEN！请检查环境变量设置`);
        throw new Error('未提供AUTH_TOKEN，请检查环境变量设置');
    }
    console.log(`✅ 收到AUTH_TOKEN，长度: ${TOKEN.length}`);
    
    try {
        // 添加调试输出
        console.log(`🌐 开始请求X.com manifest.json...`);
        const resp = await axios.get("https://x.com/manifest.json", {
            headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                cookie: `auth_token=${TOKEN}`,
            },
            timeout: 10000, // 10秒超时
        });

        console.log(`✅ 获取manifest成功，状态码: ${resp.status}`);
        
        const resCookie = resp.headers["set-cookie"] as string[];
        if (!resCookie || resCookie.length === 0) {
            console.warn('⚠️ 警告：未获取到任何cookie，可能影响后续认证');
        } else {
            console.log(`✅ 获取到${resCookie.length}个cookie`);
        }
        
        const cookieObj = resCookie ? resCookie.reduce((acc: Record<string, string>, cookie: string) => {
            const parts = cookie.split(";")[0].split("=");
            if (parts.length >= 2) {
                const name = parts[0];
                const value = parts[1];
                acc[name] = value;
            }
            return acc;
        }, {}) : {};

        // 添加auth_token到cookie对象
        cookieObj.auth_token = TOKEN;
        
        console.log(`🔄 正在初始化TwitterOpenApi...`);
        const api = new TwitterOpenApi();
        
        console.log(`🔄 使用cookie创建客户端...`);
        const client = await api.getClientFromCookies(cookieObj);
        
        if (!client) {
            throw new Error('客户端初始化失败，返回值为空');
        }
        
        console.log('✅ 认证客户端创建成功');
        return client;
    } catch (error: any) {
        // 详细输出错误信息
        console.error(`❌ 创建客户端失败: ${error.message}`);
        if (error.response) {
            console.error(`❌ 响应状态: ${error.response.status}`);
            console.error(`❌ 响应数据: ${JSON.stringify(error.response.data || {})}`);
        }
        // 继续抛出错误让上层处理
        throw error;
    }
};

export const XAuthClient = () => {
    // 输出环境变量信息以便调试
    const authToken = process.env.AUTH_TOKEN;
    
    console.log(`🔍 环境变量检查:`);
    console.log(`AUTH_TOKEN存在: ${!!authToken}`);
    
    if (!authToken) {
        console.error('❌ AUTH_TOKEN环境变量未设置或为空!');
        throw new Error('AUTH_TOKEN环境变量未设置，请确保在运行此脚本前设置环境变量');
    }
    
    return _xClient(authToken);
};


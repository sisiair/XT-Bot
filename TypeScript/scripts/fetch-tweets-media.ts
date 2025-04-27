import '../utils/logger';
import {cleanupLogger} from '../utils/logger';
import {processTweetsByScreenName} from './fetch-tweets';
import {XAuthClient} from "./utils";
import fs from 'fs';
import path from 'path';

// 用户处理逻辑
async function processUser(screenName: string, client: XAuthClient) {
    try {
        console.log('🚀 开始处理用户:', screenName);

        // 使用主函数传递的客户端
        try {
            await processTweetsByScreenName(screenName, client, {
                contentType: "tweets"
            });
            console.log(`✅ [${screenName}] 推文处理完成`);
        } catch (tweetsError) {
            console.error(`❌ [${screenName}] 推文处理失败:`, tweetsError instanceof Error ? tweetsError.message : tweetsError);
            console.log(`⚠️ [${screenName}] 继续处理媒体...`);
        }

        try {
            await processTweetsByScreenName(screenName, client, {
                contentType: "media"
            });
            console.log(`✅ [${screenName}] 媒体处理完成`);
        } catch (mediaError) {
            console.error(`❌ [${screenName}] 媒体处理失败:`, mediaError instanceof Error ? mediaError.message : mediaError);
        }

    } catch (error) {
        console.error(`❌ [${screenName}] 处理失败:`, error instanceof Error ? error.message : error);
    }
}

// 主执行程序
async function main() {

    try {
        // 初始化全局客户端
        const client = await XAuthClient();

        // 读取配置文件
        const configPath = path.resolve(__dirname, '../../config/config.json');
        if (!fs.existsSync(configPath)) {
            // 尝试创建默认配置
            try {
                const screenName = process.env.SCREEN_NAME;
                if (screenName) {
                    const defaultConfig = {
                        screenName: [screenName]
                    };
                    fs.mkdirSync(path.dirname(configPath), { recursive: true });
                    fs.writeFileSync(configPath, JSON.stringify(defaultConfig, null, 2));
                    console.log(`✅ 已使用环境变量创建默认配置文件: ${configPath}`);
                } else {
                    throw new Error('环境变量 SCREEN_NAME 未设置');
                }
            } catch (createError) {
                console.error(`❌ 无法创建配置文件: ${createError.message}`);
                throw new Error(`配置文件不存在: ${configPath}`);
            }
        }

        const configData = fs.readFileSync(configPath, 'utf-8');
        let config;
        try {
            config = JSON.parse(configData);
        } catch (parseError) {
            console.error(`❌ 配置文件格式错误: ${parseError.message}`);
            // 尝试从环境变量创建配置
            const screenName = process.env.SCREEN_NAME;
            if (screenName) {
                config = { screenName: [screenName] };
                console.log(`✅ 已使用环境变量 SCREEN_NAME=${screenName} 作为备用配置`);
            } else {
                throw new Error('配置文件解析失败且环境变量 SCREEN_NAME 未设置');
            }
        }

        // 严格校验配置结构
        if (!config || !config.screenName) {
            throw new Error('配置文件必须包含 screenName 字段');
        }

        const screenNames = config.screenName;
        if (!Array.isArray(screenNames)) {
            throw new Error('screenName 必须为数组');
        }

        if (screenNames.length === 0) {
            console.warn('⚠️ 用户名列表为空，尝试从环境变量获取');
            const envUser = process.env.SCREEN_NAME;
            if (envUser) {
                screenNames.push(envUser);
                console.log(`✅ 已添加环境变量中的用户: ${envUser}`);
            }
        }

        // 如果仍然没有用户名，则报错
        if (screenNames.length === 0) {
            throw new Error('没有有效的用户名可处理');
        }

        let processedCount = 0;
        let errorCount = 0;

        for (const item of screenNames) {
            if (typeof item !== 'string') {
                console.warn(`⚠️ 跳过非字符串用户项：${typeof item} [${JSON.stringify(item)}]`);
                continue;
            }

            const screenName = item.trim();
            if (!screenName) {
                console.warn('⚠️ 跳过空用户名');
                continue;
            }

            try {
                await processUser(screenName, client);
                processedCount++;
            } catch (userError) {
                errorCount++;
                console.error(`❌ 处理用户 ${screenName} 失败:`, userError instanceof Error ? userError.message : userError);
            }
        }

        console.log(`\n🎉 处理完成! 成功: ${processedCount}/${screenNames.length} 用户`);
        if (errorCount > 0) {
            console.warn(`⚠️ ${errorCount} 个用户处理失败`);
            if (errorCount === screenNames.length) {
                throw new Error('所有用户处理都失败了');
            }
        }

    } catch (error) {
        console.error('❌ 初始化失败:', error instanceof Error ? error.message : error);
        process.exitCode = 1;
    } finally {
        // 统一清理资源
        await cleanupLogger();
        process.exit(process.exitCode || 0);
    }
}

// 启动程序
main();
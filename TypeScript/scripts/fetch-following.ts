import '../utils/logger';
import {cleanupLogger} from '../utils/logger';
import {XAuthClient} from "./utils";
import path from 'path';
import fs from "fs-extra";
import {get} from 'lodash';
import dayjs from "dayjs";

export async function processHomeTimeline() {
    console.log(`----- ----- ----- ----- fetch-following begin ----- ----- ----- -----`);
    try {
        const client = await XAuthClient();

        // 存储最终用户数据
        let finalUsers: any[] = [];
        const envScreenName = process.env.SCREEN_NAME;
        
        // 获取用户列表
        try {
            const configPath = path.resolve(__dirname, '../../config/config.json');
            if (fs.existsSync(configPath)) {
                const configData = fs.readFileSync(configPath, 'utf-8');
                const config = JSON.parse(configData);
                if (config && Array.isArray(config.screenName) && config.screenName.length > 0) {
                    const screenNames = config.screenName.filter((name: string) => name && name.trim());
                    console.log(`✅ 从配置文件获取到 ${screenNames.length} 个用户`);
                    
                    // 限制处理数量
                    const limit = config.limit || 20; // 默认限制为20
                    console.log(`ℹ️ 每个用户数据限制: ${limit} 条`);
                    
                    // 直接处理配置文件中的用户列表
                    for (const screenName of screenNames) {
                        console.log(`\n=== 处理用户: @${screenName} ===`);
                        
                        try {
                            // 获取用户基本信息
                            const response = await client.getUserApi().getUserByScreenName({screenName});
                            if (!response.data?.user?.restId) {
                                console.log(`⚠️ 用户 @${screenName} 无法获取有效ID，跳过`);
                                continue;
                            }
                            
                            const user = response.data.user;
                            // 简化用户数据结构并添加到最终列表
                            finalUsers.push({
                                restId: user.restId,
                                legacy: {
                                    name: get(user, 'legacy.name', ''),
                                    screenName: get(user, 'legacy.screenName', ''),
                                    createdAt: get(user, 'legacy.createdAt', ''),
                                    description: get(user, 'legacy.description', ''),
                                    entities: get(user, 'legacy.entities', {}),
                                    profileBannerUrl: get(user, 'legacy.profileBannerUrl', ''),
                                    profileImageUrlHttps: get(user, 'legacy.profileImageUrlHttps', '')
                                }
                            });
                            
                            console.log(`✅ 已添加用户: @${screenName}`);
                            
                            // 确保用户缓存信息保存
                            try {
                                const cacheDir = path.join('../resp/cache');
                                try {
                                    if (!fs.existsSync(cacheDir)) {
                                        fs.mkdirSync(cacheDir, { recursive: true });
                                    }
                                } catch (mkdirError: any) {
                                    console.error(`⚠️ 创建缓存目录失败: ${mkdirError.message}`);
                                }
                                
                                const cacheFile = path.join(cacheDir, `${screenName}.json`);
                                const cacheData = {
                                    screenName: screenName,
                                    userId: user.restId
                                };
                                await fs.writeJSON(cacheFile, cacheData, {spaces: 2});
                                console.log(`✅ 用户ID缓存已更新: ${cacheFile}`);
                            } catch (cacheError: any) {
                                console.error(`⚠️ 缓存保存失败: ${cacheError.message}`);
                            }
                            
                        } catch (userError: any) {
                            console.error(`❌ 获取用户 @${screenName} 信息失败: ${userError.message}`);
                        }
                        
                        // 添加间隔，避免API限制
                        if (screenNames.indexOf(screenName) < screenNames.length - 1) {
                            console.log(`⏸️ 等待 2 秒...`);
                            await new Promise(r => setTimeout(r, 2000));
                        }
                    }
                } else {
                    console.log("⚠️ 配置文件中的用户列表为空或格式无效");
                }
            } else {
                console.log(`⚠️ 配置文件不存在: ${configPath}`);
            }
        } catch (configError: any) {
            console.error(`❌ 配置文件读取失败: ${configError.message}`);
        }
        
        // 如果环境变量中有设置，添加到列表
        if (envScreenName && envScreenName.trim()) {
            try {
                console.log(`\n=== 处理环境变量用户: @${envScreenName} ===`);
                
                const response = await client.getUserApi().getUserByScreenName({screenName: envScreenName});
                if (response.data?.user?.restId) {
                    const user = response.data.user;
                    
                    // 检查是否已存在
                    const existingIndex = finalUsers.findIndex(u => u.restId === user.restId);
                    if (existingIndex >= 0) {
                        console.log(`ℹ️ 用户 @${envScreenName} 已在列表中`);
                    } else {
                        finalUsers.push({
                            restId: user.restId,
                            legacy: {
                                name: get(user, 'legacy.name', ''),
                                screenName: get(user, 'legacy.screenName', ''),
                                createdAt: get(user, 'legacy.createdAt', ''),
                                description: get(user, 'legacy.description', ''),
                                entities: get(user, 'legacy.entities', {}),
                                profileBannerUrl: get(user, 'legacy.profileBannerUrl', ''),
                                profileImageUrlHttps: get(user, 'legacy.profileImageUrlHttps', '')
                            }
                        });
                        console.log(`✅ 已添加环境变量用户: @${envScreenName}`);
                    }
                    
                    // 缓存用户信息
                    try {
                        const cacheDir = path.join('../resp/cache');
                        try {
                            if (!fs.existsSync(cacheDir)) {
                                fs.mkdirSync(cacheDir, { recursive: true });
                            }
                        } catch (mkdirError: any) {
                            console.error(`⚠️ 创建缓存目录失败: ${mkdirError.message}`);
                        }
                        
                        const cacheFile = path.join(cacheDir, `${envScreenName}.json`);
                        const cacheData = {
                            screenName: envScreenName,
                            userId: user.restId
                        };
                        await fs.writeJSON(cacheFile, cacheData, {spaces: 2});
                        console.log(`✅ 用户ID缓存已更新: ${cacheFile}`);
                    } catch (cacheError: any) {
                        console.error(`⚠️ 缓存保存失败: ${cacheError.message}`);
                    }
                } else {
                    console.log(`⚠️ 环境变量用户 @${envScreenName} 无法获取有效ID`);
                }
            } catch (envError: any) {
                console.error(`❌ 获取环境变量用户 @${envScreenName} 信息失败: ${envError.message}`);
            }
        }
        
        // 如果有获取到用户数据，保存
        if (finalUsers.length > 0) {
            console.log(`\n🔍 共获取 ${finalUsers.length} 个用户`);
            
            // 按 screenName 排序
            finalUsers.sort((a, b) => 
                a.legacy.screenName.localeCompare(b.legacy.screenName)
            );
            
            // 输出路径
            const outputPath = `../data/followingUser.json`;
            try {
                const dataDir = path.dirname(outputPath);
                if (!fs.existsSync(dataDir)) {
                    fs.mkdirSync(dataDir, { recursive: true });
                }
                await fs.writeJSON(outputPath, finalUsers, {spaces: 2});
                console.log(`✅ 用户列表已保存: ${outputPath}`);
            } catch (saveError: any) {
                console.error(`❌ 保存用户列表失败: ${saveError.message}`);
            }
        } else {
            console.log(`⚠️ 未获取到任何用户数据`);
        }

    } catch (error: any) {
        console.error('处理失败:', error.message);
        console.log(`⚠️ 继续执行其他流程`);
    }
    console.log(`----- ----- ----- ----- fetch-following end ----- ----- ----- -----`);
}

export async function main() {
    try {
        await processHomeTimeline();
    } catch (error: any) {
        console.error('❌ 全局异常:', error.message);
        process.exitCode = 1;
    } finally {
        await cleanupLogger();
        process.exit(process.exitCode || 0);
    }
}

// 启动执行
main();

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动跑步步数提交脚本
功能：自动为多个账号提交跑步步数，支持GitHub Actions定时执行
作者：gaocaipeng
仓库：https://github.com/gaocaipeng/xiaomi-auto-zeep
"""

import requests  # 用于发送网络请求
import random    # 用于生成随机步数
import time      # 用于延时等待
import json      # 用于解析JSON响应
import logging   # 用于记录日志
from datetime import datetime  # 用于获取当前时间
import os        # 用于读取环境变量
 
# 配置日志系统，记录脚本运行过程
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
 
# ==================== 账号配置部分 ====================
def get_accounts_from_env():
    """
    从环境变量获取账号配置
    这个函数会从GitHub Secrets中读取账号信息，确保账号安全
    支持最多5个账号同时运行
    """
    accounts = []
    
    # 循环检查环境变量中的账号配置（最多支持5个账号）
    for i in range(1, 6):
        username = os.getenv(f'ACCOUNT{i}_USERNAME')  # 获取用户名
        password = os.getenv(f'ACCOUNT{i}_PASSWORD')  # 获取密码
        
        # 如果用户名和密码都存在，就添加到账号列表
        if username and password:
            accounts.append({"username": username, "password": password})
            logger.info(f"✅ 成功加载账号 {i}: {username}")
    
    # 如果没有找到任何账号配置，给出提示
    if not accounts:
        logger.warning("⚠️  未找到任何账号配置，请检查GitHub Secrets设置")
    
    return accounts

# 获取所有配置的账号
ACCOUNTS = get_accounts_from_env()
 
# ==================== 步数生成规则 ====================
# 根据不同的时间段，生成不同范围的步数，让数据更真实
STEP_RANGES = {
    8: {"min": 6000, "max": 10000},   # 早上8点：6000-10000步
    12: {"min": 8000, "max": 14000},  # 中午12点：8000-14000步
    16: {"min": 10000, "max": 18000}, # 下午4点：10000-18000步
    20: {"min": 12000, "max": 22000}, # 晚上8点：12000-22000步
    22: {"min": 15000, "max": 24000}  # 晚上10点：15000-24000步
}
 
# 默认步数（当不在上述时间段时使用）
DEFAULT_STEPS = 24465
 
# ==================== 主要功能类 ====================
class StepSubmitter:
    """
    步数提交器
    负责处理所有与步数提交相关的操作
    """
def __init__(self):
    # 创建网络请求会话
    self.session = requests.Session()

    # 从GitHub Secrets读取接口Token
    self.token = os.getenv('CXZJA_TOKEN')

    if not self.token:
        logger.warning("⚠️ 未找到CXZJA_TOKEN，请检查GitHub Secrets")

    # 新接口请求头
    self.headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Bearer {self.token}'
    }

    # Zepp Life新接口
    self.base_url = 'https://api.cxzja.cn/api/mZeppLife'
         
    def get_current_steps(self, account_index=0):
        """
        根据当前时间智能生成步数
        让生成的步数更符合真实情况
        每个账号的步数都会有所不同
        """
        current_hour = datetime.now().hour
        logger.info(f"🕐 当前时间: {datetime.now()}, 小时: {current_hour}")
         
        # 寻找最接近的配置时间段
        closest_hour = None
        min_diff = float('inf')
         
        # 遍历所有配置的时间点，找到最接近当前时间的
        for hour in STEP_RANGES.keys():
            diff = abs(current_hour - hour)
            if diff < min_diff:
                min_diff = diff
                closest_hour = hour
         
        # 如果找到接近的配置且在合理范围内（2小时内），使用该配置
        if min_diff <= 2 and closest_hour in STEP_RANGES:
            step_config = STEP_RANGES[closest_hour]
            # 为每个账号添加不同的随机偏移，让步数更真实
            base_steps = random.randint(step_config['min'], step_config['max'])
            # 根据账号索引添加不同的偏移量（-500到+500步）
            offset = random.randint(-500, 500)
            steps = max(1000, base_steps + offset)  # 确保步数不少于1000
            logger.info(f"✅ 使用 {closest_hour} 点配置，账号{account_index+1}生成步数: {steps}")
        else:
            # 默认步数也添加账号差异
            base_steps = DEFAULT_STEPS
            offset = random.randint(-1000, 1000)  # 默认步数的偏移范围更大
            steps = max(1000, base_steps + offset)
            logger.info(f"✅ 使用默认步数，账号{account_index+1}生成步数: {steps}")
         
        return steps
     
    def validate_credentials(self, username, password):
        """
        验证账号密码格式
        确保账号和密码符合基本要求
        """
        import re
         
        # 手机号格式验证（中国大陆手机号）
        phone_pattern = r'^1[3-9]\d{9}$'
        # 邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
         
        # 检查账号和密码是否为空
        if not username or not password:
            return False, "❌ 账号或密码不能为空"
         
        # 检查密码是否包含空格
        if ' ' in password:
            return False, "❌ 密码不能包含空格"
         
        # 验证账号格式（手机号或邮箱）
        if re.match(phone_pattern, username) or re.match(email_pattern, username):
            return True, "✅ 账号格式验证通过"
        else:
            return False, "❌ 账号格式错误（需要是手机号或邮箱）"
     
    def submit_steps(self, username, password, steps):
        """
        提交步数到服务器
        这是核心功能，负责将步数数据发送到目标服务器
        """
        try:
            # 第一步：验证账号密码格式
            is_valid, message = self.validate_credentials(username, password)
            if not is_valid:
                return False, f"❌ 验证失败: {message}"
             
            # 第二步：准备要发送的数据
            data = {
                'user': username,    # 账号（手机号或邮箱）
                'pass': password,      # 密码
                'steps': str(steps)         # 步数
            }
             
            logger.info(f"🚀 准备提交 - 账号: {username}, 步数: {steps}")
             
            # 第三步：发送网络请求
            response = self.session.post(
                self.base_url,
                data=data,
                headers=self.headers,
                timeout=30  # 30秒超时
            )
             
            # 第四步：处理服务器响应
if response.status_code == 200:
    result = response.json()
    logger.info(f"接口返回: {result}")
                if result.get('code') == 200:
                    return True, f"✅ 提交成功! 步数: {steps}"
                else:
                    error_msg = result.get('data', '未知错误')
                    # 处理频繁提交的情况
                    if '频繁' in error_msg:
                        return False, "⏰ 提交过于频繁，请稍后再试"
                    else:
                        return False, f"❌ 提交失败: {error_msg}"
            else:
                return False, f"❌ 网络错误: {response.status_code}"
                 
        except requests.exceptions.RequestException as e:
            return False, f"❌ 网络请求错误: {str(e)}"
        except json.JSONDecodeError:
            return False, "❌ 服务器响应格式错误"
        except Exception as e:
            return False, f"❌ 未知错误: {str(e)}"
     
    def run(self):
        """
        主执行函数
        这是脚本的核心入口，负责处理所有账号的步数提交
        """
        logger.info("🎯 开始执行步数提交任务")
        
        # 检查是否有账号配置
        if not ACCOUNTS:
            logger.error("❌ 没有找到任何账号配置，请检查GitHub Secrets设置")
            return 0, 0
            
        logger.info(f"📊 共有 {len(ACCOUNTS)} 个账号需要处理")
         
        success_count = 0  # 成功提交的账号数量
        fail_count = 0     # 提交失败的账号数量
         
        # 逐个处理每个账号
        for i, account in enumerate(ACCOUNTS, 1):
            logger.info(f"🔄 处理第 {i}/{len(ACCOUNTS)} 个账号: {account['username']}")
             
            try:
                # 获取当前应提交的步数（传入账号索引，让每个账号步数不同）
                steps = self.get_current_steps(i - 1)
                 
                # 提交步数到服务器
                success, message = self.submit_steps(
                    account['username'], 
                    account['password'], 
                    steps
                )
                 
                if success:
                    success_count += 1
                    logger.info(f"✅ 账号 {account['username']} - {message}")
                else:
                    fail_count += 1
                    logger.error(f"❌ 账号 {account['username']} - {message}")
                 
            except Exception as e:
                fail_count += 1
                logger.error(f"❌ 账号 {account['username']} - 处理异常: {str(e)}")
             
            # 账号间间隔（避免请求过于频繁）
            if i < len(ACCOUNTS):
                logger.info("⏳ 等待5秒后处理下一个账号...")
                time.sleep(5)
         
        # 输出最终结果
        logger.info(f"🏁 任务完成! 成功: {success_count}, 失败: {fail_count}")
         
        return success_count, fail_count
 
# ==================== 程序入口 ====================
def main():
    """
    主函数
    这是程序的入口点，负责启动整个步数提交流程
    """
    try:
        # 创建步数提交器实例
        submitter = StepSubmitter()
        
        # 执行步数提交任务
        success_count, fail_count = submitter.run()
         
        # 根据执行结果返回相应的退出码
        if fail_count == 0:
            print("🎉 所有账号提交成功!")
            exit(0)  # 成功退出
        else:
            print(f"⚠️  部分账号提交失败，成功: {success_count}, 失败: {fail_count}")
            exit(1)  # 失败退出
             
    except Exception as e:
        logger.error(f"💥 脚本执行异常: {str(e)}")
        exit(1)  # 异常退出
 
# 程序启动点
if __name__ == "__main__":
    main()

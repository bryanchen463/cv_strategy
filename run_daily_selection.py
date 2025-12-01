#!/usr/bin/env python3
"""
每日自动选股脚本 - 专为cron job设计
"""

import os
import sys
import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """运行每日选股并保存结果"""
    print(f"=== 开始每日选股 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")

    try:
        # 导入选股模块
        from run_daily import main as run_daily_selection

        # 运行选股策略（返回数据模式）
        result = run_daily_selection(return_data=True)

        if result is None:
            print("选股返回空结果")
            return False

        print(f"选股完成！共选中 {len(result['stocks'])} 只股票")
        print(f"板块分布: {result['stats']['by_sector']}")

        # 保存到缓存文件
        import json
        cache_file = 'cache/selected_stocks_cache.json'

        # 确保缓存目录存在
        if not os.path.exists('cache'):
            os.makedirs('cache')

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"结果已保存到: {cache_file}")
        print(f"=== 每日选股完成 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
        return True

    except Exception as e:
        print(f"选股过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
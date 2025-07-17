#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富API调用模块
用于获取股票实时数据
"""

import requests
import json
import time
import re


class EastMoneyAPI:
    """东方财富API调用类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 字段映射说明
        self.field_mapping = {
            'f2': '最新价',
            'f3': '涨跌幅',
            'f4': '涨跌额',
            'f5': '成交量',
            'f6': '成交额',
            'f7': '振幅',
            'f8': '换手率',
            'f9': '市盈率',
            'f10': '量比',  # 量比是衡量相对成交量的指标。它是指股市开市后平均每分钟的成交量与过去5个交易日平均每分钟成交量之比。其计算公式为：量比=（现成交总手数 / 现累计开市时间(分) ）/ 过去5日平均每分钟成交量
            'f11': '五分钟涨跌',
            'f12': '股票代码',
            'f14': '股票名称',
            'f15': '最高',
            'f16': '最低',
            'f17': '今开',
            'f18': '昨收',
            'f20': '总市值',
            'f21': '流通市值',
            'f22': '涨速',  # 最近5分钟涨速
            'f23': '市净率',
            'f24': '60日涨跌幅',
            'f25': '年初至今涨跌幅'
        }
    
    def get_all_stocks(self) -> list:
        """
        获取所有A股数据（分页获取）
        
        Returns:
            list: 股票数据列表
        """
        url = 'https://99.push2.eastmoney.com/api/qt/clist/get'
        
        try:
            print("📡 开始分页获取所有A股数据...")
            print("=" * 60)
            
            all_stocks = []
            page = 1
            total_count = 0
            
            while True:
                params = {
                    'pn': str(page),
                    'pz': '100',
                    'po': '1',
                    'np': '1',
                    'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                    'fltt': '2',
                    'invt': '2',
                    'fid': 'f3',
                    'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
                    'fields': 'f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11'
                }
                
                print(f"📄 正在获取第 {page} 页...")
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # 尝试直接解析JSON
                try:
                    data = response.json()
                    
                    if 'data' in data and data['data'] and 'diff' in data['data']:
                        diff = data['data']['diff']
                        current_count = len(diff)
                        total_count += current_count
                        
                        print(f"✅ 第 {page} 页获取到 {current_count} 只股票")
                        
                        if current_count == 0:
                            print("📄 已到达最后一页")
                            break
                        
                        # 转换数据格式
                        for item in diff:
                            stock_info = {}
                            for field, description in self.field_mapping.items():
                                if field in item:
                                    stock_info[description] = item[field]
                            all_stocks.append(stock_info)
                        
                        # 如果返回的数据少于100，说明已经到最后一页
                        if current_count < 100:
                            print("📄 已到达最后一页")
                            break
                            
                    else:
                        print(f"❌ 第 {page} 页响应中没有找到股票数据")
                        break
                        
                except json.JSONDecodeError:
                    print("⚠️  直接JSON解析失败，尝试JSONP解析")
                    
                    # 解析返回的JSONP数据
                    jsdata = re.findall(r'\(.*?\)', response.text)
                    if jsdata:
                        dicts = json.loads(jsdata[0][1:len(jsdata[0])-1])
                        
                        if 'data' in dicts and dicts['data'] and 'diff' in dicts['data']:
                            diff = dicts['data']['diff']
                            current_count = len(diff)
                            total_count += current_count
                            
                            print(f"✅ 第 {page} 页获取到 {current_count} 只股票")
                            
                            if current_count == 0:
                                print("📄 已到达最后一页")
                                break
                            
                            # 转换数据格式
                            for item in diff:
                                stock_info = {}
                                for field, description in self.field_mapping.items():
                                    if field in item:
                                        stock_info[description] = item[field]
                                all_stocks.append(stock_info)
                            
                            # 如果返回的数据少于100，说明已经到最后一页
                            if current_count < 100:
                                print("📄 已到达最后一页")
                                break
                        else:
                            print(f"❌ 第 {page} 页JSONP响应中没有找到股票数据")
                            break
                    else:
                        print(f"❌ 第 {page} 页未找到JSONP格式数据")
                        break
                
                page += 1
                
                # 添加延迟避免请求过快
                time.sleep(0.1)
            
            print(f"✅ 分页获取完成，共获取 {len(all_stocks)} 只股票数据")
            print("=" * 60)
            
            return all_stocks
                
        except Exception as e:
            print(f"请求失败: {e}")
            return []


def test_api():
    """测试API调用"""
    api = EastMoneyAPI()
    
    print("=== 东方财富API测试 ===")
    print("获取所有A股数据...")
    print("=" * 60)
    
    start_time = time.perf_counter()
    
    # 获取所有股票数据
    all_stocks = api.get_all_stocks()
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    if all_stocks:
        print(f"✅ 成功获取 {len(all_stocks)} 只股票数据")
        print(f"⏱️  耗时: {duration:.2f}秒")
        print("=" * 60)
        
        # 按股票代码排序，显示前三位
        sorted_stocks = sorted(all_stocks, key=lambda x: x.get('股票代码', ''))
        
        print("📊 按股票代码排序的前三位:")
        print("-" * 60)
        
        for i, stock in enumerate(sorted_stocks[:3], 1):
            print(f"\n第{i}位: {stock.get('股票代码', 'N/A')} {stock.get('股票名称', 'N/A')}")
            print("-" * 40)
            
            # 显示关键字段
            key_fields = ['最新价', '涨跌幅', '涨跌额', '成交量', '成交额', '振幅', 
                         '换手率', '市盈率', '量比', '最高', '最低', '今开', '昨收',
                         '总市值', '流通市值', '涨速', '市净率', '60日涨跌幅', '年初至今涨跌幅']
            
            for field in key_fields:
                if field in stock:
                    value = stock[field]
                    if field in ['涨跌幅', '涨跌额', '振幅', '换手率', '市盈率', '量比', '市净率', '60日涨跌幅', '年初至今涨跌幅']:
                        print(f"  {field}: {value}")
                    else:
                        print(f"  {field}: {value}")
        
        # 统计A股分布
        codes = [stock.get('股票代码', '') for stock in all_stocks if stock.get('股票代码')]
        if codes:
            print(f"\n📊 A股分布统计:")
            print("=" * 40)
            sh_main = [code for code in codes if code.startswith('60')]
            sh_star = [code for code in codes if code.startswith('68')]
            sz_main = [code for code in codes if code.startswith('00')]
            sz_gem = [code for code in codes if code.startswith('30')]
            print(f"  沪市主板(60开头): {len(sh_main)} 只")
            print(f"  科创板(68开头): {len(sh_star)} 只")
            print(f"  深市主板(00开头): {len(sz_main)} 只")
            print(f"  创业板(30开头): {len(sz_gem)} 只")
            print(f"  总计: {len(all_stocks)} 只")
            
            # 显示代码范围
            print(f"\n📊 股票代码范围:")
            print(f"  最小代码: {min(codes)}")
            print(f"  最大代码: {max(codes)}")
        
        # 统计涨跌情况
        up_count = 0
        down_count = 0
        flat_count = 0
        
        for stock in all_stocks:
            if '涨跌幅' in stock and stock['涨跌幅'] != '-':
                change_rate = stock['涨跌幅']
                if change_rate > 0:
                    up_count += 1
                elif change_rate < 0:
                    down_count += 1
                else:
                    flat_count += 1
        
        print(f"\n📈 市场涨跌统计:")
        print("=" * 40)
        print(f"  上涨股票: {up_count} 只")
        print(f"  下跌股票: {down_count} 只") 
        print(f"  平盘股票: {flat_count} 只")
        
    else:
        print("❌ 获取股票数据失败")


if __name__ == "__main__":
    test_api() 
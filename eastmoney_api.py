#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富API调用模块
用于获取股票实时数据
"""

import requests
import json
from typing import Dict, Optional, List
import time
import re # Added for JSONP parsing


class EastMoneyAPI:
    """东方财富API调用类"""
    
    def __init__(self):
        self.base_url = "http://push2.eastmoney.com/api/qt/stock/get"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_stock_data(self, secid: str, fields: Optional[List[str]] = None) -> Dict:
        """
        获取股票数据
        
        Args:
            secid: 股票代码，格式为 "市场.代码"，如 "1.000001" (深市) 或 "0.600000" (沪市)
            fields: 需要获取的字段列表，如果为None则使用默认字段
            
        Returns:
            Dict: 股票数据字典
        """
        if fields is None:
            # 默认字段：最新价、最高价、最低价、今开、成交量、股票代码、股票名称、涨跌幅、涨跌额
            fields = ['f43', 'f44', 'f45', 'f46', 'f47', 'f57', 'f58', 'f169', 'f170']
        
        # 构建请求参数
        params = {
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'invt': '2',
            'fltt': '2',
            'fields': ','.join(fields),
            'secid': secid
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return {}
    
    def get_stock_info(self, secid: str) -> Dict:
        """
        获取股票详细信息，包含字段说明
        
        Args:
            secid: 股票代码
            
        Returns:
            Dict: 包含字段说明的股票信息
        """
        # 字段映射说明
        field_mapping = {
            'f43': '最新价',
            'f44': '最高价',
            'f45': '最低价',
            'f46': '今开',
            'f47': '成交量(手)',
            'f57': '股票代码',
            'f58': '股票名称',
            'f135': '1分钟涨速',
            'f136': '3分钟涨速',
            'f168': '换手率(%)',
            'f169': '涨跌额',
            'f170': '涨跌幅(%)',
            'f104': '总股本',
            'f105': '流通股本'
        }
        
        # 获取所有字段的数据
        all_fields = list(field_mapping.keys())
        data = self.get_stock_data(secid, all_fields)
        
        if not data or 'data' not in data or data['data'] is None:
            return {}
        
        stock_data = data['data']
        result = {}
        
        # 添加字段说明
        for field, description in field_mapping.items():
            if field in stock_data:
                result[description] = stock_data[field]
        
        return result
    
    def get_stock_list_data(self, secid_list: List[str], fields: Optional[List[str]] = None) -> List[Dict]:
        """
        批量获取股票数据（通过逐个请求实现）
        
        Args:
            secid_list: 股票代码列表，格式为 ["市场.代码", ...]
            fields: 需要获取的字段列表，如果为None则使用默认字段
            
        Returns:
            List[Dict]: 股票数据列表
        """
        result = []
        
        for secid in secid_list:
            try:
                stock_info = self.get_stock_info(secid)
                if stock_info:
                    result.append(stock_info)
                else:
                    print(f"获取股票 {secid} 数据失败")
                
                # 添加延迟避免请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                print(f"获取股票 {secid} 数据时出错: {e}")
                continue
        
        return result
    
    def get_stock_list_data_v2(self, secid_list: List[str], fields: Optional[List[str]] = None) -> List[Dict]:
        """
        尝试使用ulist接口批量获取股票数据
        
        Args:
            secid_list: 股票代码列表，格式为 ["市场.代码", ...]
            fields: 需要获取的字段列表，如果为None则使用默认字段
            
        Returns:
            List[Dict]: 股票数据列表
        """
        if fields is None:
            # ulist接口可能使用不同的字段标识
            fields = ['f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f12', 'f14', 'f15', 'f16', 'f17', 'f18']
        
        # ulist接口的字段映射说明
        field_mapping = {
            'f2': '最新价',
            'f3': '涨跌幅',
            'f4': '涨跌额',
            'f5': '成交量',
            'f6': '成交额',
            'f7': '振幅',
            'f8': '换手率',
            'f9': '市盈率',
            'f10': '量比',
            'f12': '股票代码',
            'f14': '股票名称',
            'f15': '最高价',
            'f16': '最低价',
            'f17': '今开',
            'f18': '昨收'
        }
        
        # 构建请求参数 - 尝试不同的参数组合
        params = {
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'invt': '2',
            'fltt': '2',
            'fields': ','.join(fields),
            'secids': ','.join(secid_list),
            'pn': '1',  # 页码
            'pz': '50',  # 每页数量
            'po': '1',   # 排序
            'np': '1',   # 新股
            'fid': 'f43'  # 排序字段
        }
        
        try:
            response = requests.get(
                "http://push2.eastmoney.com/api/qt/ulist/get",
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            print(f"ulist接口响应: {data}")
            
            if not data or 'data' not in data or data['data'] is None or 'diff' not in data['data']:
                print("ulist接口数据格式不正确，回退到逐个请求")
                return self.get_stock_list_data(secid_list, fields)
            
            result = []
            for i, item in enumerate(data['data']['diff']):
                print(f"\n原始数据项 {i+1}: {item}")
                stock_info = {}
                for field, description in field_mapping.items():
                    if field in item:
                        stock_info[description] = item[field]
                result.append(stock_info)
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"ulist接口请求失败: {e}")
            return self.get_stock_list_data(secid_list, fields)
        except json.JSONDecodeError as e:
            print(f"ulist接口JSON解析失败: {e}")
            return self.get_stock_list_data(secid_list, fields)
    
    def get_market_statistics(self) -> Dict:
        """
        获取市场整体统计数据
        
        Returns:
            Dict: 包含涨跌幅均值、上涨率、下跌率等市场统计数据
        """
        # 构建请求参数
        params = {
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'invt': '2',
            'fltt': '2',
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152',
            'pn': '1',
            'pz': '10000',  # 获取更多股票数据，确保覆盖所有A股
            'po': '1',
            'np': '1',
            'fid': 'f3',  # 按涨跌幅排序
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048'  # A股市场
        }
        
        try:
            response = requests.get(
                "http://push2.eastmoney.com/api/qt/clist/get",
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'data' not in data or data['data'] is None or 'diff' not in data['data']:
                print("获取市场统计数据失败")
                return {}
            
            # 获取总数据量
            total_count = data['data'].get('total', 0)
            print(f"API返回的总股票数: {total_count}")
            
            stock_list = data['data']['diff']
            current_page_count = len(stock_list)
            
            # 如果数据量不够，需要分页获取
            if total_count > current_page_count:
                print(f"需要分页获取，当前页: {current_page_count}，总数: {total_count}")
                
                # 计算需要多少页
                pages_needed = (total_count + 9999) // 10000  # 向上取整
                print(f"需要获取 {pages_needed} 页数据")
                
                # 获取剩余页面的数据
                for page in range(2, pages_needed + 1):
                    params['pn'] = str(page)
                    try:
                        response = requests.get(
                            "http://push2.eastmoney.com/api/qt/clist/get",
                            params=params,
                            headers=self.headers,
                            timeout=10
                        )
                        response.raise_for_status()
                        page_data = response.json()
                        
                        if page_data and 'data' in page_data and page_data['data'] and 'diff' in page_data['data']:
                            stock_list.extend(page_data['data']['diff'])
                            print(f"第 {page} 页获取到 {len(page_data['data']['diff'])} 只股票")
                        
                        time.sleep(0.1)  # 避免请求过快
                        
                    except Exception as e:
                        print(f"获取第 {page} 页数据失败: {e}")
                        continue
            
            total_stocks = len(stock_list)
            
            print(f"实际获取到 {total_stocks} 只股票数据")
            
            if total_stocks == 0:
                return {}
            
            # 统计涨跌情况
            up_count = 0      # 上涨股票数
            down_count = 0    # 下跌股票数
            flat_count = 0    # 平盘股票数
            total_change = 0  # 总涨跌幅
            
            for stock in stock_list:
                if 'f3' in stock and stock['f3'] != '-':  # f3是涨跌幅
                    change_rate = stock['f3']
                    total_change += change_rate
                    
                    if change_rate > 0:
                        up_count += 1
                    elif change_rate < 0:
                        down_count += 1
                    else:
                        flat_count += 1
            
            # 计算统计数据
            avg_change_rate = round(total_change / total_stocks, 2) if total_stocks > 0 else 0
            up_rate = round(up_count / total_stocks * 100, 2) if total_stocks > 0 else 0
            down_rate = round(down_count / total_stocks * 100, 2) if total_stocks > 0 else 0
            flat_rate = round(flat_count / total_stocks * 100, 2) if total_stocks > 0 else 0
            
            result = {
                '总股票数': total_stocks,
                '上涨股票数': up_count,
                '下跌股票数': down_count,
                '平盘股票数': flat_count,
                '平均涨跌幅(%)': avg_change_rate,
                '上涨率(%)': up_rate,
                '下跌率(%)': down_rate,
                '平盘率(%)': flat_rate,
                '上涨率': f"{up_rate}%",
                '下跌率': f"{down_rate}%",
                '平盘率': f"{flat_rate}%"
            }
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"获取市场统计数据失败: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"解析市场统计数据失败: {e}")
            return {}

    def get_stock_list_data_v3(self, page_size: int = 20, max_pages: int = 236) -> List[Dict]:
        """
        使用clist接口批量获取股票数据（参考用户提供的代码）
        
        Args:
            page_size: 每页获取的股票数量，默认20
            max_pages: 最大页数，默认236页
            
        Returns:
            List[Dict]: 股票数据列表
        """
        # 字段映射说明
        field_mapping = {
            'f12': '股票代码',
            'f14': '股票名称', 
            'f15': '最新价',
            'f3': '涨跌幅(%)',
            'f4': '涨跌额',
            'f5': '成交量(手)',
            'f6': '成交额',
            'f7': '振幅',
            'f8': '换手率(%)',
            'f9': '市盈率(动态)',
            'f10': '量比',
            'f16': '最高价',
            'f17': '最低价',
            'f18': '今开',
            'f23': '市净率'
        }
        
        all_stocks = []
        start_time = time.perf_counter()
        
        print(f"开始批量获取股票数据，每页{page_size}只，最多{max_pages}页...")
        print("=" * 60)
        
        for page in range(max_pages):
            # 构建请求URL
            url = f'http://81.push2.eastmoney.com/api/qt/clist/get'
            params = {
                'cb': f'jQuery{int(time.time()*1000)}',
                'pn': str(page + 1),  # 页码从1开始
                'pz': str(page_size),
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # A股市场
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
                '_': str(int(time.time()*1000))
            }
            
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # 解析返回的JSONP数据
                jsdata = re.findall(r'\(.*?\)', response.text)
                if jsdata:
                    dicts = json.loads(jsdata[0][1:len(jsdata[0])-1])
                    diff = dicts.get('data', {}).get('diff', [])
                    
                    if diff:
                        # 转换数据格式
                        for item in diff:
                            stock_info = {}
                            for field, description in field_mapping.items():
                                if field in item:
                                    stock_info[description] = item[field]
                            all_stocks.append(stock_info)
                        
                        # 显示进度
                        progress = (page + 1) / max_pages * 100
                        duration = time.perf_counter() - start_time
                        print(f"\r进度: {progress:^3.0f}% [{page+1}/{max_pages}] 已获取{len(all_stocks)}只股票 耗时{duration:.2f}s", end="")
                        
                        # 如果返回的数据少于page_size，说明已经到最后一页
                        if len(diff) < page_size:
                            print(f"\n已到达最后一页，共获取{len(all_stocks)}只股票")
                            break
                    else:
                        print(f"\n第{page+1}页无数据，停止获取")
                        break
                else:
                    print(f"\n第{page+1}页数据解析失败")
                    break
                    
            except Exception as e:
                print(f"\n第{page+1}页请求失败: {e}")
                break
            
            # 添加延迟避免请求过快
            time.sleep(0.1)
        
        print(f"\n批量获取完成，共获取{len(all_stocks)}只股票数据")
        print("=" * 60)
        
        return all_stocks

    def get_stock_list_data_v4(self, page_size: int = 20, max_pages: int = 236, 
                              market_filter: str = None, sort_field: str = 'f3', 
                              sort_order: int = 1) -> List[Dict]:
        """
        使用clist接口批量获取股票数据（支持自定义筛选条件）
        
        Args:
            page_size: 每页获取的股票数量，默认20
            max_pages: 最大页数，默认236页
            market_filter: 市场筛选条件，默认获取所有A股
                - 'm:0+t:6' - 深市主板
                - 'm:0+t:80' - 深市创业板  
                - 'm:1+t:2' - 沪市主板
                - 'm:1+t:23' - 沪市科创板
                - 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23' - 所有A股
            sort_field: 排序字段，默认'f3'(涨跌幅)
                - 'f2' - 最新价
                - 'f3' - 涨跌幅
                - 'f5' - 成交量
                - 'f6' - 成交额
                - 'f8' - 换手率
            sort_order: 排序方向，1=降序，0=升序
            
        Returns:
            List[Dict]: 股票数据列表
        """
        # 字段映射说明
        field_mapping = {
            'f12': '股票代码',
            'f14': '股票名称', 
            'f15': '最新价',
            'f3': '涨跌幅(%)',
            'f4': '涨跌额',
            'f5': '成交量(手)',
            'f6': '成交额',
            'f7': '振幅',
            'f8': '换手率(%)',
            'f9': '市盈率(动态)',
            'f10': '量比',
            'f16': '最高价',
            'f17': '最低价',
            'f18': '今开',
            'f23': '市净率'
        }
        
        # 默认市场筛选条件
        if market_filter is None:
            market_filter = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'  # 所有A股
        
        all_stocks = []
        start_time = time.perf_counter()
        
        print(f"开始批量获取股票数据，每页{page_size}只，最多{max_pages}页...")
        print(f"市场筛选: {market_filter}")
        print(f"排序字段: {sort_field} ({'降序' if sort_order == 1 else '升序'})")
        if max_pages == 1:
            print("🚀 单次请求模式，将一次性获取所有数据")
        else:
            print("📄 分页请求模式，将分多次获取数据")
        print("=" * 60)
        
        for page in range(max_pages):
            # 构建请求URL
            url = f'http://81.push2.eastmoney.com/api/qt/clist/get'
            params = {
                'cb': f'jQuery{int(time.time()*1000)}',
                'pn': str(page + 1),  # 页码从1开始
                'pz': str(page_size),
                'po': str(sort_order),
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': sort_field,
                'fs': market_filter,
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
                '_': str(int(time.time()*1000))
            }
            
            try:
                response = requests.get(url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                
                # 解析返回的JSONP数据
                jsdata = re.findall(r'\(.*?\)', response.text)
                if jsdata:
                    dicts = json.loads(jsdata[0][1:len(jsdata[0])-1])
                    diff = dicts.get('data', {}).get('diff', [])
                    
                    if diff:
                        # 转换数据格式
                        for item in diff:
                            stock_info = {}
                            for field, description in field_mapping.items():
                                if field in item:
                                    stock_info[description] = item[field]
                            all_stocks.append(stock_info)
                        
                        # 显示进度
                        progress = (page + 1) / max_pages * 100
                        duration = time.perf_counter() - start_time
                        print(f"\r进度: {progress:^3.0f}% [{page+1}/{max_pages}] 已获取{len(all_stocks)}只股票 耗时{duration:.2f}s", end="")
                        
                        # 如果返回的数据少于page_size，说明已经到最后一页
                        if len(diff) < page_size:
                            print(f"\n已到达最后一页，共获取{len(all_stocks)}只股票")
                            break
                    else:
                        print(f"\n第{page+1}页无数据，停止获取")
                        break
                else:
                    print(f"\n第{page+1}页数据解析失败")
                    break
                    
            except Exception as e:
                print(f"\n第{page+1}页请求失败: {e}")
                break
            
            # 添加延迟避免请求过快
            time.sleep(0.1)
        
        print(f"\n批量获取完成，共获取{len(all_stocks)}只股票数据")
        print("=" * 60)
        
        return all_stocks

    def get_all_stocks_fast(self, market_filter: str = None, sort_field: str = 'f3', 
                           sort_order: int = 1) -> List[Dict]:
        """
        快速获取所有股票数据（单次请求）
        
        Args:
            market_filter: 市场筛选条件，默认获取所有A股
            sort_field: 排序字段，默认'f3'(涨跌幅)
            sort_order: 排序方向，1=降序，0=升序
            
        Returns:
            List[Dict]: 股票数据列表
        """
        # 字段映射说明
        field_mapping = {
            'f12': '股票代码',
            'f14': '股票名称', 
            'f15': '最新价',
            'f3': '涨跌幅(%)',
            'f4': '涨跌额',
            'f5': '成交量(手)',
            'f6': '成交额',
            'f7': '振幅',
            'f8': '换手率(%)',
            'f9': '市盈率(动态)',
            'f10': '量比',
            'f16': '最高价',
            'f17': '最低价',
            'f18': '今开',
            'f23': '市净率'
        }
        
        # 默认市场筛选条件
        if market_filter is None:
            market_filter = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'  # 所有A股
        
        start_time = time.perf_counter()
        
        print(f"🚀 快速获取所有股票数据...")
        print(f"市场筛选: {market_filter}")
        print(f"排序字段: {sort_field} ({'降序' if sort_order == 1 else '升序'})")
        print("=" * 60)
        
        # 构建请求URL - 一次性获取大量数据
        url = f'http://81.push2.eastmoney.com/api/qt/clist/get'
        params = {
            'cb': f'jQuery{int(time.time()*1000)}',
            'pn': '1',  # 只请求第1页
            'pz': '10000',  # 一次性获取10000只股票
            'po': str(sort_order),
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': sort_field,
            'fs': market_filter,
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
            '_': str(int(time.time()*1000))
        }
        
        try:
            print("📡 发送请求中...")
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 解析返回的JSONP数据
            jsdata = re.findall(r'\(.*?\)', response.text)
            if jsdata:
                dicts = json.loads(jsdata[0][1:len(jsdata[0])-1])
                
                # 打印API响应信息
                print(f"📊 API响应信息:")
                if 'data' in dicts:
                    data = dicts['data']
                    print(f"  总数据量: {data.get('total', 'N/A')}")
                    print(f"  当前页数据量: {len(data.get('diff', []))}")
                    print(f"  请求的每页数量: {params['pz']}")
                
                diff = dicts.get('data', {}).get('diff', [])
                
                if diff:
                    # 转换数据格式
                    all_stocks = []
                    for item in diff:
                        stock_info = {}
                        for field, description in field_mapping.items():
                            if field in item:
                                stock_info[description] = item[field]
                        all_stocks.append(stock_info)
                    
                    duration = time.perf_counter() - start_time
                    print(f"✅ 快速获取完成！")
                    print(f"📊 获取到 {len(all_stocks)} 只股票数据")
                    print(f"⏱️  耗时: {duration:.2f}秒")
                    print("=" * 60)
                    
                    return all_stocks
                else:
                    print("❌ 未获取到股票数据")
                    return []
            else:
                print("❌ 数据解析失败")
                return []
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []

    def get_all_stocks_smart(self, market_filter: str = None, sort_field: str = 'f3', 
                            sort_order: int = 1) -> List[Dict]:
        """
        智能获取所有股票数据（自动分页）
        
        Args:
            market_filter: 市场筛选条件，默认获取所有A股
            sort_field: 排序字段，默认'f3'(涨跌幅)
            sort_order: 排序方向，1=降序，0=升序
            
        Returns:
            List[Dict]: 股票数据列表
        """
        # 字段映射说明
        field_mapping = {
            'f12': '股票代码',
            'f14': '股票名称', 
            'f15': '最新价',
            'f3': '涨跌幅(%)',
            'f4': '涨跌额',
            'f5': '成交量(手)',
            'f6': '成交额',
            'f7': '振幅',
            'f8': '换手率(%)',
            'f9': '市盈率(动态)',
            'f10': '量比',
            'f16': '最高价',
            'f17': '最低价',
            'f18': '今开',
            'f23': '市净率'
        }
        
        # 默认市场筛选条件
        if market_filter is None:
            market_filter = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'  # 所有A股
        
        start_time = time.perf_counter()
        
        print(f"🧠 智能获取所有股票数据...")
        print(f"市场筛选: {market_filter}")
        print(f"排序字段: {sort_field} ({'降序' if sort_order == 1 else '升序'})")
        print("=" * 60)
        
        # 首先获取第一页来确定总数据量
        url = f'http://81.push2.eastmoney.com/api/qt/clist/get'
        params = {
            'cb': f'jQuery{int(time.time()*1000)}',
            'pn': '1',
            'pz': '100',  # 先获取100条来测试
            'po': str(sort_order),
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': sort_field,
            'fs': market_filter,
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152',
            '_': str(int(time.time()*1000))
        }
        
        try:
            print("📡 发送测试请求...")
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 解析返回的JSONP数据
            jsdata = re.findall(r'\(.*?\)', response.text)
            if jsdata:
                dicts = json.loads(jsdata[0][1:len(jsdata[0])-1])
                
                if 'data' in dicts:
                    data = dicts['data']
                    total_count = data.get('total', 0)
                    current_count = len(data.get('diff', []))
                    
                    print(f"📊 检测到总数据量: {total_count}")
                    print(f"📊 当前页数据量: {current_count}")
                    
                    if total_count == 0:
                        print("❌ 没有找到股票数据")
                        return []
                    
                    # 如果总数据量小于等于当前页数据量，说明一次性获取完成
                    if total_count <= current_count:
                        print("✅ 一次性获取完成！")
                        all_stocks = []
                        for item in data.get('diff', []):
                            stock_info = {}
                            for field, description in field_mapping.items():
                                if field in item:
                                    stock_info[description] = item[field]
                            all_stocks.append(stock_info)
                        
                        duration = time.perf_counter() - start_time
                        print(f"📊 获取到 {len(all_stocks)} 只股票数据")
                        print(f"⏱️  耗时: {duration:.2f}秒")
                        print("=" * 60)
                        return all_stocks
                    
                    # 需要分页获取
                    print(f"📄 需要分页获取，计算最优分页策略...")
                    
                    # 东方财富API单次请求有数据量限制，使用较小的page_size
                    optimal_page_size = min(100, total_count)  # 使用100作为每页数量
                    pages_needed = (total_count + optimal_page_size - 1) // optimal_page_size
                    
                    print(f"📄 使用每页 {optimal_page_size} 只，需要 {pages_needed} 页")
                    
                    all_stocks = []
                    
                    for page in range(1, pages_needed + 1):
                        params['pn'] = str(page)
                        params['pz'] = str(optimal_page_size)
                        
                        try:
                            response = requests.get(url, params=params, headers=self.headers, timeout=30)
                            response.raise_for_status()
                            
                            jsdata = re.findall(r'\(.*?\)', response.text)
                            if jsdata:
                                dicts = json.loads(jsdata[0][1:len(jsdata[0])-1])
                                diff = dicts.get('data', {}).get('diff', [])
                                
                                if diff:
                                    for item in diff:
                                        stock_info = {}
                                        for field, description in field_mapping.items():
                                            if field in item:
                                                stock_info[description] = item[field]
                                        all_stocks.append(stock_info)
                                    
                                    progress = page / pages_needed * 100
                                    duration = time.perf_counter() - start_time
                                    print(f"\r进度: {progress:^3.0f}% [{page}/{pages_needed}] 已获取{len(all_stocks)}只股票 耗时{duration:.2f}s", end="")
                                    
                                    # 如果返回的数据少于page_size，说明已经到最后一页
                                    if len(diff) < optimal_page_size:
                                        print(f"\n已到达最后一页")
                                        break
                                else:
                                    print(f"\n第{page}页无数据，停止获取")
                                    break
                            else:
                                print(f"\n第{page}页数据解析失败")
                                break
                                
                        except Exception as e:
                            print(f"\n第{page}页请求失败: {e}")
                            break
                        
                        # 添加延迟避免请求过快
                        time.sleep(0.1)
                    
                    duration = time.perf_counter() - start_time
                    print(f"\n✅ 智能获取完成！")
                    print(f"📊 获取到 {len(all_stocks)} 只股票数据")
                    print(f"⏱️  总耗时: {duration:.2f}秒")
                    print("=" * 60)
                    
                    return all_stocks
                else:
                    print("❌ API响应格式错误")
                    return []
            else:
                print("❌ 数据解析失败")
                return []
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []


def test_api():
    """测试API调用"""
    api = EastMoneyAPI()
    
    # 测试股票代码列表
    test_stocks = [
        "1.000001",  # 上证指数
        "0.600000",  # 沪市：浦发银行
        "1.000002",  # 深市：万科A
        "0.600036",   # 沪市：招商银行
        "0.000001",   # 深市：平安银行
        "1.601086",   # 深市：国芳集团
    ]
    
    print("=== 东方财富API测试 ===\n")
    
    for secid in test_stocks:
        print(f"获取股票 {secid} 的数据:")
        print("-" * 50)
        
        # 获取详细数据
        stock_info = api.get_stock_info(secid)
        
        if stock_info:
            for key, value in stock_info.items():
                print(f"{key}: {value}")
        else:
            print("获取数据失败或无数据")
        
        print("\n")
        time.sleep(1)  # 避免请求过于频繁


def get_single_stock_data(secid: str):
    """获取单个股票数据的便捷函数"""
    api = EastMoneyAPI()
    stock_info = api.get_stock_info(secid)
    
    if stock_info:
        print(f"股票 {secid} 数据:")
        print("-" * 30)
        for key, value in stock_info.items():
            print(f"{key}: {value}")
    else:
        print(f"获取股票 {secid} 数据失败")


def test_batch_api():
    """测试批量API调用"""
    api = EastMoneyAPI()
    
    # 测试股票代码列表
    test_stocks = [
        "1.000001",  # 上证指数
        "0.600000",  # 沪市：浦发银行
        "1.000002",  # 深市：万科A
        "0.600036",  # 沪市：招商银行
        "0.000001",   # 深市：平安银行
        "1.601086"   # 深市：国芳集团
    ]
    
    print("=== 东方财富批量API测试 ===\n")
    
    # 批量获取数据
    stock_list = api.get_stock_list_data(test_stocks)
    
    if stock_list:
        print(f"成功获取 {len(stock_list)} 只股票的数据:")
        print("=" * 60)
        
        for i, stock_info in enumerate(stock_list, 1):
            print(f"\n股票 {i}:")
            print("-" * 30)
            for key, value in stock_info.items():
                print(f"{key}: {value}")
    else:
        print("批量获取数据失败")


def test_market_statistics():
    """测试市场统计数据"""
    api = EastMoneyAPI()
    
    print("=== 市场统计数据测试 ===\n")
    
    # 获取市场统计数据
    market_stats = api.get_market_statistics()
    
    if market_stats:
        print("📊 市场整体统计:")
        print("=" * 50)
        
        key_stats = [
            '总股票数', '上涨股票数', '下跌股票数', '平盘股票数',
            '平均涨跌幅(%)', '上涨率(%)', '下跌率(%)', '平盘率(%)'
        ]
        
        for stat in key_stats:
            if stat in market_stats:
                print(f"{stat}: {market_stats[stat]}")
        
        print("\n📈 市场情绪分析:")
        print("-" * 30)
        if market_stats['上涨率(%)'] > market_stats['下跌率(%)']:
            print("🟢 市场偏乐观，上涨股票占多数")
        elif market_stats['下跌率(%)'] > market_stats['上涨率(%)']:
            print("🔴 市场偏悲观，下跌股票占多数")
        else:
            print("🟡 市场相对平衡")
            
        if market_stats['平均涨跌幅(%)'] > 0:
            print(f"📈 平均涨幅: +{market_stats['平均涨跌幅(%)']}%")
        else:
            print(f"📉 平均跌幅: {market_stats['平均涨跌幅(%)']}%")
    else:
        print("❌ 获取市场统计数据失败")


def test_ulist_api():
    """测试ulist接口"""
    api = EastMoneyAPI()
    
    # 测试股票代码列表
    test_stocks = [
        "1.000001",  # 上证指数
        "0.600000",  # 沪市：浦发银行
        "1.000002",  # 深市：万科A
        "0.600036",  # 沪市：招商银行
        "0.000001"   # 深市：平安银行
    ]
    
    print("=== 东方财富ulist接口测试 ===\n")
    
    # 尝试ulist接口
    stock_list = api.get_stock_list_data_v2(test_stocks)
    
    if stock_list:
        print(f"ulist接口成功获取 {len(stock_list)} 只股票的数据:")
        print("=" * 60)
        
        for i, stock_info in enumerate(stock_list, 1):
            print(f"\n股票 {i}:")
            print("-" * 30)
            for key, value in stock_info.items():
                print(f"{key}: {value}")
    else:
        print("ulist接口获取数据失败")


def test_single_loop_api():
    """详细测试循环单个接口的批量获取方法"""
    api = EastMoneyAPI()
    
    # 测试股票代码列表
    test_stocks = [
        "1.000001",  # 上证指数
        "0.600000",  # 沪市：浦发银行
        "1.000002",  # 深市：万科A
        "0.600036",  # 沪市：招商银行
        "0.000001"   # 深市：平安银行
    ]
    
    print("=== 详细测试循环单个接口批量获取 ===\n")
    print(f"测试股票列表: {test_stocks}")
    print("=" * 60)
    
    # 使用循环单个接口的方法
    stock_list = api.get_stock_list_data(test_stocks)
    
    if stock_list:
        print(f"\n✅ 成功获取 {len(stock_list)} 只股票的完整数据:")
        print("=" * 60)
        
        for i, stock_info in enumerate(stock_list, 1):
            print(f"\n📈 股票 {i}:")
            print("-" * 40)
            
            # 检查是否包含你关心的字段
            key_fields = ['股票代码', '股票名称', '最新价', '涨跌幅(%)', '涨跌额', 
                         '最高价', '最低价', '今开', '成交量(手)', '1分钟涨速', 
                         '3分钟涨速', '换手率(%)', '总股本', '流通股本']
            
            for field in key_fields:
                if field in stock_info:
                    print(f"✅ {field}: {stock_info[field]}")
                else:
                    print(f"❌ {field}: 未获取到")
            
            # 显示所有获取到的字段
            print(f"\n📊 所有字段 ({len(stock_info)} 个):")
            for key, value in stock_info.items():
                print(f"   {key}: {value}")
    else:
        print("❌ 循环单个接口批量获取数据失败")


def test_ulist_fields():
    """测试ulist接口指定字段返回情况"""
    api = EastMoneyAPI()
    params = {
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'invt': '2',
        'fltt': '2',
        'fields': 'f43,f168,f135,f136,f169,f44,f45,f104,f105',
        'pn': '1',
        'pz': '50',
        'po': '1',
        'np': '1',
        'fid': 'f3',
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'
    }
    try:
        response = requests.get(
            "http://push2.eastmoney.com/api/qt/clist/get",
            params=params,
            headers=api.headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        print("原始返回内容：", data)  # 打印原始内容便于调试
        if data and 'data' in data and data['data'] and 'diff' in data['data'] and len(data['data']['diff']) > 0:
            first = data['data']['diff'][0]
            print("ulist接口返回的字段如下：")
            for k, v in first.items():
                print(f"{k}: {v}")
        else:
            print("未获取到数据")
    except Exception as e:
        print(f"ulist字段测试失败: {e}")


def test_clist_batch_api():
    """测试使用clist接口的批量获取方法"""
    api = EastMoneyAPI()
    
    print("=== 测试clist接口批量获取股票数据 ===\n")
    
    # 测试获取前几页数据（避免获取太多）
    stock_list = api.get_stock_list_data_v3(page_size=20, max_pages=3)
    
    if stock_list:
        print(f"\n✅ 成功获取 {len(stock_list)} 只股票数据:")
        print("=" * 80)
        
        # 显示前5只股票的数据作为示例
        for i, stock_info in enumerate(stock_list[:5], 1):
            print(f"\n📈 股票 {i}:")
            print("-" * 50)
            
            # 显示关键字段
            key_fields = ['股票代码', '股票名称', '最新价', '涨跌幅(%)', '涨跌额', 
                         '成交量(手)', '成交额', '振幅', '最高价', '最低价', 
                         '今开', '量比', '换手率(%)', '市盈率(动态)', '市净率']
            
            for field in key_fields:
                if field in stock_info:
                    print(f"✅ {field}: {stock_info[field]}")
                else:
                    print(f"❌ {field}: 未获取到")
        
        if len(stock_list) > 5:
            print(f"\n... 还有 {len(stock_list) - 5} 只股票数据未显示")
        
        # 统计涨跌情况
        up_count = 0
        down_count = 0
        flat_count = 0
        
        for stock in stock_list:
            if '涨跌幅(%)' in stock and stock['涨跌幅(%)'] != '-':
                change_rate = stock['涨跌幅(%)']
                if change_rate > 0:
                    up_count += 1
                elif change_rate < 0:
                    down_count += 1
                else:
                    flat_count += 1
        
        print(f"\n📊 统计信息:")
        print(f"上涨股票: {up_count} 只")
        print(f"下跌股票: {down_count} 只") 
        print(f"平盘股票: {flat_count} 只")
        
    else:
        print("❌ clist接口批量获取数据失败")


def test_custom_filter_api():
    """测试获取所有A股数据"""
    api = EastMoneyAPI()
    
    print("=== 测试获取所有A股数据 ===\n")
    
    # 获取所有A股，按股票代码排序
    print("📊 获取所有A股（按股票代码排序）")
    print("-" * 50)
    all_stocks = api.get_all_stocks_smart(
        market_filter='m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # 所有A股
        sort_field='f12',          # 按股票代码排序
        sort_order=0               # 升序（从小到大）
    )
    
    if all_stocks:
        print(f"\n✅ 获取到 {len(all_stocks)} 只A股股票:")
        
        # 显示前5只股票的所有字段
        print("\n前5只股票的所有字段:")
        print("=" * 80)
        
        for i, stock in enumerate(all_stocks[:5], 1):
            print(f"\n📈 股票 {i}: {stock.get('股票代码', 'N/A')} {stock.get('股票名称', 'N/A')}")
            print("-" * 60)
            
            # 显示所有字段
            for key, value in stock.items():
                print(f"  {key}: {value}")
        
        # 显示后5只股票的所有字段
        print(f"\n后5只股票的所有字段:")
        print("=" * 80)
        
        for i, stock in enumerate(all_stocks[-5:], len(all_stocks)-4):
            print(f"\n📈 股票 {i}: {stock.get('股票代码', 'N/A')} {stock.get('股票名称', 'N/A')}")
            print("-" * 60)
            
            # 显示所有字段
            for key, value in stock.items():
                print(f"  {key}: {value}")
        
        # 统计A股分布
        if all_stocks:
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


if __name__ == "__main__":
    
    # 测试自定义筛选条件的批量获取
    test_custom_filter_api() 
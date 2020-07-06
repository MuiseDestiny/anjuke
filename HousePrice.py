from fake_useragent import UserAgent
from random import randint
from lxml import etree
import pandas as pd
import numpy as np
import requests
import pickle
import time
import re
import os
os.chdir("F:/python/课程设计/")


class HousePrice(object):
    province_cn = '山东'  # 需要爬取的省份
    province_en = 'shandong'  # 拼音，用于生成链接得到省份所有市和自治区
    city_dict = {'青岛市': ['黄岛区']}  # 可手动指定城市
    finished = []  # 如遇程序奔溃，讲完成的市填入此处，自动跳过


    def __init__(self, cn, en, finished=[]):
        self.province_cn = cn
        self.province_en = en
        self.finished = finished
        # 初始化session
        self.ua =  UserAgent()
        self.session = requests.Session()
        self.headers = {'User-Agent': self.ua.random}
        self.session.headers = self.headers
        # 获取省包含的的市和自治区
        self.get_city()
        # 获取安居客支持的地区链接
        self.get_target_url()
        # 打开txt待命
        self.init_txt()
        # 前往安居客
        self.get_all_house_info()
    
    def get_city(self):
        if len(self.city_dict):
            self.print_and_log('[初始化]: 检测到自定义的city_dict')
        else:
            self.print_and_log('[初始化]: 正在采集{}省详细信息'.format(self.province_cn))
            city_info_url = 'http://sou.chinawutong.com/webparts/selectarea/{}.htm'
            r = self.session.get(city_info_url.format(self.province_en))
            r.encoding = 'gbk'
            html = etree.HTML(r.text)
            a_tags = html.xpath('.//table//td//a')
            city_dict = {}
            key = ''
            for a in a_tags:
                is_class = a.xpath('@class')
                if is_class:
                    key = a.xpath('text()')[0]
                    city_dict[key] = []
                else:
                    city_dict[key].append(a.xpath('text()')[0])
            self.city_dict = city_dict
            self.print_and_log('[初始化]: 有关{}省的地区采集完成:'.format(self.province_cn))
            self.print_and_log(str(self.city_dict))

    def get_target_url(self):
        if os.path.exists('city_url_dict.pkl'):
            self.print_and_log('[IO信息]: city_url_dict | 已存在，读取中...')
            self.city_url_dict = self.load_obj('city_url_dict')
            self.print_and_log('[IO信息]: 读取成功')
        else:
            self.print_and_log('[IO信息]: city_url_dict | 不存在， 获取中...')
            html = etree.HTML(self.session.get('https://www.anjuke.com/sy-city.html').text)
            a_tags = html.xpath('.//div[@class="city-itm"]//a')
            city_url_dict = {}
            for a in a_tags:
                city_url_dict[a.xpath('text()')[0]] = a.xpath('@href')[0]
            self.print_and_log('[IO信息]: 已保存到本地')
            self.save_obj(city_url_dict, 'city_url_dict')
            self.city_url_dict = city_url_dict

    def get_all_house_info(self):
        self.print_and_log('[状态信息]: 正在前往安居客...')
        # 检测市是否包含在安居客
        for city in self.city_dict.keys():
            city = city.replace('市', '').replace('自治州', '').replace('地区', '')
            if city in self.finished:
                continue
            if city in self.city_url_dict:
                self.print_and_log('[状态信息]: 检测到"{}"的目标网址 火速前往...'.format(city))
                self.city_name = city
                self.get_city_house_info_by_phone(self.city_url_dict[city])
                self.finished.append(city)
                self.print_and_log('[状态信息]: 已完成列表={} | {}/{}'.format(
                    self.finished, len(self.finished), len(self.city_dict)))
            else:
                self.print_and_log('{} | 安居客暂时不支持该地区'.format(city))
    
    def get_city_house_info_by_pc(self, url):
        url = url.replace('.anjuke', '.xinfang.anjuke')
        print(url)
        i = 1
        while True:
            _url = url + '/loupan/all/p{}/'.format(i)
            self.headers['User-Agent'] = self.ua.random
            html = etree.HTML(requests.get(_url, headers=self.headers).text)
            div_tags = html.xpath('.//div[contains(@data-soj,"AF_RANK")]')
            if not len(div_tags):
                break
            for div in div_tags:
                name = div.xpath(
                    'div[@class="infos"]/a[1]/span[@class="items-name"]/text()')[0]
                address = div.xpath(
                    'div[@class="infos"]/a[2]/span[@class="list-map"]/text()')[0]
                try:
                    area = div.xpath(
                        'div[@class="infos"]/a[3]/span[@class="building-area"]/text()')[0]
                except:
                    area = '未知'
                try:
                    price = div.xpath(
                        'a[@class="favor-pos"]/p/span/text()')[0]
                except:
                    price = '售价待定'
                lon, lat = self.search_lon_lat(
                    re.findall('\[(.+?)\]', address)[0].split()[0], self.city_name
                )
                info_list = [name, address, area, price, lon, lat]
                with open(self.file, 'a+', encoding='utf-8') as f:
                    f.write('\t'.join(info_list) + '\n')
                self.print_and_log(' | '.join(info_list))
            i += 1
    
    def get_cid(self, url):
        r = requests.get(url, headers={'User-Agent': self.ua.random}, timeout=6)
        self.print_and_log('[状态信息]: 查找cid中...')
        try:
            cid = re.findall("value: '(\d+)'", r.text)[0]
        except:
            print(r.text)
            input('[开发者提示]: 请检查网页信息...')
        if cid == '0':
            verify = 'https://www.anjuke.com'
            input('[开发者提示]: 请前往网页验证 | {}'.format(verify))
            time.sleep(1)
            return self.get_cid(url)
        self.print_and_log('[查找结果]: cid={}'.format(cid))
        return cid

    def get_city_house_info_by_phone(self, url):
        api = 'https://m.anjuke.com/xinfang/api/loupan/list/'
        cid = self.get_cid(url)
        i = 1
        while True:
            page = i
            args = '{"cid": ' + str(cid) + ',"page":' + str(page) + \
                ',"pageSize":20,"args":{},"commerce":0,"commerce_type":0,"seoPage":null}'
            params = {'args': args}
            headers = {
                'host': 'm.anjuke.com',
                'cookie': 'aQQ_ajkguid=E7CFBAAC-77C1-D29E-92BE-50F2D1288C53; id58=e87rkF7wYzlLu79nBLK4Ag==; _ga=GA1.2.1508265039.1592812345; _gid=GA1.2.640025303.1592812345; 58tj_uuid=fea97018-abd3-4389-b83c-b2fc3c6813b2; als=0; isp=true; lp_lt_ut=c4a7babd19f77520569bf5495a6f893c; sessid=474701FA-DF23-09F5-5452-005AD07CDC01; app_cv=unknown; new_uv=5; init_refer=; wmda_new_uuid=1; wmda_uuid=c58f6df68d8e47c3638a7802b1567fe2; lps="/cityList/?from=xinfang_home|https://m.anjuke.com/xinfang/"; new_session=0; wmda_visited_projects=%3B8146401978551%3B6145577459763%3B8797075781809; xzfzqtoken=49JrBi%2BX9J%2BhtCkA4ONaoSoWHxNOHS90FSfMjKyxE7a%2F7JDsKXbRETaLkRpg55Sjin35brBb%2F%2FeSODvMgkQULA%3D%3D; twe=2; ANJUKE_BUCKET=pc-home%3AErshou_Web_Home_Home-b; xxzl_cid=d5973348500849a1b6771128ff9da0b1; wmda_session_id_8797075781809=1592881111369-a9debe30-4809-2eb7; wmda_session_id_6145577459763=1592881161262-5b4f09f2-3ce6-3ba2; ctid=13; xzuid=8778aca2-8ff3-4728-8cc3-9803542bc179; wmda_session_id_8146401978551=1592881198840-b9bb9899-0c7d-097c',
                'user-agent': self.ua.random
            }
            r = requests.get(api, params=params, headers=headers)
            r.encoding = 'utf-8'
            try:
                json_res_list = eval(r.text.replace('null', 'None').replace('true', 'True'))['result']['rows']
            except Exception as e:
                self.print_and_log(str(e))
                if eval(r.text.replace('null', 'None').replace('true', 'True'))['code'] == 'CAPTCHA':
                    input('[开发者提示]: 请亲自前往{}验证身份，然后按任意键继续...'.format(
                        eval(r.text.replace('null', 'None').replace('true', 'True'))['url'].replace('\\', '')
                    ))
                else:
                    self.print_and_log('[开发者提示]: 建议您更换网络环境后重试')
            if json_res_list == []:
                break
            for row_data in json_res_list:
                name = row_data['loupan_name']
                price = row_data['new_price_value']
                unit = row_data['new_price_back'].replace('\\', '')
                lon = row_data['baidu_lng']
                lat = row_data['baidu_lat']
                region = row_data['region_title']
                address = row_data['address']
                lon, lat = self.check_lon_lat(lon, lat, region, address)
                info_list = [name, price, unit, lon, lat, region, address]
                # 去除无效数据
                if price == '' or unit != '元/㎡':
                    continue
                with open(self.file, 'a+', encoding='utf-8') as f:
                    f.write('\t'.join(info_list) + '\n')
                print(' | '.join(info_list))
            self.print_and_log('[状态信息]: page={} | 已完成列表={} | {}/{}'.format(
                                        i, self.finished, len(self.finished), len(self.city_dict)))
            i += 1
    
    def check_lon_lat(self, lon, lat, region, address):
        if float(lon) == 0 or float(lat) == 0:
            try:
                place = re.findall('(.+[道路街站号镇畔])', address)[0]
            except:
                place = address[:4]
            return self.search_lon_lat(place, region)
        else:
            return lon, lat

    def search_lon_lat(self, place, region):
        api = 'http://api.map.baidu.com/place/v2/search'
        params = {
            'q': place,
            'region': region,
            'scope': '1',
            'page_size': '1',
            'page_num': '1',
            'output': 'json',
            'ak': '7xE1uAen9sNBIuyoB4cPF3HN0aV43v6n'
        }
        r = requests.get(api, params=params)
        r = r.text
        try:
            lat, lon = list(eval(r)['results'][0]['location'].values())
        except:
            self.print_and_log(place + region + '未找到经纬度信息')
            lon, lat = 0, 0
        return str(lon), str(lat)

    def print_and_log(self, s):
        with open('log/log_{}.txt'.format(self.province_en), 'a+', encoding='utf-8') as f:
            f.write(s + '\n')
            print(s)
    
    def init_txt(self):
        self.file = 'output/output_{}.txt'.format(self.province_en)
        if os.path.exists(self.file):
            with open(self.file, 'r', encoding='utf-8') as f:
                line = f.readline()
            if 'Name' not in line:
                self.print_and_log('[IO信息]: 创建txt头中...')
                self.creat_header()
            else:
                self.print_and_log('[IO信息]: txt头信息已存在')
        else:
            self.print_and_log('[IO信息]: 创建txt头中...')
            self.creat_header()

    def creat_header(self):
        with open(self.file, 'a+', encoding='utf-8') as f:
            f.write('\t'.join(['Name', 'Price', 'Unit', 'Lon', 'Lat', 'Region', 'Address']) + '\n')

    @staticmethod
    def save_obj(obj, name):
        with open(name + '.pkl', 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
    
    @staticmethod
    def load_obj(name):
        with open(name + '.pkl', 'rb') as f:
            return pickle.load(f)
        
if __name__ == "__main__":
    # 直接填写 省份中文 拼音 已完成的列表
    HousePrice('四川', 'sichuan', [])

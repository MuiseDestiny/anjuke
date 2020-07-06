import requests
from lxml import etree
# from fake_useragent import FakeUserAgent
import pandas as pd


pd.read_excel(r'C:\Users\zhou1\Desktop\data.xls')
print(pd)

# ua = FakeUserAgent()
# city_info_url = 'http://sou.chinawutong.com/webparts/selectarea/shandong.htm'
# r = requests.get(city_info_url, headers={
#     'User-Agent': ua.random
# })
# r.encoding = 'gbk'
# html = etree.HTML(r.text)
# a_tags = html.xpath('.//table//td//a')
# city_dict = {}
# key = ''
# for a in a_tags:
#     is_class = a.xpath('@class')
#     if is_class:
#         key = a.xpath('text()')[0]
#         city_dict[key] = []
#     else:
#         city_dict[key].append(a.xpath('text()')[0])
# print(city_dict)

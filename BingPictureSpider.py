# -*- coding: utf-8 -*-

import json
import re

import pymysql
from lxml import etree
import requests

def get_bing_pic(url,img_info_list):

    headers = {
                'referer': 'https://bing.ioliu.cn/?p=1',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
                'Accept': 'text / html, application / xhtml + xml, application / xml;q = 0.9, image / webp, image / apng, * / *;q = 0.8'
            }

    resp = requests.get(url,headers = headers)

    html = etree.HTML(resp.content.decode())

    # 获取当前页面的所有图片详情链接
    img_desc_list = html.xpath("//a[@class='mark']/@href")

    for i in img_desc_list:
        item = {}

        response = requests.get('https://bing.ioliu.cn'+ i,headers = headers)

        html = etree.HTML(response.content.decode())
        item["title"] = html.xpath("//p[@class='title']/text()")
        item["content"] = html.xpath("//p[@class='sub']/text()")
        item['img_url'] = re.search('data-progressive="(.*?)"',response.content.decode(),re.S).group(1).strip()

        print(item['img_url'] )
        other = html.xpath("//p/em[@class='t']/text()")

        item["date"] = other[0]
        item["position"] = other[1]
        item["look"] = other[2]

        img_info_list.append(item)

if __name__ == '__main__':
    img_info_list = []

    for j in range(6,8):
        get_bing_pic("https://bing.ioliu.cn/?p=" + str(j),img_info_list)

        # with open('img_info.json','wb') as f:
        #     f.write(json.dumps(img_info_list).encode('utf-8'))

        conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='5456', db='vue')  # 创建连接

        cursor = conn.cursor()  # 创建游标，为了日后的回滚

        for i in img_info_list:
            sql = 'insert into tb_picture(category_id,content,title,date,position,look,img_url)values(%s,%s,%s,%s,%s,%s,%s)'
            cursor.execute(sql, (j, i['content'], i['title'], i['date'],i['position'],i['look'],i['img_url']))

        conn.commit()  # 提交，不然无法保存新建或者修改的数据

        cursor.close()  # 关闭游标

        conn.close()  # 关闭连接
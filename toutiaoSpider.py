#coding:utf-8

import json

import datetime
import time

import gevent
import requests
from bs4 import BeautifulSoup
import js2xml
from lxml import etree
import pymysql

import html as hl

class Toutiao(object):

    def __init__(self,keyword):
        self.headers = {
            'referer': 'https://www.toutiao.com/search/?keyword=%E7%8E%8B%E4%BF%8A%E5%87%AF',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }

        self.offset = 0
        self.keyword = keyword

        self.conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='5456', db='vue')
        self.cursor = self.conn.cursor()

        # 线（协）程们
        self.threads = []

    def get_news_list(self):
        """
        获取新闻列表
        :param keyword:查询关键词
        :param offset:偏移量
        :param newsList:新闻列表
        :return:
        """
        base_url = 'https://www.toutiao.com/search_content/?'

        # 定义url的参数
        params = {
            'offset': self.offset,
            'format': 'json',
            'keyword': self.keyword,
            'autoload': 'true',
            'count': '20',
            'cur_tab': '1',
            'from': 'search_tab'
        }

        response = requests.get(base_url, params=params, headers=self.headers)

        # print(response.request.url)

        dict_ret = json.loads(response.content.decode())

        self.offset += 20
        if dict_ret["has_more"] and self.offset < 40:
            # 使用协程
            self.threads.append(gevent.spawn(self.get_news_list()))

        # 遍厉每一条新闻
        for i in dict_ret["data"]:
            if i.get("article_url") and i["article_url"].startswith("http://toutiao.com/group/"):
                item = {}
                item["id"] = i["id"]
                item["title"] = i["title"]
                item["add_time"] = i["datetime"]
                item["article_url"] = i["article_url"]
                item["img_url"] = 'http:' + i['image_list'][0]["url"]
                item["article_list_url"] = response.request.url

                print(item)

                self.get_news_content(item)

    def get_news_content(self, item):
        """
        获取文章具体内容
        :param item:
        :return:
        """

        # 1.向文章详情页面发送请求
        resp = requests.get(item["article_url"], headers=self.headers)
        resp_url = resp.url
        if resp_url.startswith("https://www.toutiao.com"):  # 判断新闻是否是头条的

            item["article_url"] = resp_url

            html = resp.content

            time.sleep(1)

            # 2.对请求对结果进行解析，找出第四个script标签中对内容，并对<script>标签进行剪切
            soup = BeautifulSoup(html)
            res = soup.find_all('script')
            try:
                l = res[6].text
                l.replace("</script>", "").replace("<script>", "")

                # 3.使用js2xml将js代码转化成xml
                src_text = js2xml.parse(l, encoding='utf-8', debug=False)
                src_tree = js2xml.pretty_print(src_text)

                # 4.通过xpath将文章内容取出
                selector = etree.HTML(src_tree)
                content = selector.xpath('//property[@name="content"]/string/text()')

                item['content'] = hl.unescape(content[0])
            except Exception as ex:
                print(ex)
                return # 结束当前方法

            self.save_2_mysql(item)

    def save_2_mysql(self,item):
        """
        将数据插入到数据库中
        :param item:
        :return:
        """
        # 执行SQL，并返回受影响行数
        sql = 'insert into tb_news(id,add_time,click,content,img_url,title)values(%s,%s,%s,%s,%s,%s)'
        self.cursor.execute(sql, (item['id'] ,datetime.datetime.strptime(item['add_time'], "%Y-%m-%d %H:%M:%S"), '0', item['content'], item["img_url"],item["title"]))
        self.conn.commit()  # 提交，不然无法保存新建或者修改的数据
        print("插入数据成功，文章链接为" + item["article_url"])


    def destory(self):
        """
        结束时调用方法
        :return:
        """

        # 协程只有在joinall的时候，线程池中的方法才会真正执行
        gevent.joinall(self.threads)

        self.cursor.close()  # 关闭游标
        self.conn.close()  # 关闭连接


if __name__ == '__main__':
    obj = Toutiao("科技")
    obj.get_news_list()
    obj.destory()
# biqu_core.py
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://www.qu02.cc"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

class NovelDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def search(self, keyword):
        """搜索小说，返回结果列表"""
        try:
            params = {"s": quote(keyword)}
            response = self.session.get(f"{BASE_URL}/search.html", params=params, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            for item in soup.select('.novelslist2 li'):
                link = item.select_one('a')
                if not link or not link.get('href'):
                    continue
                title_elem = item.select_one('.s2 a')
                author_elem = item.select_one('.s4')
                if not title_elem or not author_elem:
                    continue
                results.append({
                    "articlename": title_elem.get_text(strip=True),
                    "author": author_elem.get_text(strip=True),
                    "url_list": link['href']
                })
            return results
        except Exception as e:
            return []

    def get_chapter_list(self, novel_url):
        """获取章节列表"""
        try:
            response = self.session.get(novel_url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            chapters = []
            for a in soup.select('#list dl dd a'):
                href = a.get('href')
                title = a.get_text(strip=True)
                if href and title:
                    full_url = urljoin(novel_url, href)
                    chapters.append((title, full_url))
            return chapters
        except Exception:
            return []

    def fetch_chapter_content(self, title, url):
        """获取单章内容（纯文本）"""
        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            content_div = soup.select_one('#content')
            if content_div:
                for ad in content_div.select('div'):
                    ad.decompose()
                text = content_div.get_text(strip=False)
                text = "\n".join(line.strip() for line in text.split("\n") if line.strip())
                return f"\n\n{title}\n\n{text}\n"
        except Exception:
            pass
        return f"\n\n{title}\n\n[下载失败]\n"

    def download_novel_to_text(self, novel_url, title, author):
        """下载整本小说为字符串（不保存文件）"""
        chapters = self.get_chapter_list(novel_url)
        if not chapters:
            return False, "未找到章节", ""

        output = f"书名：{title}\n作者：{author}\n来源：{novel_url}\n\n"

        # 并发下载（限制线程数）
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_title = {
                executor.submit(self.fetch_chapter_content, title, url): title
                for title, url in chapters
            }
            results = {}
            for future in as_completed(future_to_title):
                title = future_to_title[future]
                try:
                    content = future.result()
                    results[title] = content
                except Exception:
                    results[title] = f"\n\n{title}\n\n[解析异常]\n"

        # 按原始顺序拼接
        for title, _ in chapters:
            output += results.get(title, f"\n\n{title}\n\n[内容丢失]\n")

        return True, "成功", output


# 暴露函数
def search_novels(keyword):
    downloader = NovelDownloader()
    return downloader.search(keyword)

def download_novel_to_text(novel_url, title, author):
    downloader = NovelDownloader()
    return downloader.download_novel_to_text(novel_url, title, author)
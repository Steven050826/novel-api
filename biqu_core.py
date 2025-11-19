# biqu_core.py
import os
import time
import urllib.parse
import copy
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== 完全复制自 biqu.py 的配置 ==========
BASE_URL = "https://www.qu02.cc/"

HEADERS = {
    "authority": "www.biqg.cc",
    "accept": "application/json",
    "accept-language": "zh,en;q=0.9,zh-CN;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "x-requested-with": "XMLHttpRequest",
}

# ========== 核心类（精简版，移除终端交互） ==========
class NovelDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_hm_cookie(self, url):
        try:
            self.session.get(url=url, timeout=10)
            return True
        except requests.RequestException:
            return False

    def search(self, key_word):
        new_header = copy.deepcopy(HEADERS)
        new_header["referer"] = urllib.parse.quote(f"{BASE_URL}/s?q={key_word}", safe="/&=:?")
        hm_url = urllib.parse.quote(f"{BASE_URL}/user/hm.html?q={key_word}", safe="/&=:?")
        if not self.get_hm_cookie(hm_url):
            return []
        params = {"q": key_word}
        try:
            response = self.session.get(
                f"{BASE_URL}/user/search.html",
                params=params,
                headers=new_header,
                timeout=10,
            )
            return response.json()
        except Exception:
            return []

    def download_chapter(self, args):
        tag, href, index = args
        title = tag.text.strip()
        url = f"{BASE_URL}{href}"
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, "html.parser")
                text = soup.find(id="chaptercontent")
                if not text:
                    raise ValueError("未找到章节内容")
                content = [f"\n\n{title}\n\n"]
                # ⚠️ 完全保留原逻辑：split(" ")[1:-2]
                content.extend(f"{i}\n" for i in text.get_text().split(" ")[1:-2])
                return index, title, "".join(content)
            except Exception as e:
                if attempt == max_retries - 1:
                    return index, title, f"\n\n{title}\n\n下载失败: {str(e)}\n\n"
                time.sleep(1)
        return index, title, f"\n\n{title}\n\n下载失败\n\n"

    def download_novel_to_text(self, url, novel_name, author):
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            chapters = []
            index = 0
            # ========== 完全复制章节收集逻辑 ==========
            for tag in soup.select("div[class='listmain'] dl dd a"):
                href = tag["href"]
                if href == "javascript:dd_show()":
                    for hide_tag in soup.select("span[class='dd_hide'] dd a"):
                        chapters.append((hide_tag, hide_tag["href"], index))
                        index += 1
                else:
                    chapters.append((tag, href, index))
                    index += 1

            if not chapters:
                return False, "未找到章节", ""

            chapter_contents = {}
            max_workers = min(20, len(chapters))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_chapter = {
                    executor.submit(self.download_chapter, args): args
                    for args in chapters
                }
                for future in as_completed(future_to_chapter):
                    index, title, content = future.result()
                    if index is not None:
                        chapter_contents[index] = content

            # ========== 拼接顺序完全一致 ==========
            output_lines = [f"《{novel_name}》\n作者：{author}\n\n"]
            for i in range(len(chapter_contents)):
                output_lines.append(chapter_contents[i])
            return True, "成功", "".join(output_lines)

        except Exception as e:
            return False, str(e), ""

# ========== 暴露给 app.py 的接口 ==========
def search_novels(keyword):
    downloader = NovelDownloader()
    raw_results = downloader.search(keyword)
    # biqu.py 的 search 返回的是 list[dict]，直接返回即可
    return raw_results

def download_novel_to_text(novel_url, title, author):
    downloader = NovelDownloader()
    return downloader.download_novel_to_text(novel_url, title, author)
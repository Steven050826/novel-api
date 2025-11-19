# app.py
import os
from flask import Flask, request, jsonify
from biqu_core import search_novels, download_novel_to_text
from urllib.parse import urljoin

app = Flask(__name__)
BASE_URL = "https://www.qu02.cc"

# === 关键：让 jsonify 输出中文不转义 ===
app.config['JSON_AS_ASCII'] = False
# Flask 2.3+ 推荐方式（向下兼容）
app.json.ensure_ascii = False

@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "参数 q 不能为空"}), 400

    results = search_novels(keyword)
    return jsonify({
        "keyword": keyword,
        "count": len(results),
        "results": results
    })

@app.route("/download")
def download():
    url = request.args.get("url")
    title = request.args.get("title", "未知小说")
    author = request.args.get("author", "未知作者")

    if not url:
        return jsonify({"error": "参数 url 不能为空"}), 400

    # 补全绝对 URL
    if url.startswith("/"):
        url = urljoin(BASE_URL, url)

    try:
        success, msg, content = download_novel_to_text(url, title, author)
        if success:
            return jsonify({
                "success": True,
                "title": title,
                "author": author,
                "content_length": len(content),
                "content": content  # ⚠️ 注意：大文本可能影响性能
            })
        else:
            return jsonify({"success": False, "error": msg}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 健康检查
@app.route("/")
def hello():
    return "笔趣阁小说 API 正常运行！\nEndpoints: /search?q=... , /download?url=...&title=...&author=..."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
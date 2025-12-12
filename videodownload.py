from flask import Flask, request, Response, stream_with_context, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

app = Flask(__name__)

API_TEMPLATE = "https://savepinmedia.com/php/api/api.php?url={}"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

@app.route("/download")
def download():
    pin = request.args.get("url")
    if not pin:
        return jsonify({"error": "Missing url parameter"}), 400

    # 1. Fetch SavePinMedia HTML
    api_url = API_TEMPLATE.format(pin)
    html_resp = requests.get(api_url, headers=HEADERS)
    html = html_resp.text

    # 2. Parse HTML for <a href="/download.php?id=REAL_MP4">
    soup = BeautifulSoup(html, "html.parser")
    mp4_link = None

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "download.php?id=" in href and href.endswith(".mp4"):
            mp4_link = href.split("id=")[1]   # extract REAL v1.pinimg.com link
            break

    if not mp4_link:
        return jsonify({"error": "Real MP4 link not found"}), 500

    real_url = mp4_link  # example: https://v1.pinimg.com/videos/...mp4

    # 3. Download directly from v1.pinimg.com (works 100%)
    try:
        video_resp = requests.get(real_url, stream=True)
    except Exception as e:
        return jsonify({"error": "Failed to download from Pinterest", "exception": str(e)})

    if video_resp.status_code != 200:
        return jsonify({
            "error": "Pinterest MP4 returned error",
            "status": video_resp.status_code,
            "real_url": real_url
        }), 502

    # 4. Stream video to client
    filename = os.path.basename(urlparse(real_url).path)

    return Response(
        stream_with_context(video_resp.iter_content(chunk_size=8192)),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "video/mp4"
        },
        status=200
    )

if __name__ == "__main__":
    app.run(port=5555, debug=True)

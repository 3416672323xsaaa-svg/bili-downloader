from flask import Flask, request, render_template_string, jsonify, send_file
import yt_dlp
import threading
import os
import re
import uuid
import requests
import socket
from pathlib import Path

app = Flask(__name__)

DOWNLOAD_ROOT = Path(os.getenv("DOWNLOAD_ROOT", "/tmp/biliflow_downloads"))
DOWNLOAD_ROOT.mkdir(exist_ok=True, parents=True)

info_task = {}
download_task = {}

HTML_TPL = """
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#fb7299">
<title>BiliFlow · 视频下载器</title>
<style>
:root{
 --pink:#fb7299;--pink2:#ff4d83;--purple:#8b5cf6;--blue:#4f8cff;
 --ink:#121826;--muted:#7c8495;--line:#e9ecf2;--card:rgba(255,255,255,.82);
 --bg:#f6f7fb;--green:#18a66a;--shadow:0 22px 60px rgba(35,42,62,.10);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
 min-height:100vh;color:var(--ink);
 font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
 background:
 radial-gradient(650px 360px at 0% -5%,rgba(251,114,153,.22),transparent 65%),
 radial-gradient(520px 340px at 100% 0%,rgba(139,92,246,.16),transparent 65%),
 linear-gradient(180deg,#fff 0%,var(--bg) 48%,#f4f5f9 100%);
 padding:env(safe-area-inset-top) 14px calc(30px + env(safe-area-inset-bottom));
}
.app{max-width:560px;margin:auto}
.top{padding:20px 5px 18px;display:flex;justify-content:space-between;align-items:center}
.brand{display:flex;align-items:center;gap:12px}
.logo{
 width:50px;height:50px;border-radius:17px;display:grid;place-items:center;
 color:#fff;font-size:21px;font-weight:900;
 background:linear-gradient(145deg,#ff87aa,#fb7299 52%,#ff4d83);
 box-shadow:0 13px 28px rgba(251,114,153,.30);
 position:relative;overflow:hidden
}
.logo:after{content:"";position:absolute;width:80px;height:20px;background:rgba(255,255,255,.20);transform:rotate(-35deg);top:-20px;left:-25px}
.title{font-size:23px;font-weight:850;letter-spacing:-.6px}.subtitle{margin-top:3px;color:var(--muted);font-size:12px}
.pill{padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.72);border:1px solid var(--line);font-size:11px;color:#626b7c;backdrop-filter:blur(12px)}
.card{
 background:var(--card);border:1px solid rgba(225,229,237,.85);border-radius:25px;
 box-shadow:var(--shadow);backdrop-filter:blur(18px);padding:19px;margin-bottom:14px;
}
.hero{padding:21px}
.label{font-size:12px;font-weight:800;letter-spacing:.2px;color:#5e6778;margin-bottom:10px}
.inputbox{display:flex;align-items:center;gap:8px;background:#f8f9fc;border:1px solid #e7eaf0;border-radius:17px;padding:5px;transition:.2s}
.inputbox:focus-within{background:#fff;border-color:rgba(251,114,153,.6);box-shadow:0 0 0 5px rgba(251,114,153,.09)}
input{
 min-width:0;flex:1;border:0;outline:0;background:transparent;padding:12px 10px;
 color:var(--ink);font-size:16px
}
input::placeholder{color:#a4abba}
button{
 border:0;border-radius:14px;padding:13px 16px;font-size:15px;font-weight:800;
 cursor:pointer;color:#fff;background:linear-gradient(135deg,var(--pink),var(--pink2));
 box-shadow:0 9px 20px rgba(251,114,153,.23);transition:transform .12s,filter .12s
}
button:active{transform:scale(.98)}button:disabled{filter:grayscale(1);opacity:.5;box-shadow:none}
.parse{white-space:nowrap}
.tips{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}
.tip{font-size:11px;color:#6c7485;background:#f0f2f6;padding:6px 9px;border-radius:999px}
.status{display:flex;gap:11px;align-items:flex-start;padding:13px;border-radius:16px;background:#f7f8fa;color:#596274;font-size:13px;line-height:1.55}
.statusicon{width:28px;height:28px;border-radius:10px;display:grid;place-items:center;background:#fff0f4;color:#e64c75;font-weight:900;flex:none}
select{
 width:100%;appearance:none;border:1px solid var(--line);border-radius:16px;padding:14px 42px 14px 14px;
 font-size:15px;color:var(--ink);background:#f8f9fc;
 background-image:linear-gradient(45deg,transparent 50%,#8992a3 50%),linear-gradient(135deg,#8992a3 50%,transparent 50%);
 background-position:calc(100% - 19px) 19px,calc(100% - 14px) 19px;background-size:5px 5px;background-repeat:no-repeat
}
.download{width:100%;margin-top:10px}
.badge{display:inline-flex;align-items:center;gap:5px;margin-top:11px;font-size:11px;font-weight:750;color:#d94e74;background:#fff0f4;padding:6px 9px;border-radius:999px}
.taskhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px}.tasktitle{font-weight:850;font-size:16px}
.live{font-size:10px;font-weight:800;color:var(--green);background:#e9f8f1;border-radius:999px;padding:6px 8px}
.cover{display:none;width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:18px;margin-top:14px;box-shadow:0 10px 28px rgba(20,25,40,.12)}
.progressbox{background:#f7f8fa;border-radius:17px;padding:12px}
.pbar{height:10px;border-radius:99px;background:#e7eaf0;overflow:hidden}
.bar{height:100%;width:0;border-radius:99px;background:linear-gradient(90deg,#fb7299,#ff8eaa,#8b5cf6);transition:width .25s}
.pinfo{display:flex;justify-content:space-between;margin-top:8px;font-size:11px;color:#7b8495}
.log{margin-top:10px;background:#111620;color:#b9f6d3;border-radius:15px;padding:12px;font:11px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;max-height:145px;overflow:auto;white-space:pre-wrap}
.video{display:none;margin-top:12px}.video video{display:block;width:100%;border-radius:17px;background:#000}
.actions{display:none;gap:8px;margin-top:10px}.actions .half{flex:1}
.actions a{flex:1;text-decoration:none}.actions button{width:100%}
.secondary{background:#eef0f5;color:#3d4657;box-shadow:none}.green{background:linear-gradient(135deg,#20ad74,#138a59)}
.footer{text-align:center;color:#a0a7b4;font-size:11px;padding:6px 0 12px}
@media(max-width:420px){.top{padding-top:16px}.pill{display:none}.inputbox{display:block;padding:5px}.parse{width:100%;margin-top:3px}.actions{display:none!important}}
</style>
</head>
<body>
<div class="app">
 <header class="top">
  <div class="brand">
   <div class="logo">▶</div>
   <div><div class="title">BiliFlow</div><div class="subtitle">轻盈 · 快速 · 本地下载</div></div>
  </div>
  <div class="pill">B站视频工具</div>
 </header>

 <section class="card hero">
  <div class="label">粘贴视频链接</div>
  <form action="/getinfo" method="post">
   <div class="inputbox">
    <input name="bili_input" value="{{ bili_input }}" placeholder="BV号、AV号或 B站链接" autocomplete="off" spellcheck="false">
    <button class="parse" type="submit">解析</button>
   </div>
  </form>
  <div class="tips"><span class="tip">支持 BV / AV</span><span class="tip">自动识别清晰度</span><span class="tip">本地保存</span></div>
 </section>

 {% if msg %}
 <section class="card"><div class="status"><div class="statusicon">!</div><div>{{ msg }}</div></div></section>
 {% endif %}

 {% if qualities %}
 <section class="card">
  <div class="label">选择下载画质</div>
  <form action="/startdl" method="post">
   <input type="hidden" name="bili_input" value="{{ bili_input }}">
   <input type="hidden" name="url" value="{{ cached_url }}">
   <input type="hidden" name="avid_bvid" value="{{ avid_bvid }}">
   <input type="hidden" name="cover_url" value="{{ cover_url }}">
   <select name="quality">{% for q in qualities %}<option value="{{ q.fid }}">{{ q.label }}</option>{% endfor %}</select>
   <button class="download" type="submit">开始下载</button>
  </form>
  <span class="badge">✦ 已发现 {{ qualities|length }} 个可用选项</span>
 </section>
 {% endif %}

 {% if task_id %}
 <section class="card">
  <div class="taskhead"><div class="tasktitle">正在下载</div><div class="live" id="live">● WORKING</div></div>
  <div class="progressbox">
   <div class="pbar"><div class="bar" id="bar"></div></div>
   <div class="pinfo"><span id="prog_text">{{ percent }}%</span><span id="size_text">{{ size_info }}</span></div>
  </div>
  <div class="log" id="logBox">任务日志：{{ log }}</div>
  <img id="coverImg" class="cover">
  <div class="video" id="vidWrap"><video id="myvid" controls playsinline></video></div>
  <div class="actions" id="btn-group">
   <a href="/api/downloadfile?tid={{ task_id }}"><button type="button">保存视频</button></a>
   <button class="secondary half" type="button" onclick="playVideo('{{ task_id }}')">预览</button>
   <a href="/api/downloadcover?tid={{ task_id }}"><button class="green" type="button">保存封面</button></a>
  </div>
 </section>
 {% endif %}

 <div class="footer">仅用于下载你有权保存的视频内容</div>
</div>

<script>
const activeTaskId="{{task_id}}",coverSrc="{{cover_url}}";
if(activeTaskId)pollLoop();
async function pollLoop(){
 if(!activeTaskId)return;
 try{
  const r=await fetch("/api/status?tid="+encodeURIComponent(activeTaskId));
  const d=await r.json(),pct=Math.max(0,Math.min(100,parseFloat(d.percent)||0));
  const p=document.getElementById("prog_text"),b=document.getElementById("bar"),sz=document.getElementById("size_text"),log=document.getElementById("logBox");
  if(p)p.textContent=pct.toFixed(1)+"%"; if(b)b.style.width=pct+"%"; if(sz)sz.textContent=d.size_info||""; if(log)log.textContent="任务日志：\n"+(d.log||"");
  if(d.finished){
   const live=document.getElementById("live");if(live){live.textContent=d.ok?"● COMPLETED":"● FAILED";live.style.color=d.ok?"#18a66a":"#e64c4c";live.style.background=d.ok?"#e9f8f1":"#fff0f0"}
   if(d.ok){
    const actions=document.getElementById("btn-group");if(actions)actions.style.display="flex";
    if(coverSrc){const c=document.getElementById("coverImg");c.src=coverSrc;c.style.display="block"}
   }
   return;
  }
 }catch(e){}
 setTimeout(pollLoop,1200);
}
function playVideo(tid){
 const wrap=document.getElementById("vidWrap"),v=document.getElementById("myvid");
 wrap.style.display="block";v.src="/api/stream?tid="+encodeURIComponent(tid);v.play().catch(()=>{});
 wrap.scrollIntoView({behavior:"smooth",block:"center"});
}
</script>
</body>
</html>
"""


def get_free_port():
    # 让系统自动分配空闲端口
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def parse_input(raw_text):
    raw = raw_text.strip()
    bv_match = re.search(r'(BV[\w\d]{10})', raw, re.IGNORECASE)
    av_match = re.search(r'av(\d+)', raw, re.IGNORECASE)
    avid_bvid_label = ""
    if bv_match:
        avid_bvid_label = bv_match.group(1).upper()
        return f"https://www.bilibili.com/video/{bv_match.group(1)}", avid_bvid_label
    if av_match:
        avid_bvid_label = "av"+av_match.group(1)
        return f"https://www.bilibili.com/video/av{av_match.group(1)}", avid_bvid_label
    # 仅允许 Bilibili / b23.tv，避免公开部署后被当成通用远程下载代理。
    if re.match(r"^https?://(?:www\.)?bilibili\.com/", raw, re.IGNORECASE) or re.match(r"^https?://b23\.tv/", raw, re.IGNORECASE):
        return raw, ""
    return "", ""

def info_thread_func(task_uid, url):
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            cover_url = info.get("thumbnail","")
            formats = info.get('formats', [])
            video_streams = []
            for f in formats:
                h = f.get('height')
                fid = f.get('format_id')
                if not h or not fid or not isinstance(h, int):
                    continue
                vcodec = f.get('vcodec') or 'none'
                acodec = f.get('acodec') or 'none'
                ext = f.get('ext') or ''
                if vcodec == 'none':
                    continue
                # 优先展示有声音的完整流；没有完整流时也允许视频流，
                # 下载阶段再尝试自动寻找音频并合并。
                score = 2 if acodec != 'none' else 1
                video_streams.append({
                    "height": h, "fid": fid, "ext": ext,
                    "has_audio": acodec != "none", "score": score
                })
            if not video_streams:
                info_task[task_uid] = {"ok":False,"msg":"没有找到可下载的视频流，请检查链接、登录状态或稍后重试","cover":cover_url}
                return

            # 同一分辨率优先选择带声音的流，其次选择更适合下载的格式。
            best_by_height = {}
            for item in video_streams:
                key = item["height"]
                old_item = best_by_height.get(key)
                if old_item is None or (item["score"], item["ext"] == "mp4") > (old_item["score"], old_item["ext"] == "mp4"):
                    best_by_height[key] = item

            real_list = sorted(best_by_height.values(), key=lambda x:x["height"], reverse=True)
            qualities_ui = []
            for item in real_list:
                audio_text = "" if item["has_audio"] else "（下载时自动配音）"
                qualities_ui.append({
                    "label": f'{item["height"]}p{audio_text}',
                    "fid": item["fid"]
                })
            info_task[task_uid] = {"ok": True,"url": url,"qualities": qualities_ui,"cover":cover_url}
    except Exception as e:
        info_task[task_uid] = {"ok":False,"msg":str(e),"cover":""}

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TPL, msg="", bili_input="", cached_url="", qualities=[], task_id="", percent="0", size_info="0.00MB / 0.00MB", log="", finished=False, ok=False, avid_bvid="",cover_url="")

@app.route("/getinfo", methods=["POST"])
def route_getinfo():
    raw_input = request.form.get("bili_input","")
    target_url, avid_bvid = parse_input(raw_input)
    if not target_url:
        return render_template_string(HTML_TPL, msg="识别失败", bili_input=raw_input, cached_url="", qualities=[], task_id="", percent="0", size_info="0.00MB / 0.00MB", log="", finished=False, ok=False, avid_bvid=avid_bvid,cover_url="")
    tid = str(uuid.uuid4())
    t = threading.Thread(target=info_thread_func, args=(tid, target_url))
    t.start()
    t.join(timeout=15)
    res_data = info_task.pop(tid, None)
    cover = res_data.get("cover","") if res_data else ""
    if not res_data or not res_data["ok"]:
        err = res_data.get("msg","解析超时") if res_data else "解析超时"
        return render_template_string(HTML_TPL, msg=err, bili_input=raw_input, cached_url="", qualities=[], task_id="", percent="0", size_info="0.00MB / 0.00MB", log="", finished=False, ok=False, avid_bvid=avid_bvid,cover_url=cover)
    return render_template_string(HTML_TPL, msg="选择清晰度开始下载", bili_input=raw_input, cached_url=res_data["url"], qualities=res_data["qualities"], task_id="", percent="0", size_info="0.00MB / 0.00MB", log="", finished=False, ok=False, avid_bvid=avid_bvid,cover_url=res_data["cover"])

def hook(tid, info):
    if tid not in download_task:return
    status = info.get("status")
    if status == "downloading":
        total_bytes = info.get("total_bytes") or info.get("total_bytes_estimate") or 0
        downloaded_bytes = info.get("downloaded_bytes",0)
        download_task[tid]["total_bytes"] = total_bytes
        download_task[tid]["downloaded_bytes"] = downloaded_bytes
        if total_bytes>0:
            pct = round(downloaded_bytes / total_bytes *100,1)
            download_task[tid]["percent"] = str(pct)
            download_task[tid]["log"] = f"下载中 {downloaded_bytes/1048576:.2f}MB / {total_bytes/1048576:.2f}MB\n"
    elif status == "finished":
        download_task[tid]["percent"] = "100.0"
        download_task[tid]["log"] += "分片下载完成\n"

def download_worker(taskid, url, format_id, avid_bvid, cover_url):
    download_task[taskid] = {
        "percent": "0.0",
        "finished": False,
        "ok": False,
        "video_path": "",
        "cover_path":"",
        "cover_url":cover_url,
        "log": "任务启动\n",
        "total_bytes":0,
        "downloaded_bytes":0
    }
    custom_outtmpl = str(DOWNLOAD_ROOT / f"【{avid_bvid}】%(title)s.%(ext)s")
    # 优先使用用户选择的清晰度；如果该流失效，则让 yt-dlp 自动回退。
    # B站常见 DASH 情况需要视频+音频合并，因此同时提供 fallback。
    fallback_format = (
        f"{format_id}+bestaudio[ext=m4a]/"
        f"{format_id}+bestaudio/"
        f"{format_id}/"
        "best[ext=mp4]/best"
    )
    ydl_opts = {
        "outtmpl": custom_outtmpl,
        "quiet": False,
        "no_warnings": False,
        "format": fallback_format,
        "merge_output_format": "mp4",
        "retries": 5,
        "fragment_retries": 5,
        "file_access_retries": 3,
        "retry_sleep": {"http": 2, "fragment": 2},
        "socket_timeout": 30,
        "continuedl": True,
        "noplaylist": True,
        "progress_hooks": [lambda info: hook(taskid, info)]
    }
    try:
        download_task[taskid]["log"] += "使用音画合一mp4流下载\n"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fp = ydl.prepare_filename(info)
            download_task[taskid]["video_path"] = fp
            download_task[taskid]["log"] += f"输出文件:{fp}\n"
            if os.path.exists(fp):
                real_size = os.path.getsize(fp)
                download_task[taskid]["downloaded_bytes"] = real_size
                download_task[taskid]["total_bytes"] = real_size
                download_task[taskid]["ok"] = True
                download_task[taskid]["log"] += "✅视频文件保存成功\n"
        #封面单独下载保存
        if cover_url:
            cover_save = DOWNLOAD_ROOT / f"【{avid_bvid}】cover.jpg"
            r = requests.get(cover_url,timeout=20)
            with open(cover_save,"wb")as f:
                f.write(r.content)
            download_task[taskid]["cover_path"] = str(cover_save)
            download_task[taskid]["log"] += "✅封面图片已保存\n"
    except Exception as e:
        err = str(e)
        if "ffmpeg" in err.lower():
            err += "\n提示：当前环境缺少 FFmpeg，无法把视频和音频合并成 MP4。"
        elif "403" in err or "Forbidden" in err:
            err += "\n提示：视频地址已过期或需要登录/Cookie，请重新解析后立即下载。"
        elif "login" in err.lower() or "sign in" in err.lower():
            err += "\n提示：该视频可能需要登录后才能下载。"
        download_task[taskid]["log"] += f"❌下载失败：{err}\n"
    finally:
        download_task[taskid]["finished"] = True

@app.route("/startdl", methods=["POST"])
def route_startdl():
    bili_input = request.form.get("bili_input","")
    url = request.form.get("url","")
    format_id = request.form.get("quality","")
    avid_bvid = request.form.get("avid_bvid","")
    cover_url = request.form.get("cover_url","")
    if not url or not format_id:
        return render_template_string(HTML_TPL, msg="参数缺失", bili_input=bili_input, cached_url=url, qualities=[], task_id="", percent="0", size_info="0.00MB / 0.00MB", log="", finished=False, ok=False, avid_bvid=avid_bvid,cover_url=cover_url)
    tid = str(uuid.uuid4())
    t = threading.Thread(target=download_worker, args=(tid, url, format_id, avid_bvid, cover_url))
    t.start()
    return render_template_string(HTML_TPL, msg="已启动下载", bili_input=bili_input, cached_url=url, qualities=[], task_id=tid, percent="0.0", size_info="0.00MB / 0.00MB", log="任务启动", finished=False, ok=False, avid_bvid=avid_bvid,cover_url=cover_url)

@app.route("/api/status")
def api_status():
    tid = request.args.get("tid","")
    item = download_task.get(tid)
    if not item:
        return jsonify({"percent":"0.0","finished":True,"ok":False,"size_info":"0.00MB / 0.00MB","log":"任务不存在"})
    size_info = f"{item['downloaded_bytes']/1048576:.2f}MB / {item['total_bytes']/1048576:.2f}MB"
    return jsonify({
        "percent":item.get("percent","0.0"),
        "finished":item.get("finished"),
        "ok":item.get("ok"),
        "size_info":size_info,
        "log":item.get("log","")
    })

@app.route("/api/stream")
def api_stream():
    tid = request.args.get("tid","")
    item = download_task.get(tid,{})
    p = item.get("video_path","")
    if not p or not os.path.exists(p):
        return "404",404
    return send_file(p)

@app.route("/api/downloadfile")
def api_dlfile():
    tid = request.args.get("tid","")
    item = download_task.get(tid, {})
    p = item.get("video_path","")
    if not p or not os.path.exists(p):
        return "视频文件不存在",404
    return send_file(p, as_attachment=True)

@app.route("/api/downloadcover")
def api_downloadcover():
    tid = request.args.get("tid","")
    item = download_task.get(tid, {})
    p = item.get("cover_path","")
    if not p or not os.path.exists(p):
        return "封面文件不存在",404
    return send_file(p, as_attachment=True)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    print(f"BiliFlow listening on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

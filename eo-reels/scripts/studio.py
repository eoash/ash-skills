"""The work screen: transcript on the left, title and script in the middle, video and chat on the right.
One interview can hold many reels, each with its own script, versions and chat. A small local server holds the screen's state. Claude does the work and talks to the server with the commands below.

usage: studio.py serve   <project>                 run the server (start it in the background)
       studio.py open    <project>                 open the screen in the default browser, print its address
       studio.py wait    <project>                 block until the person asks for something, print it as JSON
       studio.py status  <project> "<text>"        show what is happening now above the video
       studio.py say     <project> "<text>"        add a Claude message to the chat
       studio.py publish <project> <config> <mp4>  show this render in the player as a new version
say and publish go to the reel of the request being worked on.

Only this machine can reach the server, and every request needs the secret in the screen's address, so another
website open in the same browser cannot send requests to it."""
import glob, http.server, json, os, re, secrets, shutil, socket, subprocess, sys, threading, time, urllib.error, urllib.parse, urllib.request

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
MAX_BODY = 1 << 20
LISTEN_SECONDS = 20  # one long poll from `wait`; the person's request wakes it sooner
HOST = "127.0.0.1"


def paths(project):
    d = os.path.join(os.path.abspath(project), "studio")
    return dict(dir=d, server=f"{d}/server.json", state=f"{d}/state.json", videos=f"{d}/videos")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def headline_lines(title):
    if isinstance(title, list):
        return [str(x).strip() for x in title if str(x).strip()]
    return [x.strip() for x in re.split(r"[/\n]", title or "") if x.strip()]


def file_name(title):
    name = " - ".join(headline_lines(title)) or "EO 릴스"
    return re.sub(r'[\\:*?"<>|\x00-\x1f]', "", name)[:120] + ".mp4"


def new_reel(rid):
    return dict(id=rid, draft=dict(title="", script="", rev=0), messages=[], versions=[], selected=None, unseen=False)


class Studio:
    """One interview holds many reels. Each reel keeps its own title, script, versions and chat."""

    def __init__(self, project):
        self.project = os.path.abspath(project)
        self.p = paths(project)
        os.makedirs(self.p["videos"], exist_ok=True)
        self.lock = threading.Condition()
        self.s = read_json(self.p["state"]) or dict(
            reels=[new_reel(1)], shown=1, next_reel=2, queue=[], current=None, status="", seen=0, activity=0, next_id=1)

    def save(self):
        write_json(self.p["state"], self.s)

    def reel(self, rid):
        r = next((r for r in self.s["reels"] if r["id"] == rid), None)
        if not r:
            raise ValueError(f"no such reel: {rid}")
        return r

    def video_path(self, rid, n, ext="mp4"):
        return f'{self.p["videos"]}/r{rid}-v{n}.{ext}'

    # what the screen asks for
    def state(self):
        with self.lock:
            s, now = self.s, time.time()
            cur = s["current"]
            agent = "working" if cur else "listening" if now - s["seen"] < LISTEN_SECONDS * 2 else "away"
            queued = {e["reel"] for e in s["queue"]}
            job = cur["reel"] if cur else None
            r = self.reel(s["shown"])
            return dict(
                reel={k: r[k] for k in ("id", "draft", "messages", "versions", "selected")},
                reels=[dict(id=x["id"], title=(x["draft"]["title"].strip().split("\n") or [""])[0], unseen=x["unseen"],
                            busy=x["id"] == job or x["id"] in queued) for x in s["reels"]],
                job_reel=job, queued_here=r["id"] in queued, status=s["status"], agent=agent,
                working_for=int(now - cur["started"]) if cur else 0, quiet_for=int(now - s["activity"]) if cur else 0,
                transcript=self.transcript_stamp())

    def transcript_stamp(self):
        try:
            return os.path.getmtime(f"{self.project}/transcript.json")
        except OSError:
            return 0

    def set_draft(self, rid, title, script):
        with self.lock:
            d = self.reel(rid)["draft"]
            d.update(title=title, script=script, rev=d["rev"] + 1)
            self.save()
            return d["rev"]

    def show_reel(self, rid):
        with self.lock:
            r = self.reel(rid)
            self.s["shown"], r["unseen"] = rid, False
            self.save()

    def add_reel(self):
        with self.lock:
            s = self.s
            r = next((x for x in s["reels"] if not (x["draft"]["title"].strip() or x["draft"]["script"].strip() or x["versions"])), None)
            if not r:  # an untouched reel is reused, so clicking twice does not leave empty tabs behind
                r = new_reel(s["next_reel"])
                s["next_reel"] += 1
                s["reels"].append(r)
            s["shown"] = r["id"]
            self.save()

    def delete_reel(self, rid):
        """Remove a reel and its videos. Refused while Claude has a request for it, because that request would lose its target."""
        with self.lock:
            s = self.s
            r = self.reel(rid)
            if (s["current"] and s["current"]["reel"] == rid) or any(e["reel"] == rid for e in s["queue"]):
                raise ValueError("this reel has a request in progress")
            i = s["reels"].index(r)
            s["reels"].remove(r)
            if not s["reels"]:  # the screen always has a reel to type into
                s["reels"].append(new_reel(s["next_reel"]))
                s["next_reel"] += 1
            if s["shown"] == rid:
                s["shown"] = s["reels"][min(i, len(s["reels"]) - 1)]["id"]
            self.save()
        for path in glob.glob(glob.escape(self.p["videos"]) + f"/r{rid}-v*"):
            os.remove(path)
        for path in (f"{self.project}/reel-{rid}.json", f"{self.project}/build/reel-{rid}.mp4", f"{self.project}/build/reel-{rid}-preview.jpg"):
            if os.path.exists(path):
                os.remove(path)
        shutil.rmtree(f"{self.project}/build/reel-{rid}", ignore_errors=True)

    def pick_version(self, rid, n):
        with self.lock:
            r = self.reel(rid)
            v = next((v for v in r["versions"] if v["n"] == n), None)
            if not v:
                raise ValueError(f"no such version: {n}")
            d = r["draft"]
            d.update(title=v["title"], script=v["script"], rev=d["rev"] + 1)
            r["selected"] = n
            self.save()
            return d["rev"]

    def request(self, rid, kind, title, script, text, version):
        with self.lock:
            s = self.s
            r = self.reel(rid)
            d = r["draft"]
            d.update(title=title, script=script, rev=d["rev"] + 1)
            base = next((v for v in r["versions"] if v["n"] == version), None)
            event = dict(id=s["next_id"], type=kind, reel=rid, title=title, script=script, rev=d["rev"],
                         config=f"{self.project}/reel-{rid}.json", mp4=f"{self.project}/build/reel-{rid}.mp4",
                         base_version=base["n"] if base else None,
                         base_config=self.video_path(rid, base["n"], "json") if base else None)
            s["next_id"] += 1
            if kind == "chat":
                event["text"] = text
                r["messages"].append(dict(who="user", text=text, at=time.time()))
            s["queue"].append(event)
            self.save()
            self.lock.notify_all()
            return d["rev"]

    # what Claude asks for
    def next_event(self):
        with self.lock:
            s = self.s
            s["seen"] = time.time()
            s["current"], s["status"] = None, ""  # asking for more means the last request is finished
            self.save()
            end = time.time() + LISTEN_SECONDS
            while not s["queue"]:
                left = end - time.time()
                if left <= 0:
                    s["seen"] = time.time()
                    return None
                self.lock.wait(left)
            event = s["queue"].pop(0)
            now = time.time()
            s["current"] = dict(event, started=now)
            s["seen"] = s["activity"] = now
            s["status"] = "대본을 음성에 맞추는 중이에요" if event["type"] == "render" else "요청을 살펴보는 중이에요"
            self.save()
            return event

    def set_status(self, text):
        with self.lock:
            self.s["status"], self.s["seen"], self.s["activity"] = text, time.time(), time.time()
            self.save()

    def target(self):
        """The reel Claude is working on, or the one on screen when it is between requests."""
        cur = self.s["current"]
        return self.reel(cur["reel"] if cur else self.s["shown"])

    def touched(self, r):
        now = time.time()
        self.s["seen"] = self.s["activity"] = now
        if r["id"] != self.s["shown"]:
            r["unseen"] = True
        return now

    def say(self, text):
        with self.lock:
            r = self.target()
            r["messages"].append(dict(who="claude", text=text, at=self.touched(r)))
            self.save()

    def publish(self, config, mp4):
        cfg = read_json(config)
        if not cfg:
            raise ValueError(f"cannot read {config}")
        if not os.path.isfile(mp4):
            raise ValueError(f"no such video: {mp4}")
        with self.lock:
            r = self.target()
            n = max((v["n"] for v in r["versions"]), default=0) + 1
        shutil.copyfile(mp4, self.video_path(r["id"], n))
        shutil.copyfile(config, self.video_path(r["id"], n, "json"))
        title = "\n".join(headline_lines(cfg.get("headline")))
        script = "\n".join(c["t"].replace("\n", " ") for c in cfg.get("caps", []))
        seconds = round(sum(b - a for a, b in cfg.get("pieces", [])), 1)
        with self.lock:
            now = self.touched(r)
            r["versions"].append(dict(n=n, title=title, script=script, seconds=seconds, at=now, name=file_name(title)))
            r["selected"] = n
            d, cur = r["draft"], self.s["current"]
            if not cur or d["rev"] == cur["rev"]:  # keep anything the person typed while this was rendering
                d.update(title=title, script=script, rev=d["rev"] + 1)
            self.save()
        return n


def make_handler(studio, token):
    page = os.path.join(ASSETS, "studio.html")
    allowed = None  # set once the port is known

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def send(self, code, body=b"", kind="application/json; charset=utf-8", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, data, code=200):
            self.send(code, json.dumps(data, ensure_ascii=False).encode())

        def trusted(self, query):
            nonlocal allowed
            if allowed is None:
                port = self.server.server_address[1]
                allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host") not in allowed:  # refuses DNS rebinding
                return False
            given = self.headers.get("X-Studio-Token") or (query.get("t") or [""])[0]
            return secrets.compare_digest(given.encode(), token.encode())

        def body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("too large")
            return json.loads(self.rfile.read(n) or b"{}")

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(url.query)
            if not self.trusted(query):
                return self.send(403, "이 주소로는 열 수 없어요. Claude가 알려준 주소로 열어 주세요.".encode(), "text/plain; charset=utf-8")
            if url.path == "/":
                with open(page, "rb") as f:
                    return self.send(200, f.read(), "text/html; charset=utf-8", {
                        "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                                                   "img-src 'self' data:; frame-ancestors 'none'"})
            if url.path == "/api/state":
                return self.send_json(studio.state())
            if url.path == "/api/transcript":
                return self.send_json(read_json(f"{studio.project}/transcript.json"))
            m = re.fullmatch(r"/(media|download)/(\d+)/(\d+)", url.path)
            if m:
                return self.video(int(m[2]), int(m[3]), m[1] == "download")
            self.send(404, b"{}")

        def video(self, rid, n, attach):
            reel = next((r for r in studio.s["reels"] if r["id"] == rid), None)
            v = next((v for v in reel["versions"] if v["n"] == n), None) if reel else None
            path = studio.video_path(rid, n)
            if not v or not os.path.isfile(path):
                return self.send(404, b"{}")
            size = os.path.getsize(path)
            start, end = 0, size - 1
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
            if m and (m[1] or m[2]):
                if m[1]:
                    start = int(m[1]); end = min(int(m[2]), size - 1) if m[2] else size - 1
                else:
                    start = max(size - int(m[2]), 0)
                if start > end:
                    return self.send(416, b"", extra={"Content-Range": f"bytes */{size}"})
            self.send_response(206 if m and (m[1] or m[2]) else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Cache-Control", "no-store")
            if m and (m[1] or m[2]):
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            if attach:
                self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + urllib.parse.quote(v["name"]))
            self.end_headers()
            if self.command == "HEAD":
                return
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                try:
                    while left > 0:
                        chunk = f.read(min(1 << 16, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    self.close_connection = True

        def do_POST(self):
            url = urllib.parse.urlsplit(self.path)
            # POST takes the secret from the header only, so a form on another site cannot submit one
            if not self.trusted({}) or not self.headers.get("X-Studio-Token"):
                return self.send(403, b"{}")
            try:
                b = self.body()
                return self.route(url.path, b)
            except (ValueError, KeyError, TypeError) as e:
                return self.send_json(dict(error=str(e)), 400)

        def route(self, path, b):
            if path == "/api/draft":
                return self.send_json(dict(rev=studio.set_draft(int(b["reel"]), str(b["title"]), str(b["script"]))))
            if path == "/api/reel/show":
                studio.show_reel(int(b["reel"]))
                return self.send_json({})
            if path == "/api/reel/add":
                studio.add_reel()
                return self.send_json({})
            if path == "/api/reel/delete":
                studio.delete_reel(int(b["reel"]))
                return self.send_json({})
            if path == "/api/version":
                return self.send_json(dict(rev=studio.pick_version(int(b["reel"]), int(b["n"]))))
            if path == "/api/request":
                kind = b["type"]
                if kind not in ("render", "chat"):
                    raise ValueError("unknown request")
                text = str(b.get("text") or "").strip()
                if kind == "chat" and not text:
                    raise ValueError("empty message")
                rev = studio.request(int(b["reel"]), kind, str(b.get("title") or ""), str(b.get("script") or ""), text, b.get("version"))
                return self.send_json(dict(rev=rev))
            if path == "/agent/wait":
                return self.send_json(dict(event=studio.next_event()))
            if path == "/agent/status":
                studio.set_status(str(b["text"]))
                return self.send_json({})
            if path == "/agent/say":
                studio.say(str(b["text"]))
                return self.send_json({})
            if path == "/agent/publish":
                return self.send_json(dict(version=studio.publish(b["config"], b["mp4"])))
            self.send(404, b"{}")

    return Handler


def address(project):
    info = read_json(paths(project)["server"])
    return (f'http://127.0.0.1:{info["port"]}/?t={info["token"]}', info) if info else (None, None)


def call(project, route, data=None, timeout=10):
    url, info = address(project)
    if not url:
        raise OSError("server not started")
    req = urllib.request.Request(f'http://127.0.0.1:{info["port"]}{route}', json.dumps(data or {}).encode(),
                                 {"X-Studio-Token": info["token"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def running(project):
    try:
        call(project, "/agent/status_ping", timeout=2)
    except urllib.error.HTTPError as e:
        return e.code == 404
    except (OSError, ValueError):
        return False
    return True


def serve(project):
    if running(project):
        print(address(project)[0])
        return
    studio = Studio(project)
    old = read_json(studio.p["server"]) or {}
    token = old.get("token") or secrets.token_urlsafe(24)
    http.server.ThreadingHTTPServer.daemon_threads = True
    try:
        srv = http.server.ThreadingHTTPServer((HOST, old.get("port") or 0), make_handler(studio, token))
    except OSError:  # the old port is taken
        srv = http.server.ThreadingHTTPServer((HOST, 0), make_handler(studio, token))
    write_json(studio.p["server"], dict(port=srv.server_address[1], token=token))
    os.chmod(studio.p["server"], 0o600)
    print(address(project)[0], flush=True)
    srv.serve_forever()


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, project = sys.argv[1:3]
    args = sys.argv[3:]
    if cmd == "serve":
        return serve(project)
    if cmd == "open":
        for _ in range(50):
            if running(project):
                url = address(project)[0]
                subprocess.run(["open", url], check=False)
                return print(url)
            time.sleep(0.2)
        sys.exit("The work screen server is not running. Start it with: studio.py serve <project>")
    if cmd == "wait":
        while True:
            try:
                event = call(project, "/agent/wait", timeout=LISTEN_SECONDS + 15)["event"]
            except socket.timeout:
                continue
            except urllib.error.URLError as e:
                if isinstance(e.reason, socket.timeout):
                    continue
                sys.exit(f"The work screen server is not running ({e.reason}). Start it again with: studio.py serve <project>")
            if event:
                return print(json.dumps(event, ensure_ascii=False, indent=1))
    if cmd == "status":
        return call(project, "/agent/status", dict(text=args[0]))
    if cmd == "say":
        return call(project, "/agent/say", dict(text=args[0]))
    if cmd == "publish":
        n = call(project, "/agent/publish", dict(config=os.path.abspath(args[0]), mp4=os.path.abspath(args[1])), timeout=120)
        return print("version", n["version"])
    sys.exit(__doc__)


if __name__ == "__main__":
    main()

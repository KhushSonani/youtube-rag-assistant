import urllib.request, json

data = json.dumps({
    "question": "What is the main topic of this video?",
    "video_id": "Gfr50f6ZBvo"
}).encode()

req = urllib.request.Request(
    "http://127.0.0.1:8000/ask",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req, timeout=90) as r:
    for line in r:
        line = line.decode().strip()
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[6:])
        if payload["type"] == "token":
            print(payload["content"], end="", flush=True)
        elif payload["type"] == "sources":
            print()
            print("\nSOURCES:")
            for s in payload["sources"]:
                print(f"  {s['formatted']} -> {s['url']}")
        elif payload["type"] == "done":
            print("\n[DONE]")
            break

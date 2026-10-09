import os
import re
import httpx
import base64
from fastapi import FastAPI, Query, Response, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vidmoly Config
VIDMOLY_DOMAINS = ["vidmoly.to", "vidmoly.me", "vidmoly.net", "vidmoly.org"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://vidmoly.to/",
}

@app.get("/")
def root():
    return {"status": "Live", "mode": "Koyeb Dynamic Proxy", "usage": "/v.m3u8?id=VIDEO_ID"}

@app.get("/v.m3u8")
async def permanent_stream(request: Request, id: str = Query(...)):
    # Si otomaatig ah u ogow hostname-ka Koyeb ama meel kasta uu joogo
    hostname = request.url.netloc
    base_proxy_url = f"https://{hostname}"
    
    video_url = None
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        for domain in VIDMOLY_DOMAINS:
            try:
                test_url = f"https://{domain}/embed-{id}.html"
                resp = await client.get(test_url)
                if resp.status_code == 200:
                    links = re.findall(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', resp.text)
                    if links:
                        video_url = links[0]
                        break
            except: continue
    
    if not video_url:
        return Response(content="Error: Video not found", status_code=404)

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
            resp_m3u8 = await client.get(video_url)
            content = resp_m3u8.text
            base_url = video_url.rsplit('/', 1)[0]
            
            new_content = ""
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    full_url = line if line.startswith('http') else f"{base_url}/{line}"
                    encoded = base64.urlsafe_b64encode(full_url.encode()).decode().replace('=', '')
                    route = "proxy.m3u8" if ".m3u8" in line.lower() else "stream"
                    new_content += f"{base_proxy_url}/{route}?data={encoded}\n"
                else:
                    new_content += line + "\n"
            
            return Response(content=new_content, media_type="application/vnd.apple.mpegurl")
    except Exception as e:
        return Response(content=str(e), status_code=500)

@app.get("/proxy.m3u8")
async def proxy_sub_m3u8(request: Request, data: str = Query(...)):
    hostname = request.url.netloc
    base_proxy_url = f"https://{hostname}"
    
    padding = '=' * (4 - len(data) % 4) if len(data) % 4 else ''
    url = base64.urlsafe_b64decode(data + padding).decode()
    
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(url)
        content = resp.text
        base_url = url.rsplit('/', 1)[0]
        new_content = ""
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                full_url = line if line.startswith('http') else f"{base_url}/{line}"
                encoded = base64.urlsafe_b64encode(full_url.encode()).decode().replace('=', '')
                new_content += f"{base_proxy_url}/stream?data={encoded}\n"
            else:
                new_content += line + "\n"
        return Response(content=new_content, media_type="application/vnd.apple.mpegurl")

@app.get("/stream")
async def stream(request: Request, data: str = Query(...)):
    try:
        padding = '=' * (4 - len(data) % 4) if len(data) % 4 else ''
        url = base64.urlsafe_b64decode(data + padding).decode()
        
        # Range Support: Muhiim u ah inuu video-ga bilaawdo (ArtPlayer)
        range_header = request.headers.get("range")
        fetch_headers = {**HEADERS}
        if range_header:
            fetch_headers["range"] = range_header

        async def generate():
            async with httpx.AsyncClient(headers=fetch_headers, timeout=60) as client:
                async with client.stream("GET", url) as r:
                    async for chunk in r.aiter_bytes(chunk_size=32768):
                        yield chunk
        return StreamingResponse(generate(), media_type="video/MP2T")
    except: return Response(status_code=500)

if __name__ == "__main__":
    import uvicorn
    # Koyeb iyo meelaha kaleba waxay isticmaalaan PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

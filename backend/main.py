import os
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import glob
from backend.generator import generate_cardnews_job
import uuid
from fastapi import BackgroundTasks

app = FastAPI(title="CardNews API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

tasks_progress = {}

def update_progress(task_id, message, panel_url=None):
    if task_id in tasks_progress:
        tasks_progress[task_id]["message"] = message
        if panel_url:
            if "panels" not in tasks_progress[task_id]:
                tasks_progress[task_id]["panels"] = []
            tasks_progress[task_id]["panels"].append(panel_url)

def background_process(task_id: str, text_prompt: str):
    try:
        def callback(msg, panel_url=None):
            update_progress(task_id, msg, panel_url)
            
        output_folder = generate_cardnews_job(text_prompt, callback)
        panels = tasks_progress.get(task_id, {}).get("panels", [])
        folder_name = os.path.basename(output_folder)
        
        tasks_progress[task_id] = {
            "status": "completed",
            "message": "생성 완료",
            "final_image_url": f"/output/{folder_name}/final_webtoon_9x16.png",
            "video_url": f"/output/{folder_name}/video_reels_9x16.mp4",
            "folder_name": folder_name,
            "panels": panels
        }
    except Exception as e:
        print(f"Error in task {task_id}: {e}")
        tasks_progress[task_id] = {
            "status": "error",
            "message": str(e)
        }

@app.post("/api/generate")
async def generate_webtoon(background_tasks: BackgroundTasks, text_prompt: str = Form(...)):
    try:
        task_id = str(uuid.uuid4())
        tasks_progress[task_id] = {"status": "processing", "message": "작업 대기 중...", "panels": []}
        background_tasks.add_task(background_process, task_id, text_prompt)
        return JSONResponse(content={"success": True, "task_id": task_id})
    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id not in tasks_progress:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return JSONResponse(content=tasks_progress[task_id])

@app.get("/api/webtoons")
async def get_webtoons():
    try:
        webtoons = []
        for folder in sorted(glob.glob(os.path.join(OUTPUT_DIR, "*")), reverse=True):
            if os.path.isdir(folder):
                folder_name = os.path.basename(folder)
                final_img_path = os.path.join(folder, "final_webtoon_9x16.png")
                if os.path.exists(final_img_path):
                    video_path = os.path.join(folder, "video_reels_9x16.mp4")
                    webtoons.append({
                        "id": folder_name,
                        "thumbnail_url": f"/output/{folder_name}/final_webtoon_9x16.png",
                        "video_url": f"/output/{folder_name}/video_reels_9x16.mp4" if os.path.exists(video_path) else "",
                        "created_at": folder_name
                    })
        return JSONResponse(content={"webtoons": webtoons})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

# Mount assets explicitly to avoid catching them in the catch-all
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Allow serving other files in dist like favicon.ico, manifest.json, etc.
    file_path = os.path.join(FRONTEND_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # Default to serving index.html for SPA routing
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"detail": "Frontend not built or index.html not found"})

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="智能药盒管理系统", version="1.3 完整版")

from api.box_api import router
app.include_router(router)

@app.get("/", tags=["default"])
def root():
    return {"msg": "智能药盒后端运行正常"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
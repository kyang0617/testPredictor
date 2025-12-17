from fastapi import FastAPI

app = FastAPI(title="Backend API Template")

@app.get("/health")
def health():
    return {"ok": True}

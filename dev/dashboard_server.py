import time, sys
try:
    from fastapi import FastAPI
    import uvicorn
    app=FastAPI()
    @app.get("/health")
    def health(): return {"ok":True}
    @app.get("/metrics")
    def metrics(): return {"hint":"see reports/metrics.json"}
    if __name__=="__main__":
        uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
except Exception:
    if __name__=="__main__":
        print("dashboard skipped (deps missing)"); time.sleep(2)

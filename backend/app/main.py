from fastapi import FastAPI

app = FastAPI(title="MerryMapped")


@app.get("/health")
def health():
    """Report that the backend is running."""
    return {"status": "ok"}

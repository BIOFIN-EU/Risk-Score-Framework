from fastapi import FastAPI

# Create FastAPI instance
app = FastAPI(
    title="Risk Framework API",
    description="API for biodiversity risk assessment",
    version="0.1.0",
)

@app.get("/")
async def hello_world():
    """
    Hello World endpoint.

    Returns a simple greeting message.
    """
    return {"message": "Hello World"}

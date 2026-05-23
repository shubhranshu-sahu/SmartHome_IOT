from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Smart Home IoT Backend")

# Allow frontend/browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
def health():

    return {
        "status": "ok",
        "message": "Backend running"
    }

# ESP32 sends sensor/device data here
@app.post("/device-data")
async def device_data(data: dict):

    print("\n========= DEVICE DATA =========")
    print(data)
    print("================================\n")

    return {
        "success": True,
        "received": data
    }
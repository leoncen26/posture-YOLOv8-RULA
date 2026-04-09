# posture-YOLOv8-RULA

Real-time sitting posture detection using YOLOv8-Pose with RULA-based scoring for table-manner analysis.

## Project Structure

- `backend/`: Flask API, YOLOv8-Pose inference, RULA scoring, camera stream
- `frontend/`: React + Vite web UI

## Prerequisites

Install these first:

- Python 3.10+ (recommended: 3.11 or 3.12)
- Node.js 18+ and npm
- Webcam access enabled

Also make sure the model file exists:

- `backend/yolov8n-pose.pt`

## 1) Clone the Repository

```powershell
git clone <YOUR_REPO_URL>
cd posture-RULA-web
```

## 2) Backend Setup (Flask + YOLO)

Open terminal in project root, then:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Run backend:

```powershell
python app.py
```

Backend will run at:

- `http://localhost:5000`

Useful backend endpoints:

- `GET /status`
- `GET /video`
- `GET /rula_data`
- `POST /start`
- `POST /stop`

## 3) Frontend Setup (React + Vite)

Open a second terminal in project root, then:

```powershell
cd frontend
npm install
npm run dev
```

Frontend will run at:

- `http://localhost:5173`

## 4) Run Both Together

You need 2 terminals running at the same time:

1. Terminal A:

```powershell
cd backend
venv\Scripts\activate
python app.py
```

2. Terminal B:

```powershell
cd frontend
npm run dev
```

Then open the frontend URL in browser and click the webcam start button.

## Quick Verification Checklist

- Backend terminal shows Flask started without import errors
- Frontend page loads without build errors
- Camera starts from UI
- Video stream appears
- RULA scores and FPS update in real-time

## Common Issues

- `ModuleNotFoundError`: activate backend venv and re-run `pip install -r requirements.txt`
- Camera cannot open: close other apps using webcam and allow OS/browser camera permission
- Frontend cannot fetch data: confirm backend is running on port `5000`
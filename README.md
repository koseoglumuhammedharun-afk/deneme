# 🎯 Drone Howitzer Detection System

A professional-grade Python application that detects concealed howitzer models in drone imagery using YOLOv8 object detection, extracts metadata, estimates locations, and generates automated reports.

## ✨ Features

- **🖼️ Multi-Format Support**: Analyze JPEG, PNG images and MP4 video files
- **🤖 Advanced Detection**: YOLOv8-based neural network for accurate howitzer identification
- **📍 Metadata Extraction**: Captures EXIF data (date, time, GPS) from images and video metadata
- **⏱️ Video Analysis**: Frame-by-frame analysis with detection timestamp (MM:SS format)
- **📊 Automated Reporting**: Generate Excel and JSON reports with detailed analysis results
- **🎨 Modern GUI**: PyQt5 user interface with preview, crop viewer, and real-time progress
- **🔍 Confidence Threshold**: Adjustable detection sensitivity (0-100%)
- **📋 Comprehensive Logging**: Real-time analysis status and error tracking

## 📋 Requirements

- Python 3.8+
- 8GB RAM recommended (4GB minimum)
- CUDA-capable GPU optional (will use CPU fallback)
- Disk space: ~500MB for dependencies + ~100MB for model

## 🚀 Installation

### 1. Clone/Create Project
```bash
cd /path/to/project
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- **opencv-python**: Image/video processing
- **torch + torchvision**: Deep learning framework
- **ultralytics**: YOLOv8 implementation
- **PyQt5**: GUI framework
- **pandas + openpyxl**: Excel export
- **exifread**: EXIF metadata extraction
- **numpy**: Numerical computing
- **pillow**: Image manipulation

### 3. Prepare Model
Place your trained YOLOv8 howitzer model at:
```
models/howitzer_detector.pt
```

**Note**: The application will use a general YOLOv8n model as fallback if custom model not found.

### 4. Run Application
```bash
python main.py
```

## 📖 Usage Guide

### Step 1: Load File
1. Click **"Browse & Upload File"** button
2. Select an image (.jpg, .png) or video (.mp4)
3. File preview appears automatically

### Step 2: Configure Analysis
- Adjust **Confidence Threshold** slider (default: 0.5)
  - Lower = more detections (higher false positives)
  - Higher = fewer detections (higher accuracy)

### Step 3: Run Analysis
1. Click **"Start Analysis"** button
2. For videos: see frame-by-frame progress
3. Results display in **Analysis Results** panel

### Step 4: Review Results
- **Detection Status**: Yes/No indicator
- **Confidence Score**: Detection confidence percentage
- **Capture Date/Time**: From file metadata
- **GPS Coordinates**: If available in EXIF (photos only)
- **Detection Time (MM:SS)**: For videos, shows when detection occurred

### Step 5: Export Results
- **View Crop**: Display cropped detection region in new window
- **Export Excel**: Saves `analysis_report_YYYY-MM-DD_HH-MM-SS.xlsx`
- **Export JSON**: Saves `analysis_report_YYYY-MM-DD_HH-MM-SS.json`

All reports saved to `./outputs/` directory

## 📊 Output Formats

### Excel Report Columns
| Column | Content |
|--------|---------|
| File Name | Input filename |
| Detection Status | Yes/No |
| Confidence Score | 0-1 (4 decimals) |
| Detection Time (MM:SS) | Video only |
| Capture Date | YYYY-MM-DD |
| Capture Time | HH:MM:SS |
| Analysis Date | Report date |
| Analysis Time | Report time |
| Estimated Distance (m) | Not implemented* |
| GPS Latitude | From EXIF or N/A |
| GPS Longitude | From EXIF or N/A |

*Distance estimation requires drone altitude & lens specs

### JSON Report Schema
```json
{
  "detected": true/false,
  "confidence": 0.0-1.0,
  "time_in_video": "MM:SS",
  "capture_date": "YYYY-MM-DD",
  "capture_time": "HH:MM:SS",
  "analysis_datetime": "ISO timestamp",
  "distance_m": null,
  "gps": {
    "lat": 0.0,
    "lon": 0.0
  },
  "crop_image_path": "path/to/crop.jpg",
  "metadata": {
    "filename": "image.jpg",
    "file_type": "image/video",
    "capture_source": "exif/file_time"
  }
}
```

## 🗂️ Project Structure

```
howitzer-detector/
├── main.py                          # PyQt5 GUI entry point
├── config.py                        # Configuration & constants
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
│
├── src/
│   ├── __init__.py                 # Package initialization
│   ├── detector.py                 # YOLOv8 detection engine
│   ├── metadata_extractor.py       # EXIF & video metadata
│   ├── report_generator.py         # Excel & JSON export
│   └── utils.py                    # Utility functions
│
├── models/
│   └── howitzer_detector.pt        # Custom YOLOv8 model (user-provided)
│
└── outputs/
    ├── analysis_report_*.xlsx      # Generated Excel reports
    ├── analysis_report_*.json      # Generated JSON reports
    └── detection_crop_*.jpg        # Cropped detection images
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Model & Detection
MODEL_PATH = "models/howitzer_detector.pt"
CONFIDENCE_THRESHOLD = 0.5
SUPPORTED_FORMATS = ('.jpg', '.jpeg', '.png', '.mp4', ...)

# File Size Limits
MAX_IMAGE_SIZE_MB = 100
MAX_VIDEO_SIZE_MB = 500

# Video Processing
VIDEO_SKIP_FRAMES = 1           # Analyze every frame
VIDEO_PROGRESS_UPDATE_INTERVAL = 10

# GUI
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 900
THUMBNAIL_SIZE = (200, 150)
CROP_PADDING = 20

# Output
OUTPUTS_DIR = Path(__file__).parent / "outputs"
EXCEL_SHEET_NAME = "Analysis Results"
JSON_INDENT = 2

# GPU
USE_GPU = True
```

## 🐛 Troubleshooting

### Model Not Found
**Error**: `Model not found at ./models/howitzer_detector.pt`
- Provide your trained model file
- Or program auto-falls back to YOLOv8n pretrained

### CUDA/GPU Issues
**Error**: Model loading slow or OutOfMemory
```bash
# Force CPU mode
# In config.py: USE_GPU = False

# Or check GPU
python -c "import torch; print(torch.cuda.is_available())"
```

### EXIF Not Extracting
**Issue**: No GPS or date captured from image
- Use file modification time (automatic fallback)
- Some cameras don't embed GPS; use manual entry
- Check photo was taken with drone/camera with GPS

### Video Format Error
**Error**: "Cannot open video"
- Use H.264 codec MP4 files
- Convert with FFmpeg: `ffmpeg -i input.mp4 -c:v libx264 output.mp4`

### Excel Export Error
**Error**: Permission denied writing to outputs/
- Ensure `outputs/` directory exists and is writable
- Close any open Excel files from previous runs

## 📈 Performance

| Task | Time | Hardware |
|------|------|----------|
| Load Model | 2-3s | CPU/GPU |
| Single Image | < 2s | GPU |
| Single Image | 5-10s | CPU |
| 30fps 1min Video | 30-40s | GPU |
| 30fps 1min Video | 120s+ | CPU |

## 🔮 Future Enhancements

- [ ] Distance estimation with drone altitude input
- [ ] Batch processing (multiple files)
- [ ] Custom model training UI
- [ ] Real-time drone feed analysis
- [ ] GIS integration with map display
- [ ] Advanced false-positive filtering
- [ ] Multi-object cropping
- [ ] Video streaming support

## 📝 License

For military/security applications, consult licensing requirements.

## 🤝 Contributing

To improve detection:
1. Collect false positive/negative samples
2. Retrain model with expanded dataset
3. Update `models/howitzer_detector.pt`

## 📞 Support

For issues or questions:
1. Check `./log.txt` for detailed error messages
2. Enable verbose logging in `config.py`
3. Verify dependencies: `pip list`
4. Test with sample image/video

---

**Version**: 1.0  
**Last Updated**: 2024-01-15  
**Author**: AI Development Team

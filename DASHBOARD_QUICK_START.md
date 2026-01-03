# 🎯 Quick Dashboard Guide

## 🚀 Access Dashboard

Open: **http://localhost:8000**

## 📋 Pages

| Page | What it does |
|------|--------------|
| **/** | Dashboard with stats & charts |
| **/documents** | Browse & filter all documents |
| **/upload** | Upload new documents (drag & drop) |
| **/documents/{id}** | View OCR results & metadata |
| **/health** | System health monitoring |

## 💡 Quick Tips

### Upload Document
1. Click **Upload** → Drag file or browse
2. Supports: PNG, JPG, PDF, TIFF
3. Auto-redirects to results

### View Results
- Go to **Documents** → Click **View**
- See extracted text, confidence, entities
- Copy text or download as TXT

### Monitor System
- Click **Health** for system status
- Auto-refreshes every 10 seconds
- Shows active workers

## 🎨 Status Colors

- 🟡 **Yellow** = Pending
- 🔵 **Blue** = Processing  
- 🟢 **Green** = Completed
- 🔴 **Red** = Failed

## 🔧 Troubleshooting

**Dashboard not loading?**
```bash
curl http://localhost:8000
```

**Documents stuck?**
```bash
# Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info
```

---

**Full docs**: [DASHBOARD_README.md](DASHBOARD_README.md)

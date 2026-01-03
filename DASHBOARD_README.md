# 🎨 Document Ingestion Dashboard

## Overview
A modern, responsive web dashboard for the Intelligent Document Ingestion Service, built with FastAPI, Jinja2 templates, and Tailwind CSS.

## 🚀 Features

### Dashboard Pages

#### 1. **Home Dashboard** (`/`)
- **Live Statistics Cards**
  - Total Documents
  - Completed Documents
  - Pending Documents
  - Failed Documents
- **Interactive Charts**
  - Document Status Distribution (Doughnut Chart)
  - Document Types Bar Chart
- **Recent Documents List**
  - Quick view of last 5 uploaded documents
  - Status badges with color coding
  - One-click navigation to details
- **Auto-refresh**: Updates every 10 seconds

#### 2. **Documents Page** (`/documents`)
- **Document Table**
  - Filename with file icons
  - Document type classification
  - Status badges
  - Upload timestamp
  - OCR confidence progress bars
  - Quick actions (View/Delete)
- **Advanced Filters**
  - Search by filename
  - Filter by status (Pending/Processing/Completed/Failed)
  - Filter by document type (Invoice/Receipt/Unknown)
  - Real-time filtering as you type
- **Pagination & Sorting**
  - Responsive table layout
  - Mobile-friendly design

#### 3. **Upload Page** (`/upload`)
- **Drag & Drop Interface**
  - Visual drop zone
  - File browser fallback
  - Real-time file validation
- **File Preview**
  - Shows selected filename
  - Displays file size
  - Quick remove option
- **Upload Progress**
  - Visual progress bar
  - Status indicators
  - Success/error messages
- **Upload Tips**
  - Best practices for OCR
  - Supported formats
  - Quality guidelines

#### 4. **Document Detail Page** (`/documents/{id}`)
- **Document Metadata**
  - Current status with timeline
  - Processing timestamps
  - OCR confidence score
  - Document type classification
- **Extracted Text Display**
  - Full OCR output
  - Monospace formatting
  - Copy to clipboard
  - Download as TXT
- **Extracted Entities**
  - Structured field display
  - Key-value pairs grid
  - Responsive layout
- **Processing Timeline**
  - Upload timestamp
  - Processing started time
  - Completion time
  - Visual progress indicators
- **Actions**
  - Reprocess document
  - Delete document
  - Auto-refresh for pending documents

#### 5. **Health Monitor Page** (`/health`)
- **Overall System Status**
  - Healthy/Unhealthy indicator
  - Large status icon
  - Refresh button
- **Component Health Cards**
  - Database connection status
  - Celery queue status
  - Active workers count
- **Worker Details**
  - List of active Celery workers
  - Worker names and status
  - Online/Offline indicators
- **System Statistics**
  - Documents processed (24h)
  - Success rate percentage
  - Average processing time
- **Service Information**
  - API version
  - OCR engine (PaddleOCR)
  - Storage backend (PostgreSQL)
  - Queue backend (Redis)
- **Auto-refresh**: Updates every 10 seconds

## 🎨 Design Features

### Visual Design
- **Color Scheme**: Indigo primary, with semantic status colors
  - Green: Completed/Healthy
  - Yellow: Pending/Warning
  - Blue: Processing
  - Red: Failed/Error
- **Typography**: System fonts with FontAwesome icons
- **Layout**: Card-based design with clean spacing
- **Responsive**: Mobile-first, works on all screen sizes

### User Experience
- **Real-time Updates**: JavaScript auto-refresh for live data
- **Loading States**: Spinners and placeholders during data fetch
- **Error Handling**: User-friendly error messages
- **Navigation**: Persistent top navigation bar
- **Visual Feedback**: Hover states, transitions, animations
- **Accessibility**: Semantic HTML, ARIA labels where needed

### Interactive Elements
- **Status Badges**: Color-coded pills for document states
- **Progress Bars**: Visual representation of confidence scores
- **Charts**: Interactive Chart.js visualizations
- **Buttons**: Clear call-to-action styling
- **Icons**: FontAwesome icons for visual clarity

## 🛠️ Technical Stack

### Frontend
- **HTML5**: Semantic markup with Jinja2 templates
- **Tailwind CSS**: Utility-first CSS via CDN (v3)
- **JavaScript**: Vanilla JS for API interactions
- **Chart.js**: Data visualization library
- **FontAwesome**: Icon library (v6.4.0)

### Backend Integration
- **FastAPI Routes**: Server-side rendering with Jinja2
- **RESTful API**: Consumes existing API endpoints
- **Async Database**: SQLAlchemy async sessions
- **Static Files**: Served via FastAPI StaticFiles

### Data Flow
1. Browser requests HTML page → FastAPI route
2. Jinja2 renders template with server data
3. JavaScript fetches live data from API endpoints
4. Chart.js renders visualizations
5. Auto-refresh keeps data current

## 📁 File Structure

```
src/
├── templates/               # Jinja2 HTML templates
│   ├── base.html           # Base layout with nav/footer
│   ├── dashboard.html      # Home dashboard page
│   ├── documents.html      # Documents list page
│   ├── upload.html         # Upload interface
│   ├── document_detail.html # Single document view
│   ├── health.html         # System health monitor
│   └── error.html          # Error page template
├── static/                 # Static assets
│   ├── css/
│   │   └── custom.css      # Custom styles
│   └── js/
│       └── utils.js        # JavaScript utilities
├── api/
│   └── routes/
│       └── dashboard.py    # Dashboard routes
└── main.py                 # Updated with dashboard routes
```

## 🔌 API Endpoints Used

### Dashboard Routes (HTML)
- `GET /` - Home dashboard
- `GET /documents` - Documents list
- `GET /upload` - Upload page
- `GET /documents/{id}` - Document detail
- `GET /health` - Health monitor

### API Endpoints (JSON)
- `GET /api/v1/documents` - List all documents
- `GET /api/v1/documents/{id}` - Get document details
- `POST /api/v1/documents/upload` - Upload document
- `POST /api/v1/documents/{id}/reprocess` - Reprocess document
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/dashboard/health` - System health check

## 🚀 Usage

### Starting the Dashboard
```bash
# Make sure PostgreSQL and Redis are running
docker start doc_postgres doc_redis

# Start the API server (includes dashboard)
cd "/home/aarav/Document ingestion"
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Access dashboard at http://localhost:8000
```

### Navigation Flow
1. **Dashboard** → Overview and recent documents
2. **Documents** → Browse all documents with filters
3. **Upload** → Add new documents
4. **Document Detail** → View OCR results and metadata
5. **Health** → Monitor system status

## 🎯 Key Improvements Over API-Only Interface

### Before (API Only)
❌ Needed tools like Postman or curl  
❌ JSON responses hard to visualize  
❌ No overview of system status  
❌ Command-line file uploads  
❌ Manual status polling  

### After (Web Dashboard)
✅ User-friendly web interface  
✅ Visual charts and graphs  
✅ Real-time system monitoring  
✅ Drag & drop file uploads  
✅ Auto-refreshing live data  
✅ Mobile-responsive design  
✅ One-click document actions  

## 📊 Dashboard Screenshots (Conceptual)

### Home Dashboard
```
┌─────────────────────────────────────────────────────────┐
│  DocIngest  [Dashboard] [Documents] [Upload] [Health]  │
├─────────────────────────────────────────────────────────┤
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                   │
│  │ 12  │  │ 10  │  │  2  │  │  0  │                   │
│  │Total│  │Done │  │Pend │  │Fail │                   │
│  └─────┘  └─────┘  └─────┘  └─────┘                   │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐                   │
│  │Status Chart  │  │Type Chart    │                   │
│  │   🍩        │  │   📊         │                   │
│  └──────────────┘  └──────────────┘                   │
│                                                          │
│  Recent Documents                          [View All >] │
│  ┌────────────────────────────────────────────────┐   │
│  │ 📄 invoice.png      [completed]    [View]     │   │
│  │ 📄 receipt.pdf      [pending]      [View]     │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Configuration

### Dependencies Added
```toml
# pyproject.toml
"jinja2>=3.1.2",      # Template engine
"aiofiles>=23.2.1",   # Async file operations
```

### Static Files Mount
```python
# src/main.py
app.mount("/static", StaticFiles(directory="src/static"), name="static")
```

## 🎓 Learning Features

### For Users
- **Visual Feedback**: Instant understanding of system state
- **Self-Service**: Upload and manage documents without CLI
- **Monitoring**: Track processing in real-time

### For Developers
- **Template Inheritance**: Jinja2 base templates
- **Async Patterns**: FastAPI + SQLAlchemy async
- **REST Integration**: Frontend consuming backend APIs
- **Responsive Design**: Mobile-first CSS approach

## 🔒 Security Considerations

### Current Implementation
- ⚠️ CORS set to allow all origins (development)
- ⚠️ No authentication/authorization
- ⚠️ Direct file uploads without user validation

### Production Recommendations
1. **Add Authentication**: JWT tokens or session-based
2. **Restrict CORS**: Whitelist specific origins
3. **File Validation**: Server-side type/size checks
4. **Rate Limiting**: Prevent abuse
5. **HTTPS**: Use SSL/TLS certificates
6. **Input Sanitization**: Prevent XSS attacks

## 📈 Future Enhancements

### Phase 2 Features
- [ ] User authentication & multi-tenancy
- [ ] Batch upload interface
- [ ] Document comparison view
- [ ] Export to CSV/Excel
- [ ] Advanced search with filters
- [ ] Document tagging system
- [ ] Webhook configuration UI
- [ ] API key management
- [ ] Usage analytics & reports
- [ ] Dark mode toggle

### Technical Improvements
- [ ] WebSocket for real-time updates
- [ ] Progressive Web App (PWA)
- [ ] Service worker for offline mode
- [ ] Server-side pagination
- [ ] GraphQL API option
- [ ] React/Vue.js SPA version

## ✅ Testing Checklist

- [x] Dashboard loads without errors
- [x] All navigation links work
- [x] Document list fetches from API
- [x] Charts render with data
- [x] Upload page accepts files
- [x] Health monitor shows system status
- [x] Auto-refresh updates data
- [x] Mobile responsive design
- [x] Error handling works
- [x] Static files serve correctly

## 📝 Summary

Created a **complete web dashboard** for the Document Ingestion Service featuring:
- 5 main pages with full functionality
- Real-time data updates and monitoring
- Professional UI/UX with Tailwind CSS
- Responsive design for all devices
- Integration with existing API
- No API knowledge required for end users

**Users can now**:
- Upload documents via drag & drop
- Monitor processing in real-time
- View OCR results visually
- Track system health
- Manage documents without command-line tools

**Access**: http://localhost:8000

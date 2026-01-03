"""Streamlit Dashboard for Document Ingestion Service."""

import io
import json
from datetime import datetime, timedelta

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageDraw

# Configuration
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000/api/v1")

# Page config
st.set_page_config(
    page_title="Document Ingestion Dashboard",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .status-completed { color: #28a745; }
    .status-failed { color: #dc3545; }
    .status-pending { color: #ffc107; }
    .status-needs_review { color: #17a2b8; }
</style>
""", unsafe_allow_html=True)


# ============== API Client ==============

class APIClient:
    """Client for interacting with the Document Ingestion API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def get_metrics(self) -> dict:
        """Get dashboard metrics."""
        try:
            response = self.client.get(f"{self.base_url}/dashboard/metrics")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch metrics: {e}")
            return {}
    
    def get_queue_status(self) -> dict:
        """Get queue status."""
        try:
            response = self.client.get(f"{self.base_url}/dashboard/queue")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"queue_depth": 0, "active_workers": 0}
    
    def list_documents(
        self,
        status: str | None = None,
        doc_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List documents with filters."""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        if doc_type:
            params["type"] = doc_type
        
        try:
            response = self.client.get(f"{self.base_url}/documents", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch documents: {e}")
            return {"documents": [], "total": 0}
    
    def get_document(self, document_id: str) -> dict:
        """Get document details."""
        try:
            response = self.client.get(f"{self.base_url}/documents/{document_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch document: {e}")
            return {}
            
    def get_document_ocr(self, document_id: str) -> dict:
        """Get detailed OCR results."""
        try:
            response = self.client.get(f"{self.base_url}/documents/{document_id}/ocr")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch OCR details: {e}")
            return {}
    
    def upload_document(self, file) -> dict:
        """Upload a document."""
        try:
            files = {"file": (file.name, file.getvalue(), file.type)}
            response = self.client.post(f"{self.base_url}/documents/upload", files=files)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Upload failed: {e}")
            return {}
    
    def search_documents(self, query: str, page: int = 1) -> dict:
        """Search documents."""
        try:
            response = self.client.get(
                f"{self.base_url}/search",
                params={"q": query, "page": page},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Search failed: {e}")
            return {"results": [], "total": 0}
    
    def update_review(self, document_id: str, data: dict) -> dict:
        """Update document after review."""
        try:
            response = self.client.put(
                f"{self.base_url}/documents/{document_id}/review",
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Update failed: {e}")
            return {}
    
    def reprocess_document(self, document_id: str) -> dict:
        """Reprocess a document."""
        try:
            response = self.client.post(f"{self.base_url}/documents/{document_id}/reprocess")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Reprocess failed: {e}")
            return {}

    def download_document(self, document_id: str) -> bytes | None:
        """Download document file content."""
        try:
            response = self.client.get(f"{self.base_url}/documents/{document_id}/download")
            response.raise_for_status()
            return response.content
        except Exception as e:
            st.error(f"Failed to download document: {e}")
            return None


# Initialize API client
api = APIClient()


# ============== Sidebar ==============

st.sidebar.title("📄 Document Ingestion")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "📈 Analytics", "📤 Upload", "📋 Documents", "🔍 Search", "👁️ Review Station"],
)

st.sidebar.markdown("---")

# Quick stats in sidebar
with st.sidebar:
    st.subheader("Quick Stats")
    metrics = api.get_metrics()
    
    if metrics:
        st.metric("Total Documents", metrics.get("total_documents", 0))
        st.metric("Processed Today", metrics.get("documents_today", 0))
        
        queue = api.get_queue_status()
        st.metric("Queue Depth", queue.get("queue_depth", 0))


# ============== Dashboard Page ==============

if page == "📊 Dashboard":
    st.title("📊 Processing Dashboard")
    
    # Fetch metrics
    metrics = api.get_metrics()
    
    if metrics:
        # Top metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Documents",
                metrics.get("total_documents", 0),
                delta=f"+{metrics.get('documents_today', 0)} today",
            )
        
        with col2:
            st.metric(
                "Processed",
                metrics.get("documents_processed", 0),
                delta_color="normal",
            )
        
        with col3:
            st.metric(
                "Pending",
                metrics.get("documents_pending", 0),
            )
        
        with col4:
            st.metric(
                "Failed",
                metrics.get("documents_failed", 0),
                delta_color="inverse",
            )
        
        with col5:
            st.metric(
                "Needs Review",
                metrics.get("documents_needs_review", 0),
            )
        
        st.markdown("---")
        
        # Charts row
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Document Status Distribution")
            
            status_data = {
                "Status": ["Completed", "Pending", "Failed", "Needs Review"],
                "Count": [
                    metrics.get("documents_processed", 0),
                    metrics.get("documents_pending", 0),
                    metrics.get("documents_failed", 0),
                    metrics.get("documents_needs_review", 0),
                ],
            }
            df = pd.DataFrame(status_data)
            
            fig = px.pie(
                df,
                values="Count",
                names="Status",
                color="Status",
                color_discrete_map={
                    "Completed": "#28a745",
                    "Pending": "#ffc107",
                    "Failed": "#dc3545",
                    "Needs Review": "#17a2b8",
                },
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Processing Metrics")
            
            avg_confidence = metrics.get("average_confidence", 0) * 100
            avg_time = metrics.get("average_processing_time") or 0
            
            # Confidence gauge
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=avg_confidence,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Average OCR Confidence"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#28a745" if avg_confidence > 60 else "#ffc107"},
                    "steps": [
                        {"range": [0, 60], "color": "#ffebee"},
                        {"range": [60, 80], "color": "#fff3e0"},
                        {"range": [80, 100], "color": "#e8f5e9"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 60,
                    },
                },
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            if avg_time:
                st.info(f"⏱️ Average Processing Time: {avg_time:.1f} seconds")
        
        # Queue status
        st.markdown("---")
        st.subheader("Queue Status")
        
        queue = api.get_queue_status()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Queue Depth", queue.get("queue_depth", 0))
        with col2:
            st.metric("Active Workers", queue.get("active_workers", 0))
        with col3:
            wait_time = queue.get("average_wait_time")
            st.metric("Avg Wait Time", f"{wait_time:.1f}s" if wait_time else "N/A")


# ============== Upload Page ==============

elif page == "📈 Analytics":
    st.title("📈 Advanced Analytics")
    
    # Fetch recent data for analysis
    with st.spinner("Fetching document data for analysis..."):
        # Fetch up to 500 docs for reasonable stats
        docs_data = api.list_documents(page_size=500)
        documents = docs_data.get("documents", [])
        
    if not documents:
        st.warning("No data available for analytics.")
    else:
        # Convert to DataFrame
        df = pd.DataFrame(documents)
        
        # KPIs
        total_docs = len(df)
        avg_ocr = df["ocr_confidence"].mean() * 100 if "ocr_confidence" in df.columns else 0
        avg_cls = df["classification_confidence"].mean() * 100 if "classification_confidence" in df.columns else 0
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Analyzed Documents", total_docs)
        kpi2.metric("Avg OCR Confidence", f"{avg_ocr:.1f}%")
        kpi3.metric("Avg Classification", f"{avg_cls:.1f}%")
        
        st.markdown("---")
        
        # 1. Document Type Distribution
        st.subheader("📊 Document Type Distribution")
        
        if "document_type" in df.columns:
            # Count types
            type_counts = df["document_type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            
            fig_types = px.pie(
                type_counts, 
                values="Count", 
                names="Type", 
                title="Distribution by Document Type",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            st.plotly_chart(fig_types, use_container_width=True)
        
        # 2. Confidence Analysis
        st.subheader("🎯 Confidence Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
             # Histogram of OCR Confidence
             if "ocr_confidence" in df.columns:
                 fig_hist = px.histogram(
                     df, 
                     x="ocr_confidence", 
                     nbins=20, 
                     title="OCR Confidence Distribution",
                     labels={"ocr_confidence": "Confidence Score"},
                     color_discrete_sequence=["#1f77b4"],
                     range_x=[0, 1.05]
                 )
                 st.plotly_chart(fig_hist, use_container_width=True)
             
        with col2:
             # Histogram of Classification Confidence
             if "classification_confidence" in df.columns:
                 fig_cls = px.histogram(
                     df, 
                     x="classification_confidence", 
                     nbins=20, 
                     title="Classification Confidence Distribution",
                     labels={"classification_confidence": "Confidence Score"},
                     color_discrete_sequence=["#2ca02c"],
                     range_x=[0, 1.05]
                 )
                 st.plotly_chart(fig_cls, use_container_width=True)

        # 3. Time Series
        if "created_at" in df.columns:
            st.subheader("📅 Processing Volume Timeline")
            # Handle string to datetime conversion
            df["created_at"] = pd.to_datetime(df["created_at"])
            df["date"] = df["created_at"].dt.date
            daily_counts = df.groupby("date").size().reset_index(name="count")
            
            fig_trend = px.bar(
                daily_counts, 
                x="date", 
                y="count", 
                title="Documents Processed per Day",
                color_discrete_sequence=["#ff7f0e"]
            )
            st.plotly_chart(fig_trend, use_container_width=True)


# ============== Upload Page ==============

elif page == "📤 Upload":
    st.title("📤 Upload Documents")
    
    st.markdown("""
    Upload documents for processing. Supported formats:
    - **PDF** - Scanned or digital documents
    - **Images** - PNG, JPG, JPEG, TIFF
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg", "tiff", "tif"],
        help="Maximum file size: 50MB",
    )
    
    if uploaded_file:
        st.write(f"**Filename:** {uploaded_file.name}")
        st.write(f"**Size:** {uploaded_file.size / 1024:.1f} KB")
        st.write(f"**Type:** {uploaded_file.type}")
        
        # Preview for images
        if uploaded_file.type.startswith("image/"):
            st.image(uploaded_file, caption="Preview", width=400)
        
        if st.button("🚀 Upload & Process", type="primary"):
            with st.spinner("Uploading..."):
                result = api.upload_document(uploaded_file)
                
                if result:
                    st.success(f"✅ Document uploaded successfully!")
                    st.json(result)
                    st.info("The document has been queued for processing. Check the Documents page for status.")


# ============== Documents Page ==============

elif page == "📋 Documents":
    st.title("📋 Document List")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "processing", "completed", "failed", "needs_review"],
        )
    
    with col2:
        type_filter = st.selectbox(
            "Document Type",
            ["All", "invoice", "receipt", "medical", "legal", "financial", "unknown"],
        )
    
    with col3:
        page_num = st.number_input("Page", min_value=1, value=1)
    
    # Fetch documents
    status = status_filter if status_filter != "All" else None
    doc_type = type_filter if type_filter != "All" else None
    
    result = api.list_documents(status=status, doc_type=doc_type, page=page_num)
    
    if result.get("documents"):
        st.write(f"Showing {len(result['documents'])} of {result['total']} documents")
        
        # Initialize session state for selected document
        if "selected_doc_id" not in st.session_state:
            st.session_state.selected_doc_id = None
        
        # Display documents in a table with View buttons
        st.markdown("### Documents")
        
        # Header row
        header_cols = st.columns([1, 3, 2, 2, 2, 2, 1])
        header_cols[0].markdown("**#**")
        header_cols[1].markdown("**Filename**")
        header_cols[2].markdown("**Status**")
        header_cols[3].markdown("**Type**")
        header_cols[4].markdown("**Confidence**")
        header_cols[5].markdown("**Uploaded**")
        header_cols[6].markdown("**Action**")
        
        # Data rows
        for idx, doc in enumerate(result["documents"], start=1):
            cols = st.columns([1, 3, 2, 2, 2, 2, 1])
            cols[0].write(str(idx))
            cols[1].write(doc["filename"][:30] + "..." if len(doc["filename"]) > 30 else doc["filename"])
            
            # Status with color
            status = doc["status"]
            status_colors = {
                "completed": "🟢",
                "failed": "🔴",
                "pending": "🟡",
                "needs_review": "🔵",
                "processing": "⚪"
            }
            cols[2].write(f"{status_colors.get(status, '⚪')} {status}")
            cols[3].write(doc.get("document_type") or "Unknown")
            cols[4].write(f"{(doc.get('ocr_confidence') or 0) * 100:.1f}%")
            cols[5].write(doc["upload_timestamp"][:10])
            
            # View button
            if cols[6].button("👁️", key=f"view_{doc['id']}", help="View document details"):
                st.session_state.selected_doc_id = doc["id"]
        
        # Document Details Section
        st.markdown("---")
        st.subheader("📄 Document Details")
        
        if st.session_state.selected_doc_id:
            doc_id = st.session_state.selected_doc_id
            doc = api.get_document(doc_id)
            
            if doc:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Display document image
                    if doc.get('original_filename', '').lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
                        image_data = api.download_document(doc_id)
                        if image_data:
                            try:
                                st.image(image_data, caption=doc.get('original_filename'), use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to display image: {e}")
                    
                    st.write("**Basic Information**")
                    st.write(f"- **ID**: `{doc.get('id')}`")
                    st.write(f"- **Filename**: {doc.get('original_filename')}")
                    st.write(f"- **Status**: {doc.get('status')}")
                    st.write(f"- **Type**: {doc.get('document_type')}")
                    st.write(f"- **Pages**: {doc.get('page_count')}")
                    st.write(f"- **OCR Confidence**: {(doc.get('ocr_confidence') or 0) * 100:.1f}%")
                    st.write(f"- **Classification Confidence**: {(doc.get('classification_confidence') or 0) * 100:.1f}%")
                
                with col2:
                    st.write("**📋 Extracted Data**")
                    extracted = doc.get("extracted_data")
                    
                    if extracted and isinstance(extracted, dict):
                        # Filter out None values and display as clean table
                        data_rows = []
                        
                        # Define display labels for common fields
                        field_labels = {
                            # Identity/Insurance fields
                            "member_name": "👤 Name",
                            "member_id": "🆔 Member ID",
                            "group_number": "🔢 Group Number",
                            "effective_date": "📅 Effective Date",
                            "plan_type": "📋 Plan Type",
                            "issuer_name": "🏢 Issuer",
                            "card_type": "🎴 Card Type",
                            # Copays
                            "copay_pcp": "💊 PCP Copay",
                            "copay_specialist": "👨‍⚕️ Specialist Copay",
                            "copay_er": "🚑 ER Copay",
                            "copay_urgent_care": "🏥 Urgent Care Copay",
                            "copay_rx": "💊 Rx Copay",
                            # Deductibles
                            "deductible_individual": "💰 Deductible (Ind)",
                            "deductible_family": "👨‍👩‍👧 Deductible (Fam)",
                            "out_of_pocket_individual": "💵 OOP Max (Ind)",
                            "out_of_pocket_family": "👨‍👩‍👧 OOP Max (Fam)",
                            # Coinsurance
                            "coinsurance_in_network": "📊 In-Network %",
                            "coinsurance_out_of_network": "📊 Out-of-Network %",
                            # Rx identifiers
                            "rx_bin": "🏷️ RxBIN",
                            "rx_pcn": "🏷️ RxPCN",
                            "rx_group": "🏷️ RxGroup",
                            # Invoice fields
                            "invoice_number": "📄 Invoice #",
                            "invoice_date": "📅 Date",
                            "vendor_name": "🏢 Vendor",
                            "total_amount": "💰 Total",
                            # Medical fields
                            "patient_name": "👤 Patient",
                            "provider_name": "👨‍⚕️ Provider",
                            "diagnosis": "🩺 Diagnosis",
                        }
                        
                        for field, value in extracted.items():
                            if value is not None and value != "" and value != []:
                                label = field_labels.get(field, field.replace("_", " ").title())
                                # Format value
                                if isinstance(value, list):
                                    display_val = ", ".join(str(v) for v in value[:5])
                                elif isinstance(value, float):
                                    display_val = f"${value:,.2f}" if "amount" in field or "total" in field else f"{value:.2f}"
                                else:
                                    display_val = str(value)
                                data_rows.append({"Field": label, "Value": display_val})
                        
                        if data_rows:
                            import pandas as pd
                            df = pd.DataFrame(data_rows)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                        else:
                            st.info("No data extracted")
                    else:
                        st.info("No extracted data available")
                
                if doc.get("raw_text"):
                    with st.expander("📝 View Raw OCR Text", expanded=False):
                        st.text(doc["raw_text"][:5000])
                
                # Action buttons
                action_cols = st.columns(3)
                with action_cols[0]:
                    if st.button("🔄 Reprocess", key="reprocess_selected"):
                        api.reprocess_document(doc_id)
                        st.success("Queued for reprocessing!")
                        st.rerun()
                with action_cols[1]:
                    if st.button("❌ Clear Selection", key="clear_selection"):
                        st.session_state.selected_doc_id = None
                        st.rerun()
            else:
                st.error("Could not load document details.")
        else:
            st.info("👆 Click a **👁️ View** button above to see document details.")



# ============== Search Page ==============

elif page == "🔍 Search":
    st.title("🔍 Search Documents")
    
    query = st.text_input("Search query", placeholder="Enter search terms...")
    
    if query:
        with st.spinner("Searching..."):
            results = api.search_documents(query)
        
        if results.get("results"):
            st.write(f"Found {results['total']} results")
            
            for result in results["results"]:
                with st.expander(f"📄 {result['filename']} ({result.get('document_type', 'Unknown')})"):
                    st.write(f"**Document ID:** {result['document_id']}")
                    st.write(f"**Relevance Score:** {result['relevance_score']:.4f}")
                    st.write(f"**Uploaded:** {result['upload_timestamp'][:19]}")
                    st.markdown("**Snippet:**")
                    st.markdown(result.get("snippet", "No preview available"), unsafe_allow_html=True)
        else:
            st.info("No results found")


# ============== Review Station Page ==============

elif page == "👁️ Review Station":
    st.title("👁️ Review Station")
    st.markdown("Review and correct documents flagged for manual review")
    
    # Fetch documents needing review
    result = api.list_documents(status="needs_review", page_size=50)
    
    if result.get("documents"):
        st.warning(f"⚠️ {result['total']} documents need review")
        
        # Document selector
        doc_options = {
            f"{doc['filename']} (Confidence: {(doc.get('ocr_confidence') or 0) * 100:.0f}%)": doc["id"]
            for doc in result["documents"]
        }
        
        selected_doc_name = st.selectbox("Select document to review:", list(doc_options.keys()))
        selected_doc_id = doc_options[selected_doc_name]
        
        if selected_doc_id:
            doc = api.get_document(selected_doc_id)
            
            if doc:
                st.markdown("---")
                
                # Split view
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📸 Document View")
                    
                    # Fetch Image
                    image_bytes = api.download_document(selected_doc_id)
                    if image_bytes:
                        try:
                            img = Image.open(io.BytesIO(image_bytes))
                            
                            # Valid image check
                            if img:
                                show_boxes = st.checkbox("Show OCR Bounding Boxes", value=True, key=f"box_{selected_doc_id}")
                                
                                if show_boxes:
                                    # Fetch OCR details
                                    ocr_details = api.get_document_ocr(selected_doc_id)
                                    results = ocr_details.get("results", [])
                                    
                                    if results:
                                        # Work on a copy to preserve original
                                        img_draw = img.copy()
                                        draw = ImageDraw.Draw(img_draw)
                                        for res in results:
                                            bbox = res.get("bounding_box")
                                            if bbox:
                                                # Draw polygon
                                                xy = [tuple(p) for p in bbox]
                                                draw.polygon(xy, outline="red", width=3)
                                        img = img_draw
                                
                                st.image(img, use_container_width=True, caption=f"Page {doc.get('page_count', 1)}")
                        except Exception as e:
                            st.warning(f"Could not load image: {e}")
                    
                    with st.expander("📝 Raw OCR Text", expanded=False):
                        st.text_area(
                            "Content",
                            value=doc.get("raw_text", ""),
                            height=200,
                            disabled=True,
                        )
                    
                    st.write(f"**OCR Confidence:** {(doc.get('ocr_confidence') or 0) * 100:.1f}%")
                    st.write(f"**Detected Type:** {doc.get('document_type')}")
                
                with col2:
                    st.subheader("✏️ Extracted Fields")
                    
                    extracted = doc.get("extracted_data") or {}
                    
                    # Editable JSON
                    edited_json = st.text_area(
                        "Edit extracted data (JSON)",
                        value=json.dumps(extracted, indent=2),
                        height=300,
                    )
                    
                    # Document type override
                    doc_types = ["invoice", "receipt", "medical", "legal", "financial", "correspondence", "unknown"]
                    current_type = doc.get("document_type") or "unknown"
                    new_type = st.selectbox(
                        "Document Type",
                        doc_types,
                        index=doc_types.index(current_type) if current_type in doc_types else -1,
                    )
                    
                    # Action buttons
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        if st.button("✅ Approve & Save", type="primary"):
                            try:
                                new_data = json.loads(edited_json)
                                result = api.update_review(
                                    selected_doc_id,
                                    {
                                        "extracted_data": new_data,
                                        "document_type": new_type,
                                    },
                                )
                                if result:
                                    st.success("Document updated successfully!")
                                    st.rerun()
                            except json.JSONDecodeError:
                                st.error("Invalid JSON format")
                    
                    with col_b:
                        if st.button("🔄 Reprocess"):
                            result = api.reprocess_document(selected_doc_id)
                            if result:
                                st.success("Document queued for reprocessing")
                                st.rerun()
                    
                    with col_c:
                        if st.button("⏭️ Skip"):
                            st.info("Skipping document...")
                            st.rerun()
    else:
        st.success("✅ No documents pending review!")


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown("""
**Document Ingestion Service**  
Version 1.0.0

Built with ❤️ using:
- FastAPI
- PaddleOCR
- PostgreSQL
- Streamlit
""")

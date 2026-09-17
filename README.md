# Lightweight R2R Retrieval Service for Microsoft Copilot

A lightweight, high-quality knowledge retrieval service using R2R designed to provide grounded knowledge chunks for Microsoft Copilot from SharePoint sites.

## Features

- **SharePoint & Local Connector Support**: Ingests files from a configured SharePoint site drive or a local directory (`data/sharepoint_mock`).
- **Logical Folder Mapping**: Maps each SharePoint/local folder to an isolated `knowledgeBaseId` / R2R collection.
- **Multi-Format Parsing**: Supports PDF, DOCX, PPTX, XLSX, TXT, CSV, and HTML formats.
- **Incremental Synchronization**: Performs hourly background syncs and supports manual sync triggers for additions, updates, and deletions.
- **Metadata Preservation**: Retains source URLs, filenames, folder structures, modified dates, and document IDs.
- **Strict Collection Isolation**: Guarantees retrieval results are rigidly scoped to the requested `knowledgeBaseId`.
- **Azure OpenAI Ready**: Prepared for Azure OpenAI embedding models and cloud deployments.
- **Diagnostics & Testing Tools**: Exposes health, metrics, sync status, and a dummy Copilot client test endpoint.

## Getting Started

### 1. Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 2. Local Development

Install dependencies and start the service:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Docker Setup

To build and run using Docker Compose:

```bash
docker-compose up --build
```

## API Endpoints

- `POST /v1/retrieve`: Main authenticated retrieval endpoint for Copilot.
- `POST /v1/sync/trigger`: Trigger immediate incremental sync pass.
- `GET /v1/sync/status`: View current sync statistics and diagnostics.
- `POST /v1/test/copilot`: Dummy Copilot test client endpoint.
- `GET /health` & `GET /metrics`: Service health and metrics.

## Running Tests

Run test suite with pytest:

```bash
pytest
```

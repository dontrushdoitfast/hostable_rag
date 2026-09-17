Build a lightweight retrieval service using R2R to provide high-quality knowledge retrieval for Microsoft Copilot.

The service must:

* Ingest documents from one configured SharePoint site containing approximately 20 logical knowledge-base folders.
* Support up to approximately 3,000 documents per folder.
* Support PDF, DOCX, PPTX, XLSX, TXT, CSV, images/ocr and HTML where practical. You may use another library like docling if needed.
* Preserve source metadata including SharePoint URL, filename, folder, modified date, and document ID.
* Map each SharePoint folder to an isolated knowledge-base ID / R2R collection.
* Synchronise SharePoint incrementally at least once per hour, including additions, updates, and deletions.
* Assume all authorised users of the service may access all documents; per-file SharePoint ACL enforcement is not required.
* Use Azure-hosted embedding models.
* Expose an authenticated retrieval API using service-to-service authentication.
* Accept at minimum:

  * `knowledgeBaseId`
  * `query`
  * `maxResults`
* Guarantee retrieval is restricted to the requested knowledge base.
* Use R2R hybrid/vector retrieval and return ranked chunks containing title, source URL, snippet, document ID, and relevance metadata.
* Return a configurable maximum of 10–15 chunks suitable for Copilot grounding.
* Perform retrieval only; Microsoft Copilot remains responsible for answer generation.
* Provide health, sync status, logging, metrics, and basic ingestion diagnostics.
* Support local/self-hosted development and later deployment to Azure using containers and externalised configuration/secrets.

For prototyping, the service must also support:

* A dummy SharePoint connector that ingests files from a local directory using the same folder-to-knowledge-base mapping.
* A manual ingestion/sync trigger for development.
* A dummy Copilot client or test endpoint that submits `knowledgeBaseId`, query, and result count and displays the raw retrieval response.
* Configurable fake source URLs and document metadata for local test documents.
* Environment-based switching between dummy/local connectors and production SharePoint/Copilot integrations.


include making tests

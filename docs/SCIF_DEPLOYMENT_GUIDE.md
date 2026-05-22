# SCIF Deployment & Data Sanitization Guide
## Sensitive Compartmented Information Facility (SCIF) Air-Gapped Deployment

This document defines the deployment procedures and security protocols for running PHYNX in a Tier-1 air-gapped environment (SCIF). 

---

## 1. Network Topology: Unidirectional Data Flow (Data Diode)

To ingest OSINT, RF, and geospatial data without exposing the analysis environment, PHYNX enforces a strict unidirectional network isolation model between the **Dirty Zone** (Ingestion/Scraping) and the **Clean Zone** (Analysis/Graph Fusion).

```
 ┌─────────────────────────┐               ┌────────────────────────┐               ┌─────────────────────────┐
 │       DIRTY ZONE        │               │   SOFTWARE DATA DIODE  │               │       CLEAN ZONE        │
 │  - Internet Scrapers    │               │  - Optical Link / UDP  │               │  - Neo4j Graph Database │
 │  - RF Receiver Stream   │  ───[UDP]───► │  - No TCP Handshake    │  ───[UDP]───► │  - Milvus Vector DB     │
 │  - Raw File Ingestion   │               │  - Strictly Outbound   │               │  - Local Ollama Cluster │
 └─────────────────────────┘               └────────────────────────┘               └─────────────────────────┘
```

### Physical/Logical Separation:
1.  **No Backchannels**: The Clean Zone has no physical or logical path to transmit packets back to the Dirty Zone.
2.  **UDP Unicast/Multicast Broadcast**: Data collected in the Dirty Zone is serialized into custom binary packets and broadcast over a unidirectional link (UDP) to a receiver in the Clean Zone. No TCP three-way handshake is allowed across the boundary.

---

## 2. Inbound Data Sanitization Protocol (CDR: Content Disarm & Reconstruction)

All unstructured files (PDFs, images, CSVs, JSON, PCAPs) crossing the boundary must be sanitized in a transient sandbox environment before ingestion into the Clean Zone databases. This prevents steganographic payloads, exploits, or embedded command-and-control (C2) markers from executing.

```
┌─────────────────┐      ┌─────────────────────────┐      ┌─────────────────────────┐      ┌─────────────────┐
│  Raw Ingested   │ ───► │   Recursive Sandbox     │ ───► │   Structural Parser     │ ───► │  Sanitized Raw  │
│  File Stream    │      │   Extraction (Tar/Zip)  │      │   (Stripping/Rebuild)   │      │  Text & Vectors │
└─────────────────┘      └─────────────────────────┘      └─────────────────────────┘      └─────────────────┘
```

### File-Specific Sanitization Actions:

#### 1. Document Files (PDF, DOCX, HTML)
*   **Deconstruction**: Convert PDFs to raw text using static parsing libraries (e.g., `pdfminer`). Discard formatting, styling, and structural elements.
*   **Active Content Removal**: Strip all Javascript nodes, macros, forms, actions, and external URL references.
*   **Reconstruction**: Rebuild the document as flat ASCII/UTF-8 plaintext. Only pass the raw text payload to the processing workers.

#### 2. Imagery (JPEG, PNG, TIFF, Geospatial Raster)
*   **Metadata Stripping**: Run `mat2` or similar static binary parser to scrub EXIF, IPTC, and XMP metadata (GPS coordinates, camera models, creation timestamps).
*   **Format Transcoding**: Re-encode images using a safe library (e.g., OpenCV/Pillow) to strip potential steganographic modifications (LSB manipulation) or container-level exploits.
    *   *Example*: Convert JPEG -> raw pixels -> new PNG in-memory.

#### 3. Structured Data (CSV, JSON, XML)
*   **Strict Schema Validation**: Validate all fields against predefined JSON/XML schemas.
*   **Escaping**: Strip or escape control characters, shell-injection characters (e.g., `;`, `|`, `` ` ``), and SQL/Cypher injection sequences.
*   **Normalization**: Cast data values strictly to primitive types (Integers, Floats, Alpha-numeric Strings) before loading them into Kafka.

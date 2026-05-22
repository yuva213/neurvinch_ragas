# Neurvinch Model Context Protocol (MCP) Server

This documentation provides a comprehensive guide to using, configuring, and developing with the **Neurvinch MCP Server**. 

The Neurvinch MCP server implements Anthropic's **Model Context Protocol (MCP)**, allowing compatible AI clients (such as Cursor, Claude Desktop, or custom clients) to directly connect to your local Neurvinch RAG knowledge base. The server provides automated dataset cleaning (deduplication and contradiction resolution) and hallucination-free, 100% grounded Q&A.

---

## 🚀 Key Features

* **Dynamic Dataset Path Selection**: Dynamically swap the target directory containing your raw dataset.
* **On-the-Fly File Ingestion**: Upload new markdown or text documents directly to the active knowledge base.
* **Automated Data Cleaning**:
  * **Exact Deduplication**: Detects and drops identical chunks to minimize token consumption and avoid redundancy.
  * **Contradiction Auditing**: Scans similar text chunks for logical contradictions. If found, it automatically deprecates older document versions (e.g. `v1.0` vs `v2.0`) or drops less comprehensive chunks.
* **Hallucination-Free Q&A**: Fits your hybrid RAG retriever **strictly** on the remaining clean chunks, ensuring generated answers are 100% grounded and cited.

---

## 🛠️ API & Tool Reference

The server exposes the following **FastMCP Tools**:

### 1. `set_knowledge_base_path`
Configures the directory containing the dataset you want to clean and query.
* **Arguments**:
  * `directory_path` (string, required): The absolute local folder path.
* **Behavior**: Updates the active dataset target path, resets current memory state, and creates the folder if it does not exist.

### 2. `upload_document`
Writes a new text or markdown file directly into the active dataset folder.
* **Arguments**:
  * `filename` (string, required): The file name (e.g., `policy_v2.0.md`).
  * `content` (string, required): The document's raw text content.

### 3. `clean_and_index_dataset`
Triggers the indexing and cleaning pipeline.
* **Process**:
  1. Parses raw files using the `StructuralIndexer`.
  2. Runs exact-match string de-duplication.
  3. Uses `NLIAuditor` (NLI cross-encoder or heuristic) to locate semantic conflicts.
  4. Automatically resolves conflicts by dropping older versions/older modified files.
  5. Fits the hybrid retriever on the active clean chunks.
  6. Saves clean state to `outputs/cleaned_chunks.json` and writes a report to `outputs/mcp_clean_report.json`.

### 4. `ask_grounded_question`
Submits a question to the cleaned dataset.
* **Arguments**:
  * `query` (string, required): Your question about the dataset.
* **Behavior**: Retrieves matching clean evidence and formats a response grounded solely in the retrieved context using your Groq LLM configuration. If Groq is offline, it returns the cited text results directly.

### 5. `get_cleaned_dataset_summary`
Returns active dataset analytics (current directory, clean chunk counts, list of active files).

---

## 📂 MCP Resource Reference

The server exposes the following standard **FastMCP Resources**:

* **`audit://report`**: Fetches the structured JSON cleaning report, detailing exact deduplication stats and contradiction logs.
* **`audit://cleaned_chunks`**: Exposes the complete list of active, deduplicated, and conflict-resolved chunks in raw JSON format.

---

## ⚙️ Client Integration Instructions

To connect the server to your favorite local AI tools, use the command runner script `run_mcp_server.py`.

### Option A: Cursor Setup
1. Open **Cursor Settings** > **Features** > **MCP**.
2. Click **+ Add New MCP Server**.
3. Configure the server with these values:
   * **Name**: `Neurvinch`
   * **Type**: `stdio`
   * **Command**: `python -X utf8 "c:\Users\yuvar\Desktop\web_hoster\HACKATHONS--\naanmudhalvan\neurvinch_ragas\run_mcp_server.py"`
4. Click **Save**.

### Option B: Claude Desktop Setup
Open or create your Claude Desktop configuration file at `%APPDATA%\Claude\claude_desktop_config.json` and paste:

```json
{
  "mcpServers": {
    "neurvinch": {
      "command": "python",
      "args": [
        "-X",
        "utf8",
        "c:\\Users\\yuvar\\Desktop\\web_hoster\\HACKATHONS--\\naanmudhalvan\\neurvinch_ragas\\run_mcp_server.py"
      ]
    }
  }
}
```
Restart Claude Desktop to activate the tools.

---

## 🔍 How to Run & Debug Locally

### 1. Manual Testing via MCP Inspector
The official MCP Inspector allows you to test tools interactively in the browser without an active AI client:
```bash
npx -y @modelcontextprotocol/inspector python run_mcp_server.py
```

### 2. Force UTF-8 Encoding
When running or executing the MCP server on Windows systems, always use the `-X utf8` flag to prevent `UnicodeEncodeError` when emitting logs or report summaries containing formatting characters:
```bash
python -X utf8 run_mcp_server.py
```

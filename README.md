```text
+-----------------------+
| 1. USER INTERFACE (Frontend) |
|   - Web App (React/Vue)   |
|   - Chat Window           |
+-----------+-----------+
            | (User Input)
+-----------v-----------+
| 2. CONVERSATIONAL AI (LLM Engine) |
|   - **LLM/Agentic Workflow** |
|   - **NLU** (Intent & Entity Extraction)  <-- *The LLM extracts 'LLC' & 'Texas'*
+-----------+-----------+
            | (Triggers Step)
+-----------v-----------+
| 3. BACKEND ORCHESTRATION (The Conductor) |
|   - Application Server (Python/Node.js) |
|   - **State Manager** (Database)  <-- *Logs current step (e.g., 'Name Check Pending')*
|   - RAG/Knowledge Base Manager    <-- *Retrieves TX LLC rules for LLM*
+-----------+-----------+
            | (If Automation Needed)
+-----------v-----------+
| 4. AUTOMATION SERVICE (The Robot) |
|   - **Robotic Process Automation (RPA)** |
|   - Headless Browser (Playwright/Puppeteer) |
|   - **Credential Vault** (Secure Login) |
+-----------+-----------+
            | (Automated Actions)
+-----------v-----------+
| 5. EXTERNAL SYSTEMS |
|   - State Secretary of State Website (Name Search/Filing) |
|   - IRS/Federal Tax ID (EIN) Site |
|   - Payment Gateway / ID Verification Service |
+-----------------------+
```
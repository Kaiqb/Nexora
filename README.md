Nexora - business creation process

graph TD
    %% User Interface Layer
    A[1. USER INTERFACE (Frontend)] --> B;
    A -- Web App (React/Vue) --> A;
    A -- Chat Window --> A;

    %% Conversational AI Layer
    B[2. CONVERSATIONAL AI (LLM Engine)] --> C;
    B -- LLM/Agentic Workflow --> B;
    B -- NLU (Intent & Entity Extraction) --> B;
    B -- *LLM extracts 'LLC' & 'Texas'* --> B;

    %% Backend Orchestration Layer
    C[3. BACKEND ORCHESTRATION (The Conductor)] --> D;
    C -- Application Server (Python/Node.js) --> C;
    C -- State Manager (DB) --> C;
    C -- RAG/Knowledge Base Manager --> C;

    %% Automation Service Layer
    D{4. AUTOMATION SERVICE (The Robot)} --> E;
    D -- Robotic Process Automation (RPA) --> D;
    D -- Headless Browser (Playwright) --> D;
    D -- Credential Vault (Secure Login) --> D;

    %% External Systems Layer
    E[5. EXTERNAL SYSTEMS]
    E -- State SOS Website (Filing) --> E;
    E -- IRS/Federal Tax ID (EIN) Site --> E;
    E -- Payment Gateway --> E;

    %% Data Flow Back to User (Simplified)
    E -->|Status/Result| D;
    D -->|Status Update| C;
    C -->|Next Prompt| B;
    B -->|Response| A;
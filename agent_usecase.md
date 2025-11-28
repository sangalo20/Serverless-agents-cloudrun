Objective: Scaffold a production-ready, serverless Python application designed to run on Google Cloud Run. The application must implement a "Micro-Agent" architecture using two separate Cloud Run services, Flask, Vertex AI (Gemini 2.5 Flash), Firestore, and Eventarc.

Technical Constraints:

Language: Python 3.11

Framework: Flask (using Gunicorn for production)

Infrastructure: 
- 2x Cloud Run Services (Compute)
- Firestore (State/Memory)
- Eventarc (Async Triggers)
- Vertex AI (Inference)
- Cloud Storage (Ingestion Source)

Style: Native SDKs only. Do NOT use LangChain or other heavy agent frameworks. Keep the containers lightweight.

Agent Architecture & Logic:

The application will be split into two independent Cloud Run services to demonstrate scalability and separation of concerns:

1. Service A: "The Librarian" (Async Knowledge Ingestion)

Trigger: This service is triggered via Eventarc when a file (PDF or Text) is uploaded to a Cloud Storage Bucket.

Task:
- Parse the CloudEvent to get the bucket name and file name.
- Download the file contents from Google Cloud Storage.
- Send the file content to Vertex AI (Gemini 2.5 Flash) with a prompt to "Extract a structured summary of the conference schedule, speakers, and topics."
- Save this summary into Firestore in a collection named `knowledge_base`, document ID `devfest_schedule`.
- Handle errors gracefully.

2. Service B: "The Guide" (Sync User Interaction)

Trigger: This service listens for POST requests on the `/chat` endpoint.

Input Payload: `{"session_id": "string", "query": "string"}`

Task:
- Retrieve Long-Term Memory: Fetch the `devfest_schedule` summary from Firestore (`knowledge_base` collection).
- Retrieve Short-Term Memory: Fetch the last 5 conversation turns from Firestore (Collection `chat_history`, Document `session_id`).
- Inference: Construct a system prompt that combines the Schedule Knowledge, Chat History, and the User's Current Query. Instruct the model to act as a helpful conference concierge.
- Response: Generate a response using Vertex AI (Gemini 2.5 Flash).
- State Update: Append the new User/Agent turn to the `chat_history` in Firestore.
- Output: Return JSON `{"response": "string"}`.

Deliverables Required:

- `librarian/`: Directory containing `main.py` and `Dockerfile` for the Librarian service.
- `guide/`: Directory containing `main.py` and `Dockerfile` for the Guide service.
- `setup_workshop.ipynb`: A Google Colab notebook that:
    - Authenticates the user.
    - Enables necessary APIs (run, eventarc, aiplatform, firestore, storage).
    - Creates the GCS bucket and Firestore database.
    - Builds and Deploys both services to Cloud Run.
    - Sets up the Eventarc trigger for the Librarian.
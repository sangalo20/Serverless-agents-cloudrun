import os
from flask import Flask, request, jsonify
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession

app = Flask(__name__)

# Initialize Firestore
db = firestore.Client()

# Initialize Vertex AI
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
vertexai.init(project=PROJECT_ID, location=LOCATION)

MODEL_ID = "gemini-2.5-flash"

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        session_id = data.get("session_id")
        user_query = data.get("query")
        
        if not session_id or not user_query:
            return jsonify({"error": "Missing session_id or query"}), 400

        # 1. Retrieve Knowledge Base (All Documents)
        docs = db.collection("knowledge_base").stream()
        
        summaries = []
        for doc in docs:
            doc_data = doc.to_dict()
            summary = doc_data.get("summary", "")
            source = doc_data.get("source_file", "Unknown Source")
            summaries.append(f"--- Source: {source} ---\n{summary}")
        
        if summaries:
            knowledge_context = "\n\n".join(summaries)
        else:
            knowledge_context = "I have not processed any documents yet. Please upload a PDF to the Knowledge Base bucket to get started."

        # 2. Retrieve Chat History (Short-term memory)
        # We'll store history as a list of turns in a single document for simplicity in this workshop
        # Real-world apps might use a subcollection
        history_ref = db.collection("chat_history").document(session_id)
        history_doc = history_ref.get()
        
        history = []
        if history_doc.exists:
            history = history_doc.to_dict().get("turns", [])
        
        # Keep only last 5 turns
        recent_history = history[-5:]

        # 3. Construct Prompt
        system_instruction = f"""
        You are a helpful assistant.
        
        Your goal is to answer the user's question using the information provided in the document context below.
        
        --- Document Context ---
        {knowledge_context}
        ------------------------
        
        Instructions:
        1. Answer the user's question directly and concisely based on the context above.
        2. If the answer is not found in the context, politely state that the information is not available in the provided documents.
        3. Do not make up information that is not in the context.
        """

        model = GenerativeModel(MODEL_ID, system_instruction=system_instruction)
        chat = model.start_chat() # We will manually manage history in the prompt context if needed, 
                                  
        
        full_prompt = "Previous conversation:\n"
        for turn in recent_history:
            full_prompt += f"User: {turn['user']}\nModel: {turn['model']}\n"
        
        full_prompt += f"\nCurrent User Question: {user_query}"

        response = model.generate_content(full_prompt)
        response_text = response.text

        # 4. Update History
        new_turn = {"user": user_query, "model": response_text}
        history.append(new_turn)
        
        # Save back to Firestore (merge=True to create if not exists)
        history_ref.set({"turns": history}, merge=True)

        return jsonify({"answer": response_text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

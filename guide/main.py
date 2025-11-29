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

        # 1. Retrieve Knowledge Base
        kb_ref = db.collection("knowledge_base").document("devfest_schedule")
        kb_doc = kb_ref.get()
        
        knowledge_context = ""
        if kb_doc.exists:
            knowledge_context = kb_doc.to_dict().get("summary", "")
        else:
            knowledge_context = "No conference schedule is currently available."

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
        You are a helpful conference concierge for DevFest.
        Use the following Conference Schedule Information to answer the user's question.
        If the answer is not in the schedule, politely say you don't know.
        
        --- Conference Schedule ---
        {knowledge_context}
        ---------------------------
        """

        model = GenerativeModel(MODEL_ID, system_instruction=system_instruction)
        chat = model.start_chat() # We will manually manage history in the prompt context if needed, 
                                  # but here we can just send the history as context or rely on the model's statelessness with context injection.
                                  # For simplicity and robustness with the "history" list we fetched:
        
        # Let's construct a full prompt with history instead of using start_chat state, 
        # because we are in a stateless Cloud Run container and fetching history from DB.
        
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

        return jsonify({"response": response_text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

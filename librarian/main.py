import os
import json
from flask import Flask, request
from google.cloud import storage
from google.cloud import firestore
import vertexai
from vertexai.generative_models import GenerativeModel, Part

app = Flask(__name__)

# Initialize Google Cloud Clients
storage_client = storage.Client()
db = firestore.Client()

# Initialize Vertex AI
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# TODO: Update this to the correct model ID if "gemini-2.5-flash-001" is not the exact string
MODEL_ID = "gemini-flash-latest" 

@app.route("/", methods=["POST"])
def ingest():
    """
    Handles CloudEvents from Eventarc (GCS Object Finalize).
    """
    print("Event received.")
    
    # CloudEvents specification: Content-Type: application/cloudevents+json
    # However, Eventarc often sends the event as the body.
    # We'll try to parse the JSON body directly.
    try:
        event = request.get_json()
        if not event:
             msg = "no json body received"
             print(f"error: {msg}")
             return f"Bad Request: {msg}", 400
        
        print(f"Event body: {event}")

        # Extract bucket and file name from the event
        # Structure depends on the event type (google.cloud.storage.object.v1.finalized)
        # Usually it's in 'bucket' and 'name' fields of the data payload
        if 'bucket' in event: # Direct GCS notification format
             bucket_name = event['bucket']
             file_name = event['name']
        elif 'protoPayload' in event: # Audit log format (less common for direct triggers but possible)
             # This is complex, assume direct notification for workshop simplicity
             pass
        else:
             # Fallback for CloudEvent format where data is nested
             # This is the standard for Eventarc
             bucket_name = event.get('bucket')
             file_name = event.get('name')

        if not bucket_name or not file_name:
             msg = "Could not determine bucket or filename from event"
             print(f"error: {msg}")
             return f"Bad Request: {msg}", 400

        print(f"Processing file: {file_name} from bucket: {bucket_name}")

        # Download the file
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        # For Gemini Multimodal, we can pass the GCS URI directly!
        # This is much more efficient than downloading bytes.
        gcs_uri = f"gs://{bucket_name}/{file_name}"
        
        # Generate Summary
        model = GenerativeModel(MODEL_ID)
        
        prompt = """
        You are a helpful conference assistant. 
        Analyze the attached document (which is a conference schedule).
        Extract a structured summary of the conference schedule, including:
        - Key speakers
        - Topics covered
        - Session times
        
        Format the output as a clean, readable text summary that can be used to answer user questions.
        """
        
        # Create the part from GCS URI
        # Determine mime type based on extension
        mime_type = "application/pdf"
        if file_name.endswith(".txt"):
            mime_type = "text/plain"
        
        document_part = Part.from_uri(gcs_uri, mime_type=mime_type)
        
        response = model.generate_content([document_part, prompt])
        summary_text = response.text
        print("Summary generated successfully.")

        # Save to Firestore
        doc_ref = db.collection("knowledge_base").document("devfest_schedule")
        doc_ref.set({
            "summary": summary_text,
            "source_file": gcs_uri,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        print("Summary saved to Firestore.")

        return "OK", 200

    except Exception as e:
        print(f"Error processing event: {e}")
        return f"Internal Server Error: {e}", 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

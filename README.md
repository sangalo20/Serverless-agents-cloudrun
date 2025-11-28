# Serverless Agents on Cloud Run Workshop

Welcome to the Serverless Agents workshop! In this session, you will build a production-ready "Micro-Agent" system using Google Cloud Run, Vertex AI (Gemini 2.5 Flash), and Eventarc.

## Architecture

- **The Librarian**: An event-driven service that ingests PDFs, summarizes them, and stores knowledge.
- **The Guide**: A chat service that answers user questions based on the stored knowledge.

## Getting Started

We have prepared a Google Colab notebook that automates the setup, deployment, and testing of your agents.

### 🚀 Run the Workshop

Click the button below to open the workshop notebook in Google Colab:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/sangalo20/Severless-agents-cloudrun/blob/main/workshop_setup.ipynb)

**Note**: The link above is now configured for your repository.

## Prerequisites

- A Google Cloud Project with billing enabled.
- A Google Account.

## Repository Structure

- `librarian/`: Source code for the ingestion agent.
- `guide/`: Source code for the chat agent.
- `workshop_setup.ipynb`: The notebook to run the workshop.

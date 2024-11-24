# Ultimate Rules RAG

An AI-powered web application that answers questions about Ultimate Retrieval Augmented Generation (RAG). Meant to help you quickly find the rule you are looking for while on the field trying to resolve a dispute. It answers your question in plain text AND returns the full text of the relevant rule(s). Amazing!

**Note**: This project is a work in progress.

<img src="img/app_screenshot.png" width="600" alt="Ultimate Rules Chat Interface">

## Features

- Chat interface for Ultimate rules questions
- Secure user authentication
- Conversation history storage
- Responsive, clean UI design
- Answers questions based on the official 2024 USAU rules, and returns the full text of the relevant rules


## Tech Stack

### Frontend

- React
- Tailwind CSS
- Modern, responsive design

### Backend

- FastAPI (Python)
- RAG implementation for accurate rule retrieval
- JWT authentication

### Database

- PostgreSQL with pgvector for embeddings storage
- Stores user data, conversations, and vectorized rules

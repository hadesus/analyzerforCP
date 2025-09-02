# Clinical Protocol Analyzer

This project is a full-stack web application designed to analyze clinical protocols from `.docx` files. It extracts information about medications, enriches it with data from external medical databases, and provides an AI-powered analysis to generate an interactive, exportable report.

## Features

-   **.docx Parsing:** Upload a clinical protocol in `.docx` format.
-   **Automated Drug Extraction:** Uses AI (Google's Gemini model) to identify and extract structured information about medications mentioned in the text.
-   **Drug Name Normalization:** Maps brand names to their International Nonproprietary Name (INN) using the RxNav API, with an AI fallback.
-   **Regulatory Status Checks:** Verifies drug approval status against major international bodies:
    -   FDA (via openFDA API)
    -   EMA (via EMA's public API)
    -   BNF and WHO EML (via AI-powered checks)
-   **Dosage Comparison:** An AI-powered comparison between the dosage found in the protocol and the standard dosage from official labels.
-   **PubMed Integration:** Fetches relevant clinical studies (Systematic Reviews, Meta-Analyses, RCTs) from PubMed, complete with caching to ensure performance.
-   **AI-Powered Analysis:** Generates a GRADE evidence rating and a concise summary note in Russian for each medication.
-   **Interactive Frontend:** A responsive UI built with React to upload files and display results in a sortable, filterable table with expandable rows for details.
-   **Multiple Export Formats:** Export the final analysis report as a `.docx`, `.xlsx`, or `.json` file.

## Tech Stack

-   **Backend:** Python, FastAPI
-   **Frontend:** JavaScript, React
-   **AI:** Google Gemini (`gemini-2.5-flash`)
-   **Databases/APIs:** RxNav, openFDA, EMA's ePI, PubMed Entrez
-   **Caching:** Redis
-   **Core Python Libraries:** `python-docx`, `httpx`, `biopython`, `openpyxl`
-   **Core JS Libraries:** `axios`

## Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Prerequisites

-   Python 3.9+ and `pip`
-   Node.js and `npm`
-   A running Redis instance

### 2. Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a Python virtual environment and activate it:**
    - On macOS/Linux:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
    - On Windows:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    -   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    -   Open the new `.env` file and fill in your API keys for `GEMINI_API_KEY` and `PUBMED_API_KEY`, and your email for `PUBMED_API_EMAIL`.

5.  **Run the backend server:**
    ```bash
    uvicorn main:app --reload
    ```
    The backend API will be running at `http://127.0.0.1:8000`.

### 3. Frontend Setup

1.  **Open a new terminal window.**

2.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

3.  **Install dependencies:**
    ```bash
    npm install
    ```

4.  **Run the frontend development server:**
    ```bash
    npm start
    ```
    The React application will open automatically in your browser at `http://localhost:3000`. The frontend is configured to proxy API requests to the backend server running on port 8000.

You can now upload a `.docx` file through the web interface to start the analysis.

## Running with Docker

The easiest way to get the entire application running is with Docker Compose.

1.  **Ensure Docker is installed** and running on your machine.
2.  **Configure environment variables:**
    -   Copy the example environment file in the `backend` directory:
        ```bash
        cp backend/.env.example backend/.env
        ```
    -   Open `backend/.env` and fill in your API keys.
3.  **Build and run the services:**
    -   From the root of the project, run:
        ```bash
        docker-compose up --build
        ```
    - This command will build the images for the backend and frontend, and start all three services (`backend`, `frontend`, `redis`).
    - **Note:** If you change any configuration files (like `package.json` or `Dockerfile`), you need to run with the `--build` flag again to apply the changes to the image.
    - The frontend will be available at `http://localhost:3000`.

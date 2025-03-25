Receipt Processor
=================

A production-ready web service that processes receipts and calculates points based on defined rules, implemented in Python using Flask, SQLite, and Gunicorn.

Overview
--------

This Receipt Processor is a RESTful API service that:
1. Accepts receipt data via a POST endpoint
2. Stores receipt data persistently in an SQLite database
3. Calculates points for each receipt based on specified rules
4. Provides an endpoint to retrieve points for a specific receipt

Prerequisites
-------------

- Python 3.9+: Required for local execution.
- Docker: Optional, for containerized execution.
- curl: Recommended for testing API endpoints from the command line.
- SQLite CLI: Optional, for inspecting the database (`sqlite3` command).

Setup Instructions
------------------

Clone the Repository:
    git clone https://github.com/yourusername/receipt-processor.git
    cd receipt-processor

Configuration
-------------

- Port: Default is 8080. Override with the `PORT` environment variable:
    export PORT=5000
- Database Path: Default is `receipts.db`. Override with `DB_PATH`:
    export DB_PATH=/path/to/receipts.db

API Endpoints
-------------

Root Endpoint
- URL: /
- Method: GET
- Response: Welcome message
- Example: {"message": "Welcome to Receipt Processor. Use /receipts/process to submit a receipt or /receipts/<id>/points to get points."}

Process Receipt
- URL: /receipts/process
- Method: POST
- Request Body: Receipt JSON
- Response: JSON with receipt ID
- Example: {"id": "7fb1377b-b223-49d9-a31a-5a02701dd310"}

Get Points
- URL: /receipts/{id}/points
- Method: GET
- Response: JSON with points
- Example: {"points": 32}


How SQLite is Used
------------------

- Automatic Setup: The app initializes an SQLite database (`receipts.db`) on startup, creating a `receipts` table if it doesn’t exist.
- No Manual Config Needed: SQLite is embedded and file-based; the code handles table creation.
- Persistence: Data is stored in `receipts.db` in the project directory (or a custom `DB_PATH`).

Running the App
---------------

You can run the app using either Python locally or Docker. Below are the two options:

Option 1: Run Locally with Python
1. Install Dependencies:
   Create a virtual environment and install required packages:
       python -m venv venv
       source venv/bin/activate  # On Windows: venv\Scripts\activate
       pip install -r requirements.txt
2. Run:
       python app.py
   - Starts on `http://localhost:8080` (or the port specified by `PORT`).
   - Logs are written to `app.log` and the console.
   - Creates `receipts.db` if not present.


Option 2: Run with Docker
1. Build:
       docker build -t receipt-processor .
2. Run:
       docker run -p 8080:8080 -v $(pwd)/receipts.db:/app/receipts.db receipt-processor
   - Maps port 8080 on your host to the container (adjust to `-p 5000:8080` if `PORT=5000`).
   - Persists the SQLite database (`receipts.db`) in your local directory.
   - Logs appear in the terminal.

Testing Scenarios
-----------------

Run these tests after starting the app (via Python or Docker) using `curl` in a terminal. Each scenario tests a specific case, and you’ll need to extract the receipt ID from the `/receipts/process` response to test `/receipts/<id>/points`.

Test Scenario 1: Target Receipt (Multiple Items)
    # Process the receipt
    curl -X POST http://localhost:8080/receipts/process \
      -H "Content-Type: application/json" \
      -d '{
        "retailer": "Target",
        "purchaseDate": "2022-01-01",
        "purchaseTime": "13:01",
        "items": [
          {"shortDescription": "Mountain Dew 12PK", "price": "6.49"},
          {"shortDescription": "Emils Cheese Pizza", "price": "12.25"},
          {"shortDescription": "Knorr Creamy Chicken", "price": "1.26"},
          {"shortDescription": "Doritos Nacho Cheese", "price": "3.35"},
          {"shortDescription": " Klarbrunn 12-PK 12 FL OZ ", "price": "12.00"}
        ],
        "total": "35.35"
      }'
    - Expected Response: {"id": "<uuid>"}
    - Next Step: Copy the `<uuid>` from the response.
    - Get Points:
        curl http://localhost:8080/receipts/<uuid>/points
    - Expected Response: {"points": 33}
    - Verification: Check `app.log` for "Processed receipt <uuid> with 33 points".

Test Scenario 2: M&M Corner Market Receipt (Round Total, Afternoon Purchase)
    # Process the receipt
    curl -X POST http://localhost:8080/receipts/process \
      -H "Content-Type: application/json" \
      -d '{
        "retailer": "M&M Corner Market",
        "purchaseDate": "2022-03-20",
        "purchaseTime": "14:33",
        "items": [
          {"shortDescription": "Gatorade", "price": "2.25"},
          {"shortDescription": "Gatorade", "price": "2.25"},
          {"shortDescription": "Gatorade", "price": "2.25"},
          {"shortDescription": "Gatorade", "price": "2.25"}
        ],
        "total": "9.00"
      }'
    - Expected Response: {"id": "<uuid>"}
    - Next Step: Copy the `<uuid>` from the response.
    - Get Points:
        curl http://localhost:8080/receipts/<uuid>/points
    - Expected Response: {"points": 109}
    - Verification: Check `app.log` for "Processed receipt <uuid> with 109 points".

Test Scenario 3: Invalid Receipt (Missing Field)
    curl -X POST http://localhost:8080/receipts/process \
      -H "Content-Type: application/json" \
      -d '{
        "retailer": "Test",
        "purchaseDate": "2022-01-01",
        "items": [{"shortDescription": "Item", "price": "1.00"}],
        "total": "1.00"
      }'
    - Expected Response: {"error": "Missing required fields"} (HTTP 400)
    - Verification: Check `app.log` for "Validation error".

Test Scenario 4: Non-Existent Receipt ID
    curl http://localhost:8080/receipts/invalid-id/points
    - Expected Response: {"error": "Receipt not found"} (HTTP 404)
    - Verification: Check `app.log` for "Retrieved points" or error.

Inspecting the Database
-----------------------

To verify data persistence:
    sqlite3 receipts.db
    .tables  # Shows "receipts"
    SELECT * FROM receipts;  # Lists stored receipts
    .exit

Troubleshooting
---------------

- Port Conflict: Use a different port:
    export PORT=5000
    python app.py  # Or: docker run -p 5000:8080 ...
- Permissions: Ensure the directory is writable for `receipts.db`:
    chmod 666 receipts.db
- Logs: Check `app.log` for errors if endpoints fail.
- Docker Issues: Verify volume mount path is correct (use absolute path if needed, e.g., `-v /full/path/to/receipts.db:/app/receipts.db`).




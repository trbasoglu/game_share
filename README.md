# Game Code Share

A simple web application for sharing one-time visible game codes. Each IP address can only receive one code.

## Features

- One-time code distribution
- IP-based tracking to prevent multiple code requests
- Admin interface to add new codes
- Clean and modern UI
- SQLite database for storing codes

## Setup

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:5000`

## Usage

### Getting a Code
- Click the "Get Code" button to receive your one-time code
- Each IP address can only receive one code
- Once a code is viewed, it cannot be accessed again

### Adding New Codes (Admin)
- Use the admin section at the bottom of the page
- Enter a new code in the input field
- Click "Add Code" to add it to the database

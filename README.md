# Family Management Solution

A comprehensive web application designed to simplify family organization and logistics.

## Overview

Family Management Solution (FMS) is a full-stack web application that provides three core tools:

1. **Checklist Tool** - Create, run, and track custom checklists with automated email reporting
2. **Carpool Management** - Manage carpool schedules with a calendar or list view
3. **Meal Planning** - Plan meals for the week with AI-driven suggestions based on historical data

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, JavaScript, CSS (with Tailwind CSS)
- **Database**: PostgreSQL
- **Search**: Azure Cognitive Search
- **Authentication**: JWT-based authentication

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Azure Cognitive Search (Azure account required)

### Installation

1. Clone the repository
```
git clone <repository-url>
cd family-management-solution
```

2. Create a virtual environment and install dependencies
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up your environment variables in a `.env` file
```
ENVIRONMENT=dev
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fms_dev
ENABLE_SEARCH=true
SEARCH_SERVICE_NAME=your-azure-search-service-name
SEARCH_API_KEY=your-azure-search-api-key
SECRET_KEY=your_secret_key
EMAIL_SENDER=noreply@familymanagement.app
SENDGRID_API_KEY=
```

4. Run the application
```
python main.py
```

5. Open your browser and navigate to http://localhost:8000

## Features

### Checklist Tool

- Create checklists with required and optional items
- Run checklists, marking items as complete
- Finish the checklist and send a report via email
- Search and organize checklists by category

### Carpool Management

- Add, edit, and delete carpool events
- View events in a calendar (large screens) or list (mobile)
- Search for events by description or destination

### Meal Planning

- Plan meals for the entire week
- Get AI-generated meal suggestions based on your history
- Search for meal ideas

## Development

### Environment Setup

The application supports three environments:

- `dev` - Development environment (default)
- `test` - Testing environment
- `prod` - Production environment

### Database Migrations

Database tables are created automatically when running the application for the first time.

### Azure Search Setup

Azure Search indices are created automatically when running the application. You'll need a valid Azure Cognitive Search service name and API key in your environment variables.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
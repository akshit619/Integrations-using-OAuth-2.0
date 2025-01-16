# OAuth and OAuth 2.0 Integrations and Data Loading for HubSpot, Notion, and AirTable  

This repository contains the implementation of a full-stack project focused on building and completing integrations for HubSpot, Notion, and AirTable. It features both backend and frontend components, including OAuth flows for authentication and data retrieval from these platforms.  

## Features  

### 1. OAuth Integrations  
- Completed OAuth flows for HubSpot, Notion, and AirTable.  
- Implemented authentication functions (`authorize`, `oauth2callback`, and `get_credentials`) in Python using FastAPI for all integrations.  
- Set up secure handling of client credentials and token exchanges.  

### 2. Data Loading  
- Developed data retrieval functions to query HubSpot, Notion, and AirTable APIs.  
- Processed and returned data as `IntegrationItem` objects, ensuring consistency across all integrations.  
- Designed endpoints to retrieve and handle data dynamically from each platform.  

### 3. Frontend Integration  
- Enhanced the React-based frontend to support seamless interaction with HubSpot, Notion, and AirTable integrations.  
- Built and updated JavaScript files (`hubspot.js`, `notion.js`, and `airtable.js`) to connect the UI with backend functionality.  
- Ensured a user-friendly experience for managing integration workflows.  

## Tech Stack  
- **Frontend:** JavaScript (React)  
- **Backend:** Python (FastAPI)  
- **Database/Cache:** Redis  

## Setup

## Backend:
1. Navigate to backend directory
2. pip install -r requirements.txt
3. uvicorn main:app

## Redis:
1. redis-server (in shell terminal)

## Frontend:
1. navigate to frontend directory
2. npm i
3. npm run start

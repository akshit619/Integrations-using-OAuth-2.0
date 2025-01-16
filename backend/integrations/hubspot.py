# hubspot.py

import datetime
import json
import secrets
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
import base64
import hashlib
from dotenv import load_dotenv
import os

from hubspot import HubSpot
from pprint import pprint
from hubspot.crm.contacts import ApiException

import requests
from integrations.integration_item import IntegrationItem

from integrations.redis_client import add_key_value_redis, get_value_redis, delete_key_redis

load_dotenv('/Users/akshitbarnwal/Desktop/integrations_technical_assessment/backend/integrations/.env.hubspot')
CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
SCOPE = 'crm.objects.contacts.write%20oauth%20crm.objects.deals.read%20crm.objects.deals.write%20crm.objects.contacts.read'
AUTHORIZATION_URL = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&scope={SCOPE}&redirect_uri={REDIRECT_URI}'


async def authorize_hubspot(user_id, org_id):
    state_data = {
        "state": secrets.token_urlsafe(32),
        "user_id": user_id,
        "org_id": org_id,
    }
    encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode('utf-8')).decode('utf-8')
    await add_key_value_redis(f"hubspot_state:{org_id}:{user_id}", json.dumps(state_data), expire=600)

    auth_url = f'{AUTHORIZATION_URL}&state={encoded_state}'
    return auth_url



async def oauth2callback_hubspot(request: Request):
    error = request.query_params.get('error')
    if error:
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description', error))
    
    # Extract required parameters from the query
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail="Authorization code or state is missing.")
    
    # Decode and parse the state
    try:
        state_data = json.loads(base64.urlsafe_b64decode(encoded_state).decode('utf-8'))
    except (json.JSONDecodeError, base64.binascii.Error) as e:
        raise HTTPException(status_code=400, detail=f"Invalid state parameter: {str(e)}")
    
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')
    original_state = state_data.get('state')
    if not user_id or not org_id or not original_state:
        raise HTTPException(status_code=400, detail="Invalid state data.")
    
    # Fetch the original state from Redis
    redis_key = f'hubspot_state:{org_id}:{user_id}'
    saved_state = await get_value_redis(redis_key)
    if not saved_state:
        raise HTTPException(status_code=400, detail="State not found in Redis or has expired.")
    
    # Validate the state value
    try:
        saved_state_data = json.loads(saved_state)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse saved state: {str(e)}")
    
    if saved_state_data.get('state') != original_state:
        raise HTTPException(status_code=400, detail="State mismatch. Possible CSRF attack.")
    
    # Exchange authorization code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_response, _ = await asyncio.gather(
                client.post(
                    'https://api.hubapi.com/oauth/v1/token',
                    data={
                        "grant_type": "authorization_code",
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "redirect_uri": REDIRECT_URI,
                        "code": code,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ),
                delete_key_redis(redis_key),
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to HubSpot token endpoint: {str(e)}")
    
    # Check the token response status
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=token_response.status_code,
            detail=f"Failed to fetch tokens: {token_response.text}",
        )
    
    try:
        response_json = token_response.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse token response from HubSpot."
        )
    
    # Save the credentials in Redis
    credentials_key = f'hubspot_credentials:{org_id}:{user_id}'
    await add_key_value_redis(credentials_key, json.dumps(response_json), expire=600)

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    
    # Close the browser window
    return HTMLResponse(content=close_window_script)



async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')

    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials



def create_integration_item_metadata_object(response_list: str, item_type: str) -> IntegrationItem:
    integration_item_metadata = IntegrationItem(
        id=response_list.id,
        name=f"{response_list.properties['firstname']} {response_list.properties['lastname']}",
        type=item_type,
        url=response_list.properties['email'],
        creation_time=response_list.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        last_modified_time=response_list.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
    )

    return integration_item_metadata


async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    credentials = json.loads(credentials)
    url = 'https://api.hubapi.com/crm/v3/objects/contacts'
    list_of_integration_item_metadata = []
    list_of_responses = []

    client = HubSpot()
    client.access_token = credentials.get('access_token')

    try:
        api_response = client.crm.contacts.basic_api.get_page(limit=10, archived=False)
        # pprint(api_response)
    except ApiException as e:
        print("Exception when calling basic_api->get_page: %s\n" % e)

    results = api_response.results

    for contact in results:
        integration_item_metadata = create_integration_item_metadata_object(contact, 'Contact')
        list_of_integration_item_metadata.append(integration_item_metadata)

    return list_of_integration_item_metadata
    
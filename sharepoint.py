import msal
import requests
import pandas as pd
import json
import numpy as np

import streamlit as st

client_id = st.secrets["CLIENT_ID"]
client_secret = st.secrets["CLIENT_SECRET"]
tenant_id = st.secrets["TENANT_ID"]

authority = f"https://login.microsoftonline.com/{tenant_id}"
scope = ["https://graph.microsoft.com/.default"]
def make_connection():
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )

    token_result = app.acquire_token_for_client(scopes=scope)
    access_token = token_result["access_token"]

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    site_resp = requests.get(
        "https://graph.microsoft.com/v1.0/sites/chandrudemo.sharepoint.com:/sites/PRProcessing",
        headers=headers
    )
    site_id = site_resp.json()["id"]

    list_name = "standardized_items"  # Replace with your actual list name

    return headers, site_id, list_name


def fetch_full_list():
    headers, site_id, list_name = make_connection()

    all_items = []
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items?expand=fields"

    while url:
        resp = requests.get(url, headers=headers).json()
        items = resp.get("value", [])
        for item in items:
            all_items.append(item["fields"])
        # Pagination
        url = resp.get("@odata.nextLink", None)

    df = pd.DataFrame(all_items)
    # Filter and rename columns
    df_filtered = df.iloc[:, 1:5].rename(columns={
    df.columns[1]: "Original Item",
    df.columns[2]: "Standardized Name",
    df.columns[3]: "Price",
    df.columns[4]: "Embedding"
})
    return df_filtered


def save_to_masterlist(new_rows_df):
    headers, site_id, list_name = make_connection()
    # Step 2: Push only new rows to SharePoint
    for _, row in new_rows_df.iterrows():
        def safe(val, fallback=""):
            if isinstance(val, (list, np.ndarray)):
                return json.dumps(val)  # convert array to string
            if pd.isna(val) or val is None:
                return fallback
            return val

        payload = {
            "fields": {
                "Title": row["Original Item"],
                "field_1": row["Standardized Name"],
                "field_2": float(safe(row["Price"], 0)),  # must be a float
                "field_3": safe(row["Embedding"])         # string or null
            }
        }

        response = requests.post(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items",
            headers=headers,
            json=payload
        )

        if response.status_code in [200, 201]:
            print("✅ Added:", row["Original Item"])
        else:
            print("❌ Error:", response.status_code, response.text)

def delete_all_items_from_list(site_id, list_id, headers):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields"
    response = requests.get(url, headers=headers).json()
    for item in response.get("value", []):
        item_id = item["id"]
        del_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items/{item_id}"
        del_resp = requests.delete(del_url, headers=headers)
        print(f"🗑️ Deleted item {item_id} → {del_resp.status_code}")


def create_new_sharepoint_list(list_name, site_id, headers):
    create_list_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    displayName = f"BOQ {list_name}"
    list_payload = {
        "displayName": displayName,
        "list": {
            "template": "genericList"
        },
        "columns": [
            {"name": "PRName", "displayName": "PR Name", "text": {}},
            {"name": "ItemName", "displayName": "Item Name", "text": {}},
            {"name": "StandardizedName", "displayName": "Standardized Name", "text": {}},
            {"name": "Level1Category", "displayName": "Level 1 Category", "text": {}},
            {"name": "Level2Category", "displayName": "Level 1 Category", "text": {}},
            {"name": "Level3Category", "displayName": "Level 1 Category", "text": {}},
            {"name": "Quantity", "displayName": "Quantity", "number": {}},
            {"name": "Price", "displayName": "Price", "number": {}},
            {"name": "TotalPrice", "displayName": "Total Price", "number": {}},
        ]  
    }
    print("Creating new SharePoint list...")
    print("Payload:", list_payload)
    resp = requests.post(create_list_url, headers=headers, json=list_payload)
    print(resp.status_code, resp.json())
    return displayName, resp.status_code


def save_to_new_list_boq(standardized_df):
    headers, site_id, list_nam = make_connection()
    list_name, status_code = create_new_sharepoint_list(standardized_df["PR Name"].iloc[0], site_id, headers)
    if status_code == 409:
        print("List already exists. Deleting all items...")
        delete_all_items_from_list(site_id, list_name, headers)
    # Step 2: Push only new rows to SharePoint
    for _, row in standardized_df.iterrows():
        payload = {
            "fields": {
                "PRName": row["PR Name"],
                "ItemName": row["Item Name"],
                "StandardizedName": row["Standardized Name"],
                "Level1Category": row["Level 1 Category"],
                "Level2Category": row["Level 2 Category"],
                "Level3Category": row["Level 3 Category"],
                "Quantity": int(row["Quantity"]),
                "Price": float(row["Price"]),
                "TotalPrice": float(row["Total Price"])
            }
        }

        resp = requests.post(
            f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items",
            headers=headers,
            json=payload
        )

        if resp.status_code not in [200, 201]:
            print("❌", resp.status_code, resp.text)
        else:
            print("✅ Row added")

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, util
import json
import os
import torch

# Load model once
model = SentenceTransformer('all-MiniLM-L6-v2')

# Excel path
excel_path = "standardized_items.xlsx"

# Load data
master_list = pd.read_excel(excel_path)

if 'Embedding' not in master_list.columns:
    master_list['Embedding'] = master_list.apply(lambda row: model.encode(f"{row['Original Item']} {row['Standardized Name']}", convert_to_numpy=True).tolist(), axis=1)
    master_list.to_excel(excel_path, index=False)


# Function to process a new user query
def find_or_generate_standardized_name(user_query, llm, df):
    query_embedding = model.encode(user_query, convert_to_numpy=True)

    # Convert embeddings to numpy
    stored_embeddings = np.array([json.loads(e) if isinstance(e, str) else e for e in df['Embedding']], dtype=np.float32)


    # Compute cosine similarities
    similarities = util.cos_sim(query_embedding, stored_embeddings)[0]

    # Find best match
    best_idx = int(torch.argmax(similarities))
    best_score = similarities[best_idx].item()

    print(f"Best match score: {best_score:.3f}")

    # If above threshold, return existing
    if best_score >= 0.85:
        return {"name": str(df.iloc[best_idx]['Standardized Name']), "price": df.iloc[best_idx]['Price'], "message": "Found Match in List"}

    prompt = f"""
You are a naming standardizer.

Your job is to convert item names into a standardized format using the pattern:  
**Category_SpecificDescription**

🔒 STRICT RULES:
- Use the **examples below as your only guide**
- Do not invent new patterns or words
- Use underscores and CamelCase where shown
- Return ONLY the standardized name — nothing else
- Do not include words like 'School', 'Company', or 'General' in the output.
- These terms are irrelevant to the category and must be strictly excluded.
- Only return the core functional or item-related name."
- Output must be in **this exact JSON format** (no extra keys, no explanations):

{{
  "name": "Standardized_Name_Here"
}}

✅ Good Example:
Input: "UPS Backup Battery Units with Installation Services"  
Output: {{ "name": "General_UPS_Backup_Battery" }}

---

Examples:
"UPS Backup Battery Units with Installation Services" → "General_UPS_Backup_Battery"
"UPS Battery Rack and Cabling" → "UPSBatteryRack_Cabling_Setup"
"Installation & Testing of UPS Batteries" → "General_Installation_&_Testing"
"Removal of Existing Parquet Flooring" → "Flooring_Parquet_Removal"
"Supply of New Wooden Parquet Panels" → "Flooring_Parquet_WoodenPanels"
"Installation and Finishing of Parquet Flooring" → "Flooring_Parquet_InstallationFinishing"
"Preventive Maintenance for CCTV Systems" → "CCTV_Maintenance_Preventive"
"Door Access Control System AMC" → "AccessControl_AMC_Annual"
"Replacement of Faulty Cameras or Sensors" → "General_Replacement_Of_Faulty"
"Removal of Broken Mirror Panels" → "Mirror_Broken_Removal"
"Supply of Pool-Grade Safety Mirror" → "Mirror_Safety_PoolGrade"
"Installation of Mirror with Sealants" → "Mirror_Installation_Sealants"
"Inspection and Assessment of Pole" → "Pole_Inspection_Assessment"
"Reinforcement of Base with Concrete" → "Base_Reinforcement_Concrete"
"Repainting and Sealing of Metal Surface" → "MetalSurface_Repainting_Sealing"
"Chiller Compressor Unit" → "Chiller_Compressor_Unit"
"Trash Collection and Disposal" → "Waste_Trash_Collection"

---

Input: "{user_query}"
"""
    # Else, fallback to LLM
    print("⚠️ Not found confidently, falling back to LLM...")
    response = llm.invoke(prompt)
    response  = response.content.strip()
    standardized_name = json.loads(response)["name"]

    if standardized_name in df['Standardized Name'].values:
        return {"name": standardized_name, "price": df.iloc[best_idx]['Price'], "message": "Found Match in List"}

    else:
        new_data = {col: None for col in df.columns}
        new_data['Original Item'] = user_query
        new_data['Standardized Name'] = standardized_name
        new_data['Price'] = 10
        # Generate embedding for the new data
        new_data['Embedding'] = model.encode(f"{user_query} {standardized_name}", convert_to_numpy=True).tolist()
        # Append new data to the DataFrame
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        df.to_excel(excel_path, index=False)
        return {"name": standardized_name, "price": 10, "message": "Name was not present in existing list, added to list"}

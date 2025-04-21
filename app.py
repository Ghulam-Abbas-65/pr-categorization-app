import os
import streamlit as st
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from naming_convention import find_or_generate_standardized_name
import pandas as pd
import json
from io import BytesIO

# Set your Groq API Key here or use st.secrets
os.environ["GROQ_API_KEY"] = "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"

# Initialize LLaMA 3.3 on Groq
llm_standardize = ChatGroq(temperature=0, model_name="llama3-8b-8192")
llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")

# -------------------------------
# Load Master Item File
excel_path = "standardized_items.xlsx"
master_list = pd.read_excel(excel_path)
standardized_names = master_list['Standardized Name'].values.tolist() # Standardized names list

LEVEL_1_CATEGORIES = [
    
    "Hard FM",
    "Soft FM",
    
]

LEVEL_2_CATEGORIES = {
    "Hard FM": [
        "Integrated FM",
        "Civil Works",
        "FLS",
        "Mechanical",
        "Electrical",
        "Electro Mechanical",
        "Construction & Renovation"
    ],
    "Soft FM": [
        "Pest Control",
        "Cleaning",
        "Security Services",
        "Landscape",
        "Waste Management",
        "Manpower",
        "Groundskeeping",
        "Housekeeping"
    ]
}
LEVEL_3_CATEGORIES = {
    "Hard FM": {
        "Integrated FM": [],
        "Civil Works": [],
        "FLS": [],
        "Mechanical": [
            "Pumps", "Belts", "Water Distribution Systems", "Valves", "Bearings",
            "Fasteners", "Seals and Gaskets", "Hose and Fittings", "Pulleys", "Water Treatment Equipments"
        ],
        "Electrical": [
            "Installation & Maintenance Services", "Switchgears", "Electrical Cables, Hardware & Supplies",
            "Lamp, Light Fittings and Accessories", "Power Backup Systems",
            "Measuring, Observing and Testing Instruments", "Motors"
        ],
        "Electro Mechanical": [
            "Elevators & Escalators & Travelator systems", "HVAC Systems",
            "Automatic Doors & Shutters", "Car Parking System & Supplies", "BMS"
        ],
        "Construction & Renovation": [
            "Fit Out / Joinery", "Outdoor"
        ]
    },
    "Soft FM": {
        "Pest Control": [],
        "Cleaning": [
            "Tank Cleaning", "Indoor Cleaning", "Outdoor Cleaning", "General Cleaning",
            "Facade Cleaning", "Sewerage Cleaning"
        ],
        "Security Services": [],
        "Landscape": [
            "Indoor", "Outdoor", "Tree Rental", "Flower Arrangement"
        ],
        "Waste Management": [],
        "Manpower": [
            "Housekeeping", "Driver", "Stewarding", "Movers"
        ]
    }
}

# -------------------------------
# Load Prompt Templates from Files
# -------------------------------
with open("prompt1.txt", "r") as file:
    level1_prompt_template = file.read()

with open("prompt2.txt", "r") as file:
    level2_prompt_template = file.read()

with open("prompt3.txt", "r") as file:
    level3_prompt_template = file.read()

# Create PromptTemplate objects
level1_prompt = PromptTemplate(
    input_variables=["purchase_req", "item_name", "level1_options"],
    template=level1_prompt_template
)


level2_prompt = PromptTemplate(
    input_variables=["purchase_req", "item_name", "level1", "level2_options"],
    template=level2_prompt_template
)


level3_prompt = PromptTemplate(
    input_variables=["purchase_req", "item_name", "level1", "level2", "level3_options"],
    template=level3_prompt_template
)

# Chains
level1_chain = LLMChain(llm=llm, prompt=level1_prompt)
level2_chain = LLMChain(llm=llm, prompt=level2_prompt)
level3_chain = LLMChain(llm=llm, prompt=level3_prompt)

# Classification function
def classify_purchase_req(purchase_req: str, item_name: str):
    # Level 1
    level1 = level1_chain.run(
        purchase_req=purchase_req,
        item_name=item_name,
        level1_options=str(LEVEL_1_CATEGORIES)
    ).strip()

    # Level 2
    level2_list = LEVEL_2_CATEGORIES.get(level1, [])
    level2 = level2_chain.run(
        purchase_req=purchase_req,
        item_name=item_name,
        level1=level1,
        level2_options=str(level2_list)
    ).strip()

    # Level 3
    level3_list = LEVEL_3_CATEGORIES.get(level1, {}).get(level2, [])
    level3 = level3_chain.run(
        purchase_req=purchase_req,
        item_name=item_name,
        level1=level1,
        level2=level2,
        level3_options=str(level3_list)
    ).strip()

    return {
        "purchase_req": purchase_req,
        "item_name": item_name,
        "level_1_category": level1,
        "level_2_category": level2,
        "level_3_category": level3
    }



# -------------------------------
# Streamlit UI
# -------------------------------
st.title("🧾 Purchase Requisition Classifier")

# --- Inputs ---
purchase_req = st.text_area("Enter Purchase Requisition Description")
item_name = st.text_input("Enter Item or Service Name")
quantity = st.number_input("Enter Quantity", min_value=1, step=1, value=1)

# --- Buttons Side by Side ---
col1, col2, col3 = st.columns(3)

if "last_action" not in st.session_state:
    st.session_state.last_action = None

with col1:
    if st.button("Classify"):
        st.session_state.last_action = "classify"

with col2:
    if st.button("Standardized Name"):
        st.session_state.last_action = "standardize"

with col3:
    if st.button("Generate BOQ"):
        st.session_state.last_action = "boq"

# --- Unified Output Area Below ---
st.markdown("---")  # Horizontal line for separation

if st.session_state.last_action == "classify":
    if purchase_req.strip() and item_name.strip():
        with st.spinner("Classifying..."):
            result = classify_purchase_req(purchase_req, item_name)

        st.success("Classification Complete!")
        st.markdown(f"**Level 1 (Main Category):** `{result['level_1_category']}`")
        st.markdown(f"**Level 2 (Subcategory):** `{result['level_2_category']}`")
        st.markdown(f"**Level 3 (Specific Function):** `{result['level_3_category']}`")
    else:
        st.warning("Please fill both the PR and Item/Service fields.")

elif st.session_state.last_action == "standardize":
    if item_name:
        name = find_or_generate_standardized_name(item_name, llm_standardize, master_list)
        print(name)
        standardized_name = name["name"]
        if name["message"] == "Name was not present in existing list, added to list":
            st.success(f"New Standardized Name Added: {standardized_name}")

        elif name["message"] == "Found Match in List":
            st.success(f"Standardized Name Found: {standardized_name}")

    else:
        st.error("Please enter an original name")

elif st.session_state.last_action == "boq":
    if item_name:
        boq_df = pd.read_excel("boq_template.xlsx", sheet_name='BOQ')
        name = find_or_generate_standardized_name(item_name, llm_standardize, master_list)
        standardized_name = name["name"]
        price = name["price"]
        total_price = price * quantity
        print(f"Standardized Name: {standardized_name}, Price: {price}, Total Price: {total_price}")
        start_row = 1
        new_row = {
            "Item #": start_row,
            "Item Name": purchase_req,
            "Item Description": item_name,
            "Quantity": quantity,
            "Cost/Unit": price,
            "Total Price": total_price
        }
        boq_df = pd.concat([boq_df, pd.DataFrame([new_row])], ignore_index=True)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            boq_df.to_excel(writer, index=False, sheet_name='BOQ')
        processed_data = output.getvalue()
        st.download_button(
            label="Download BOQ",
            data=processed_data,
            file_name="BOQ.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.info("BOQ Generated!!!!")
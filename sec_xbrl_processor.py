import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import json

def fetch_xbrl_json(filing_url, api_key):
    """
    Fetches XBRL JSON data from SEC API.io for a given filing URL
    """
    xbrl_converter_api_endpoint = "https://api.sec-api.io/xbrl-to-json"
    final_url = f"{xbrl_converter_api_endpoint}?htm-url={filing_url}&token={api_key}"
    
    response = requests.get(final_url)
    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
    
    return json.loads(response.text)

def save_xbrl_json(xbrl_json, filename="xbrl_data.json"):
    """
    Saves XBRL JSON data to a file
    """
    with open(filename, "w") as f:
        json.dump(xbrl_json, f, indent=2)
    
    return filename

def get_income_statement(xbrl_json):
    """
    Converts XBRL JSON income statement data to a pandas DataFrame
    """
    income_statement_store = {}

    # iterate over each US GAAP item in the income statement
    for usGaapItem in xbrl_json['StatementsOfIncome']:
        values = []
        indices = []

        for fact in xbrl_json['StatementsOfIncome'][usGaapItem]:
            # only consider items without segment
            if 'segment' not in fact:
                index = fact['period']['startDate'] + '-' + fact['period']['endDate']
                # ensure no index duplicates are created
                if index not in indices:
                    values.append(fact['value'])
                    indices.append(index)                    

        income_statement_store[usGaapItem] = pd.Series(values, index=indices) 

    income_statement = pd.DataFrame(income_statement_store)
    # switch columns and rows so that US GAAP items are rows and each column header represents a date range
    return income_statement.T 

def get_balance_sheet(xbrl_json):
    """
    Converts XBRL JSON balance sheet data to a pandas DataFrame
    """
    balance_sheet_store = {}

    for usGaapItem in xbrl_json['BalanceSheets']:
        values = []
        indices = []

        for fact in xbrl_json['BalanceSheets'][usGaapItem]:
            # only consider items without segment
            if 'segment' not in fact:
                index = fact['period']['instant']

                # avoid duplicate indices with same values
                if index in indices:
                    continue
                    
                # add 0 if value is nil
                if "value" not in fact:
                    values.append(0)
                else:
                    values.append(fact['value'])

                indices.append(index)                    

        balance_sheet_store[usGaapItem] = pd.Series(values, index=indices) 

    balance_sheet = pd.DataFrame(balance_sheet_store)
    # switch columns and rows so that US GAAP items are rows and each column header represents a date instant
    return balance_sheet.T

def get_cash_flow_statement(xbrl_json):
    """
    Converts XBRL JSON cash flow statement data to a pandas DataFrame
    """
    cash_flows_store = {}

    for usGaapItem in xbrl_json['StatementsOfCashFlows']:
        values = []
        indices = []

        for fact in xbrl_json['StatementsOfCashFlows'][usGaapItem]:        
            # only consider items without segment
            if 'segment' not in fact:
                # check if date instant or date range is present
                if "instant" in fact['period']:
                    index = fact['period']['instant']
                else:
                    index = fact['period']['startDate'] + '-' + fact['period']['endDate']

                # avoid duplicate indices with same values
                if index in indices:
                    continue

                if "value" not in fact:
                    values.append(0)
                else:
                    values.append(fact['value'])

                indices.append(index)                    

        cash_flows_store[usGaapItem] = pd.Series(values, index=indices) 

    cash_flows = pd.DataFrame(cash_flows_store)
    return cash_flows.T


# Update the main app to include tab6
def add_tab6():
    with st.expander("About SEC XBRL Processing", expanded=False):
        st.markdown("""
        ## SEC XBRL Financial Data Processor
        
        This tab allows you to process SEC filings in XBRL format directly from the SEC website. The tool:
        
        1. Takes any SEC filing URL (10-K, 10-Q, etc.)
        2. Converts the XBRL data to structured JSON 
        3. Extracts Income Statement, Balance Sheet, and Cash Flow Statement
        4. Displays the financial data and visualizations
        
        You'll need an API key from SEC-API.io to use this functionality.
        """)
    
    st.header("🧮 SEC XBRL Financial Data Processor")
    
    filing_url = st.text_input(
        "Enter SEC Filing URL", 
        value="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.html",
        help="URL of the SEC filing HTML document (10-K, 10-Q, etc.)"
    )
    
    api_key = st.text_input(
        "Enter SEC-API.io API Key", 
        value="44ba705581dee21a56a223d5418b0d944702a85ac447047ed3a4b1f6f2ace0db",
        help="Your SEC-API.io API key for XBRL conversion"
    )
    
    if st.button("Process XBRL Filing", key="process_xbrl"):
        if not filing_url or not api_key:
            st.warning("⚠️ Please enter both a filing URL and an API key.")
        else:
            try:
                with st.spinner("Fetching and processing XBRL data..."):
                    # Fetch XBRL JSON data
                    xbrl_json = fetch_xbrl_json(filing_url, api_key)
                    
                    # Save to file (optional)
                    filename = save_xbrl_json(xbrl_json)
                    st.success(f"✅ Successfully fetched XBRL data and saved to {filename}")
                    
                    # Extract financial statements
                    income_statement = get_income_statement(xbrl_json)
                    balance_sheet = get_balance_sheet(xbrl_json)
                    cash_flows = get_cash_flow_statement(xbrl_json)
                    
                    # Display tabs for each financial statement
                    statement_tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flows"])
                    
                    with statement_tabs[0]:
                        st.header("Income Statement")
                        if not income_statement.empty:
                            st.dataframe(income_statement)
                            
                            # Export button
                            csv = income_statement.to_csv()
                            st.download_button(
                                label="Download Income Statement CSV",
                                data=csv,
                                file_name="income_statement.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("No income statement data found in this filing")
                    
                    with statement_tabs[1]:
                        st.header("Balance Sheet")
                        if not balance_sheet.empty:
                            st.dataframe(balance_sheet)
                            
                            # Export button
                            csv = balance_sheet.to_csv()
                            st.download_button(
                                label="Download Balance Sheet CSV",
                                data=csv,
                                file_name="balance_sheet.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("No balance sheet data found in this filing")
                    
                    with statement_tabs[2]:
                        st.header("Cash Flow Statement")
                        if not cash_flows.empty:
                            st.dataframe(cash_flows)
                            
                            # Export button
                            csv = cash_flows.to_csv()
                            st.download_button(
                                label="Download Cash Flows CSV",
                                data=csv,
                                file_name="cash_flows.csv",
                                mime="text/csv"
                            )
                        else:
                            st.warning("No cash flow data found in this filing")
                    
                    
            except Exception as e:
                st.error(f"Error processing XBRL data: {str(e)}")
                st.info("Check if the URL is correct and accessible, or try a different API key.")

# To integrate this with your app, add tab6 to your main app's tabs
# Replace the main tabs declaration with:
# tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Data Collection", "🌐 URL Fetcher", "📂 MD&A Extraction", "📈 Advanced Analysis", "Extract Financials", "XBRL Processing"])
# And add with tab6: add_tab6()
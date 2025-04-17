import streamlit as st
from pathlib import Path
import shutil
import pandas as pd
from edgar_downloader import get_filing_types, download_edgar_filings, download_and_extract_mda
from mda_analyzer_gemini import analyze_mda_with_gemini, load_gemini_api_key

st.set_page_config(page_title="SEC Filings Downloader and Analyzer", layout="centered"  )
st.title("SEC Filings Downloader and Analyzer")

# Initialize session state variables if they don't exist
if 'downloaded_files' not in st.session_state:
    st.session_state.downloaded_files = []
if 'mda_dir' not in st.session_state:
    st.session_state.mda_dir = None
if 'identifier' not in st.session_state:
    st.session_state.identifier = None
if 'filing_type' not in st.session_state:
    st.session_state.filing_type = None

st.markdown("Enter a **company ticker** (e.g., `AAPL`) or a **CIK number** (e.g., `320193`).")

user_input = st.text_input("Ticker or CIK").strip()
filing_type = st.selectbox("Select Filing Type", get_filing_types())
years_back = st.slider("Years Back", 1, 20, 5)

if st.button("📥 Download Filings"):
    if not user_input:
        st.warning("⚠️ Please enter a ticker or CIK.")
    else:
        ticker, cik = (None, user_input) if user_input.isdigit() else (user_input.upper(), None)
        identifier = ticker if ticker else cik
        ## Aman's code starts here
        ## FetchIncomeStatements(ticker, cik,filing_type,years_back)
        ## Aman's code ends here
        with st.spinner("Downloading filings and extracting MD&A sections..."):
            success, count, mda_count = download_and_extract_mda(
                ticker=ticker,
                cik=cik,
                filing_type=filing_type,
                years_back=years_back
            )
            if success and count > 0:
                st.success(f"✅ Downloaded {count} filings and extracted {mda_count} MD&A sections.")
                
                # Store information about the download
                data_dir = Path("edgar_data")
                mda_dir = data_dir / "mda_sections" / identifier / filing_type
                
                # Save the list of downloaded files
                if mda_dir.exists():
                    st.session_state.downloaded_files = list(mda_dir.glob("*.txt"))
                    st.session_state.mda_dir = mda_dir
                    st.session_state.identifier = identifier
                    st.session_state.filing_type = filing_type
                
                # Create a ZIP file containing both original filings and extracted MD&A
                zip_path = shutil.make_archive("edgar_filings", 'zip', data_dir)

                st.download_button(
                    label="📦 Download ZIP",
                    data=open(zip_path, "rb"),
                    file_name="edgar_filings.zip",
                    mime="application/zip"
                )
            else:
                st.error("❌ Failed to download filings. Please check your input.")

# Display analysis options if files have been downloaded
if st.session_state.downloaded_files:
    st.divider()
    st.header("📊 Analyze MD&A Sections")
    
    # Check if Gemini API key is available
    api_key = load_gemini_api_key()
    if not api_key:
        st.error("❌ Gemini API key not found. Please create a 'gemini_api_key.txt' file in your app folder.")
    else:
        # File selection
        st.subheader("Select Files to Analyze")
        
        # Create a DataFrame to display file information
        file_data = []
        for file in st.session_state.downloaded_files:
            fiscal_year = file.name.split('_')[1] if '_' in file.name else 'Unknown'
            file_size = f"{file.stat().st_size / 1024:.1f} KB"
            file_data.append({
                "File": file.name,
                "Fiscal Year": fiscal_year,
                "Size": file_size,
                "Path": str(file)
            })
        
        file_df = pd.DataFrame(file_data)
        
        # Create selection options
        file_options = ["All Files"] + [f.name for f in st.session_state.downloaded_files]
        selected_files = st.multiselect(
            "Choose Files", 
            options=file_options,
            default=["All Files"]
        )
        
        # Handle file selection logic
        files_to_analyze = []
        if "All Files" in selected_files:
            files_to_analyze = st.session_state.downloaded_files
        else:
            files_to_analyze = [f for f in st.session_state.downloaded_files if f.name in selected_files]
        
        # Analysis type selection
        st.subheader("Select Analysis Type")
        analysis_type = st.radio(
            "Analysis Focus", 
            ["comprehensive", "revenue", "profitability", "risks"],
            horizontal=True
        )
        
        # Analysis button
        if st.button("🔍 Analyze Selected Files"):
            if not files_to_analyze:
                st.warning("⚠️ Please select at least one file to analyze.")
            else:
                with st.spinner("Analyzing MD&A sections..."):
                    # Read all selected files
                    combined_text = ""
                    for file_path in files_to_analyze:
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                combined_text += f"\n\n--- FROM FILE: {file_path.name} ---\n\n"
                                combined_text += f.read()
                        except Exception as e:
                            st.warning(f"Error reading {file_path.name}: {str(e)}")
                    
                    # Perform analysis
                    analysis_result = analyze_mda_with_gemini(combined_text, analysis_type)
                    
                    # Display results
                    st.subheader(f"{analysis_type.capitalize()} Analysis Results")
                    st.markdown(analysis_result)
                    
                    # Provide option to download the analysis
                    st.download_button(
                        label="📄 Download Analysis Report",
                        data=analysis_result,
                        file_name=f"{st.session_state.identifier}_{st.session_state.filing_type}_{analysis_type}_analysis.md",
                        mime="text/markdown"
                    )
else:
    st.info("Download filings first to enable analysis options.")
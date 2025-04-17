import streamlit as st
from pathlib import Path
import shutil
import pandas as pd
from edgar_downloader import get_filing_types, download_edgar_filings, download_and_extract_mda
from mda_analyzer_gemini import analyze_mda_with_gemini, load_gemini_api_key

st.set_page_config(page_title="EDGAR Filings Downloader", layout="centered")
st.title("📄 SEC EDGAR Filings Downloader")

# Initialize session state variables if they don't exist
if 'downloaded_files' not in st.session_state:
    st.session_state.downloaded_files = []
if 'mda_dir' not in st.session_state:
    st.session_state.mda_dir = None
if 'identifier' not in st.session_state:
    st.session_state.identifier = None
if 'filing_type' not in st.session_state:
    st.session_state.filing_type = None
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

st.markdown("Enter a **company ticker** (e.g., `AAPL`) or a **CIK number** (e.g., `320193`).")

user_input = st.text_input("Ticker or CIK").strip()
filing_type = st.selectbox("Select Filing Type", get_filing_types())
years_back = st.slider("Years Back", 1, 20, 5)

if st.button("📥 Download & Analyze Filings"):
    if not user_input:
        st.warning("⚠️ Please enter a ticker or CIK.")
    else:
        ticker, cik = (None, user_input) if user_input.isdigit() else (user_input.upper(), None)
        identifier = ticker if ticker else cik

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

                # Automatically analyze all files with a comprehensive analysis
                with st.spinner("Analyzing MD&A sections..."):
                    # Read all files
                    combined_text = ""
                    for file_path in st.session_state.downloaded_files:
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                combined_text += f"\n\n--- FROM FILE: {file_path.name} ---\n\n"
                                combined_text += f.read()
                        except Exception as e:
                            st.warning(f"Error reading {file_path.name}: {str(e)}")
                    
                    # Check if Gemini API key is available
                    api_key = load_gemini_api_key()
                    if not api_key:
                        st.error("❌ Gemini API key not found. Please create a 'gemini_api_key.txt' file in your app folder.")
                    else:
                        # Perform comprehensive analysis
                        analysis_result = analyze_mda_with_gemini(combined_text, "comprehensive")
                        st.session_state.analysis_result = analysis_result
                
                st.download_button(
                    label="📦 Download ZIP",
                    data=open(zip_path, "rb"),
                    file_name="edgar_filings.zip",
                    mime="application/zip"
                )
            else:
                st.error("❌ Failed to download filings. Please check your input.")

# Display analysis results if available
if st.session_state.analysis_result:
    st.divider()
    st.header("📊 AI Analysis of MD&A Sections")
    st.markdown(st.session_state.analysis_result)
    
    # Provide option to download the analysis
    if st.session_state.identifier and st.session_state.filing_type:
        st.download_button(
            label="📄 Download Analysis Report",
            data=st.session_state.analysis_result,
            file_name=f"{st.session_state.identifier}_{st.session_state.filing_type}_comprehensive_analysis.md",
            mime="text/markdown"
        )
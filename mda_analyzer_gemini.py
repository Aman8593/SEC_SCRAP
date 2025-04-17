import os
import google.generativeai as genai
import streamlit as st
from pathlib import Path

def build_prompt(mda_text, analysis_type):
    """Build a prompt for the Gemini model based on analysis type."""
    if analysis_type == "comprehensive":
        return f"""Analyze this MD&A section and provide a comprehensive financial analysis:

{mda_text}

Include:
1. Revenue and growth analysis
2. Profitability analysis
3. Liquidity and solvency assessment
4. Key business risks
5. Forward-looking statements
6. Overall financial health assessment

Format as a markdown report with clear headings and bullet points where appropriate.
"""
    elif analysis_type == "revenue":
        return f"""Analyze revenue trends from this MD&A section:

{mda_text}

Focus on:
- Revenue trends over time
- Revenue segments and their performance
- Key drivers of growth or decline
- Seasonality factors
- Geographic distribution if available
- Forward guidance on revenue
- Competitive landscape impact on revenue

Return in markdown format with clear headings and bullet points where appropriate.
"""
    elif analysis_type == "profitability":
        return f"""Analyze profitability from this MD&A section:

{mda_text}

Focus on:
- Gross profit margins and trends
- Operating profit margins and trends
- Net profit margins and trends
- Cost structure analysis
- Key expenses affecting profitability
- Efficiency improvements or concerns
- Comparison to industry benchmarks if mentioned
- Future profitability outlook

Return in markdown format with clear headings and bullet points where appropriate.
"""
    elif analysis_type == "risks":
        return f"""Extract and summarize risk factors from this MD&A section:

{mda_text}

Include:
- Financial risks (debt, liquidity, currency, interest rate)
- Operational risks (supply chain, production, infrastructure)
- Market risks (competition, demand shifts, pricing pressure)
- Regulatory and compliance risks
- Environmental and sustainability risks
- Technology and cybersecurity risks
- Forward-looking risk assessments
- Risk mitigation strategies mentioned

Return in markdown format with clear headings and bullet points where appropriate.
"""
    else:
        return f"Analyze this MD&A section:\n\n{mda_text}"

def load_gemini_api_key():
    """Load Gemini API key from file."""
    try:
        with open("gemini_api_key.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def analyze_mda_with_gemini(mda_text, analysis_type="comprehensive"):
    """Analyze MD&A text using Gemini API with specified analysis type."""
    api_key = load_gemini_api_key()
    if not api_key:
        return "❌ Gemini API key not found. Please create a 'gemini_api_key.txt' file in your app folder."

    genai.configure(api_key=api_key)
    
    # Select appropriate model based on text length
    if len(mda_text) > 100000:
        model = genai.GenerativeModel("gemini-1.5-pro")  # For very long texts
    else:
        model = genai.GenerativeModel("gemini-1.5-flash")  # Faster for shorter texts
    
    prompt = build_prompt(mda_text, analysis_type)

    try:
        # Break very long texts into chunks if needed
        if len(mda_text) > 200000:
            # This is a simplified approach - a more robust implementation would 
            # need to handle segmentation at appropriate breaks
            st.warning("Text is very long - analysis may be limited or incomplete.")
            mda_text = mda_text[:190000] + "\n\n[Content truncated due to length...]"
            prompt = build_prompt(mda_text, analysis_type)
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Gemini Analysis failed: {str(e)}"

def read_file_content(file_path):
    """Read content from a single file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def get_available_mda_files(company_identifier=None, filing_type=None):
    """Get available MD&A files for a specific company and filing type."""
    base_dir = Path("edgar_data/mda_sections")
    
    if not base_dir.exists():
        return []
    
    if company_identifier and filing_type:
        target_dir = base_dir / company_identifier / filing_type
        if target_dir.exists():
            return list(target_dir.glob("*.txt"))
    
    # If no specific company/filing or directory doesn't exist, return all files
    all_files = []
    for path in base_dir.rglob("*.txt"):
        all_files.append(path)
    
    return all_files
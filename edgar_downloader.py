from sec_edgar_downloader import Downloader
from datetime import datetime
from pathlib import Path
from enum import Enum
import os
import re
from bs4 import BeautifulSoup

# Define filing types available in SEC EDGAR
class FilingType(str, Enum):
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"
    FORM_S1 = "S-1"
    FORM_13F = "13F-HR"
    FORM_4 = "4"
    FORM_DEF14A = "DEF 14A"
    FORM_10KSB = "10-KSB"
    FORM_10QSB = "10-QSB"
    FORM_20F = "20-F"
    FORM_40F = "40-F"
    FORM_6K = "6-K"
    FORM_10 = "10"
    FORM_8A = "8-A"
    FORM_485BPOS = "485BPOS"
    FORM_497 = "497"
    FORM_N1A = "N-1A"
    FORM_N2 = "N-2"
    FORM_NT10K = "NT 10-K"
    FORM_NT10Q = "NT 10-Q"

def get_filing_types():
    """Return a list of available filing types"""
    return [filing.value for filing in FilingType]

def download_edgar_filings(ticker: str, filing_type: str, years_back: int, cik: str = None):
    """
    Download SEC filings for a given ticker, filing type, and years back.
    Returns a tuple: (success_status, number_of_filings, data_directory)
    """
    # Set the data directory
    data_dir = Path("edgar_data")
    data_dir.mkdir(exist_ok=True)  # Ensure the data directory exists
    
    # Initialize downloader
    dl = Downloader("MyCompany", "myemail@example.com", data_dir)
    
    # Calculate date ranges based on user input
    today = datetime.now().year
    start_year = today - years_back
    
    try:
        # Determine if we're using a ticker or CIK
        if ticker:
            identifier = ticker
        elif cik:
            identifier = cik
        else:
            raise ValueError("Either a ticker or CIK number must be provided.")
        
        # Download the filings
        try:
            num_downloaded = dl.get(
                filing_type,
                identifier,
                after=f"{start_year}-01-01",
                before=f"{today}-12-31",
                download_details=True
            )
            print(f"Downloaded {num_downloaded} filings")
            
            # Find the directory where filings were downloaded
            filing_dir = data_dir / "sec-edgar-filings" / identifier / filing_type
            print(f"Looking for filings in: {filing_dir}")
            
            if not filing_dir.exists() and num_downloaded > 0:
                print(f"Warning: .get() reported success but directory not found at {filing_dir}")
                return False, 0, data_dir
                
            return True, num_downloaded, data_dir
            
        except Exception as e:
            print(f"Error downloading filings: {str(e)}")
            return False, 0, data_dir
    
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return False, 0, data_dir

def extract_item_7_from_html(html_content):
    """
    Extracts Item 7 (MD&A) section from HTML, starting at actual heading (not TOC),
    and ending at Item 7A or Item 8.
    """
    if not html_content or len(html_content) < 1000:
        return "File too small or empty"

    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(" ", strip=True)

    # Find all matches of Item 7 headings
    pattern = r"(Item\s+7\.\s+Management[''`s]{0,2}\s+Discussion\s+and\s+Analysis.*?)(?=Item\s+7A\.|Item\s+8\.|$)"
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

    if not matches:
        # Fallback method - try alternate patterns
        alt_patterns = [
            r"(Management[''`s]{0,2}\s+Discussion\s+and\s+Analysis.*?)(?=Item\s+7A\.|Item\s+8\.|$)",
            r"(MD&A.*?)(?=Item\s+7A\.|Item\s+8\.|$)",
            r"(Item\s+7\..*?)(?=Item\s+7A\.|Item\s+8\.|$)"
        ]
        
        for pattern in alt_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                break

    if not matches:
        return "Item 7 not found"

    # Choose the longest match assuming it's the full content (not TOC)
    item_7_section = max(matches, key=len).strip()

    if len(item_7_section) < 1000:
        return "Extracted Item 7 too short"

    return item_7_section

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text or "not found" in text.lower():
        return text
    
    # Replace non-breaking spaces and normalize whitespace
    text = re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    
    return text

def extract_fiscal_year_from_content(content, filename):
    """Extract fiscal year from text content or filename"""
    # Try to find year in content
    year_patterns = [
        r'fiscal\s+year\s+ended\s+.*?\b(20\d{2})\b',
        r'for\s+the\s+year\s+ended\s+.*?\b(20\d{2})\b',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(20\d{2})',
        r'FY\s*(20\d{2})',
        r'\b(20\d{2})\s+Annual\s+Report'
    ]
    
    content_lower = content.lower()
    
    for pattern in year_patterns:
        match = re.search(pattern, content_lower)
        if match:
            return match.group(1)
    
    # Try to extract from filename if it's in SEC format
    sec_match = re.search(r'(\d{10})-(\d{2})-(\d{6})', filename)
    if sec_match:
        file_year = f"20{sec_match.group(2)}"
        return file_year
    
    # Look for any 4-digit year in filename
    year_match = re.search(r'(20\d{2})', filename)
    if year_match:
        return year_match.group(1)
    
    # Default to unknown
    return "unknown_year"

def download_and_extract_mda(ticker: str, filing_type: str, years_back: int, cik: str = None):
    """
    Download SEC filings and extract MD&A sections for a given ticker
    Returns: (success_status, number_of_filings, number_of_mda_extracted)
    """
    # Download filings first
    success, num_downloaded, data_dir = download_edgar_filings(ticker, filing_type, years_back, cik)
    
    if not success or num_downloaded == 0:
        return False, 0, 0
        
    # Set up directories
    data_dir = Path("edgar_data")
    identifier = ticker if ticker else cik
    filing_dir = data_dir / "sec-edgar-filings" / identifier / filing_type
    mda_output_dir = data_dir / "mda_sections" / identifier / filing_type
    mda_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nMD&A sections will be saved to: {mda_output_dir.absolute()}\n")
    
    # Clear existing files to avoid confusion
    for existing_file in mda_output_dir.glob("*.txt"):
        existing_file.unlink()
    
    # Extract MD&A sections
    mda_count = 0
    
    # Get all HTML files
    html_files = list(filing_dir.rglob("*.html"))
    html_files.extend(list(filing_dir.rglob("*.htm")))
    print(f"Found {len(html_files)} HTML files to process")
    
    # Process each HTML file
    for i, html_file in enumerate(html_files, 1):
        try:
            print(f"\nProcessing file {i}/{len(html_files)}: {html_file.name}")
            
            with open(html_file, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
            
            # Skip very small files
            if len(html_content) < 1000:
                print(f"❌ Skipped: {html_file.name} - File too small")
                continue
                
            # Extract and clean MD&A content
            mdna_text = extract_item_7_from_html(html_content)
            clean_mdna_text = clean_text(mdna_text)
            
            # Validate content
            if len(clean_mdna_text) > 1000 and "not found" not in clean_mdna_text.lower():
                fiscal_year = extract_fiscal_year_from_content(clean_mdna_text, html_file.name)
                print(f"✅ Found MD&A section for fiscal year {fiscal_year}")
                
                output_filename = f"MDNA_{fiscal_year}_{html_file.stem}.txt"
                output_path = mda_output_dir / output_filename
                
                # Save to file
                with open(output_path, 'w', encoding='utf-8') as out_file:
                    out_file.write(clean_mdna_text)
                
                # Verify the file was created successfully
                if output_path.exists() and output_path.stat().st_size > 0:
                    mda_count += 1
                    print(f"✅ Successfully saved MD&A to: {output_path} ({output_path.stat().st_size} bytes)")
                else:
                    print(f"❌ Error: File not written properly to {output_path}")
            else:
                print(f"❌ No valid MD&A section found in {html_file.name}")
                
        except Exception as e:
            print(f"❌ Error processing {html_file.name}: {str(e)}")
    
    # Final verification
    actual_files = list(mda_output_dir.glob("*.txt"))
    print(f"\nExtraction Summary:")
    print(f"- HTML files processed: {len(html_files)}")
    print(f"- MD&A sections detected and extracted: {mda_count}")
    print(f"- MD&A files actually on disk: {len(actual_files)}")
    
    if mda_count != len(actual_files):
        print(f"⚠️ WARNING: Discrepancy between counted extractions ({mda_count}) and actual files ({len(actual_files)})")
        print(f"Files found on disk: {[f.name for f in actual_files]}")
    
    print(f"\n✅ Successfully extracted {len(actual_files)} MD&A sections out of {num_downloaded} filings")
    return True, num_downloaded, len(actual_files)

# Debug function to help troubleshoot specific files
def debug_extraction(file_path):
    """Debug extraction for a specific file"""
    print(f"Debugging extraction for: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        print(f"File size: {len(content)} bytes")
        
        # Check for common Item 7 text patterns
        item7_mentions = len(re.findall(r'item\s*7', content, re.IGNORECASE))
        mdna_mentions = len(re.findall(r'management\'s discussion', content, re.IGNORECASE))
        
        print(f"Item 7 mentions: {item7_mentions}")
        print(f"MD&A mentions: {mdna_mentions}")
        
        # Try extraction
        result = extract_item_7_from_html(content)
        clean_result = clean_text(result)
        
        print(f"Extraction result length: {len(clean_result)}")
        if len(clean_result) > 0:
            print(f"First 200 chars: {clean_result[:200]}...")
            
        return len(clean_result) > 1000 and "not found" not in clean_result.lower()
        
    except Exception as e:
        print(f"Debug error: {str(e)}")
        return False
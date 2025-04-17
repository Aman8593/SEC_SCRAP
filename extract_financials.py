import os
import re
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import logging
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_tables_by_title(soup: BeautifulSoup, keywords: List[str]) -> List[pd.DataFrame]:
    """
    Extracts financial tables from the HTML content based on provided keywords.
    Returns a list of cleaned DataFrames.
    """
    tables = []
    seen_tables = set()  # To avoid duplicate tables
    
    # Find all potential table containers (SEC filings often wrap tables in divs)
    for container in soup.find_all(['div', 'table']):
        if container.name == 'table':
            table = container
            preceding_text = get_preceding_text(table)
        else:
            # Handle cases where tables are inside divs
            table = container.find('table')
            if not table:
                continue
            preceding_text = get_preceding_text(container)
        
        # Skip if we've already processed this table
        table_hash = hash(str(table))
        if table_hash in seen_tables:
            continue
        seen_tables.add(table_hash)
        
        # Check if the preceding text matches our keywords
        if any(keyword in preceding_text.lower() for keyword in keywords):
            try:
                df = pd.read_html(str(table), flavor="bs4")[0]
                df = clean_table(df)
                if not df.empty and df.shape[1] > 1:  # Only store meaningful tables
                    tables.append(df)
            except Exception as e:
                logger.warning(f"Failed to parse table: {str(e)}")
                continue
    return tables

def get_preceding_text(element) -> str:
    """Get relevant preceding text for context"""
    text_parts = []
    
    # Look at previous siblings
    prev = element.find_previous_sibling()
    while prev and len(' '.join(text_parts)) < 500:  # Limit context size
        if prev.name in ['p', 'div', 'font', 'b', 'strong', 'h1', 'h2', 'h3', 'h4']:
            text = prev.get_text(' ', strip=True)
            if text:
                text_parts.insert(0, text)
        prev = prev.find_previous_sibling()
    
    return ' '.join(text_parts)

def clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize the extracted table"""
    # Remove empty rows and columns
    df = df.dropna(how='all').dropna(axis=1, how='all')
    
    # Clean column headers
    if len(df.columns) > 0:
        df.columns = [str(col).strip() for col in df.columns]
        
        # Handle multi-index headers
        if df.columns.nlevels > 1:
            df.columns = [' '.join(col).strip() for col in df.columns.values]
    
    # Remove dollar signs and commas from numeric values
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(r'[\$,]', '', regex=True)
    
    # Convert to numeric where possible
    df = df.apply(pd.to_numeric, errors='ignore')
    
    return df

def save_tables(tables: List[pd.DataFrame], statement_type: str, output_dir: Path, filename_prefix: str):
    """Save extracted tables to CSV files"""
    saved_files = []
    for i, df in enumerate(tables):
        if df.empty:
            continue
            
        output_path = output_dir / f"{filename_prefix}_{statement_type}_{i+1}.csv"
        try:
            df.to_csv(output_path, index=False)
            saved_files.append(output_path)
        except Exception as e:
            logger.error(f"Failed to save {output_path}: {str(e)}")
    return saved_files

def extract_financial_statements(input_dir: str, output_dir: str) -> int:
    """
    Extract financial statements from HTML files in input_dir and save to output_dir.
    Returns the number of files with successfully extracted data.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    count = 0
    processed_files = 0
    
    for html_file in input_path.glob("*.htm*"):  # Match both .html and .htm
        try:
            with open(html_file, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
            
            soup = BeautifulSoup(html, "html.parser")
            filename_prefix = html_file.stem
            
            # Define search patterns for each financial statement
            statement_patterns = {
                "balance": ["balance sheet", "financial position", "assets.*liabilities", "statement of financial position"],
                "income": ["income statement", "statement of operations", "statement of earnings", "profit and loss"],
                "cashflow": ["cash flow", "cash flows", "statement of cash flows"]
            }
            
            extracted_any = False
            
            for statement_type, keywords in statement_patterns.items():
                tables = extract_tables_by_title(soup, keywords)
                if tables:
                    saved_files = save_tables(tables, statement_type, output_path, filename_prefix)
                    if saved_files:
                        logger.info(f"Extracted {len(saved_files)} {statement_type} tables from {html_file.name}")
                        extracted_any = True
            
            if extracted_any:
                count += 1
            processed_files += 1
            
        except Exception as e:
            logger.error(f"Error processing {html_file.name}: {str(e)}")
    
    logger.info(f"Processed {processed_files} files, extracted data from {count} files")
    return count

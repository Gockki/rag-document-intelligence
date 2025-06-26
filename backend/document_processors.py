# backend/document_processors.py (PÄIVITETTY VERSIO)
import pandas as pd
import PyPDF2
from io import BytesIO
from typing import Tuple, Dict, Any

# UUSI: Import syvennettyä analysaattoria
try:
    from advanced_excel_processor import AdvancedExcelAnalyzer
    ADVANCED_EXCEL_AVAILABLE = True
    print("✅ Advanced Excel analyzer loaded")
except ImportError:
    ADVANCED_EXCEL_AVAILABLE = False
    print("⚠️ Advanced Excel analyzer not available, using basic version")

def process_excel_file(content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """Käsittele Excel-tiedosto (päivitetty syvennetyllä analytiikalla)"""
    
    # UUSI: Kokeile syvennettyä analytiikkaa ensin
    if ADVANCED_EXCEL_AVAILABLE:
        try:
            analyzer = AdvancedExcelAnalyzer()
            return analyzer.analyze_excel_advanced(content, filename)
        except Exception as e:
            print(f"⚠️ Advanced analysis failed, falling back to basic: {e}")
            # Jos syvennetty epäonnistuu, käytä perusversiota
    
    # PERUSVERSIO (backup)
    try:
        # Lue Excel-tiedosto
        excel_file = BytesIO(content)
        
        # Lue kaikki työarkit
        excel_data = pd.ExcelFile(excel_file, engine='openpyxl')
        
        text_parts = []
        numerical_summary = {}
        
        for sheet_name in excel_data.sheet_names:
            # Lue työarkki
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
            
            # Poista tyhjät rivit/sarakkeet
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if df.empty:
                continue
            
            # Luo tekstikuvaus
            sheet_text = f"\n=== TYÖARKKI: {sheet_name} ===\n"
            sheet_text += f"Rivejä: {len(df)}, Sarakkeita: {len(df.columns)}\n"
            sheet_text += f"Sarakkeet: {', '.join(df.columns.astype(str))}\n\n"
            
            # Numeerinen analyysi
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                sheet_text += "NUMEERINEN ANALYYSI:\n"
                for col in numeric_cols:
                    if df[col].count() > 0:  # Varmista että ei ole tyhjä
                        stats = df[col].describe()
                        sheet_text += f"  📊 {col}:\n"
                        sheet_text += f"    - Keskiarvo: {stats['mean']:.2f}\n"
                        sheet_text += f"    - Summa: {df[col].sum():.2f}\n"
                        sheet_text += f"    - Min/Max: {stats['min']:.2f} / {stats['max']:.2f}\n"
                        
                        # Tallenna analytiikkaa
                        numerical_summary[f"{sheet_name}_{col}"] = {
                            'mean': float(stats['mean']),
                            'sum': float(df[col].sum()),
                            'min': float(stats['min']),
                            'max': float(stats['max']),
                            'count': int(stats['count'])
                        }
            
            # Taulukon sisältö (ensimmäiset 10 riviä)
            sheet_text += f"\nDATA (10 ensimmäistä riviä):\n"
            sheet_text += df.head(10).to_string(index=False, max_cols=8)
            sheet_text += "\n\n"
            
            text_parts.append(sheet_text)
        
        full_text = "".join(text_parts)
        
        metadata = {
            'file_type': 'excel',
            'sheets': excel_data.sheet_names,
            'total_sheets': len(excel_data.sheet_names),
            'numerical_data': numerical_summary,
            'has_analytics': len(numerical_summary) > 0,
            'analysis_type': 'basic'  # Merkitään että käytettiin perusversiota
        }
        
        return full_text, metadata
        
    except Exception as e:
        error_text = f"VIRHE Excel-tiedoston käsittelyssä: {str(e)}"
        return error_text, {'file_type': 'excel', 'error': str(e)}

def process_pdf_file(content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
    """Käsittele PDF-tiedosto (ei muutoksia)"""
    
    try:
        pdf_file = BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_parts = []
        page_count = len(pdf_reader.pages)
        
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text.strip():
                text_parts.append(f"\n=== SIVU {i+1}/{page_count} ===\n")
                text_parts.append(page_text)
                text_parts.append("\n")
        
        full_text = "".join(text_parts)
        
        metadata = {
            'file_type': 'pdf',
            'page_count': page_count,
            'character_count': len(full_text)
        }
        
        return full_text, metadata
        
    except Exception as e:
        error_text = f"VIRHE PDF-tiedoston käsittelyssä: {str(e)}"
        return error_text, {'file_type': 'pdf', 'error': str(e)}

def process_file_by_type(content: bytes, filename: str, content_type: str) -> Tuple[str, Dict[str, Any]]:
    """Pääfunktio - käsittele tiedosto tyypin mukaan (päivitetty)"""
    
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # Excel-tiedostot (PÄIVITETTY syvennetyllä analytiikalla)
    if file_ext in ['xlsx', 'xls'] or 'excel' in content_type.lower():
        return process_excel_file(content, filename)
    
    # PDF-tiedostot  
    elif file_ext == 'pdf' or 'pdf' in content_type.lower():
        return process_pdf_file(content, filename)
    
    # Tekstimuotoiset (ei muutoksia)
    elif file_ext in ['txt', 'md'] or 'text' in content_type.lower():
        try:
            text = content.decode('utf-8')
            metadata = {'file_type': 'text', 'character_count': len(text)}
            return text, metadata
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
                metadata = {'file_type': 'text', 'character_count': len(text), 'encoding': 'latin-1'}
                return text, metadata
            except:
                error_text = "Virhe tekstin dekoodauksessa"
                return error_text, {'file_type': 'text', 'error': 'encoding_error'}
    
    # Ei tuettu
    else:
        error_text = f"Tiedostotyyppiä '{file_ext}' ei tueta. Tuetut: TXT, MD, PDF, XLSX, XLS"
        return error_text, {'file_type': 'unsupported', 'extension': file_ext}

# Testifunktio (päivitetty)
if __name__ == "__main__":
    print("🧪 Testataan document_processors (enhanced version)...")
    
    # Testaa tekstikäsittely
    test_text = "Tämä on testi".encode('utf-8')
    result_text, result_meta = process_file_by_type(test_text, "test.txt", "text/plain")
    print(f"✅ Teksti: {result_meta}")
    
    # Tarkista syvennetty Excel-tuki
    if ADVANCED_EXCEL_AVAILABLE:
        print("✅ Syvennetty Excel-analytiikka käytettävissä")
    else:
        print("⚠️ Perus Excel-analytiikka käytössä")
    
    print("📁 Document processors valmis käyttöön!")
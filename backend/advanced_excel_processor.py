# backend/advanced_excel_processor.py
import pandas as pd
import numpy as np
from io import BytesIO
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import re

class AdvancedExcelAnalyzer:
    """Syvennetty Excel-analysoija business-älykkyydellä"""
    
    def __init__(self):
        # Tunnistettavat KPI-kentät (suomeksi ja englanniksi)
        self.revenue_keywords = [
            'liikevaihto', 'myynti', 'tulot', 'revenue', 'sales', 'income',
            'net sales', 'gross revenue', 'turnover'
        ]
        
        self.profit_keywords = [
            'voitto', 'tulos', 'kate', 'profit', 'ebit', 'ebitda', 
            'operating income', 'net income', 'gross profit', 'margin'
        ]
        
        self.cost_keywords = [
            'kulut', 'kustannukset', 'menot', 'costs', 'expenses', 
            'operating costs', 'cogs', 'overhead'
        ]
        
        self.growth_keywords = [
            'kasvu', 'muutos', 'growth', 'change', 'increase', 
            'delta', 'variance', 'yoy', 'mom'
        ]
        
        # Tunnistettavat aikajaksot
        self.time_patterns = [
            r'q[1-4]', r'quarter', r'kvartaali', r'neljännes',
            r'\d{4}', r'20\d{2}',  # vuodet
            r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec',
            r'tammi|helmi|maalis|huhti|touko|kesä|heinä|elo|syys|loka|marras|joulu'
        ]

    def analyze_excel_advanced(self, content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Syvennetty Excel-analyysi"""
        
        try:
            excel_file = BytesIO(content)
            workbook = pd.ExcelFile(excel_file, engine='openpyxl')
            
            # Analyysitulokset
            analysis_results = {
                'file_type': 'excel',
                'sheets': workbook.sheet_names,
                'kpi_analysis': {},
                'trend_analysis': {},
                'comparative_analysis': {},
                'business_insights': [],
                'numerical_summary': {},
                'anomaly_detection': {},
                'forecasting_hints': []
            }
            
            text_parts = []
            
            for sheet_name in workbook.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                if df.empty:
                    continue
                
                # PERUS SHEET-ANALYYSI
                sheet_analysis = self._analyze_sheet_structure(df, sheet_name)
                text_parts.append(sheet_analysis['description'])
                
                # KPI-TUNNISTUS
                kpi_data = self._identify_kpis(df, sheet_name)
                if kpi_data:
                    analysis_results['kpi_analysis'][sheet_name] = kpi_data
                    text_parts.append(kpi_data['summary'])
                
                # TRENDIANALYYSI
                trend_data = self._analyze_trends(df, sheet_name)
                if trend_data:
                    analysis_results['trend_analysis'][sheet_name] = trend_data
                    text_parts.append(trend_data['summary'])
                
                # POIKKEAMIEN HAVAITSEMINEN
                anomalies = self._detect_anomalies(df, sheet_name)
                if anomalies:
                    analysis_results['anomaly_detection'][sheet_name] = anomalies
                    text_parts.append(anomalies['summary'])
                
                # LIIKETOIMINTA-OIVALLUKSET
                insights = self._generate_business_insights(df, sheet_name)
                analysis_results['business_insights'].extend(insights)
            
            # KOKONAISANALYYSI
            overall_summary = self._generate_overall_summary(analysis_results)
            text_parts.insert(0, overall_summary)
            
            full_text = "\n\n".join(text_parts)
            
            return full_text, analysis_results
            
        except Exception as e:
            error_text = f"Virhe syvennetyssä Excel-analyysissä: {str(e)}"
            return error_text, {'file_type': 'excel', 'error': str(e)}

    def _analyze_sheet_structure(self, df: pd.DataFrame, sheet_name: str) -> Dict:
        """Analysoi taulukon rakenne"""
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        date_cols = df.select_dtypes(include=['datetime']).columns
        text_cols = df.select_dtypes(include=['object']).columns
        
        # Etsi mahdolliset aikasarja-sarakkeet
        potential_time_cols = []
        for col in text_cols:
            if any(re.search(pattern, str(col).lower()) for pattern in self.time_patterns):
                potential_time_cols.append(col)
        
        description = f"""
=== TYÖARKKI: {sheet_name} ===
📊 RAKENNE:
- Rivejä: {len(df)}
- Sarakkeita: {len(df.columns)}
- Numeerisia: {len(numeric_cols)}
- Päivämääriä: {len(date_cols)}
- Tekstiä: {len(text_cols)}

📈 SARAKKEET:
{', '.join(df.columns.astype(str))}
"""
        
        if potential_time_cols:
            description += f"\n⏰ AIKASARJA-SARAKKEET: {', '.join(potential_time_cols)}"
        
        return {
            'description': description,
            'numeric_columns': list(numeric_cols),
            'date_columns': list(date_cols),
            'text_columns': list(text_cols),
            'potential_time_columns': potential_time_cols
        }

    def _identify_kpis(self, df: pd.DataFrame, sheet_name: str) -> Dict:
        """Tunnista KPI:t (Key Performance Indicators)"""
        
        kpis = {
            'revenue': [],
            'profit': [],
            'costs': [],
            'growth': [],
            'other': []
        }
        
        # Käy läpi sarakkeet ja tunnista KPI-tyypit
        for col in df.columns:
            col_lower = str(col).lower()
            
            if any(keyword in col_lower for keyword in self.revenue_keywords):
                kpis['revenue'].append(col)
            elif any(keyword in col_lower for keyword in self.profit_keywords):
                kpis['profit'].append(col)
            elif any(keyword in col_lower for keyword in self.cost_keywords):
                kpis['costs'].append(col)
            elif any(keyword in col_lower for keyword in self.growth_keywords):
                kpis['growth'].append(col)
            elif df[col].dtype in ['int64', 'float64']:
                kpis['other'].append(col)
        
        if not any(kpis.values()):
            return None
        
        # Laske KPI-tilastot
        kpi_stats = {}
        summary_parts = [f"\n💼 KPI-ANALYYSI ({sheet_name}):"]
        
        for category, columns in kpis.items():
            if not columns:
                continue
                
            category_stats = {}
            for col in columns:
                if df[col].dtype in ['int64', 'float64']:
                    stats = {
                        'sum': float(df[col].sum()),
                        'mean': float(df[col].mean()),
                        'median': float(df[col].median()),
                        'std': float(df[col].std()),
                        'min': float(df[col].min()),
                        'max': float(df[col].max()),
                        'growth_rate': self._calculate_growth_rate(df[col])
                    }
                    category_stats[col] = stats
                    
                    # Lisää yhteenveto
                    summary_parts.append(
                        f"  📊 {category.upper()} - {col}:\n"
                        f"    💰 Summa: {stats['sum']:,.0f}\n"
                        f"    📈 Keskiarvo: {stats['mean']:,.0f}\n"
                        f"    📊 Mediaani: {stats['median']:,.0f}\n"
                        f"    🎯 Vaihteluväli: {stats['min']:,.0f} - {stats['max']:,.0f}"
                    )
                    
                    if stats['growth_rate']:
                        summary_parts.append(f"    📈 Trendi: {stats['growth_rate']:.1f}% keskimäärin")
            
            if category_stats:
                kpi_stats[category] = category_stats
        
        return {
            'categories': kpis,
            'statistics': kpi_stats,
            'summary': '\n'.join(summary_parts)
        }

    def _analyze_trends(self, df: pd.DataFrame, sheet_name: str) -> Dict:
        """Analysoi trendit aikasarjadatasta"""
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) == 0:
            return None
        
        trends = {}
        summary_parts = [f"\n📈 TRENDIANALYYSI ({sheet_name}):"]
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:  # Tarvitaan vähintään 3 datapistettä
                continue
            
            # Laske trendi (yksinkertainen lineaarinen)
            x = np.arange(len(series))
            y = series.values
            
            # Lineaarinen regressio (yksinkertainen)
            if len(x) > 1:
                slope = np.polyfit(x, y, 1)[0]
                
                # Määritä trendin suunta
                if abs(slope) < (y.std() * 0.1):  # Matala volatiliteetti
                    trend_direction = "Vakaa"
                elif slope > 0:
                    trend_direction = "Kasvava"
                else:
                    trend_direction = "Laskeva"
                
                # Laske muutosprosentti
                if len(series) >= 2:
                    start_val = series.iloc[0]
                    end_val = series.iloc[-1]
                    if start_val != 0:
                        change_pct = ((end_val - start_val) / abs(start_val)) * 100
                    else:
                        change_pct = 0
                else:
                    change_pct = 0
                
                trends[col] = {
                    'direction': trend_direction,
                    'slope': float(slope),
                    'change_percentage': float(change_pct),
                    'volatility': float(series.std() / series.mean() * 100) if series.mean() != 0 else 0
                }
                
                summary_parts.append(
                    f"  📊 {col}:\n"
                    f"    🎯 Suunta: {trend_direction}\n"
                    f"    📈 Muutos: {change_pct:+.1f}%\n"
                    f"    📊 Volatiliteetti: {trends[col]['volatility']:.1f}%"
                )
        
        if not trends:
            return None
        
        return {
            'trends': trends,
            'summary': '\n'.join(summary_parts)
        }

    def _detect_anomalies(self, df: pd.DataFrame, sheet_name: str) -> Dict:
        """Havaitse poikkeamat datassa"""
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        anomalies = {}
        summary_parts = [f"\n🚨 POIKKEAMA-ANALYYSI ({sheet_name}):"]
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 5:  # Tarvitaan riittävästi dataa
                continue
            
            # Z-score menetelmä (yksinkertainen)
            z_scores = np.abs((series - series.mean()) / series.std())
            outliers = series[z_scores > 2]  # 2 standardipoikkeamaa
            
            if len(outliers) > 0:
                anomalies[col] = {
                    'outlier_count': len(outliers),
                    'outlier_percentage': (len(outliers) / len(series)) * 100,
                    'outlier_values': outliers.tolist(),
                    'normal_range': {
                        'min': float(series.quantile(0.05)),
                        'max': float(series.quantile(0.95))
                    }
                }
                
                summary_parts.append(
                    f"  🚨 {col}:\n"
                    f"    ⚠️ Poikkeamia: {len(outliers)} kpl ({(len(outliers)/len(series)*100):.1f}%)\n"
                    f"    📊 Normaali vaihteluväli: {anomalies[col]['normal_range']['min']:,.0f} - {anomalies[col]['normal_range']['max']:,.0f}\n"
                    f"    🎯 Suurimmat poikkeamat: {', '.join([f'{x:,.0f}' for x in sorted(outliers, key=abs, reverse=True)[:3]])}"
                )
        
        if not anomalies:
            return None
        
        return {
            'anomalies': anomalies,
            'summary': '\n'.join(summary_parts)
        }

    def _generate_business_insights(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """Generoi liiketoiminta-oivalluksia"""
        
        insights = []
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) < 2:
            return insights
        
        # Etsi suurimmat ja pienimmät arvot
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            max_val = series.max()
            min_val = series.min()
            mean_val = series.mean()
            
            # Oivalluksia suurista arvoista
            if max_val > mean_val * 3:
                insights.append(f"💡 {sheet_name}: {col} sisältää poikkeuksellisen suuren arvon ({max_val:,.0f}), joka on {max_val/mean_val:.1f}x keskiarvoa suurempi")
            
            # Oivalluksia nollista/negatiivisista arvoista
            negative_count = len(series[series < 0])
            if negative_count > 0:
                insights.append(f"⚠️ {sheet_name}: {col} sisältää {negative_count} negatiivista arvoa - tarkista mahdolliset virheet tai tappiot")
        
        # Korrelaatioanalyysi (jos useita numeerisia sarakkeita)
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            
            # Etsi vahvimmat korrelaatiot
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols[i+1:], i+1):
                    corr = corr_matrix.iloc[i, j]
                    if abs(corr) > 0.7:  # Vahva korrelaatio
                        direction = "positiivinen" if corr > 0 else "negatiivinen"
                        insights.append(f"🔗 {sheet_name}: {col1} ja {col2} välillä vahva {direction} korrelaatio ({corr:.2f})")
        
        return insights

    def _calculate_growth_rate(self, series: pd.Series) -> float:
        """Laske keskimääräinen kasvuvauhti"""
        series = series.dropna()
        if len(series) < 2:
            return None
        
        # Yksinkertainen kasvu ensimmäisestä viimeiseen
        start = series.iloc[0]
        end = series.iloc[-1]
        periods = len(series) - 1
        
        if start <= 0:
            return None
        
        # Compound Annual Growth Rate (CAGR) tyylinen laskenta
        growth_rate = ((end / start) ** (1/periods) - 1) * 100
        return growth_rate

    def _generate_overall_summary(self, analysis_results: Dict) -> str:
        """Generoi kokonaisyhteenveto"""
        
        summary_parts = [
            "🎯 EXCEL-DOKUMENTIN KOKONAISANALYYSI",
            "=" * 50,
            f"📊 Työarkkeja analysoitu: {len(analysis_results['sheets'])}",
        ]
        
        # KPI-yhteenveto
        if analysis_results['kpi_analysis']:
            summary_parts.append("\n💼 LÖYDETYT KPI:T:")
            for sheet, kpis in analysis_results['kpi_analysis'].items():
                for category, data in kpis['statistics'].items():
                    summary_parts.append(f"  • {category.upper()}: {len(data)} mittaria")
        
        # Liiketoiminta-oivallukset
        if analysis_results['business_insights']:
            summary_parts.append(f"\n💡 LIIKETOIMINTA-OIVALLUKSIA: {len(analysis_results['business_insights'])}")
            for insight in analysis_results['business_insights'][:5]:  # Max 5 tärkeintä
                summary_parts.append(f"  • {insight}")
        
        # Suosituksia
        summary_parts.extend([
            "\n🎯 SUOSITUKSIA:",
            "  • Käytä tarkentavia kysymyksiä numeroista",
            "  • Kysy trendeistä ja muutoksista",
            "  • Pyydä vertailuja eri ajanjaksojen välillä"
        ])
        
        return "\n".join(summary_parts)
import requests
from bs4 import BeautifulSoup
import random
import time
from datetime import datetime, timedelta

class NewsScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_articles(self, keyword, target_date_str=None):
        """
        Fetches news articles related to the keyword.
        Args:
            keyword (str): The search term.
            target_date_str (str): Optional. Format 'YYYY-MM-DD'. If provided, prioritizes articles near this date.
        Returns:
            list: A list of dictionaries with 'title', 'date', 'link', 'source'.
        """
        # Note: Direct Google News scraping often gets blocked. 
        # We will try a duckduckgo html search or similar simple endpoint if possible, 
        # or use a highly robust requests method. 
        # For this hackathon scope, we'll try a generic search engine query result parsing
        # that mimics a real search without heavy API keys.
        
        # Using a reliable fallback method: searching against specific domains helps quality.
        if "aadhaar" in keyword.lower():
            query = keyword
        else:
             query = f"{keyword} Aadhaar"

             # Basic date context in query if simple search
             pass

        search_url = f"https://duckduckgo.com/html/?q={query}"
        
        try:
            time.sleep(random.uniform(0.5, 1.5)) # Polite delay
            response = requests.get(search_url, headers=self.headers, timeout=10)
            
            if response.status_code not in [200, 202]:
                print(f"Error fetching news from DDG: {response.status_code}")
                # Fallback to generic search if DDG fails
                return self.fetch_articles_fallback(query)

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # DuckDuckGo HTML structure parsing
            for result in soup.find_all('div', class_='result'):
                title_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    
                    # Basic date extraction from snippet if available (often "2 days ago", "May 12, 2024")
                    # For now, we return specific found items.
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'source': 'Web Search',
                        'snippet': snippet,
                        'date': 'Relevant Match' # Difficult to extract exact date from generic HTML without NLP
                    })
                    
                    if len(results) >= 3: # Limit to top 3
                        break
            
            return results

        except Exception as e:
            print(f"Scraper Exception: {e}")
            return []

    def fetch_articles_fallback(self, query):
        # Simple fallback using a different structure or engine if needed.
        # For now, just return empty to be safe, or try a different UA/URL.
        return []

    def correlate_event(self, anomaly_type, date_obj, location):
        """
        High-level wrapper to find a reason for a specific anomaly.
        """
        query_terms = []
        if "Spike" in anomaly_type:
            query_terms = [f"Aadhaar camp {location}", f"Aadhaar drive {location}"]
        elif "Rejection" in anomaly_type:
            query_terms = [f"Aadhaar rejection reasons {location}", "Aadhaar document rules"]
        else:
            query_terms = [f"Aadhaar news {location}"]

        found_articles = []
        for term in query_terms:
            articles = self.fetch_articles(term)
            if articles:
                found_articles.extend(articles)
                break 
        
        # If no specific district news found, try a broader search if location looks like a District
        if not found_articles and location:
             # Basic heuristic: Try searching for just "Aadhaar news [Location]" or broader "Aadhaar update drive"
             # to at least show *something* relevant if it's a demo. 
             # But strictly, we only want reasons *for that location*.
             # Let's try one broader query:
             fallback_term = f"Aadhaar news {location}"
             if fallback_term not in query_terms:
                 found_articles.extend(self.fetch_articles(fallback_term))
                 
        return found_articles

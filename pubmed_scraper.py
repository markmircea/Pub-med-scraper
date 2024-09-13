import requests
from bs4 import BeautifulSoup
import time
import re
from tqdm import tqdm
import csv

print("Script starting...")

# Define a desktop user agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_pdf_link(pmc_url):
    try:
        pmc_response = requests.get(pmc_url, headers=headers)
        pmc_soup = BeautifulSoup(pmc_response.text, 'html.parser')
        
        # Try multiple selectors to find the PDF link
        selectors = [
            'li.pdf-link.other_item a',
            '.pmc-sidebar__formats li.pdf-link a',
            'a[href$=".pdf"]',
            '.format-menu a[href$=".pdf"]'  # Added this selector for potential menu items
        ]
        
        for selector in selectors:
            pdf_elements = pmc_soup.select(selector)
            if pdf_elements:
                for pdf_element in pdf_elements:
                    if 'href' in pdf_element.attrs:
                        pdf_link = "https://www.ncbi.nlm.nih.gov" + pdf_element['href']
                        print(f"Found PDF link: {pdf_link}")
                        return pdf_link
        
        print(f"No PDF link found on {pmc_url}")
        print("HTML content of the page:")
        print(pmc_soup.prettify()[:1000])  # Print first 1000 characters of the HTML
        return ""
    except Exception as e:
        print(f"Error accessing PMC page {pmc_url}: {str(e)}")
        return ""

def check_scihub(doi):
    scihub_url = f"https://sci-hub.se/{doi}"
    try:
        response = requests.get(scihub_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for error messages
        error_div = soup.select_one('div.content p#smile')
        nginx_error = 'nginx' in response.text.lower()
        
        if error_div or nginx_error:
            return ""
        else:
            return scihub_url
    except Exception as e:
        print(f"Error accessing Sci-Hub for DOI {doi}: {str(e)}")
        return ""

def scrape_pubmed():
    base_url = "https://pubmed.ncbi.nlm.nih.gov/?term=%28%22Parent*+Stress+Scale%22+OR+%22Parent*+Stress+Scale+%28PSS%29%22+AND+%28reliability+OR+validity+OR+consist*+OR+internal*+or+alpha*%29&timeline=expanded&size=200"
    
    articles = []
    page_num = 1
    
    while True:
        print(f"Processing page {page_num}")
        url = f"{base_url}&page={page_num}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        article_elements = soup.select('.docsum-content')
        print(f"Found {len(article_elements)} articles on this page")
        
        # Create a progress bar for the articles on this page
        for article in tqdm(article_elements, desc=f"Page {page_num}", unit="article"):
            title_element = article.select_one('.docsum-title')
            title = title_element.text.strip() if title_element else "No title found"
            
            link = title_element['href'] if title_element else None
            if not link:
                print(f"No link found for article: {title}")
                continue
            
            is_free = bool(article.select_one('.free-resources'))
            access_type = "FREE" if is_free else "PAID"
            
            article_url = f"https://pubmed.ncbi.nlm.nih.gov{link}"
            article_response = requests.get(article_url, headers=headers)
            article_soup = BeautifulSoup(article_response.text, 'html.parser')
            
            doi_element = article_soup.select_one('.id-link[data-ga-action="DOI"]')
            doi = doi_element.text.strip() if doi_element else "No DOI found"
            
            pdf_link = ""
            if is_free:
                pmc_link = article_soup.select_one('a.link-item.pmc')
                if pmc_link and 'href' in pmc_link.attrs:
                    pmc_url = pmc_link['href']
                    pdf_link = get_pdf_link(pmc_url)
                else:
                    print(f"No PMC link found for free article: {title}")
            
            # Check Sci-Hub if no PDF link is found
            if not pdf_link and doi != "No DOI found":
                scihub_link = check_scihub(doi)
                if scihub_link:
                    pdf_link = scihub_link
            
            articles.append((title, doi, access_type, pdf_link))
            print(f"Found article: {title} | DOI: {doi} | {access_type} | PDF: {pdf_link or 'N/A'}")
            
            time.sleep(1)  # Be respectful to the server
        
        next_button = soup.select_one('.next-page-link')
        if not next_button:
            print("No more pages to process")
            break
        
        page_num += 1
        time.sleep(2)  # Be respectful to the server
    
    # Save articles to a CSV file
    with open('pubmed_articles.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'DOI', 'Access Type', 'PDF or SCI Hub Link'])
        for title, doi, access_type, pdf_link in articles:
            writer.writerow([title, doi, access_type, pdf_link])
    
    print(f"Scraped {len(articles)} articles and saved to pubmed_articles.csv")

print("Starting scraper...")
scrape_pubmed()
print("Script finished.")
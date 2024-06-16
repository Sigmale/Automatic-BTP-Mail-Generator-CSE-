import requests
from bs4 import BeautifulSoup
import urllib.parse
import certifi
import re
from datetime import datetime
import urllib3
from flask import Flask, render_template, request

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Example list of departments and their URLs
departments = {
    'Department of Computer Science and Engineering': 'https://www.cse.iitd.ac.in/',
    'Department of Electrical Engineering': 'https://ee.iitd.ac.in/',
    'Department of Energy Science': 'https://dese.iitd.ac.in',
    # Add more departments as needed
}

def find_faculty_link(dept_url, retries=2):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    def get_response(url, headers=None, verify=True):
        try:
            response = requests.get(url, headers=headers, verify=verify)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    response = None
    original_url = dept_url

    for attempt in range(retries):
        response = get_response(dept_url, headers=headers, verify=False)
        if response and response.status_code == 200:
            break
        else:
            print(f"Attempt {attempt+1} failed with status code {response.status_code if response else 'None'}.")
            if 'https://' in dept_url:
                dept_url = dept_url.replace('https://', 'http://')
            elif 'http://' in dept_url:
                dept_url = dept_url.replace('http://', 'https://')
            if 'www.' in dept_url:
                dept_url = dept_url.replace('www.', '')
            elif attempt < retries - 1:
                dept_url = 'www.' + original_url.lstrip('http://').lstrip('https://')

    if not response or response.status_code != 200:
        print("Failed to fetch a valid response from both URLs.")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    potential_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        parsed_href = urllib.parse.urlparse(href)
        
        if parsed_href.path.rstrip('/').endswith('/faculty'):
            full_url = urllib.parse.urljoin(dept_url, href)
            potential_links.append(full_url)
            print(f"Found potential faculty link: {full_url}")

    if potential_links:
        return potential_links[0]

    print("Faculty link not found.")
    return None

def scrape_faculty_info(faculty_page_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(faculty_page_url, headers=headers, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {faculty_page_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    faculty_info_list = []

    # Extract faculty names from the HTML
    def extract_faculty_names(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        faculty_names = []
        for row in soup.find_all('tr'):
            if row.find('a'):  # Check if 'a' tag is present
                faculty_type = row.find_previous('span', class_='whiteHead')
                if faculty_type and 'faculty' in faculty_type.text.lower():
                    faculty_name_tag = row.find('a')
                    if faculty_name_tag:
                        faculty_name = faculty_name_tag.text.strip()
                        faculty_names.append(faculty_name)
        return faculty_names

    # Call the function to extract faculty names
    faculty_names = extract_faculty_names(response.text)

    return faculty_names

# Function to get research-related links for a professor
def get_professor_research_links(prof_name):
    # Construct the search URL for Google
    search_query = f"{prof_name} IITD research topics"
    search_url = f"https://www.google.com/search?q={search_query}"
    
    # Google search user-agent string to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    # Fetch the search results page
    try:
        response = requests.get(search_url, headers=headers, verify=certifi.where())
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {search_url}: {e}")
        return []
    
    # Parse the search results page
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract links from the search results
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/url?'):
            # Extract the URL after `url=`
            url_param = href.split('url=')[1]
            # Get the actual URL by splitting off the '&' parameter
            actual_url = url_param.split('&')[0]
            # Decode the URL
            decoded_url = urllib.parse.unquote(actual_url)
            # Check if the decoded URL is relevant
            if "iitd.ac.in" in decoded_url or "scholar.google" in decoded_url:
                links.append(decoded_url)
    
    # Optionally, deduplicate the links
    cleaned_links = list(set(links))
    
    return cleaned_links

# Function to scrape research-related information from the provided links
def scrape_research_info_from_links(links):
    research_info = {}
    
    for link in links:
        try:
            # Fetch the page content
            response = requests.get(link, verify=certifi.where())
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Initialize storage for information from this link
            info = {
                'research_sections': []
            }
            
            # Scrape research-related sections
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'section']):
                if 'research' in header.get_text(strip=True).lower():
                    section = {}
                    section_title = header.get_text(strip=True)
                    # Collect text from the section
                    content = []
                    next_sibling = header.find_next_sibling()
                    while next_sibling and next_sibling.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'section']:
                        if next_sibling.name in ['p', 'ul', 'ol', 'div', 'section']:
                            content.append(next_sibling.get_text(separator=' ', strip=True))
                        next_sibling = next_sibling.find_next_sibling()
                    section['title'] = section_title
                    section['content'] = ' '.join(content)
                    info['research_sections'].append(section)
            
            # Filter research sections by date (omit before 2020)
            filtered_sections = []
            for section in info['research_sections']:
                section_content = section['content'].lower()
                # Use regex to find dates in the format YYYY or YYYY-MM or YYYY/MM or YYYY.MM
                dates_found = re.findall(r'\b(20\d{2})[-/.]?\b', section_content)
                if dates_found:
                    # Convert found dates to datetime objects
                    found_years = [int(date) for date in dates_found]
                    # Only include sections where the latest date is 2020 or later
                    if max(found_years) >= 2020:
                        filtered_sections.append(section)
                else:
                    # If no date found, assume it's relevant or include additional logic if needed
                    filtered_sections.append(section)
            
            # Save information for this link
            if filtered_sections:
                info['research_sections'] = filtered_sections
                research_info[link] = info
            else:
                print(f"No relevant research information found on {link}")
        
        except Exception as e:
            print(f"Error processing {link}: {e}")
            continue
    
    return research_info



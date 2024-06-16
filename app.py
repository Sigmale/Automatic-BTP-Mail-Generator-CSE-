from flask import Flask, render_template, request
from my_module import find_faculty_link, scrape_faculty_info, get_professor_research_links, scrape_research_info_from_links
import google.generativeai as genai #type: ignore
from flask_cors import CORS #type: ignore
app = Flask(__name__)
CORS(app)
api_key = 'AIzaSyCzT84td0hzm-rY0-4wu3d_82N9y2hVytU'
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')



# Example list of departments and their URLs
departments = {
    'Department of Computer Science and Engineering': 'https://www.cse.iitd.ac.in/',
    # 'Department of Electrical Engineering': 'https://ee.iitd.ac.in/',
    # 'Department of Energy Science': 'https://dese.iitd.ac.in/',
    # Add more departments as needed
}


# Landing page - Form to input user details
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Fetch form data
        global name 
        global entry_number
        name = request.form.get('name')
        entry_number = request.form.get('entry_number')
        department = request.form.get('department')

        # Validate form data (you can add validation as per your requirement)

        # Find faculty link for the selected department
        dept_url = departments.get(department)
        if dept_url:
            faculty_url = find_faculty_link(dept_url)
            if faculty_url:
                # Scrape faculty names
                faculty_names = scrape_faculty_info(faculty_url)
                return render_template('faculty_list.html', name=name, entry_number=entry_number, faculty_names=faculty_names)
            else:
                return "Faculty list not found for this department."
        else:
            return "Department URL not found."

    return render_template('index.html', departments=departments)

# Page to display research info for a selected professor
@app.route('/professor-research', methods=['GET'])
def professor_research():
    professor_name = request.args.get('professor_name')
    

    if professor_name:
        research_links = get_professor_research_links(professor_name)
        research_data = scrape_research_info_from_links(research_links)
        # for i in research_data:
        #     print(i)
        #     for j in research_data[i]:
        #         print(j)
        query_to_ai = f"""I am {name} with entry number {entry_number},  providing you raw data about research details of a prof {professor_name}, please write a very crisp,brief, academic, non buttering email (startting with Dear {professor_name} and wherever you add my name also add entry number in the brackets)
        to the prof that I am interested in your area of research, make sure to give very general info about his research, dont give details of any speicific research, just keep it light
        and ask if I can get a BTP under that prof"""
        f=False 
        for i in research_data.keys():
            for sections in research_data[i]['research_sections']:
                if (len(query_to_ai))>28000:
                    f=True 
                    break 
                query_to_ai+="Title:" + sections['title']+" content: "+ sections['content']
                print("-------->>> "+sections['content'])
            if f:break 
        research_data = model.generate_content(query_to_ai)
        research_data = {'Research':research_data.text }
        
        return render_template('research_info.html', professor_name=professor_name, research_data=research_data)
    else:
        return "Professor name not provided."

if __name__ == '__main__':
    app.run(debug=True,port = 5003)

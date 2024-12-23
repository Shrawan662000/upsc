
import os  
import fitz
from openai import AzureOpenAI  
from dotenv import  load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)

# CORS configuration
cors_config = {
    "origins": ["http://example.com", "http://localhost:3000"],  # Allowed origins
    "methods": ["GET", "POST", "PUT", "DELETE"],                # Allowed methods
    "allow_headers": ["Content-Type", "Authorization"]          # Allowed headers
}

# Apply CORS with configuration
CORS(app, resources={r"/upsc/*": cors_config})


load_dotenv()

endpoint = os.getenv("ENDPOINT_URL", "https://azopenaiabhyas.openai.azure.com/")  

model = os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini")  
subscription_key = os.getenv("AZURE_OPENAI_API_KEY") 

# Initialize Azure OpenAI client with key-based authentication    
client = AzureOpenAI(  
    azure_endpoint=endpoint,  
    api_key=subscription_key,  
    api_version="2024-05-01-preview",  
)



def extract_text_from_pdf(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    extracted_text = ""

    # Iterate through all the pages
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        extracted_text += page.get_text()  # Extract text from the page
    
    pdf_document.close()
    return extracted_text





def questions(prompt, client, model):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that prepares the questions equivalent to UPSC Prelims standards"
        },
        {
            "role": "user",
            "content": prompt,
        }
    ]


    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=8000,
        temperature=0.5,
        stream=False
    )
    return stream 



UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/upsc/questions', methods=['POST'])
def upsc_questions():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            # Extract text from the PDF
            content = extract_text_from_pdf(file_path)

            prompt=f'''You are tasked with generating questions from the below given content, adhering to the Indian UPSC (Union Public Service Commission) prelims standard. Each section in the content corresponds to a unique topic. Generate at most two questions per section based on the following guidelines:


            ## Content : {content}

            Question Types:
            a. MCQ (Multiple Choice Question): Provide one question with four options, only one of which is correct.
            b. MSQ (Multiple Select Question): Provide one question with four options, one or more of which may be correct.
            c. Pair Matching Question: Provide one question where the left side contains at least 4 options (n ≥ 4) and the right side also contains at least 4 options (n ≥ 4). Match the items on the left with their correct counterparts on the right.


            ## Some Important Instruction:
            1. The questions should be framed in a way that they are answerable from the given content.
            2. Do not generate any questions outside  the given content.
            3. Decide the correct answers only based on the given content, without making assumptions or deciding answers independently.

            ## Instructions for Answer and Explanation:
            1. Include the correct answer for each question.
            2. Provide a short explanation for why the answer is correct.



            ## Desired output format
            Output Format:
            Section Name
            Question Type (e.g., MCQ, MSQ, Pair Matching):
            Question text...
            Options (if applicable)...
            Answer:
            Correct answer(s).
            Explanation: A concise explanation for the answer.

            '''

                
            result=questions(prompt, client, model)
            result = result.choices[0].message.content
            return jsonify({"questions": result})
                    

        except Exception as e:
            return jsonify({"error": f"Error processing the file: {str(e)}"}), 500

    else:
        return jsonify({"error": "Allowed file types are PDF"}), 400




if __name__ == '__main__':
    app.run(debug=True)

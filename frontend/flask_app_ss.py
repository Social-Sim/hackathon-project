from flask import Flask, request
from flask_cors import CORS
import openai
import ast  # import the ast module

app = Flask(__name__)
CORS(app)
openai.api_key = "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"

@app.route('/get_completion', methods=['POST'])
def get_completion():
    data = request.json
    user_input = data['user_input']

    messages = [
        {"role": "system", "content": f"You are a conversational AI taking on the role of Eileen. The user is taking on the role of student. When you receive '{user_input}' return what you think Eileen would say. Return the responses in the format as a list of tuples and always include a student response at the end. Do not use any apostrophes when writing Eileen or the student response. [('Eileen', 'that is really nice'), ('Eileen', 'maybe you could also give them cookies'), ('Student', 'hello')]"},
        {"role": "user", "content": user_input},
    ]

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )

    # Convert the string of tuples to actual tuples using ast.literal_eval
    messages = ast.literal_eval(completion['choices'][0]['message']['content'])

    return {"messages": messages}

if __name__ == "__main__":
    app.run(port=8000, debug=True)

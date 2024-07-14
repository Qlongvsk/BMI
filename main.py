
import os 
import re
import traceback
import json, time
from dotenv import load_dotenv
load_dotenv()
from utils.utils import getenv, set_env_variables

from fastapi import FastAPI, Request, status, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from agents.responseAgent import ResponseAgent
from handlers.msgHandlers import msg_handler

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


######## CHAT COMPLETIONS ################    

def tinhbmi(user_input):
    # Sử dụng regex để lấy chiều cao và cân nặng
    user_content = None
    for message in user_input['messages']:
        if message['role'] == 'user':
            user_content = message['content']

    height_match = re.search(r'cao (\d+) cm', user_content)
    weight_match = re.search(r'(\d+) kg', user_content)

    result = None

    if height_match and weight_match:
        height = int(height_match.group(1)) / 100  # Chuyển đổi chiều cao từ cm sang m
        weight = int(weight_match.group(1))

        # Tính chỉ số BMI
        bmi = weight / (height ** 2)
        result = f"Chỉ số BMI của tôi là: {bmi:.2f}"

    print(f"i am user content: {result}")

    if result:
        return result
    else:
        return None

# for streaming
def data_generator(response):
    for chunk in response:
        # print(f"chunk: {chunk}")
        yield f"data: {json.dumps(chunk.json())}\n\n"

# for completion
@app.post("/chat/completions")
async def completion(request: Request):
    data = await request.json()
    print(f"received request data: {data}")

    user_input = data
    result = tinhbmi(user_input)

    if result:
        response_agent = ResponseAgent(config=result)
    else:
        set_env_variables(data)
        data = msg_handler(data)
        response_agent = ResponseAgent(config=data)


    # handle how users send streaming
    if 'stream' in data:
        if type(data['stream']) == str: # if users send stream as str convert to bool
            # convert to bool
            if data['stream'].lower() == "true":
                data['stream'] = True # convert to boolean
    
    response = response_agent.generate(**data)
    if 'stream' in data and data['stream'] == True: # use generate_responses to stream responses
            return StreamingResponse(data_generator(response), media_type='text/event-stream')
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=getenv("PORT", 8080))
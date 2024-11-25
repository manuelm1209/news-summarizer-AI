import openai
import os
from dotenv import find_dotenv, load_dotenv
import time
import logging
from datetime import datetime
import requests
import json
import streamlit as st

# === Environment Setup ===
load_dotenv()

# Newsapi.org API key from .env
news_api_key = os.environ.get("NEWS_API_KEY")

# === OpenAI API Client Configuration ===
client = openai.OpenAI()
model = "gpt-4o-mini"

def get_news(topic):
    url = (
        f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5"
    )
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent=4)
            news_json = json.loads(news)
            
            data = news_json
            
            # Access all the fiels == loop through
            status = data["status"]
            total_results = data["totalResults"]
            articles = data["articles"]
            final_news = []
            
            # Loop through articles
            for article in articles:
                source_name = article["source"]["name"]
                author = article["author"]
                title = article["title"]
                description = article["description"]
                url = article["url"]
                content = article["content"]
                title_description = f"""
                    Title: {title},
                    Author: {author},
                    Source: {source_name},
                    Description: {description},
                    URL: {url}
                """
                final_news.append(title_description)
                
            return final_news
        else:
            return []
                
    except requests.exceptions.RequestException as e:
        print("Error occured during API Request", e)
    
class AssistantManager:
    thread_id = None
    assistant_id = None
    
    def __init__(self, model: str = model) -> None:
        self.client = client
        self.model = model
        self.assistant = (None,)
        self.thread = (None,)
        self.run = None
        self.summary = None
        
        # Retrieve existing assistant and thread if IDs are already set
        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id = AssistantManager.assistant_id
            )
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retreave(
                thread_id = AssistantManager.thread_id
            )
    def create_assistant(self, name, instructions, tools):
        if not self.assistant:
            assistant_obj = self.client.beta.assistant.create(
                name = name,
                instructions = instructions,
                tools = tools,
                model = self.model
            )
            AssistantManager.assistant_id = assistant_obj.id
            self.assistant = assistant_obj
            print(f"AssistAI:::: {self.assistant.id}")
            
    def create_thread(self):
        if not self.thread:
            thread_obj = self.client.beta.thread.create()
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj
            print(f"ThreadID::: {self.thread.id}")
    
    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id = self.thread.id,
                role = role,
                content = content
            )     
    def run_assistant(self, instructions):
        if self.thread and self.assistant:
            self.run = self.client.beta.threads.runs.create(
                thread_id = self.thread.id,
                assistant_id = self.assistant.id,
                instructions = instructions
            )
            
    def process_message(self):
        if self.thread:
            messages = self.cliet.beta.threads.messages.list(thread_id = self.thread.id)
            summary = []
            
            last_message = messages.data[0]
            role = last_message.role
            response = last_message.content[0].text.value
            summary.append(response)
            
            self.summary = "\n".join(summary)
            print(f"\nSUMMARY-----> {role.capitalize()}: ==> {response}")

            # for msg in messages:
            #     role = msg.role
            #     content = msg.content[0].text.value
            #     print(f"\nSUMMARY-----> {role.capitalize()}: ==> {response}")
            
    def call_required_functions(self, required_actions):
        if not self.run:
            return
        tool_outputs = []
        
        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])
            
            if func_name == "get_news":
                output = get_news(topic = arguments["topic"])
                print(f"STUFFFFF;;;;; {output}")
                final_str = ""
                for item in output:
                    final_str += "".join(item)
                
                tool_outputs.append({"tool_call_id": action["id"],
                                     "output": final_str})
            else:
                raise ValueError(f"Unknown function : {func_name}")
                
                print("Submiting outputs back to the Assistant...")
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id = self.thread.id,
                    run_id = self.run.id,
                    tool_outputs = tool_outputs
                    )

    # for streamlit
    def get_summary(self):
        return self.summary
                
    def wait_for_completed(self):
        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id = self.thread.id,
                    run_id = self.run.id
                )
                print(f"RUN STATUS:: {run_status.model_dump_json(indent=4)}")
                
                if run_status.status == "completed":
                    self.process_message
                    break
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW...")
                    self.call_required_functions(
                        required_actions = run_status.required_action.submit_tool_outputs.mode_dump()
                    )
                
    # Run the steps
    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id = self.thread.id
            run_id = self.run.id
        )
        print(f"RUN-STEPS::: {run_steps}")
         
def main():
    # news = get_news("bitcoin")
    # print(news)   
    manager = AssistantManager()
    
    # Streamlit interface
    st.title("News Summarizer")
    
    #TODO ----- continue HERE -------
    
            
if __name__ == "__main__":
    main()
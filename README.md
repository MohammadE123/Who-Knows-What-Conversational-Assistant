"Who Knows What" Conversational Assistant
"Who Knows What" is an AI-powered assistant designed to help interns, new hires, and team members quickly identify who in the organization has expertise in specific skills or has worked on particular projects. By building a knowledge graph from internal documents, this app provides a high-level view of your company’s structure and expertise, reducing time spent tracking down the right person.

Quick Start
Follow these steps to get the app up and running locally:

1. Clone this Repository

2. Install Dependencies
a. Install Python Packages

b. Set Up Neo4j Desktop
Neo4j is used to create a local knowledge graph that the LLM can query.

Download Neo4j Desktop: Neo4j Official Site
Create a Database Instance:
Click "Create" in the top right.
Set a name and password (default username is neo4j).
Install APOC Plugin:
Click the three dots on the instance card → Plugins → Search for APOC → Install.
Edit neo4j.conf:
Click the three dots → "Open neo4j.conf".
Add the following line:

Start the Database:
Click the Play button.
Wait until the status shows Running in green.
📚 For more details, refer to the Neo4j Documentation.

c. Install Ollama
Ollama is a tool for running large language models entirely on-device.

Install Ollama: Ollama GitHub
Install the LLM (Phi-4):

This will download the model and open a chatbot (which you can close). The model is now ready for use.
3. (Optional) Replace Dummy Data
You can replace the contents of the data/ folder with your own company-specific documents. The folder includes:

people_profiles/
project_briefs/
messages/
For this tutorial, we’ll use the provided dummy data.

4. Configure Environment Variables
Create a .env file in the root directory with the following:


Then, generate the knowledge graph:


5. View the Knowledge Graph
Once the graph is built (this may take 30–60 minutes), you can view it in Neo4j:

Go to the Query tab.
Run the following Cypher command to visualize the entire graph:

✅ This is a one-time setup step.

6. Run the App
Once the graph is ready, launch the app:


7. Start Asking Questions!
You can now interact with the assistant:

Ask questions about people, projects, or skills.
The app will show:
The chat history.
The Cypher query used (if applicable).
The response from the LLM.

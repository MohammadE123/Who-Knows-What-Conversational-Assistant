# 🧠 "Who Knows What" Conversational Assistant

"Who Knows What" is an AI-powered assistant designed to help interns, new hires, and team members quickly identify who in the organization has expertise in specific skills or has worked on particular projects. By building a knowledge graph from internal documents, this app provides a high-level view of your company’s structure and expertise, reducing time spent tracking down the right person.

---

## 🚀 Quick Start

Follow these steps to get the app up and running locally:

### 1. Clone this Repository

```bash
git clone https://github.com/MohammadE123/Who-Knows-What-Conversational-Assistant.git
cd Who-Knows-What-Conversational-Assistant
```

---

#### a. Set Up a Virtual Environment and Install Python Packages

> ⚠️ **Note:** Make sure you're using the **Python x86 (Intel/AMD)** version. The **ARM version** caused compatibility issues with certain dependencies.  
> ✅ This app was built and tested using **Python 3.10**, which is recommended for best compatibility.

It's recommended to use a virtual environment to manage dependencies.

Create and activate a virtual environment:

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

Then install the required packages:

```bash
pip install -r requirements.txt
```



#### b. Set Up Neo4j Desktop

Neo4j is used to create a local knowledge graph that the LLM can query.

- Download Neo4j Desktop: Neo4j Official Site
- Create a Database Instance:
  - Click **"Create"** in the top right.
  - Set a **name** and **password** (default username is `neo4j`).
- Install APOC Plugin:
  - Click the **three dots** on the instance card → **Plugins** → Search for **APOC** → Install.
- Edit `neo4j.conf`:
  - Click the **three dots** → **"Open neo4j.conf"**
  - Add the following line:

    ```plaintext
    dbms.security.procedures.unrestricted=apoc.meta.data
    ```

- Start the Database:
  - Click the **Play** button.
  - Wait until the status shows **Running** in green.

📚 For more details, refer to the Neo4j Documentation.

#### c. Install Ollama

Ollama is a tool for running large language models entirely on-device.

- Install Ollama: Ollama GitHub
- Install the LLM Phi-4 (for the database generation) and llama3.2 for the apps llm:
  
> The Phi-4 model has a higher number of parameters than LLaMA 3.2, making it more powerful for generating the knowledge graph and delivering more accurate results.

```bash
ollama run phi4
ollama run llama3.2
```

This will download the models and open a chatbot (which you can close). The models are now ready for use.

---

### 3. (Optional) Replace Dummy Data

You can replace the contents of the `data/` folder with your own company-specific documents. The folder includes:

- `people_profiles/`
- `project_briefs/`
- `messages/`

For this tutorial, we’ll use the provided dummy data.

---

### 4. Configure Environment Variables

Open the `neo4j.env` file in the root directory and replace the following with your credentials:

```env
NEO4J_URI=bolt:"your uri"
NEO4J_USERNAME="your username"
NEO4J_PASSWORD="your password"

```

Then, generate the knowledge graph:

```bash
python database_gen.py
```

---

### 5. View the Knowledge Graph

Once the graph is built (this may take 30–60 minutes), you can view it in Neo4j:

- Go to the **Query** tab.
- Run the following Cypher command to visualize the entire graph:

```cypher
MATCH (n) OPTIONAL MATCH (n)-[r]->(m) RETURN n, r, m
```
It should look something like:

<img width="556" height="479" alt="Screenshot 2025-07-13 182001" src="https://github.com/user-attachments/assets/3597fe26-40b8-4e2e-8d10-e8e1ed788f58" />

> This is a one-time setup step.

---

### 6. Run the App

Once the graph is ready, launch the app:

```bash
streamlit run main.py
```

---

### 7. Start Asking Questions!

You can now interact with the assistant:

- Ask questions about people, projects, or skills.
- The app will show:
  - The chat history.
  - The Cypher query used (if applicable).
  - The response from the LLM.
*** when referencing names make sure to include the full name with proper capitalization, otherwise the query may be unsuccessful

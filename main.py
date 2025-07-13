import streamlit as st
from streamlit_chat import message
from timeit import default_timer as timer

from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain.prompts.prompt import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain_ollama import OllamaLLM
from dotenv import load_dotenv

# Load environment variables
load_dotenv("neo4j.env")

# Initialize LLM
llm = OllamaLLM(model="llama3.2")

#Neo4j configuration
neo4j_url = os.getenv("NEO4J_CONNECTION_URL")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")

# Classification prompt
classification_prompt = PromptTemplate(
    input_variables=["question"],
    template="""
You are a classifier that determines whether a user's question requires querying a Neo4j database.
If the question is about people, projects, technologies, skills, or Slack messages in the workplace, respond with "QUERY".
If the question is general, conversational, or doesn't require data lookup, respond with "NOQUERY".
Only respond with "QUERY" or "NOQUERY".

Question: {question}
Answer:"""
)
classifier_chain = LLMChain(llm=llm, prompt=classification_prompt)

# Cypher generation prompt
cypher_generation_template = """
You are an expert Neo4j Cypher translator who converts English to Cypher based on the Neo4j Schema provided, following the instructions below:
1. Generate Cypher query compatible ONLY for Neo4j Version 5
2. Do not use EXISTS, SIZE, or HAVING keywords in the cypher. Use alias when using the WITH keyword
3. Use only Nodes and relationships mentioned in the schema
4. Always do a case-insensitive and fuzzy search for any properties related search. Eg: to search for a Client, use `toLower(client.id) contains 'neo4j'`. To search for Slack Messages, use 'toLower(SlackMessage.text) contains 'neo4j'`. To search for a project, use `toLower(project.summary) contains 'logistics platform' OR toLower(project.name) contains 'logistics platform'`.)
5. Never use relationships that are not mentioned in the given schema
6. When asked about projects, Match the properties using case-insensitive matching and the OR-operator, E.g, to find a logistics platform -project, use `toLower(project.summary) contains 'logistics platform' OR toLower(project.name) contains 'logistics platform'`.
7. When writing `MATCH` or `OPTIONAL MATCH` clauses, always wrap nodes in parentheses. For example:
    INVALID: OPTIONAL MATCH p<-[:HAS_SKILLS]-(t:Technology)
    VALID:   OPTIONAL MATCH (p)<-[:HAS_SKILLS]-(t:Technology)

   This applies to all directions of relationships:
   - (a)-[:REL]->(b)
   - (a)<-[:REL]-(b)
   - (a)-[:REL]-(b)

   Never leave a node unwrapped in a pattern.



schema: {schema}

Use the following examples to guide your Cypher query generation:

1. People and Their Skills/Technologies
---------------------------------------
MATCH (p:Person)-[:HAS_SKILLS]->(t:Technology)
RETURN p.name, t.name

2. Projects and Their People/Clients
------------------------------------
MATCH (pr:Project)-[:HAS_PEOPLE]->(p:Person)
RETURN pr.name, p.name

MATCH (pr:Project)-[:HAS_CLIENT]->(c:Client)
RETURN pr.name, c.name

3. Technologies Used in Projects (Indirectly via People)
---------------------------------------------------------
MATCH (pr:Project)-[:HAS_PEOPLE]->(p:Person)-[:USES_TECH]->(t:Technology)
RETURN pr.name, t.name

4. Slack Messages
-----------------
MATCH (m:SlackMessage)
RETURN m.text
LIMIT 10

MATCH (m:SlackMessage)
WHERE toLower(m.text) CONTAINS 'deadline'
RETURN m.text

5. Clients and Their Projects
-----------------------------
MATCH (c:Client)<-[:HAS_CLIENT]-(pr:Project)
RETURN c.name, pr.name

6. Advanced Filtering
---------------------
If you want to find technologies for a specific person (e.g., by name for a person named Liam Thompson):
MATCH (p:Person)-[:HAS_SKILLS]->(t:Technology)
WHERE toLower(p.name) CONTAINS 'liam thompson'
RETURN p.name, t.name

if you want to find technologies for a specific project:
MATCH (p:Project)-[:USES_TECH]->(t:Technology)
WHERE toLower(p.name) CONTAINS 'api gateway'
RETURN p.name, t.name

and do not return anything but the cypher query!


Question: {question}
"""




cypher_prompt = PromptTemplate(
    template=cypher_generation_template,
    input_variables=["schema", "question"]
)

#QA Prompt
qa_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are an assistant that helps to form nice and human understandable answers based on the question: {question}.

this is a response:
{context}

your job is to deliver this answer in a human readable way. 

"""
)


# Query function
def query_graph(user_input):
    graph = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_password)
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        return_intermediate_steps=True,
        cypher_prompt=cypher_prompt,
        qa_prompt=qa_prompt,
        allow_dangerous_requests=True
    )
    return chain(user_input)

# Streamlit UI
st.set_page_config(layout="wide")

if "user_msgs" not in st.session_state:
    st.session_state.user_msgs = []
if "system_msgs" not in st.session_state:
    st.session_state.system_msgs = []

title_col, _, img_col = st.columns([2, 1, 2])
with title_col:
    st.title("\"Who Knows What\" Conversational Assistant")
with img_col:
    st.image("Screenshot 2025-07-13 171348.png", width=500)

user_input = st.text_input("Enter your question", key="input")
if user_input:
    with st.spinner("Processing your question..."):
        st.session_state.user_msgs.append(user_input)
        start = timer()

        try:
            classification = classifier_chain.run(user_input).strip().upper()
            if classification == "QUERY":
                result = query_graph(user_input)
                intermediate_steps = result["intermediate_steps"]
                cypher_query = intermediate_steps[0]["query"]
                database_results = intermediate_steps[1]["context"]
                answer = result["result"]
            else:
                cypher_query = ""
                database_results = ""
                answer = llm.invoke(f"Respond conversationally to: {user_input}")

            st.session_state.system_msgs.append(answer)
        except Exception as e:
            st.write("Failed to process question. Please try again.")
            print(e)

    st.write(f"Time taken: {timer() - start:.2f}s")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        for i in range(len(st.session_state["system_msgs"]) - 1, -1, -1):
            message(st.session_state["system_msgs"][i], key=str(i) + "_assistant")
            message(st.session_state["user_msgs"][i], is_user=True, key=str(i) + "_user")
    with col2:
        if 'cypher_query' in locals() and cypher_query:
            st.text_area("Last Cypher Query", cypher_query, key="_cypher", height=240)
    with col3:
        if 'database_results' in locals() and database_results:
            st.text_area("Last Database Results", database_results, key="_database", height=240)

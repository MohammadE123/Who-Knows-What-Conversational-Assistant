import os
from string import Template
import json
from neo4j import GraphDatabase
import glob
from timeit import default_timer as timer
from dotenv import load_dotenv
from time import sleep
from ollama import chat

from dotenv import load_dotenv

# Load environment variables
load_dotenv("neo4j.env")

#Neo4j configuration
neo4j_url = os.getenv("NEO4J_CONNECTION_URL")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
gds = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_password))

def process_llama(file_prompt, system_msg):
    conversation = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": file_prompt}
    ]

    # No streaming — get full response at once
    reply = chat(model='phi4', messages=conversation, format="json")
    response_text = reply.message.content

    sleep(8)  # Optional delay
    return response_text



def extract_entities_relationships(folder, prompt_template):
    start = timer()
    files = glob.glob(f"./data/{folder}/*")
    system_msg = "You are a helpful IT-project and account management expert who extracts information from documents."
    print(f"Running pipeline for {len(files)} files in {folder} folder")
    results = []
    for i, file in enumerate(files):
        print(f"Extracting entities and relationships for {file}")
        try:
            with open(file, "r") as f:
                text = f.read().rstrip()
                prompt = Template(prompt_template).substitute(ctext=text)
                result = process_llama(prompt, system_msg=system_msg)
                json_obj = json.loads(result)
                results.append(json_obj)

                # Save each JSON object to a file in the root directory
                base_filename = os.path.basename(file)
                json_filename = f"{os.path.splitext(base_filename)[0]}_output.json"
                with open(json_filename, "w") as json_file:
                    json.dump(json_obj, json_file, indent=2)

        except Exception as e:
            print(f"Error processing {file}: {e}")
    end = timer()
    print(f"Pipeline completed in {end-start} seconds")
    return results




# Function to take a json-object of entitites and relationships and generate cypher query for creating those entities
def generate_cypher(json_obj):
    e_statements = []
    r_statements = []

    e_label_map = {}

    # loop through our json object
    for i, obj in enumerate(json_obj):
        print(f"Generating cypher for file {i+1} of {len(json_obj)}")
        for entity in obj["entities"]:
            label = entity["label"]
            id = entity["id"]
            id = id.replace("-", "").replace("_", "")
            properties = {k: v for k, v in entity.items() if k not in ["label", "id"]}

            cypher = f'MERGE (n:{label} {{id: "{id}"}})'
            if properties:
                props_str = ", ".join(
                    [f'n.{key} = "{val}"' for key, val in properties.items()]
                )
                cypher += f" ON CREATE SET {props_str}"
            e_statements.append(cypher)
            e_label_map[id] = label

        for rs in obj["relationships"]:
            src_id, rs_type, tgt_id = rs.split("|")
            src_id = src_id.replace("-", "").replace("_", "")
            tgt_id = tgt_id.replace("-", "").replace("_", "")

            src_label = e_label_map[src_id]
            tgt_label = e_label_map[tgt_id]

            cypher = f'MERGE (a:{src_label} {{id: "{src_id}"}}) MERGE (b:{tgt_label} {{id: "{tgt_id}"}}) MERGE (a)-[:{rs_type}]->(b)'
            r_statements.append(cypher)

    with open("cyphers.txt", "w") as outfile:
        outfile.write("\n".join(e_statements + r_statements))

    return e_statements + r_statements


# Final function to bring all the steps together
def ingestion_pipeline(folders):
    # Extrating the entites and relationships from each folder, append into one json_object
    entities_relationships = []
    for key, value in folders.items():
        entities_relationships.extend(extract_entities_relationships(key, value))

    # Generate and execute cypher statements
    cypher_statements = generate_cypher(entities_relationships)
    for i, stmt in enumerate(cypher_statements):
        print(f"Executing cypher statement {i+1} of {len(cypher_statements)}")
        try:
            gds.execute_query(stmt)
        except Exception as e:
            with open("failed_statements.txt", "w") as f:
                f.write(f"{stmt} - Exception: {e}\n")

# Prompt for processing project briefs
project_prompt_template = """
From the Project Brief below, extract the following Entities & relationships described in the mentioned format 
0. ALWAYS FINISH THE OUTPUT. Never send partial responses
1. First, look for these Entity types in the text and generate as comma-separated format similar to entity type.
   `id` property of each entity must be alphanumeric and must be unique among the entities and ensure that all the ids are in lowercase. You will be referring this property to define the relationship between entities. Do not create new entity types that aren't mentioned below. Document must be summarized and stored inside Project entity under `summary` property. You will have to generate as many entities as needed as per the types below:
    Entity Types:
    label:'Project',id:string,name:string;summary:string //Project mentioned in the brief; `id` property is the full name of the project, in lowercase, with no capital letters, special characters, spaces or hyphens; Contents of original document must be summarized inside 'summary' property
    label:'Technology',id:string,name:string //Technology Entity; `id` property is the name of the technology, in camel-case. Identify as many of the technologies used as possible
    label:'Client',id:string,name:string;industry:string //Client that the project was done for; `id` property is the name of the Client, in camel-case; 'industry' is the industry that the client operates in, as mentioned in the project brief.
    
2. Next generate each relationships as triples of head, relationship and tail. To refer the head and tail entity, use their respective `id` property. Relationship property should be mentioned within brackets as comma-separated. They should follow these relationship types below. You will have to generate as many relationships as needed as defined below and ensure that all the ids are in lowercase:
    Relationship types:
    project|USES_TECH|technology 
    project|HAS_CLIENT|client



3. for example The output should look like :
{
    "entities": [{"label":"Project","id":string,"name":string,"summary":string}],
    "relationships": ["project|USES_TECH|technology"]
}

an example with values:
{
  "entities": [
    {
      "label": "Project",
      "id": "prj101",
      "name": "Smart City Infrastructure",
      "summary": "A project focused on integrating IoT and AI to improve urban living through smart traffic systems, energy management, and public safety."
    },
    {
      "label": "Technology",
      "id": "tech001",
      "name": "Internet of Things"
    },
    {
      "label": "Technology",
      "id": "tech002",
      "name": "Artificial Intelligence"
    }
  ],
  "relationships": [
    "prj101|USES_TECH|tech001",
    "prj101|USES_TECH|tech002"
  ]
}

4. Extract all relevant entities and relationships from the following text. Return the result as a valid JSON object 


Case Sheet:
$ctext
"""


# Prompt for processing peoples' profiles
people_prompt_template = """From the list of people below, extract the following Entities & relationships described in the mentioned format 
0. ALWAYS FINISH THE OUTPUT. Never send partial responses
1. First, look for these Entity types in the text and generate as comma-separated format similar to entity type.
   `id` property of each entity must be alphanumeric and must be unique among the entities and ensure that all the ids are in lowercase. You will be referring this property to define the relationship between entities. Do not create new entity types that aren't mentioned below. You will have to generate as many entities as needed as per the types below:
    Entity Types:
    label:'Person',id:string,name:string //Person that the data is about. `id` property is the name of the person, in camel-case. 'name' is the person's name, as spelled in the text.
    label:'Project',id:string,name:string;summary:string //Project mentioned in the profile; `id` property is the full lowercase name of the project, with no capital letters, special characters, spaces or hyphens.
    label:'Technology',id:string,name:string //Technology Entity, as listed in the "skills"-section of every person; `id` property is the name of the technology, in camel-case.
    
2. Next generate each relationships as triples of head, relationship and tail. To refer the head and tail entity, use their respective `id` property. Relationship property should be mentioned within brackets as comma-separated. They should follow these relationship types below. You will have to generate as many relationships as needed as defined below and ensure that all the ids are in lowercase:
    Relationship types:
    person|HAS_SKILLS|technology 
    project|HAS_PEOPLE|person



for example The output should look like :
{
    "entities": [{"label":"Person","id":string,"name":string}],
    "relationships": ["project|HAS_PEOPLE|person"]
}

an example with values:
{
  "entities": [
    {
      "label": "Person",
      "id": "p001",
      "name": "Alice Johnson"
    },
    {
      "label": "Person",
      "id": "p002",
      "name": "Bob Smith"
    },
    {
      "label": "Project",
      "id": "prj001",
      "name": "AI Research Initiative"
    }
  ],
  "relationships": [
    "prj001|HAS_PEOPLE|p001",
    "prj001|HAS_PEOPLE|p002"
  ]
}

3. Extract all relevant entities and relationships from the following text. Return the result as a valid JSON object 


Case Sheet:
$ctext
"""


# Prompt for processing slack messages

slack_prompt_template = """
From the list of messages below, extract the following Entities & relationships described in the mentioned format 
0. ALWAYS FINISH THE OUTPUT. Never send partial responses
1. First, look for these Entity types in the text and generate as comma-separated format similar to entity type.
   `id` property of each entity must be alphanumeric and must be unique among the entities and ensure that all the ids are in lowercase. You will be referring this property to define the relationship between entities. Do not create new entity types that aren't mentioned below. You will have to generate as many entities as needed as per the types below:
    Entity Types:
    label:'Person',id:string,name:string //Person that sent the message. `id` property is the name of the person, in camel-case; for example, "michaelClark", or "emmaMartinez"; 'name' is the person's name, as spelled in the text.
    label:'SlackMessage',id:string,text:string //The Slack-Message that was sent; 'id' property should be the message id, as spelled in the reference. 'text' property is the text content of the message, as spelled in the reference
    
2. Next generate each relationships as triples of head, relationship and tail. To refer the head and tail entity, use their respective `id` property. Relationship property should be mentioned within brackets as comma-separated. They should follow these relationship types below. You will have to generate as many relationships as needed as defined below and ensure that all the ids are in lowercase:
    Relationship types:
    person|SENT|slackmessage


for example The output should look like :
{
    "entities": [{"label":"SlackMessage","id":string,"text":string}],
    "relationships": ["person|SENT|slackmessage"]
}

an example with values:
{
  "entities": [
    {
      "label": "SlackMessage",
      "id": "msg001",
      "text": "Hey team, the deployment is scheduled for 3 PM today. Please be ready for testing."
    },
    {
      "label": "Person",
      "id": "user123",
      "name": "Jordan Lee"
    }
  ],
  "relationships": [
    "user123|SENT|msg001"
  ]
}

3. Extract all relevant entities and relationships from the following text. Return the result as a valid JSON object 



Case Sheet:
$ctext
"""


folders = {
    "people_profiles": people_prompt_template,
    "project_briefs": project_prompt_template,
    "slack_messages": slack_prompt_template
}


ingestion_pipeline(folders)


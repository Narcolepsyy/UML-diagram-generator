import streamlit as st
import dotenv
import os
import base64
import anthropic
import json
import docx
import re
from plantuml import PlantUML

dotenv.load_dotenv()


anthropic_models = [
    "claude-3-7-sonnet-20250219"
]


def file_to_base64(file):
    with open(file, "rb") as f:

        return base64.b64encode(f.read())



def main():

    # --- Page Config ---
    st.set_page_config(
        page_title="The UML diagram Generator",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    # --- Header ---
    st.html("""<h1 style="text-align: center; color: #6ca395;">🤖 <i>The UML diagram Generator</i> 💬</h1>""")

    # --- Side Bar ---
    with st.sidebar:
        cols_keys = st.columns(2)
        
        default_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") if os.getenv("ANTHROPIC_API_KEY") is not None else ""
        with st.popover("🔐 Anthropic"):
            anthropic_api_key = st.text_input("Introduce your Anthropic API Key (https://console.anthropic.com/)", value=default_anthropic_api_key, type="password")

        


    # --- Main Content ---
    # Checking if the user has introduced the OpenAI API Key, if not, a warning is displayed
    if (anthropic_api_key == "" or anthropic_api_key is None):
        st.write("#")
        st.warning("⬅️ Please introduce an API Key to continue...")



    # upload a pdf, word, txt the button appear after the user
    uploaded_file = st.file_uploader("Choose a file", type=["docx", "txt"])
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type,"FileSize":uploaded_file.size}
        st.write(file_details)
        if  uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            st.write("word")
        elif uploaded_file.type == "text/plain":
            st.write("txt")
        else:
            st.write("unsupported file type")
    # if the file is uploaded, read the content and display it
    if uploaded_file is not None :
        if uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            fullText = []
            for para in doc.paragraphs:
                fullText.append(para.text)
            text = '\n'.join(fullText)
            st.write(text)
        elif uploaded_file.type == "text/plain":
            text = uploaded_file.getvalue().decode("utf-8")
            st.write(text)
    
    client = anthropic.Client(api_key=anthropic_api_key)
    if st.button("🤖 Generate use case UML Diagram"):
            prompt = f"""
            Dây là yêu cầu phần mềm:{text}

            **BƯỚC 1:** Liệt kê **toàn bộ các actor**, bỏ qua các actor hệ thống, chú ý các actor kế thừa.
            **BƯỚC 2:** Liệt kê **toàn bộ các use case**.
            **BƯỚC 3:** Xác định **tất cả các mối quan hệ** và cho biết loại quan hệ, bao gồm:
            - **Association** (Actor liên kết với Use Case)
            - **Include** (Use Case A bắt buộc gọi Use Case B)
            - **Extend** (Use Case A mở rộng Use Case B)
            - **Generalization** (Actor kế thừa từ Actor khác) chú ý không bỏ sót quan hệ này.
            
            Xuất định dạng json schema có cấu trúc:
            {{
                "actors": ["Actor1", "Actor2", ...],
                "use_cases": ["UseCase1", "UseCase2", ...],
                "relationships": [["Entity1", "Entity2", "RelationshipType"], ...]
            }}
            """
            # Initialize the model
            
            message = client.messages.create(
            model="claude-3-7-sonnet-20250219",  # Ensure this is a valid model
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
            # using regex to extract the actors, use cases and relationships

            response_text = message.content[0].text
            match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if match:
                json_text = match.group(1)
                data = json.loads(json_text)  # Chuyển thành Python dictionary
                
                # In nội dung JSON thuần túy
            else:
                print("Không tìm thấy JSON trong phản hồi!")
            
            # generate the plantuml code
            plantuml_code = """@startuml
            left to right direction
            skinparam ActorPadding 30
            skinparam UseCasePadding 25
            skinparam Linetype ortho
            skinparam dpi 150
            legend left
            Association  --> Solid Line
            Include      ..> Dashed Line
            Extend       ..|> Dotted Line
            endlegend
            ' Define actors
            """
            for actor in data['actors']:
                plantuml_code += f"actor \"{actor}\" as {actor.replace(' ', '_')}\n"

            plantuml_code += "\n' Define use cases\n"
            for use_case in data['use_cases']:
                plantuml_code += f"usecase \"{use_case}\" as {use_case.replace(' ', '_')}\n"

            plantuml_code += "\n' Define relationships\n"
            for relation in data['relationships']:
                entity1 = relation[0].replace(' ', '_')
                entity2 = relation[1].replace(' ', '_')
                relation_type = relation[2]
                
                if relation_type == "Association":
                    plantuml_code += f"{entity1} -- {entity2}\n"
                elif relation_type == "Extend":
                    plantuml_code += f"{entity1} .> {entity2}\n"
                elif relation_type == "Include":
                    plantuml_code += f"{entity1} <. {entity2}\n"
                elif relation_type == "Generalization":
                    plantuml_code += f"{entity1} <|-- {entity2}\n"

            plantuml_code += "\n@enduml"  

            # Output the PlantUML code
            st.write("## PlantUML Code")
            st.code(plantuml_code, language="uml")
            uml_file = "diagram.puml"
            with open(uml_file, "w", encoding="utf-8") as f:
                f.write(plantuml_code)

            # Define the local or online PlantUML server
            plantuml_server = "http://www.plantuml.com/plantuml/png/"

            # Initialize PlantUML processor
            plantuml = PlantUML(url=plantuml_server)

            # Generate the diagram
            plantuml.processes_file(uml_file)
            # Display the diagram
            st.write("## UML Diagram")
            # after generating the diagram, display the image and download the file
            uml_image_file = "diagram.png"
            plantuml.processes_file(uml_file, outfile=uml_image_file)
            st.image(uml_image_file, caption="Generated UML Diagram")
            # show the download button
            st.write("## Download UML Diagram")
            st.markdown(f'<a href="data:file/txt;base64,{file_to_base64(uml_file).decode()}" download="{uml_file}">Download PlantUML file</a>', unsafe_allow_html=True)

    if st.button("🤖 Generate class UML Diagram"):
            # Initialize the model
            
            prompt = f"""
            Dây là yêu cầu phần mềm:{text}

            **BƯỚC 1:** Liệt kê toàn bộ class trong biểu đồ class, bỏ qua các class hệ thống.
            **BƯỚC 2:** Liệt kê toàn bộ các phưong thức và thuộc tính của mỗi class.
            **BƯỚC 3:** Xác định tất cả các mối quan hệ và cho biết loại quan hệ, bao gồm:
            - **Association** (Class1 liên kết với Class2)
            - **Aggregation** (Class1 chứa Class2)
            - **Composition** (Class1 chứa Class2 và Class2 không thể tồn tại nếu không có Class1)
            - **Inheritance** (Class1 kế thừa từ Class2)
            **BƯỚC 4:** Xác định quan hệ số lượng giữa các class (1-1, 1-n, n-n).
                0...1: 0 hoặc 1
                n : Bắt buộc có n
                0...* : 0 hoặc nhiều
                1...* : 1 hoặc nhiều
                m...n: có tối thiểu là m và tối đa là n
            Xuất định dạng json schema có cấu trúc:
            {{
                "classes": [
                    {{
                        "name": "ClassName",
                        "attributes": ["Attribute1", "Attribute2", ...],
                        "methods": ["Method1", "Method2", ...]
                    }},
                    ...
                ],
                "relationships": [
                    ["Class1", "Class2", "RelationshipType", "Multiplicity"],
                    ...
                ]
            }}

            """
            message = client.messages.create(
            model="claude-3-7-sonnet-20250219",  # Ensure this is a valid model
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0,
        )
            
            response_text = message.content[0].text
            match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if match:
                json_text = match.group(1)
                data = json.loads(json_text)
            plantuml_code = "@startuml\n"
            plantuml_code += "skinparam classAttributeIconSize 0\n\n"

            # Define classes
            for cls in data['classes']:
                plantuml_code += f"class {cls['name']} {{\n"
                for attr in cls['attributes']:
                    plantuml_code += f"  {attr}\n"
                for method in cls['methods']:
                    plantuml_code += f"  {method}\n"
                plantuml_code += "}\n\n"

            # Define relationships
            for relation in data['relationships']:
                entity1 = relation[0]
                entity2 = relation[1]
                relation_type = relation[2]
                multiplicity = relation[3]
                
                if relation_type == "Inheritance":
                    plantuml_code += f"{entity1} <|-- {entity2}\n"
                elif relation_type == "Association":
                    plantuml_code += f"{entity1} \"{multiplicity.split('...')[0]}\" --> \"{multiplicity.split('...')[1]}\" {entity2}\n"
                elif relation_type == "Aggregation":
                    plantuml_code += f"{entity1} o-- {entity2}\n"
                elif relation_type == "Composition":
                    plantuml_code += f"{entity1} *-- {entity2}\n"

            plantuml_code += "\n@enduml"
            uml_file = "diagram.puml"
            with open(uml_file, "w", encoding="utf-8") as f:
                f.write(plantuml_code)

            # Define the local or online PlantUML server
            plantuml_server = "http://www.plantuml.com/plantuml/png/"

            # Initialize PlantUML processor
            plantuml = PlantUML(url=plantuml_server)

            # Generate the diagram
            plantuml.processes_file(uml_file)

            print("UML diagram generated successfully!")
            # Output the PlantUML code
            st.write("## PlantUML Code")
            st.code(plantuml_code, language="uml")
            # Display the diagram
            st.write("## UML Diagram")
            # after generating the diagram, display the image and download the file
            uml_image_file = "diagram.png"
            plantuml.processes_file(uml_file, outfile=uml_image_file)
            st.image(uml_image_file, caption="Generated UML Diagram")
            # show the download button
            st.write("## Download UML Diagram")
            st.markdown(f'<a href="data:file/txt;base64,{file_to_base64(uml_file).decode()}" download="{uml_file}">Download PlantUML file</a>', unsafe_allow_html=True)


if __name__=="__main__":
    main()

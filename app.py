import streamlit as st
import dotenv
import os
import base64
import anthropic
import openai
import json
import docx
import re
import uuid
from plantuml import PlantUML

dotenv.load_dotenv()

def file_to_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read())

def assign_story_ids(stories):
    """Assign a unique UUID to each user story and return as list of dicts."""
    return [{"id": str(uuid.uuid4()), "text": s} for s in stories]

def classify_user_story(stories, selected_model, anthropic_api_key, openai_api_key):
    prompt = f"""
        {stories}

        Bạn là một chuyên gia phân tích hệ thống phần mềm. Hãy phân loại các câu chuyện người dùng (user stories) thành các loại sau: 
        - Functional
        - Non-Functional

        Trả về JSON với định dạng sau:
        {{
            "Functional": [
                "Câu chuyện người dùng 1",
                "Câu chuyện người dùng 2"
            ],
            "Non-Functional": [
                "Câu chuyện người dùng 3",
                "Câu chuyện người dùng 4"
            ]
        }}
    """
    if selected_model == "Anthropic Claude":
        client = anthropic.Client(api_key=anthropic_api_key)
        message = client.messages.create(
            model=selected_model,
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        response_text = message.content[0].text
    else:
        openai.api_key = openai_api_key
        response = openai.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8096,
            temperature=0.1,
        )
        response_text = response.choices[0].message.content
    # list 
    match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
    data = json.loads(match.group(1)) if match else json.loads(response_text)
    return data

def display_functional_checklist(functional_stories):
    st.write("## Functional User Stories Checklist")
    for story in functional_stories:
        st.checkbox(story["text"], value=False)

def generate_class_plantuml(data):
    plantuml_code = "@startuml\nskinparam classAttributeIconSize 0\n\n"
    for cls in data['classes']:
        plantuml_code += f"class {cls['name']} {{\n"
        for attr in cls['attributes']:
            plantuml_code += f"  {attr}\n"
        for method in cls['methods']:
            plantuml_code += f"  {method}\n"
        plantuml_code += "}\n\n"
    for relation in data['relationships']:
        entity1 = relation[0]
        entity2 = relation[1]
        relation_type = relation[2]
        multiplicity = relation[3]
        if relation_type == "Inheritance":
            plantuml_code += f"{entity1} <|-- {entity2}\n"
        elif relation_type == "Association":
            if '-' in multiplicity:
                multiplicity_start, multiplicity_end = multiplicity.split('-')
                plantuml_code += f"{entity1} \"{multiplicity_start}\" --> \"{multiplicity_end}\" {entity2}\n"
            else:
                plantuml_code += f"{entity1} --> {entity2}\n"
        elif relation_type == "Aggregation":
            plantuml_code += f"{entity1} o-- {entity2}\n"
        elif relation_type == "Composition":
            plantuml_code += f"{entity1} *-- {entity2}\n"
    plantuml_code += "\n@enduml"
    return plantuml_code

def generate_sequence_plantuml(data):
    plantuml_code = "@startuml\n"
    for obj in data['objects']:
        plantuml_code += f"participant {obj}\n"
    for msg in data['messages']:
        sender = msg[0]
        receiver = msg[1]
        message = msg[2]
        plantuml_code += f"{sender} -> {receiver}: {message}\n"
    plantuml_code += "@enduml"
    return plantuml_code

def generate_deployment_plantuml(data):
    plantuml_code = "@startuml\n"
    # Sinh node với alias và service/artifact đúng chuẩn
    for component in data.get('components', []):
        node_name = component['name']
        plantuml_code += f'node "{node_name}" as {node_name} {{\n'
        for service in component.get('services', []):
            plantuml_code += f'  [{service}]\n'
        plantuml_code += '}\n'
    # Sinh kết nối giữa các node
    for relation in data.get('relationships', []):
        if len(relation) == 3:
            plantuml_code += f'{relation[0]} --> {relation[1]} : {relation[2]}\n'
        elif len(relation) == 2:
            plantuml_code += f'{relation[0]} --> {relation[1]}\n'
    plantuml_code += "@enduml"
    return plantuml_code

def generate_agile_process_plantuml():
    """
    Sinh PlantUML cho quy trình Agile/Scrum tổng quát của ứng dụng.
    """
    return '''@startuml
!define RECTANGLE class
RECTANGLE "Product Backlog" as Backlog
RECTANGLE "Sprint Planning" as Planning
RECTANGLE "Sprint Backlog" as SprintBacklog
RECTANGLE "Daily Scrum" as Daily
RECTANGLE "Sprint" as Sprint
RECTANGLE "Increment" as Increment
RECTANGLE "Sprint Review" as Review
RECTANGLE "Sprint Retrospective" as Retro

Backlog --> Planning : "Chọn user story"
Planning --> SprintBacklog : "Lập kế hoạch sprint"
SprintBacklog --> Sprint : "Thực hiện sprint"
Sprint --> Daily : "Họp mỗi ngày"
Sprint --> Increment : "Tạo sản phẩm hoàn chỉnh"
Increment --> Review : "Trình bày sản phẩm"
Review --> Retro : "Phản hồi & cải tiến"
Retro --> Backlog : "Cập nhật backlog"
@enduml'''

def main():
    st.set_page_config(
        page_title="The UML diagram Generator",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    st.html("""<h1 style="text-align: center; color: #6ca395;">🤖 <i>The UML diagram Generator</i> 💬</h1>""")

    with st.sidebar:
        model_option = st.radio("Chọn AI Model", ["Anthropic Claude", "OpenAI GPT"])
        openai_models = {
            "GPT-4o": "gpt-4o-2024-08-06",
            "GPT-4.1": "gpt-4.1-2025-04-14",
            "GPT-4o Mini": "gpt-4o-mini",
            "GPT-3.5 Turbo": "gpt-3.5-turbo"
        }
        anthropic_models = {
            "Claude 3.7 Sonnet": "claude-3-7-sonnet-latest",
            "Claude 3.5 Sonnet": "claude-3-5-sonnet-latest",
            "Claude 3.5 Haiku": "claude-3-5-haiku-latest",
        }
        if model_option == "OpenAI GPT":
            model_name = st.selectbox("Chọn model GPT", list(openai_models.keys()), index=0)
            selected_model = openai_models[model_name]
        else:
            model_name = st.selectbox("Chọn model Claude", list(anthropic_models.keys()), index=0)
            selected_model = anthropic_models[model_name]

        default_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or ""
        default_openai_api_key = os.getenv("OPENAI_API_KEY") or ""
        anthropic_api_key = ""
        openai_api_key = ""
        if model_option == "Anthropic Claude":
            with st.popover("🔐 Anthropic"):
                anthropic_api_key = st.text_input(
                    "Introduce your Anthropic API Key (https://console.anthropic.com/)",
                    value=default_anthropic_api_key, type="password"
                )
        else:
            with st.popover("🔐 OpenAI"):
                openai_api_key = st.text_input(
                    "Introduce your OpenAI API Key (https://platform.openai.com/)",
                    value=default_openai_api_key, type="password"
                )

    st.markdown("### Nhập danh sách User Story (mỗi dòng là một user story)")
    user_story_input = st.text_area("Nhập user story hoặc để trống để import từ file", height=200)
    uploaded_us_file = st.file_uploader("Import user story từ file .docx hoặc .txt", type=["docx", "txt"])

    user_stories = []
    if uploaded_us_file is not None:
        if uploaded_us_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_us_file)
            user_stories = assign_story_ids([para.text.strip() for para in doc.paragraphs if para.text.strip()])
        elif uploaded_us_file.type == "text/plain":
            content = uploaded_us_file.getvalue().decode("utf-8")
            user_stories = assign_story_ids([line.strip() for line in content.splitlines() if line.strip()])
        st.success(f"Đã import {len(user_stories)} user story từ file.")
    elif user_story_input.strip():
        user_stories = assign_story_ids([line.strip() for line in user_story_input.splitlines() if line.strip()])
    text = ""
    # ...sau khi phân loại...
    if user_stories:
        st.write("### Danh sách User Story đã nhập:")
        st.write(user_stories)

        if st.button("Phân loại user story (Function/Non-Function)"):
            with st.spinner("Đang phân loại..."):
                result = classify_user_story([s["text"] for s in user_stories], selected_model, anthropic_api_key, openai_api_key)
            st.session_state["functional_stories"] = assign_story_ids(result.get("Functional", []))
            st.session_state["non_functional_stories"] = assign_story_ids(result.get("Non-Functional", []))
            st.write("### Functional User Stories (JSON)")
            st.json(st.session_state["functional_stories"])
            st.write("### Non-Functional User Stories (JSON)")
            st.json(st.session_state["non_functional_stories"])

    # Đảm bảo functional_stories và non_functional_stories luôn tồn tại trong session_state
    if "functional_stories" not in st.session_state:
        st.session_state["functional_stories"] = []
    if "non_functional_stories" not in st.session_state:
        st.session_state["non_functional_stories"] = []

    # Tạo tab cho chức năng và phi chức năng
    tab1, tab2 = st.tabs(["Chức năng (Functional)", "Phi chức năng (Non-Functional)"])
    # --- Tab 1: Functional ---
    with tab1:
        functional_stories = st.session_state.get("functional_stories", [])
        st.write("### Functional User Stories")
        st.json(functional_stories)
        # --- Thêm mới user story ---
        with st.expander("➕ Thêm user story mới (Functional)"):
            new_story_text = st.text_area("Nhập nội dung user story mới", key="new_func_story")
            if st.button("Thêm user story (Functional)", key="add_func_story"):
                if new_story_text.strip():
                    new_story = {"id": str(uuid.uuid4()), "text": new_story_text.strip()}
                    st.session_state["functional_stories"].append(new_story)
                    st.success("Đã thêm user story mới!")
                    st.rerun()
        # --- Sửa/Xóa user story ---
        for story in functional_stories:
            col1, col2, col3 = st.columns([7,1,1])
            with col1:
                st.write(story["text"])
            with col2:
                if st.button("✏️", key=f"edit_func_{story['id']}"):
                    st.session_state["editing_func_story"] = story["id"]
            with col3:
                if st.button("🗑️", key=f"delete_func_{story['id']}"):
                    st.session_state["functional_stories"] = [s for s in functional_stories if s["id"] != story["id"]]
                    st.success("Đã xóa user story!")
                    st.rerun()
            # Hiển thị form sửa nếu đang chọn story này
            if st.session_state.get("editing_func_story") == story["id"]:
                new_text = st.text_area("Sửa nội dung user story", value=story["text"], key=f"edit_text_func_{story['id']}")
                if st.button("Lưu", key=f"save_func_{story['id']}"):
                    for s in st.session_state["functional_stories"]:
                        if s["id"] == story["id"]:
                            s["text"] = new_text.strip()
                    st.session_state["editing_func_story"] = None
                    st.success("Đã cập nhật user story!")
                    st.rerun()
                if st.button("Hủy", key=f"cancel_func_{story['id']}"):
                    st.session_state["editing_func_story"] = None
                    st.rerun()
        # Tạo Kanban và Sprint
        tab_name = "Functional"
        stories = functional_stories
        status_options = ["To Do", "In Progress", "Done"]
        us_key = f"us_status_{tab_name}"
        if us_key not in st.session_state:
            st.session_state[us_key] = {story["id"]: "To Do" for story in stories}
        for story in stories:
            if story["id"] not in st.session_state[us_key]:
                st.session_state[us_key][story["id"]] = "To Do"
        st.write("## Kanban User Story Board")
        cols = st.columns(3)
        for idx, status in enumerate(status_options):
            with cols[idx]:
                st.markdown(f"#### {status}")
                for story in [s for s in stories if st.session_state[us_key].get(s["id"]) == status]:
                    st.write(story["text"])
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if status != "To Do" and st.button("◀️", key=f"move_left_{story['id']}"):
                            prev_status = status_options[status_options.index(status) - 1]
                            st.session_state[us_key][story["id"]] = prev_status
                            st.rerun()
                    with col2:
                        if status != "Done" and st.button("▶️", key=f"move_right_{story['id']}"):
                            next_status = status_options[status_options.index(status) + 1]
                            st.session_state[us_key][story["id"]] = next_status
                            st.rerun()
        st.write("## Quản lý Sprint")
        sprint_key = f"sprints_{tab_name}"
        if sprint_key not in st.session_state:
            st.session_state[sprint_key] = []
        new_sprint = st.text_input(f"Tên Sprint mới ({tab_name})", key=f"new_sprint_name_{tab_name}")
        if st.button(f"Tạo Sprint mới ({tab_name})"):
            if new_sprint and new_sprint not in [s["name"] for s in st.session_state[sprint_key]]:
                st.session_state[sprint_key].append({"name": new_sprint, "stories": []})
        for sprint in st.session_state[sprint_key]:
            st.markdown(f"### {sprint['name']}")
            selected_stories = st.multiselect(
                f"Chọn user story cho {sprint['name']}",
                options=[s["id"] for s in stories],
                format_func=lambda sid: next((s["text"] for s in stories if s["id"] == sid), sid),
                default=sprint["stories"],
                key=f"{sprint_key}_{sprint['name']}_stories"
            )
            sprint["stories"] = selected_stories
        if st.button("🤖 Generate UML Diagram (Functional)"):
            prompt_stories = [s["text"] for s in stories]
            prompt = f"""
                json{prompt_stories}

                Bạn là chuyên gia phân tích hệ thống phần mềm. Hãy thực hiện các bước sau và chỉ trả về một đối tượng JSON duy nhất với 2 trường: \"class\", \"sequence\". 
                **YÊU CẦU BẮT BUỘC:** Mỗi trường trong JSON phải luôn có đầy đủ các trường con như mô tả dưới đây, kể cả khi không có dữ liệu thì trả về mảng rỗng.

                **PHẦN 1: Class Diagram**
                - Liệt kê tất cả các class, thuộc tính, phương thức.
                - Liệt kê tất cả các mối quan hệ giữa các class (Association, Aggregation, Composition, Inheritance).
                - Mỗi quan hệ phải có trường \"RelationshipType\" (ví dụ: Association, Aggregation, ...), và \"Multiplicity\" (ví dụ: 1-1, 1-n, n-n, hoặc rỗng nếu không xác định).
                - Nếu không có mối quan hệ nào, trả về \"relationships\": [].
                Trả về JSON:
                \"class\": {{
                    \"classes\": [
                        {{
                            \"name\": \"ClassName\",
                            \"attributes\": [...],
                            \"methods\": [...]
                        }},
                        ...
                    ],
                    \"relationships\": [
                        [\"Class1\", \"Class2\", \"RelationshipType\", \"Multiplicity\"],
                        ...
                    ]
                }}

                **PHẦN 2: Sequence Diagram**
                - Liệt kê các đối tượng (objects/lifelines) tham gia vào kịch bản chính.
                - Liệt kê các thông điệp (messages) trao đổi giữa các đối tượng theo thứ tự thời gian.
                - Nếu không có đối tượng hoặc thông điệp nào, trả về mảng rỗng.
                Trả về JSON:
                \"sequence\": {{
                    \"objects\": [...],
                    \"messages\": [[\"Sender\", \"Receiver\", \"Message\"], ...]
                }}

                **LƯU Ý QUAN TRỌNG:**  
                - JSON trả về phải luôn có đầy đủ các trường như trên, kể cả khi không có dữ liệu thì trả về mảng rỗng.
                - Không được bỏ sót bất kỳ trường nào.
                - Không trả về giải thích, chỉ trả về đúng một đối tượng JSON duy nhất theo cấu trúc trên.
                """
            if model_option == "Anthropic Claude":
                client = anthropic.Client(api_key=anthropic_api_key)
                message = client.messages.create(
                    model=selected_model,
                    max_tokens=8096,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=1,
                )
                response_text = message.content[0].text
            else:
                openai.api_key = openai_api_key
                response = openai.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=11000,
                    temperature=0.1,
                )
                response_text = response.choices[0].message.content
            match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            data = json.loads(match.group(1)) if match else json.loads(response_text)
            class_data = data["class"]
            sequence_data = data["sequence"]
            st.write("### Class Diagram Data (JSON)")
            st.json(class_data)
            st.write("### Sequence Diagram Data (JSON)")
            st.json(sequence_data)
            plantuml_class = generate_class_plantuml(class_data)
            plantuml_sequence = generate_sequence_plantuml(sequence_data)
            plantuml_server = "http://www.plantuml.com/plantuml/png/"
            plantuml = PlantUML(url=plantuml_server)
            st.write("## Class Diagram")
            st.code(plantuml_class, language="uml")
            uml_file_cl = "diagram_class.puml"
            with open(uml_file_cl, "w", encoding="utf-8") as f:
                f.write(plantuml_class)
            plantuml.processes_file(uml_file_cl)
            uml_image_file_cl = "diagram_class.png"
            plantuml.processes_file(uml_file_cl, outfile=uml_image_file_cl)
            st.image(uml_image_file_cl, caption="Generated Class Diagram")
            st.write("## Sequence Diagram")
            st.code(plantuml_sequence, language="uml")
            uml_file_sq = "diagram_sequence.puml"
            with open(uml_file_sq, "w", encoding="utf-8") as f:
                f.write(plantuml_sequence)
            plantuml.processes_file(uml_file_sq)
            uml_image_file_sq = "diagram_sequence.png"
            plantuml.processes_file(uml_file_sq, outfile=uml_image_file_sq)
            st.image(uml_image_file_sq, caption="Generated Sequence Diagram")
            st.write("## Download PlantUML files")
            st.markdown(f'<a href="data:file/txt;base64,{file_to_base64(uml_file_cl).decode()}" download="{uml_file_cl}">Download Class PlantUML</a>', unsafe_allow_html=True)
            st.markdown(f'<a href="data:file/txt;base64,{file_to_base64(uml_file_sq).decode()}" download="{uml_file_sq}">Download Sequence PlantUML</a>', unsafe_allow_html=True)
            st.write("## Download Images")
            st.markdown(f'<a href="data:image/png;base64,{file_to_base64(uml_image_file_cl).decode()}" download="{uml_image_file_cl}">Download Class Image</a>', unsafe_allow_html=True)
            st.markdown(f'<a href="data:image/png;base64,{file_to_base64(uml_image_file_sq).decode()}" download="{uml_image_file_sq}">Download Sequence Image</a>', unsafe_allow_html=True)

    # --- Tab 2: Non-Functional ---
    with tab2:
        non_functional_stories = st.session_state.get("non_functional_stories", [])
        st.write("### Non-Functional User Stories")
        st.json(non_functional_stories)
        # --- Thêm mới user story ---
        with st.expander("➕ Thêm user story mới (Non-Functional)"):
            new_story_text_nf = st.text_area("Nhập nội dung user story mới", key="new_nonfunc_story")
            if st.button("Thêm user story (Non-Functional)", key="add_nonfunc_story"):
                if new_story_text_nf.strip():
                    new_story = {"id": str(uuid.uuid4()), "text": new_story_text_nf.strip()}
                    st.session_state["non_functional_stories"].append(new_story)
                    st.success("Đã thêm user story mới!")
                    st.rerun()
        # --- Sửa/Xóa user story ---
        for story in non_functional_stories:
            col1, col2, col3 = st.columns([7,1,1])
            with col1:
                st.write(story["text"])
            with col2:
                if st.button("✏️", key=f"edit_nonfunc_{story['id']}"):
                    st.session_state["editing_nonfunc_story"] = story["id"]
            with col3:
                if st.button("🗑️", key=f"delete_nonfunc_{story['id']}"):
                    st.session_state["non_functional_stories"] = [s for s in non_functional_stories if s["id"] != story["id"]]
                    st.success("Đã xóa user story!")
                    st.rerun()
            # Hiển thị form sửa nếu đang chọn story này
            if st.session_state.get("editing_nonfunc_story") == story["id"]:
                new_text = st.text_area("Sửa nội dung user story", value=story["text"], key=f"edit_text_nonfunc_{story['id']}")
                if st.button("Lưu", key=f"save_nonfunc_{story['id']}"):
                    for s in st.session_state["non_functional_stories"]:
                        if s["id"] == story["id"]:
                            s["text"] = new_text.strip()
                    st.session_state["editing_nonfunc_story"] = None
                    st.success("Đã cập nhật user story!")
                    st.rerun()
                if st.button("Hủy", key=f"cancel_nonfunc_{story['id']}"):
                    st.session_state["editing_nonfunc_story"] = None
                    st.rerun()
        # Tạo Kanban và Sprint
        tab_name = "NonFunctional"
        stories = non_functional_stories
        status_options = ["To Do", "In Progress", "Done"]
        us_key = f"us_status_{tab_name}"
        if us_key not in st.session_state:
            st.session_state[us_key] = {story["id"]: "To Do" for story in stories}
        for story in stories:
            if story["id"] not in st.session_state[us_key]:
                st.session_state[us_key][story["id"]] = "To Do"
        st.write("## Kanban User Story Board")
        cols = st.columns(3)
        for idx, status in enumerate(status_options):
            with cols[idx]:
                st.markdown(f"#### {status}")
                for story in [s for s in stories if st.session_state[us_key].get(s["id"]) == status]:
                    st.write(story["text"])
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if status != "To Do" and st.button("◀️", key=f"move_left_{story['id']}"):
                            prev_status = status_options[status_options.index(status) - 1]
                            st.session_state[us_key][story["id"]] = prev_status
                            st.rerun()
                    with col2:
                        if status != "Done" and st.button("▶️", key=f"move_right_{story['id']}"):
                            next_status = status_options[status_options.index(status) + 1]
                            st.session_state[us_key][story["id"]] = next_status
                            st.rerun()
        st.write("## Quản lý Sprint")
        sprint_key = f"sprints_{tab_name}"
        if sprint_key not in st.session_state:
            st.session_state[sprint_key] = []
        new_sprint = st.text_input(f"Tên Sprint mới ({tab_name})", key=f"new_sprint_name_{tab_name}")
        if st.button(f"Tạo Sprint mới ({tab_name})"):
            if new_sprint and new_sprint not in [s["name"] for s in st.session_state[sprint_key]]:
                st.session_state[sprint_key].append({"name": new_sprint, "stories": []})
        for sprint in st.session_state[sprint_key]:
            st.markdown(f"### {sprint['name']}")
            selected_stories = st.multiselect(
                f"Chọn user story cho {sprint['name']}",
                options=[s["id"] for s in stories],
                format_func=lambda sid: next((s["text"] for s in stories if s["id"] == sid), sid),
                default=sprint["stories"],
                key=f"{sprint_key}_{sprint['name']}_stories"
            )
            sprint["stories"] = selected_stories
        if st.button("🤖 Generate Deployment Diagram (Non-Functional)"):
            prompt_stories = [s["text"] for s in stories]
            deployment_prompt = f"""
            {prompt_stories}\n\nBạn là chuyên gia phân tích hệ thống phần mềm. Hãy phân tích các yêu cầu phi chức năng trên và trả về một đối tượng JSON duy nhất mô tả deployment diagram với các trường sau:\n\n{{\n  \"components\": [{{\"name\": \"NodeName\", \"services\": [\"Service1\", ...]}}, ...],\n  \"relationships\": [[\"Node1\", \"Node2\", \"Kết nối hoặc giao thức\"], ...]\n}}\n\n- Luôn trả về đầy đủ các trường như trên, kể cả khi không có dữ liệu thì trả về mảng rỗng.\n- Không giải thích, chỉ trả về đúng một đối tượng JSON duy nhất.\n"""
            if model_option == "Anthropic Claude":
                client = anthropic.Client(api_key=anthropic_api_key)
                message = client.messages.create(
                    model=selected_model,
                    max_tokens=8096,
                    messages=[{"role": "user", "content": deployment_prompt}],
                    temperature=1,
                )
                deployment_response_text = message.content[0].text
            else:
                openai.api_key = openai_api_key
                deployment_response = openai.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": deployment_prompt}],
                    max_tokens=4096,
                    temperature=0.1,
                )
                deployment_response_text = deployment_response.choices[0].message.content
            match_dep = re.search(r'```json\n(.*?)\n```', deployment_response_text, re.DOTALL)
            deployment_data = json.loads(match_dep.group(1)) if match_dep else json.loads(deployment_response_text)
            st.write("### Deployment Diagram Data (JSON)")
            st.json(deployment_data)
            plantuml_deployment = generate_deployment_plantuml(deployment_data)
            plantuml_server = "http://www.plantuml.com/plantuml/png/"
            plantuml = PlantUML(url=plantuml_server)
            st.write("## Deployment Diagram")
            st.code(plantuml_deployment, language="uml")
            uml_file_dp = "diagram_deployment.puml"
            with open(uml_file_dp, "w", encoding="utf-8") as f:
                f.write(plantuml_deployment)
            plantuml.processes_file(uml_file_dp)
            uml_image_file_dp = "diagram_deployment.png"
            plantuml.processes_file(uml_file_dp, outfile=uml_image_file_dp)
            st.image(uml_image_file_dp, caption="Generated Deployment Diagram")
            st.write("## Download PlantUML file")
            st.markdown(f'<a href="data:file/txt;base64,{file_to_base64(uml_file_dp).decode()}" download="{uml_file_dp}">Download Deployment PlantUML</a>', unsafe_allow_html=True)
            st.write("## Download Image")
            st.markdown(f'<a href="data:image/png;base64,{file_to_base64(uml_image_file_dp).decode()}" download="{uml_image_file_dp}">Download Deployment Image</a>', unsafe_allow_html=True)
        if st.button("🤖 Show Agile Process Diagram"):
            agile_plantuml = generate_agile_process_plantuml()
            plantuml_server = "http://www.plantuml.com/plantuml/png/"
            plantuml = PlantUML(url=plantuml_server)
            st.write("## Agile Process Diagram (Scrum)")
            st.code(agile_plantuml, language="uml")
            uml_file_agile = "diagram_agile.puml"
            with open(uml_file_agile, "w", encoding="utf-8") as f:
                f.write(agile_plantuml)
            plantuml.processes_file(uml_file_agile)
            uml_image_file_agile = "diagram_agile.png"
            plantuml.processes_file(uml_file_agile, outfile=uml_image_file_agile)
            st.image(uml_image_file_agile, caption="Agile/Scrum Process")
            st.write("## Download PlantUML file")
            st.markdown(f'<a href="data:file/txt;base64,{file_to_base64(uml_file_agile).decode()}" download="{uml_file_agile}">Download Agile PlantUML</a>', unsafe_allow_html=True)
            st.write("## Download Image")
            st.markdown(f'<a href="data:image/png;base64,{file_to_base64(uml_image_file_agile).decode()}" download="{uml_image_file_agile}">Download Agile Image</a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

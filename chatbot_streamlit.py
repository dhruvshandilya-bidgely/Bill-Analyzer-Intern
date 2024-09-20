import streamlit as st
import json
from PIL import Image
from tools.utils import replace_braces, calculate_difference, fetch_itemization_data, fetch_location, fetch_vacation_data
from tools.chat import display_billing_cycles, plot_itemization_comparison
from dataset import first_prompt, second_prompt
from tools.preprocessing import preprocess
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory


user_avatar_url = 'https://m.media-amazon.com/images/I/31x+q3aNVKL._AC_UF1000,1000_QL80_.jpg'
assistant_avatar_user = 'https://cdn.theorg.com/8ad2e869-5595-4b23-bbff-6a7a8d511d15_thumb.jpg'
favicon_url = 'https://cdn.theorg.com/8ad2e869-5595-4b23-bbff-6a7a8d511d15_thumb.jpg'

# Set the page configuration with the custom icon URL
st.set_page_config(page_title="Bill Analyzer", page_icon=favicon_url, layout="centered", initial_sidebar_state="auto", menu_items=None)
html_content = """
<div style='width: 100%;'>
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div style='display: flex; align-items: center;'>
            <img src='https://cdn.theorg.com/8ad2e869-5595-4b23-bbff-6a7a8d511d15_thumb.jpg' style='width: 60px; height: 50px; margin-right: 180px;'>
            <h1 style='font-size: 2.5em;'>Bill Analyzer</h1>
        </div>
        <div>
            <p style='font-size: 1.1em; margin-top: 28px; text-align: right;'>John Wick</p>
            <p style='font-size: 0.95em; margin-top: -18px; text-align: right;'>UserID: 12345</p>
        </div>
    </div>
</div>
"""

st.markdown(html_content, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Load environment variables
load_dotenv()
key = os.getenv("OPENAI_API_KEY")


def initialize_session_state():
    if "file_uploader_disabled" not in st.session_state:
        st.session_state["file_uploader_disabled"] = False
    if "first_cycle_disabled" not in st.session_state:
        st.session_state["first_cycle_disabled"] = False
    if "second_cycle_disabled" not in st.session_state:
        st.session_state["second_cycle_disabled"] = False
    if "plot_choice_disabled" not in st.session_state:
        st.session_state["plot_choice_disabled"] = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    if "store" not in st.session_state:
        st.session_state['store'] = {}


def reset_session():
    st.session_state.clear()
    initialize_session_state()


initialize_session_state()

def disable_file_uploader():
    st.session_state["file_uploader_disabled"] = True

def load_json_data(uuid=None):
    """
    Load JSON data either from files or using a UUID to fetch the user data.
    Returns the processed JSON data.
    """
    if uuid:
        try:
            itemization_data = fetch_itemization_data(uuid)
            metadata = fetch_location(uuid)
            vacation_data = fetch_vacation_data(uuid)
            processed_data = preprocess(itemization_data, metadata, vacation_data, True)
            print("Anand",str(processed_data))
            return processed_data
        except Exception as e:
            st.error(f"Error in preprocessing data: {e}")
    else:
        # Create three file uploaders for 'itemization_json', 'metadata_json', and 'vacationdata_json'
        itemization_file = st.file_uploader(
            "Please upload the Itemization JSON file.",
            type="json", 
            disabled=st.session_state.get('file_uploader_disabled', False),
            key="itemization_uploader"
        )

        metadata_file = st.file_uploader(
            "Please upload the Metadata JSON file.",
            type="json", 
            disabled=st.session_state.get('file_uploader_disabled', False),
            key="metadata_uploader"
        )

        vacationdata_file = st.file_uploader(
            "Please upload the Vacation Data JSON file.",
            type="json", 
            disabled=st.session_state.get('file_uploader_disabled', False),
            key="vacationdata_uploader"
        )

        # Process the uploaded files
        if itemization_file and metadata_file and vacationdata_file:
            try:
                itemization_data = json.load(itemization_file)
                metadata = json.load(metadata_file)
                vacationdata = json.load(vacationdata_file)
                
                processed_data = preprocess(itemization_data, metadata, vacationdata, True)
                disable_file_uploader()  # Disable the uploader after successful upload and processing
                
                st.success("Files successfully processed.")
                return processed_data

            except Exception as e:
                st.error(f"Invalid JSON file or content: {e}")
        else:
            st.info("Please upload all three JSON files.")

    return None

def disable_first_cycle():
    st.session_state["first_cycle_disabled"] = True

def disable_second_cycle():
    st.session_state["second_cycle_disabled"] = True

def get_valid_cycle_choice(length, prompt_text, json_file, exclude_index=None):
    """
    Prompt for a valid cycle index choice using Streamlit.
    Returns the valid index chosen by the user.
    """
    available_indices = [i for i in range(length) if i != exclude_index]

    if not available_indices:
        st.error(f"No valid {prompt_text} cycles available for selection.")
        return None

    # Prepare options with dates
    options = []
    for i in available_indices:
        start_date = json_file[i]["IntervalStartDate"]
        end_date = json_file[i]["IntervalEndDate"]
        options.append(f"Cycle Id - {i + 1} : {start_date} - {end_date}")

    if not options:
        st.error(f"No valid {prompt_text} cycles available for selection.")
        return None

    disabled_state_key = f"{prompt_text}_cycle_disabled"
    disable_function = disable_first_cycle if prompt_text == "first" else disable_second_cycle

    choice = st.selectbox(
        f"Select the {prompt_text} cycle to compare:", 
        [''] + options, 
        key=f"{prompt_text}_cycle",
        disabled=st.session_state.get(disabled_state_key, False),
        on_change=disable_function
    )

    # Extract the index from the choice
    if st.session_state.get(f"{prompt_text}_cycle", '') == '':
        if st.session_state.get(f"{prompt_text}_cycle_warning_shown", False):
            st.session_state[f"{prompt_text}_cycle_warning_shown"] = True
            st.warning(f"Please select a {prompt_text} cycle.")
        return None

    st.session_state[f"{prompt_text}_cycle_warning_shown"] = False

    # Get the selected index from the choice
    choice_index = next((i for i, opt in enumerate(options) if opt == choice), None)
    return available_indices[choice_index] if choice_index is not None else None


def disable_plot_choice():
    st.session_state["plot_choice_disabled"] = True

def prompt_for_plot():
    """
    Prompt the user if they want to see the itemization comparison plot using Streamlit.
    Returns 'yes' or 'no' based on user input.
    """
    show_plot = st.selectbox(
        "Do you want to see a comparison plot?", 
        ['', 'Yes', 'No'], 
        key='plot_choice', 
        disabled=st.session_state.plot_choice_disabled,
        on_change=disable_plot_choice
    )

    if show_plot == '':
        return None

    return show_plot.lower()

def select_billing_cycles(json_file):
    """
    Allow the user to select two billing cycles for comparison.
    Returns the selected cycles, indices, and whether to show the plot.
    """
    st.markdown("<h4 style='text-align: left;'>Choose two billing cycles for comparison.</h1>", unsafe_allow_html=True)

    length = len(json_file)
    if length == 0:
        st.error("No billing cycles available in the provided JSON file.")
        return None, None, None, None, None

    idx1 = get_valid_cycle_choice(length, "first", json_file)
    if idx1 is None:
        return None, None, None, None, None

    idx2 = get_valid_cycle_choice(length, "second", json_file, exclude_index=idx1)
    if idx2 is None:
        return None, None, None, None, None

    cycle1 = replace_braces(json_file[idx1])
    cycle2 = replace_braces(json_file[idx2])

    # Check if itemization details are available
    itemization1 = json_file[idx1].get('itemizationDetailsList', 'unavailable')
    itemization2 = json_file[idx2].get('itemizationDetailsList', 'unavailable')

    if itemization1 == "unavailable" or itemization2 == "unavailable":
        if itemization1 == "unavailable":
            st.warning(f"Itemization details are not available for the first cycle.")
        if itemization2 == "unavailable":
            st.warning(f"Itemization details are not available for the second cycle.")

        return cycle1, cycle2, idx1, idx2, 'no'

    show_plot = prompt_for_plot()

    return cycle1, cycle2, idx1, idx2, show_plot


def run_bill_analyzer(flag=False):
    session_id = "abc2"
    store = {}

    if flag:
        uuid = st.text_input("Enter the UUID to fetch the data:")
        if uuid:
            processed_data = load_json_data(uuid)
            print('uuid : ',uuid)
            print("processed_data : ",processed_data)
        else:
            st.info("Please enter a UUID to fetch data.")
            return
    else:
        processed_data = load_json_data()

    if processed_data is None:
        return

    json_file = processed_data.get("usageChartDataList", [])
    json_file = json_file[-15:-2] #Fetching last 13 BCs excluding the 2 recent ones
    loc = processed_data["location"]

    st.markdown("<h3 style='text-align: center;'>Billing Cycles Summary</h1>", unsafe_allow_html=True)
    table = display_billing_cycles(json_file)
    st.text(table)

    cycle1, cycle2, idx1, idx2, show_plot = select_billing_cycles(json_file)
    if not cycle1 or not cycle2 or show_plot is None:
        return

    if show_plot == 'yes':
        image_buffer = plot_itemization_comparison(json_file[idx1], json_file[idx2])
        image = Image.open(image_buffer)
        st.image(image, caption='\n\n', use_column_width=True)

    diff = replace_braces(calculate_difference(json_file[idx1], json_file[idx2]))
    st.write('\nBill Analyzer is running! Please Wait...\n')

    st.session_state['session_id'] = session_id
    st.session_state['cycle1'] = cycle1
    st.session_state['cycle2'] = cycle2
    st.session_state['diff'] = diff
    if 'store' not in st.session_state:
        st.session_state['store'] = {}
    store = st.session_state['store']

    def get_session_history(session_id: str):
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    llm = ChatOpenAI(model="gpt-4o", openai_api_key=key, temperature=1.0)  #Using gpt-4o as a base model
    first_chain = first_prompt | llm
    second_chain = second_prompt | llm

    first_with_history = RunnableWithMessageHistory(first_chain, get_session_history)
    second_with_history = RunnableWithMessageHistory(second_chain, get_session_history)

    def chatbot_response(session_id: str, user_input: str):
        history = get_session_history(session_id)
        if not history.messages:
            response = first_with_history.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
        else:
            response = second_with_history.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}}
            )
        return response.content

    def interactive_chatbot(session_id: str, cycle1, cycle2, diff):
        if "messages" not in st.session_state:
            st.session_state.messages = []

        initial_response = None

        if not st.session_state.messages:
            first_query = f"Compare the following billing cycles: one= {cycle1} and two= {cycle2}. The difference in values between the billing cycles one and two is difference={diff}. This can help you understand the variations between the billing cycles. This user belongs to the location:{loc}"
            initial_response = chatbot_response(session_id, first_query)
            st.session_state.messages.append({"role": "assistant", "content": initial_response})

        displayed_initial_message = False
        for message in st.session_state.messages:
            if message["role"] == "assistant":
                avatar_url = assistant_avatar_user
            else:
                avatar_url = None

            with st.chat_message(message["role"], avatar=avatar_url):
                st.markdown(message["content"])

            if initial_response is not None and message["content"] == initial_response:
                displayed_initial_message = True

        if not displayed_initial_message and initial_response is not None:
            with st.chat_message("assistant", avatar=assistant_avatar_user):
                st.markdown(initial_response.replace("$", r"\$"))

        if prompt := st.chat_input("You:"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt.replace("$", "\$"))

            response = chatbot_response(session_id, prompt)
            with st.chat_message("assistant", avatar=assistant_avatar_user):
                st.markdown(response.replace("$", r"\$"))
            st.session_state.messages.append({"role": "assistant", "content": response})

    interactive_chatbot(session_id, cycle1, cycle2, diff)

if __name__ == "__main__":

    st.write('\n\n\n\n\n')
    run_bill_analyzer(flag=True)  # Pass flag=True to prompt for UUID, set to False for file upload
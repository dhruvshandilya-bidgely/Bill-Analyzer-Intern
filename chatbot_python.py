import json
from PIL import Image
import os
from tools.utils import replace_braces, calculate_difference, fetch_vacation_data, fetch_itemization_data, fetch_location
from tools.chat import display_billing_cycles, plot_itemization_comparison
from dataset import first_prompt, second_prompt
from tools.preprocessing import preprocess
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

# Load environment variables
load_dotenv()
key = os.getenv("OPENAI_API_KEY")

def load_json_data(uuid=None):
    """
    Load JSON data either from files or using a UUID to fetch the user data.

    This function either takes in a UUID if any is given. If no UUID is given, 
    then it takes files paths as inputs directly from the user.

    Args:
        uuid (str) : The uuid of the user we are interested in.

    Returns:
        processed_data (dict) : The processed JSON data.

    Raises:
        Exception: Raised when JSON file could not be loaded.
    """
    if uuid:
        try:
            itemization_data = fetch_itemization_data(uuid)
            metadata = fetch_location(uuid)
            vacation_data = fetch_vacation_data(uuid)
            processed_data = preprocess(itemization_data, metadata, vacation_data, True)
            return processed_data
        except Exception as e:
            print(f"Error in preprocessing data: {e}")
    else:
        itemization_file_path = input("Please enter the path to the Itemization JSON file: ")
        metadata_file_path = input("Please enter the path to the Metadata JSON file: ")
        vacationdata_file_path = input("Please enter the path to the Vacation Data JSON file: ")

        try:
            with open(itemization_file_path, 'r') as itemization_file:
                itemization_data = json.load(itemization_file)
            with open(metadata_file_path, 'r') as metadata_file:
                metadata = json.load(metadata_file)
            with open(vacationdata_file_path, 'r') as vacationdata_file:
                vacationdata = json.load(vacationdata_file)

            processed_data = preprocess(itemization_data, metadata, vacationdata, True)
            print("Files successfully processed.")
            return processed_data

        except Exception as e:
            print(f"Invalid JSON file or content: {e}")

    return None

def get_valid_cycle_choice(length, question_text):
    """
    Asks user to enter a valid cycle index choice using terminal input. 
    Checks for the validity of the index chosen by the user and returns it if it is valid.

    Args:
        length (int) : The length of the cycle.
        question_text (str) : Could be "first" or "second" or so on just to format the input taking message.

    Returns:
        choice (int) : The cycle index entered by the user if it is valid.

    Raises:
        ValueError: Raised when the cycle index entered by user lies out of range of cycle bounds.
    """
    while True:
        try:
            choice = int(input(f"Enter the index for the {question_text} cycle: ").strip()) - 1
            if 0 <= choice < length:
                return choice
            else:
                print(f"Invalid choice. Please enter a number between 1 and {length}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def prompt_for_plot():
    """
    Asks the user if they want to see the itemization comparison plot using terminal input. 

    Args:
        None
    
    Returns:
        show_plot (str) : Can be 'yes' or 'no' depending on whether the user wants to see the itemization comparison plot.
    """
    while True:
        show_plot = input("Do you want to see a comparison plot? (yes/no): ").strip().lower()
        if show_plot in ['yes', 'no']:
            return show_plot
        else:
            print("Invalid choice. Please enter 'yes' or 'no'.")

def select_billing_cycles(json_file):
    """
    Allow the user to select two billing cycles for comparison. 

    First checks whether the JSON file is empty or not.
    Then inputs both the valid indices from the user and makes sure not the same value.
    If itemization is unavailable the no plot can be generated.
    If itemization is available then user is asked whether plot generation is wanted or not.

    Args:
        json_file (dict): JSON file loaded in the form of a dict.
    
    Returns:
        cycle1 (---------):  -------------------------------------------------
        cycle2 (---------):  -------------------------------------------------
        idx1 (int) : The valid cycle index from user used to select cycle1.
        idx2 (int) : The valid cycle index from user used to select cycle2.
        show_plot (str) : Can be either "yes" or "no", indicates whether plot should be generated or not.
    """
    print("Choose two billing cycles for comparison.")
    length = len(json_file)
    if length == 0:
        print("No billing cycles available in the provided JSON file.")
        return None, None, None, None, None

    idx1 = get_valid_cycle_choice(length, "first")
    idx2 = get_valid_cycle_choice(length, "second")
    while idx2 == idx1:
        print("You've selected the same cycle twice. Please select a different cycle.")
        idx2 = get_valid_cycle_choice(length, "second")

    # single brace replaced by double brace, so that these cycles can be fed to the LLM.
    cycle1 = replace_braces(json_file[idx1])
    cycle2 = replace_braces(json_file[idx2])

    # Check if itemization details are available
    itemization1 = json_file[idx1].get('itemizationDetailsList', 'unavailable')
    itemization2 = json_file[idx2].get('itemizationDetailsList', 'unavailable')

    if itemization1 == "unavailable" or itemization2 == "unavailable":
        if itemization1 == "unavailable":
            print("Itemization details are not available for the first cycle.")
        if itemization2 == "unavailable":
            print("Itemization details are not available for the second cycle.")

        return cycle1, cycle2, idx1, idx2, 'no'

    show_plot = prompt_for_plot()
    return cycle1, cycle2, idx1, idx2, show_plot

def run_bill_analyzer(flag=False):
    session_id = "abc2"
    store = {}

    if flag:
        uuid = input("Enter the UUID to fetch the data: ")
        if uuid:
            processed_data = load_json_data(uuid)
        else:
            print("Please enter a UUID to fetch data.")
            return
    else:
        processed_data = load_json_data()

    if processed_data is None:
        return

    json_file = processed_data.get("usageChartDataList", [])
    json_file = json_file[-15:-2]
    loc = processed_data["location"]

    print("Billing Cycles Summary")
    table = display_billing_cycles(json_file)
    print(table)

    cycle1, cycle2, idx1, idx2, show_plot = select_billing_cycles(json_file)
    if not cycle1 or not cycle2 or show_plot is None:
        return

    if show_plot == 'yes':
        image_buffer = plot_itemization_comparison(json_file[idx1], json_file[idx2])
        image = Image.open(image_buffer)
        image.show()

    diff = replace_braces(calculate_difference(json_file[idx1], json_file[idx2]))
    print('\nBill Analyzer is running! Please Wait...\n')

    store = {}

    def get_session_history(session_id: str):
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    llm = ChatOpenAI(model="gpt-4o", openai_api_key=key, temperature=1.0)
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
        messages = []

        initial_response = None

        if not messages:
            first_query = f"Compare the following billing cycles: one= {cycle1} and two= {cycle2}. The difference in values between the billing cycles one and two is difference={diff}. This can help you understand the variations between the billing cycles. This user belongs to the location:{loc}"
            initial_response = chatbot_response(session_id, first_query)
            messages.append({"role": "assistant", "content": initial_response})

        print("Assistant:", initial_response.replace("$", r"\$"))

        while True:
            user_input = input("You: ")
            messages.append({"role": "user", "content": user_input})
            
            response = chatbot_response(session_id, user_input)
            print("Assistant:", response.replace("$", r"\$"))
            messages.append({"role": "assistant", "content": response})

    interactive_chatbot(session_id, cycle1, cycle2, diff)

if __name__ == "__main__":
    run_bill_analyzer(flag=False)  # Pass flag=True to prompt for UUID, set to False for file path input
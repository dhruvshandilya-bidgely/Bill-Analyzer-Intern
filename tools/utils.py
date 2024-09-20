import holidays
from datetime import datetime
import requests 
import json

access_token = "2509467f-40f1-45a7-8c4f-548bb6708b66" #Expires after 12 hours

# Function to load JSON file
def load_json_file(file_path):
    """
    Loads data from a JSON file.

    This function attempts to read a JSON file from the given file path and parse its contents into a dictionary. 
    If the file is not found or the contents cannot be decoded as JSON, an appropriate error message is printed and None is returned.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict or None: The dictionary containing the JSON data, or None if an error occurs.
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from '{file_path}'.")
        return None


#Function to replace single brace with double otherwise errors were raised in few-shot prompting
def replace_braces(data):
    """
    Replace every '{' with '{{' and '}' with '}}' in the given dictionary.

    Args:
    data (dict): The input dictionary with data.

    Returns:
    str: The string representation of the dictionary with replaced braces.
    """

    # Convert the dictionary to a string
    data_str = json.dumps(data)

    # Replace the braces
    data_str = data_str.replace('{', '{{').replace('}', '}}')

    return data_str

#Function to find the length of a billing cycle
def days_between_dates(date1, date2):
    """
    Calculates the number of days between two dates.

    This function takes two dates in the format 'YYYY-MM-DD', converts them to datetime objects, and calculates the difference in days between them.

    Args:
        date1 (str): The first date in 'YYYY-MM-DD' format.
        date2 (str): The second date in 'YYYY-MM-DD' format.

    Returns:
        int: The number of days between the two dates.
    """
    date_format = "%Y-%m-%d"
    
    # Convert string dates to datetime objects
    d1 = datetime.strptime(date1, date_format)
    d2 = datetime.strptime(date2, date_format)
    
    # Calculate the difference in days
    delta = d2 - d1
    return 1 + delta.days

#Function to fetch all regional holidays
def get_holidays(country_code, subdivision_code=None, start_year=2018, end_year=2025, exclude_observed=True, exclude_vacation=False, vacation_dates=None):
    """
    Retrieves a list of holidays for a specified country and date range.

    This function generates a list of holidays for the given country (and optionally a subdivision) between the specified start and end years. Holidays can be excluded based on observed status and vacation dates.

    Args:
        country_code (str): The country code for which to retrieve holidays.
        subdivision_code (str, optional): The subdivision code for the country (e.g., state or province).
        start_year (int, optional): The starting year for the holiday list. Defaults to 2018.
        end_year (int, optional): The ending year for the holiday list. Defaults to 2025.
        exclude_observed (bool, optional): Whether to exclude observed holidays. Defaults to True.
        exclude_vacation (bool, optional): Whether to exclude holidays that fall within specified vacation dates. Defaults to False.
        vacation_dates (list of str, optional): List of vacation dates in 'YYYY-MM-DD' format to exclude from holidays.

    Returns:
        list of dict: A list of dictionaries, each containing 'date' and 'name' of a holiday.
    """
    # Instantiate CountryHoliday with country_code and optional subdivision_code
    if subdivision_code:
        country_holidays = holidays.CountryHoliday(country_code, prov=subdivision_code, years=range(start_year, end_year + 1))
    else:
        country_holidays = holidays.CountryHoliday(country_code, years=range(start_year, end_year + 1))
    
    holiday_list = []
    
    if exclude_vacation and vacation_dates:
        vacation_dates_set = {datetime.strptime(date, '%Y-%m-%d').date() for date in vacation_dates}
    else:
        vacation_dates_set = set()
    
    for date, name in sorted(country_holidays.items()):
        # Check if the holiday should be excluded based on options
        if (exclude_observed and "observed" in name) or date in vacation_dates_set:
            continue
        
        # Append the holiday details to the list
        holiday_list.append({"date": date.strftime('%Y-%m-%d'), "name": name})
    
    return holiday_list


# Helper function to convert float values to integers in a JSON object
def convert_floats_to_ints(data):
    """
    Converts float values to integers in a JSON object.

    This helper function recursively traverses a JSON object and converts all float values to integers.

    Args:
        data (dict, list, float, or any): The JSON object to process.

    Returns:
        dict, list, int, or any: The processed JSON object with float values converted to integers.
    """
    if isinstance(data, dict):
        return {k: convert_floats_to_ints(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats_to_ints(item) for item in data]
    elif isinstance(data, float):
        return int(data)
    else:
        return data
    
# Function to transform itemizationDetailsList entries to simplified format
def transform_itemization_details(details):
    """
    Transforms itemization details list entries to a simplified format.

    This function takes a list of itemization details, each containing a category, usage, and cost, and transforms it into a dictionary where the keys are the categories and the values are lists containing the usage and cost as integers.

    Args:
        details (list of dict): A list of dictionaries, each containing 'category', 'usage', and 'cost'.

    Returns:
        dict: A dictionary with categories as keys and lists of [usage, cost] as values.
    """
    return {detail["category"]: [int(detail["usage"]), int(detail["cost"])] 
            for detail in details if detail["category"]}

#API call to fetch user's location
def fetch_location(uuid):
    """
    Fetches the user's location using an API call.

    This function makes an API call to fetch the location details of a user identified by the given UUID.

    Args:
        uuid (str): The unique identifier of the user.

    Returns:
        dict or None: The dictionary containing the user's location data if the 
        request is successful, or None if an error occurs.
    """
    api_url = f'https://naapi.bidgely.com/meta/users/{uuid}/homes/1?access_token={access_token}'

    try:
        # Make the request
        response = requests.get(api_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON data
            data = response.json()
            return data
        else:
            print(f"Failed to fetch data: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

    
#API call to fetch user's consumption data
def fetch_itemization_data(uuid):
    """
    Fetches the user's consumption data using an API call.

    This function makes an API call to fetch the consumption data of a user identified by the given UUID.
    
    Args:
        uuid (str): The unique identifier of the user.

    Returns:
        dict or None: The dictionary containing the user's consumption data if 
        the request is successful, or None if an error occurs.
    """
    api_url = f'https://naapi.bidgely.com/v2.0/dashboard/users/{uuid}/usage-chart-details?measurement-type=ELECTRIC&mode=year&start=0&end=1885314000&date-format=DATE_TIME&locale=en_US&next-bill-cycle=false&show-at-granularity=false&skip-ongoing-cycle=false&access_token={access_token}'
    
    try:
        # Make the request
        response = requests.get(api_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON data
            data = response.json()
            return data
        else:
            print(f"Failed to fetch data: {response.status_code}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

#API call to fetch user's vacation data
def fetch_vacation_data(uuid):
    """
    Fetches the user's vacation data using an API call.

    This function makes an API call to fetch the vacation data of a user identified by the given UUID.
    
    Args:
        uuid (str): The unique identifier of the user.

    Returns:
        dict or None: The dictionary containing the user's vacation data if 
        the request is successful, or None if an error occurs.
    """
    api_url = f'https://naapi.bidgely.com/v3.0/internal/users/{uuid}/homes/1/ELECTRIC/vacation?from=0&to=1885314000&access_token={access_token}'
    
    try:
        # Make the request
        response = requests.get(api_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON data
            data = response.json()
            return data
        else:
            print(f"Failed to fetch data: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

#Function to calculate the difference between two given billing cycles
def calculate_difference(cycle1, cycle2):
    """
    Calculates the differences between two billing cycles.

    This function takes two billing cycle dictionaries and calculates the differences for various keys including consumption, cost, number of days, number of holidays, number of vacation days, and temperature. 
    It also compares the electricity rates based on the ratio of consumption to cost, and calculates differences in itemization details if present.

    Args:
        cycle1 (dict): The first billing cycle data.
        cycle2 (dict): The second billing cycle data.

    Returns:
        dict: A dictionary containing the calculated differences.
    """
    differences = {}

    # Define the keys to compare
    keys_to_compare = ['consumption', 'cost', 'num_days', 'num_holidays', 'num_vacation', 'temperature']
    
    # Calculate differences for keys present in both cycles
    for key in keys_to_compare:
        if key in cycle1 and key in cycle2:
            try:
                value1 = cycle1.get(key)
                value2 = cycle2.get(key)
                differences[key] = round(value2 - value1, 1)
            except (TypeError, ValueError) as e:
                differences[key] = None

    # Calculate the 'rate_change' based on the ratio of consumption to cost
    if 'consumption' in cycle1 and 'cost' in cycle1 and 'consumption' in cycle2 and 'cost' in cycle2:
        try:
            value1 = round(cycle1['consumption'] / cycle1['cost'], 1)
            value2 = round(cycle2['consumption'] / cycle2['cost'], 1)
            
            if value2 - value1 >= 0.5:
                electricity_rates = 'lower in cycle2 and higher in cycle1'
            elif value2 - value1 <= -0.5:
                electricity_rates = 'higher in cycle2 and lower in cycle1'
            else:
                electricity_rates = 'same'
            
            differences['electricity_rates'] = electricity_rates
        except (TypeError, ZeroDivisionError) as e:
            differences['electricity_rates'] = None

    # Calculate differences for itemizationDetailsList
    itemization1 = cycle1.get('itemizationDetailsList', None)
    itemization2 = cycle2.get('itemizationDetailsList', None)
    itemization_differences = {}

    if itemization1 == "unavailable" and itemization2 == "unavailable":
        itemization_differences = "unavailable in both cycles"
    elif itemization1 == "unavailable":
        itemization_differences = "unavailable in cycle1"
    elif itemization2 == "unavailable":
        itemization_differences = "unavailable in cycle2"
    else:
        common_items = set(itemization1.keys()).intersection(set(itemization2.keys()))
        for item in sorted(common_items):
            try:
                value1 = itemization1.get(item)
                value2 = itemization2.get(item)
                itemization_differences[item] = [value2[0] - value1[0], value2[1] - value1[1]]
            except (TypeError, IndexError) as e:
                itemization_differences[item] = [None, None]

    if itemization_differences:
        differences['itemizationDetailsList'] = itemization_differences

    return differences


# Extract vacation dates from vacation json data
def extract_vacation_dates(data):
    """
    Extracts vacation dates from vacation JSON data.

    This function extracts unique vacation dates from the given vacation JSON data, converts Unix timestamps to dates, adjusts the timestamps, and returns the dates in a sorted list of 'YYYY-MM-DD' formatted strings.

    Args:
        data (dict): The vacation JSON data containing bill cycles and vacation timestamps.

    Returns:
        list of str: A sorted list of unique vacation dates in 'YYYY-MM-DD' format.
    """
    vacation_days = set()  # To store unique vacation days

    for cycle in data["payload"]["billCycles"]:
        # Check if vacation data is present
        if 'vacation' in cycle and cycle['vacation']:
            for i, vacation in enumerate(cycle['vacation']):
                # Convert Unix timestamp to date and adjust it
                timestamp = vacation["timeStamp"]
                if i == len(cycle['vacation']) - 1:
                    adjusted_timestamp = timestamp - (4 * 3600 + 1)
                else:
                    adjusted_timestamp = timestamp - (4 * 3600) #TODO-Make the 3600 and 4(hrs) as variable
                vacation_date = datetime.utcfromtimestamp(adjusted_timestamp).date()
                vacation_days.add(vacation_date)
    
    # Convert the set to a sorted list of strings in 'YYYY-MM-DD' format
    sorted_vacation_dates = sorted(date.strftime('%Y-%m-%d') for date in vacation_days)
    
    return sorted_vacation_dates
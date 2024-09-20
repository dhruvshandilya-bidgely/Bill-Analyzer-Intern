from tabulate import tabulate
import matplotlib.pyplot as plt
import io

#Function to plot a bar chart comparing two billing cycles
def plot_itemization_comparison(cycle1, cycle2):
    """
    Plots a comparison of itemization details between two billing cycles.

    This function extracts the itemization details from two billing cycles and plots a bar chart comparing the usage costs across different categories. 
    It also writes the total usage cost for each cycle and the values on top of each bar.

    Args:
        cycle1 (dict): The first billing cycle data containing itemization details.
        cycle2 (dict): The second billing cycle data containing itemization details.

    Returns:
        io.BytesIO: A buffer containing the saved plot in PNG format.
    """
    # Extract itemization details for each cycle
    categories = list(cycle1["itemizationDetailsList"].keys())
    values_cycle1 = [details[1] for details in cycle1["itemizationDetailsList"].values()]
    values_cycle2 = [details[1] for details in cycle2["itemizationDetailsList"].values()]

    # Calculate total usage cost for each cycle
    total_cost_cycle1 = cycle1["cost"]
    total_cost_cycle2 = cycle2["cost"]

    # Determine the maximum value for y-axis limit
    max_value = max(max(values_cycle1), max(values_cycle2))
    y_max = max_value * 1.3  # Increase y-axis limit by 30%

    # Plotting
    bar_width = 0.35
    index = range(len(categories))

    plt.figure(figsize=(12, 7))  # Increased figure size for better spacing
    bars1 = plt.bar(index, values_cycle1, bar_width, label='Cycle 1', color='b', alpha=0.6)
    bars2 = plt.bar([i + bar_width for i in index], values_cycle2, bar_width, label='Cycle 2', color='g', alpha=0.6)

    plt.xlabel('Categories')
    plt.ylabel('Usage Cost ($)')
    plt.title('Comparison Plot')
    plt.xticks([i + bar_width / 2 for i in index], categories, rotation=45)
    plt.legend()
    plt.ylim(0, y_max)  # Set y-axis limit

    # Adjust layout to make room for text annotations
    plt.tight_layout(rect=[0, 0, 1, 0.90])  # Increased top margin

    # Adding text for total usage cost
    plt.text(0.95, 0.95, f'Total Cost in Cycle 1: ${total_cost_cycle1}', horizontalalignment='right', verticalalignment='top', transform=plt.gca().transAxes, fontsize=10, bbox=dict(facecolor='white', alpha=0.5))
    plt.text(0.95, 0.90, f'Total Cost in Cycle 2: ${total_cost_cycle2}', horizontalalignment='right', verticalalignment='top', transform=plt.gca().transAxes, fontsize=10, bbox=dict(facecolor='white', alpha=0.5))

    # Adding values on top of each bar
    for i, (v1, v2) in enumerate(zip(values_cycle1, values_cycle2)):
        plt.text(i, v1 + 0.02 * y_max, f'${v1}', ha='center', va='bottom', fontsize=9)
        plt.text(i + bar_width, v2 + 0.02 * y_max, f'${v2}', ha='center', va='bottom', fontsize=9)

    # Save plot to BytesIO buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    return buffer

# Function to display billing cycles in a table
def display_billing_cycles(cycles):
    """
    Displays billing cycles in a table format.

    This function takes a list of billing cycles and displays their details in a formatted table. It includes columns for ID, start date, end date, consumption, usage cost, vacation days, rate plan, and itemization status.

    Args:
        cycles (list of dict): A list of billing cycle dictionaries.

    Returns:
        str: A formatted table as a string.
    """
    headers = [
        "ID",
        "Start Date",
        "End Date",
        "Consumption\n (in KWh)",
        "Usage Cost\n  (in $)",
        "Vacation Days",
        "Rate Plan",
        "Itemization"
    ]
    rows = []
    for i, cycle in enumerate(cycles):
        itemization_status = "Unavailable" if cycle.get("itemizationDetailsList") == "unavailable" else "Available"
        
        # Determine the Rate Plan based on touDetails and tierDetails
        if cycle['touDetails'] == "unavailable" and cycle['tierDetails'] == "unavailable":
            rate_plan = "Unavailable"
        elif cycle['touDetails'] == "unavailable":
            rate_plan = "Tier"
        else:
            rate_plan = "Tou"
        
        rows.append([
            i + 1,
            cycle["IntervalStartDate"],
            cycle["IntervalEndDate"],
            cycle['consumption'],
            cycle['cost'],
            cycle['num_vacation'],
            rate_plan,
            itemization_status
        ])

    # Print the table
    table = tabulate(rows, headers=headers, tablefmt="grid")
    return table